"""Reviewed alias identity, evidence, export and HN opt-in contracts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import build_catalog
import build_observatory
import project_aliases as aliases
import test_build_catalog as catalog_tests


class AliasTests(unittest.TestCase):
    # Reuse the small catalog fixture without inheriting its suite of tests.
    setUp = catalog_tests.CatalogTests.setUp
    build = catalog_tests.CatalogTests.build
    def alias_document(self):
        return {'schema_version': 1, 'projects': [{
            'project_url': 'https://github.com/example/open',
            'aliases': [{'name': 'Open Expanded', 'source_url': 'https://example.org/name'},
                        {'name': 'OE', 'source_url': 'https://example.org/name', 'ambiguous': True}],
            'checked_at': '2026-10-16', 'reviewed_by': 'Test reviewer'}]}

    def test_optional_aliases_preserve_legacy_shape_and_stable_identity(self):
        original = self.build()['projects'][0]
        self.assertNotIn('aliases', original)
        doc = self.alias_document(); before = deepcopy(doc)
        result = self.build(self.source.replace('[Open]', '[Renamed]'), aliases=doc)['projects'][0]
        self.assertEqual(result['id'], original['id'])
        self.assertEqual(result['url'], original['url'])
        self.assertEqual(result['aliases'], doc['projects'][0]['aliases'])
        self.assertEqual(result['alias_review']['checked_at'], '2026-10-16')
        result['aliases'][0]['name'] = 'Changed output'
        self.assertEqual(doc, before)
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(aliases.load_optional(Path(directory) / 'absent.json'))

    def test_malformed_or_unlisted_alias_evidence_fails_closed(self):
        mutations = [
            lambda d: d.update(schema_version=2),
            lambda d: d['projects'].append(deepcopy(d['projects'][0])),
            lambda d: d['projects'][0].update(project_url='https://example.org/unlisted'),
            lambda d: d['projects'][0].update(checked_at='2026-02-30'),
            lambda d: d['projects'][0].update(reviewed_by=''),
            lambda d: d['projects'][0].update(aliases=[]),
            lambda d: d['projects'][0]['aliases'].append({'name':'OPEN EXPANDED', 'source_url':'https://example.org/name'}),
            lambda d: d['projects'][0]['aliases'][0].update(name='<script>'),
            lambda d: d['projects'][0]['aliases'][0].update(name='bad\nname'),
            lambda d: d['projects'][0]['aliases'][0].update(source_url='http://example.org/name'),
            lambda d: d['projects'][0]['aliases'][0].update(ambiguous='yes'),
            lambda d: d['projects'][0]['aliases'][0].update(unreviewed=True),
        ]
        for mutate in mutations:
            doc = self.alias_document(); mutate(doc)
            with self.subTest(doc=doc), self.assertRaises(ValueError): self.build(aliases=doc)

    def test_aliases_do_not_change_observatory_display_name_groups(self):
        source = self.source + '| [OE](https://example.org/another) | A different tool. |\n'
        without = self.build(source)
        with_aliases = self.build(source, aliases=self.alias_document())
        self.assertEqual(build_observatory.project_index(without), build_observatory.project_index(with_aliases))

    def test_crosslists_and_shared_aliases_never_merge_distinct_identities(self):
        source = self.source + '## Another category\n' + self.row + '| [Different](https://example.org/another) | Tool. |\n'
        doc = self.alias_document()
        other = deepcopy(doc['projects'][0]); other['project_url'] = 'https://example.org/another'
        doc['projects'].append(other)
        result = self.build(source, aliases=doc)
        self.assertEqual(len(result['projects']), 2)
        self.assertEqual(result['category_memberships'], 3)
        self.assertEqual(len({p['id'] for p in result['projects']}), 2)
        self.assertEqual(result['projects'][0]['aliases'], result['projects'][1]['aliases'])

    def test_hn_reuse_is_explicit_and_ambiguous_names_require_context(self):
        record = self.alias_document()['projects'][0]
        self.assertEqual(aliases.hn_rules({}, record), [])
        refs = {'catalog_aliases': [{'name': 'Open Expanded'}]}
        self.assertEqual(aliases.hn_rules(refs, record), [{'name': 'Open Expanded', 'context_pattern': None,
            'source_url':'https://example.org/name', 'checked_at':'2026-10-16', 'reviewed_by':'Test reviewer'}])
        for refs in [[{'name':'OE'}], [{'name':'Missing'}], [{'name':'OE','context_pattern':'.*'}],
                     [{'name':'OE','context_pattern':'['}], [{'name':'Open Expanded'},{'name':'Open Expanded'}]]:
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                aliases.hn_rules({'catalog_aliases':refs}, record)
        self.assertEqual(aliases.hn_rules({'catalog_aliases':[{'name':'OE','context_pattern':'video recording'}]},record),
                         [{'name':'OE','context_pattern':'video recording', 'source_url':'https://example.org/name',
                           'checked_at':'2026-10-16', 'reviewed_by':'Test reviewer'}])

    def test_obs_seed_has_evidenced_names_and_keeps_canonical_identity(self):
        root = Path(__file__).resolve().parents[1]
        document = aliases.load_optional(root / aliases.PATH)
        records = aliases.validate(document, build_catalog.canonical_url)
        url = 'https://github.com/obsproject/obs-studio'
        self.assertEqual(set(records), {url})
        self.assertEqual([a['name'] for a in records[url]['aliases']], ['OBS Studio', 'Open Broadcaster Software', 'OBS'])
        self.assertNotIn('Open Broadcast Studio', json.dumps(document))
        self.assertIn('| [OBS Studio](' + url + ') |', (root / 'README.source.md').read_text())
        self.assertEqual(hashlib.sha256(url.encode()).hexdigest()[:16], '0e1c34b3f948e903')



class HNAliasReuseTests(unittest.TestCase):
    def setUp(self):
        import update_hn
        self.hn = update_hn
        self.url = 'https://github.com/obsproject/obs-studio'
        self.source = '| [OBS Studio](' + self.url + ') | Recording. |\n'
        self.evidence = {'schema_version':1, 'projects':[{'project_url':self.url,
            'aliases':[{'name':'OBS Studio','source_url':'https://obsproject.com/'},
                       {'name':'Open Broadcaster Software','source_url':'https://obsproject.com/'},
                       {'name':'OBS','source_url':'https://obsproject.com/','ambiguous':True}],
            'checked_at':'2026-10-16', 'reviewed_by':'Test reviewer'}]}
        self.base = self.hn.catalog_projects(self.source, [])[0]

    def test_catalog_aliases_never_enter_unreviewed_hn_matching(self):
        self.assertEqual(self.hn.catalog_projects(self.source, [], self.evidence)[0], self.base)
        self.assertIsNone(self.hn.identity_reason({'title':'OBS Studio release','url':'https://example.org/story'}, self.base))

    def test_only_referenced_aliases_expand_queries_and_matching(self):
        reviewed = dict(self.base, catalog_aliases=[{'name':'Open Broadcaster Software'}])
        before = deepcopy(reviewed)
        identity = self.hn.catalog_projects(self.source, [reviewed], self.evidence)[0]
        self.assertEqual(reviewed, before)
        self.assertEqual(identity['queries'], self.base['queries'] + ['Open Broadcaster Software'])
        self.assertIsNotNone(self.hn.identity_reason({'title':'Open Broadcaster Software release','url':'https://example.org/story'},identity))
        self.assertIsNone(self.hn.identity_reason({'title':'OBS release','url':'https://example.org/story'},identity))
        self.assertIsNone(self.hn.identity_reason({'title':'OBS Studio release','url':'https://example.org/story'},identity))
        self.assertNotEqual(self.hn.identity_key(self.base), self.hn.identity_key(identity))

    def test_ambiguous_obs_requires_recording_context_and_resolved_rule_changes_hash(self):
        reviewed = dict(self.base, catalog_aliases=[{'name':'OBS', 'context_pattern':r'\b(?:streaming|screen recording)\b'}])
        identity = self.hn.catalog_projects(self.source,[reviewed],self.evidence)[0]
        for title in ['OBS releases', 'Open Build Service (OBS) release', 'OBS for Linux builds', 'Jobs for screen recording']:
            self.assertIsNone(self.hn.identity_reason({'title':title, 'url':'https://example.org/story'},identity))
        self.assertIsNotNone(self.hn.identity_reason({'title':'OBS screen recording release', 'url':'https://example.org/story'},identity))
        reviewed['catalog_aliases'][0]['context_pattern'] = r'\bscreen recording\b'
        changed = self.hn.catalog_projects(self.source,[reviewed],self.evidence)[0]
        self.assertNotEqual(self.hn.identity_key(identity), self.hn.identity_key(changed))
        reviewed['catalog_aliases'][0].pop('context_pattern')
        with self.assertRaisesRegex(ValueError,'requires reviewed context'):
            self.hn.catalog_projects(self.source,[reviewed],self.evidence)

    def test_resolved_hn_rule_retains_provenance_and_rejects_changed_review(self):
        reviewed = dict(self.base, catalog_aliases=[{'name':'Open Broadcaster Software'}])
        original = self.hn.catalog_projects(self.source,[reviewed],self.evidence)[0]
        good = {'project':original, 'identity_key':self.hn.identity_key(original)}
        rule = original['catalog_title_aliases'][0]
        self.assertEqual({key:rule[key] for key in ('source_url','checked_at','reviewed_by')},
                         {'source_url':'https://obsproject.com/','checked_at':'2026-10-16','reviewed_by':'Test reviewer'})
        for field, value in [('source_url','https://obsproject.com/help'),
                             ('checked_at','2026-10-17'), ('reviewed_by','Another reviewer')]:
            changed = deepcopy(self.evidence)
            target = changed['projects'][0]['aliases'][1] if field == 'source_url' else changed['projects'][0]
            target[field] = value
            current = self.hn.catalog_projects(self.source,[reviewed],changed)[0]
            self.assertNotEqual(self.hn.identity_key(current),self.hn.identity_key(original))
            self.assertFalse(self.hn.identity_matches(good,current))
        search_only = deepcopy(self.evidence)
        search_only['projects'][0]['aliases'][2]['source_url'] = 'https://obsproject.com/help'
        self.assertEqual(self.hn.catalog_projects(self.source,[reviewed],search_only)[0],original)

    def test_production_obs_rename_keeps_original_url_only_observation(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'README.source.md').read_text()
        identities = self.hn.catalog_projects(source,json.loads((root / 'data/hn_projects.json').read_text())['projects'],
                                             aliases.load_optional(root / aliases.PATH))
        current = next(p for p in identities if p['readme_url'] == self.url)
        cached = json.loads((root / 'data/hn_evidence.json').read_text())['queue'][self.url]['last_good']
        self.assertEqual(current['name'],'OBS Studio')
        self.assertEqual(current['title_aliases'],[])
        self.assertNotIn('catalog_title_aliases',current)
        self.assertTrue(self.hn.identity_matches(cached,current))
        self.assertEqual(cached['project']['story_count'], len(cached['project']['stories']))


class AliasRenderTests(unittest.TestCase):
    def test_display_projection_changes_only_current_labels(self):
        import render_readme
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root / 'data/hn_evidence.json').read_text())
        before = deepcopy(evidence)
        display = render_readme.display_hn_evidence((root / 'README.source.md').read_text(), evidence)
        url = 'https://github.com/obsproject/obs-studio'
        current = next(p for p in display['projects'] if p['readme_url'] == url)
        original = next(p for p in evidence['projects'] if p['readme_url'] == url)
        self.assertEqual(current, dict(original, name='OBS Studio'))
        self.assertEqual(evidence, before)
        self.assertEqual(display['queue'], evidence['queue'])
        self.assertEqual(current['story_count'], original['story_count'])
        self.assertEqual(display['shared_monthly_maximum'], evidence['shared_monthly_maximum'])
