"""Synthetic, offline queue regressions: never collect production evidence."""
from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import update_hn as hn

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def project(name='OpenThing'):
    return {'name': name, 'slug': name.lower(), 'readme_url': 'https://github.com/org/' + name.lower(),
            'repositories': ['org/' + name.lower()], 'domains': [], 'title_aliases': [name], 'queries': [name]}


def empty():
    return {'schema_version': 1, 'months': hn.window(NOW)[2], 'projects': []}


def page(url):
    q = parse_qs(urlsplit(url).query)
    return {'hits': [{'objectID': '123', 'created_at_i': int(hn.window(NOW)[0].timestamp()),
                     'title': q['query'][0], 'url': ''}], 'nbPages': 1, 'nbHits': 1}


class QueueTests(unittest.TestCase):
    def refresh(self, **kwargs):
        params = dict(now=NOW, projects=[project()], existing=empty(), metadata={}, getter=page)
        params.update(kwargs)
        return hn.refresh(**params)

    def test_catalog_deduplicates_and_never_guesses_aliases_or_hosts(self):
        source = '\n'.join(['| [OpenThing](https://github.com/org/openthing) | Tool. |'] * 2 + [
            '| [OpenOther](https://shared.example/projects/other) | Tool. |',
            '| [OpenThing](https://github.com/other/thing) | Different tool. |'])
        items = hn.catalog_projects(source, [])
        self.assertEqual(len(items), 3)
        self.assertEqual(len({p['slug'] for p in items}), 3)
        for p in items:
            self.assertEqual(p['title_aliases'], [])
            self.assertEqual(p['domains'], [])
            self.assertIsNone(hn.identity_reason({'title': p['name']}, p))
        website = items[1]
        self.assertTrue(hn.identity_reason({'url': 'https://shared.example/projects/other'}, website))
        for url in ['https://shared.example/projects/else', 'https://shared.example/projects/other/more',
                    'https://shared.example.evil/projects/other']:
            self.assertIsNone(hn.identity_reason({'url': url}, website))
        reviewed = project()
        self.assertEqual(hn.catalog_projects(source, [reviewed])[0], reviewed)

    def test_catalog_url_case_slash_port_and_fragment_stay_distinct(self):
        urls = ['https://example.com/Open', 'https://example.com/open',
                'https://example.com/tool/', 'https://example.com/tool',
                'https://example.com:8443/tool', 'https://example.com/tool#section']
        items = hn.catalog_projects('\n'.join('| [Open](%s) | Tool. |' % url for url in urls), [])
        self.assertEqual(len(items), len(urls))
        for i, p in enumerate(items):
            for j, url in enumerate(urls):
                self.assertEqual(bool(hn.identity_reason({'url': url}, p)), i == j)
        evidence = {'projects': [dict(items[0], eligible=True, search_url='https://hn.algolia.com/?q=Open')]}
        rendered = hn.decorate_readme('\n'.join('| [Open](%s) | Tool. |' % url for url in urls), evidence)
        self.assertEqual(rendered.count('HN:START'), 1)

    def test_partial_pages_resume_without_publishing_partial_counts(self):
        calls = []
        def paged(url):
            calls.append(url)
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            response = page(url)
            response['hits'] = [dict(response['hits'][0], objectID=str(100 + n * 100 + i))
                                for i in range(100 if n < 2 else 1)]
            response.update(nbPages=3, nbHits=201)
            return response
        first = self.refresh(getter=paged, request_budget=2)
        self.assertEqual(first['projects'], [])
        self.assertEqual(len(first['queue'][hn.canonical_url(project()['readme_url'])]['pending']), 2)
        second = self.refresh(existing=first, getter=paged, now=NOW + timedelta(days=1), request_budget=2)
        self.assertEqual(len(calls), 3)
        self.assertEqual(second['projects'][0]['story_count'], 201)
        self.assertEqual(second['budget']['requests_used'], 1)

    def test_failure_isolated_and_last_good_kept(self):
        first = self.refresh()
        second_project = project('OpenOther')
        def fail_one(url):
            if 'OpenThing' in url:
                raise OSError('offline')
            return page(url)
        result = self.refresh(existing=first, projects=[project(), second_project], now=NOW + timedelta(days=1), force=True, getter=fail_one)
        self.assertEqual(len(result['projects']), 2)
        record = result['queue'][hn.canonical_url(project()['readme_url'])]
        self.assertEqual(record['status'], 'unavailable')
        self.assertEqual(record['last_good'], first['queue'][hn.canonical_url(project()['readme_url'])]['last_good'])

    def test_rollover_withholds_old_window_but_retains_last_good(self):
        first = self.refresh()
        result = self.refresh(existing=first, now=datetime(2026, 11, 1, tzinfo=timezone.utc),
                              getter=lambda url: (_ for _ in ()).throw(OSError()))
        self.assertEqual(result['projects'], [])
        self.assertEqual(result['months'][-1], '2026-10')
        self.assertEqual(next(iter(result['queue'].values()))['last_good']['months'][-1], '2026-09')

    def test_changed_identity_invalidates_pending_and_last_good_view(self):
        first = self.refresh()
        changed = dict(project(), title_context_pattern='required')
        result = self.refresh(existing=first, projects=[changed], request_budget=0)
        self.assertEqual(result['projects'], [])
        self.assertTrue(next(iter(result['queue'].values()))['last_good'])

    def test_display_rename_reuses_observation_and_updates_only_current_view(self):
        import chart_observations as observations
        first = self.refresh()
        original = copy.deepcopy(first)
        archive = observations.add_hn(observations.empty(), first)
        before_archive = copy.deepcopy(archive)
        renamed = dict(project(), name='Open Thing Display Name')
        result = self.refresh(existing=first, projects=[renamed], now=NOW + timedelta(days=1),
                              getter=lambda url: self.fail('A display rename must not fetch'))
        old_good = next(iter(first['queue'].values()))['last_good']
        new_good = next(iter(result['queue'].values()))['last_good']
        self.assertEqual(new_good, old_good)
        self.assertEqual(first, original)
        self.assertNotEqual(hn.identity_key(renamed), old_good['identity_key'])
        self.assertTrue(hn.identity_matches(old_good, renamed))
        self.assertEqual(result['selection_report']['due_projects'], 0)
        self.assertEqual(result['selection_report']['attempted_projects'], 0)
        self.assertEqual(result['projects'], [dict(old_good['project'], name=renamed['name'])])
        self.assertIn(renamed['name'] + ': HN discussions / 2y', hn.svg(result['projects'][0], result))
        observations.add_hn(archive, result)
        observations.validate(archive)
        self.assertEqual(archive, before_archive)
        observation = next(iter(archive['observations'].values()))
        self.assertEqual(observations.materialize(archive, observation), old_good)

    def test_legacy_snapshot_rename_preserves_original_observation_without_redating(self):
        first = self.refresh()
        legacy = {'schema_version': 1, 'months': first['months'], 'projects': first['projects'],
                  'refreshed_utc_date': NOW.date().isoformat()}
        renamed = dict(project(), name='Open Thing')
        result = self.refresh(existing=legacy, projects=[renamed], now=NOW + timedelta(days=1),
                              getter=lambda url: self.fail('A display rename must not fetch'))
        good = next(iter(result['queue'].values()))['last_good']
        self.assertEqual(good['project'], first['projects'][0])
        self.assertEqual(good['identity_key'], hn.identity_key(project()))
        self.assertNotIn('collected_at', good)
        self.assertEqual(result['projects'][0]['name'], renamed['name'])

    def test_rename_does_not_reuse_any_changed_matching_or_provenance_fields(self):
        first = self.refresh()
        changes = {
            'queries': ['different discovery query'],
            'title_aliases': ['AnotherThing'],
            'domains': ['another.example'],
            'repositories': ['another/project'],
            'exact_urls': ['https://example.org/exact'],
            'excluded_repositories': ['unrelated/project'],
            'title_context_pattern': 'required',
            'other_project_pattern': 'unrelated',
            'identity_sources': ['https://example.org/review'],
            'scope_note': 'A different reviewed scope',
            'slug': 'another-asset',
            'catalog_aliases': [{'name': 'AnotherThing'}],
            'future_identity_revision': 'review-2',
        }
        good = next(iter(first['queue'].values()))['last_good']
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = dict(project(), name='Open Thing', **{field: value})
                self.assertFalse(hn.identity_matches(good, changed))
                result = self.refresh(existing=first, projects=[changed], request_budget=0)
                self.assertEqual(result['projects'], [])
                self.assertEqual(next(iter(result['queue'].values()))['last_good'], good)

    def test_display_compatibility_preserves_json_revision_types(self):
        for revision in [1, {'nested':[1]}]:
            original = dict(project(), identity_revision=revision)
            good = {'project':original, 'identity_key':hn.identity_key(original)}
            for replacement in ([True, 1.0] if revision == 1 else [{'nested':[True]}, {'nested':[1.0]}]):
                current = dict(original, name='Renamed', identity_revision=replacement)
                self.assertNotEqual(hn.identity_key(original), hn.identity_key(current))
                self.assertFalse(hn.identity_matches(good,current))
                record = {'last_good':good, 'pending_identity_key':good['identity_key']}
                self.assertFalse(hn.pending_identity_matches(record,current))

    def test_display_compatibility_cannot_hide_corrupt_original_fingerprint(self):
        first = self.refresh()
        broken = copy.deepcopy(first)
        good = next(iter(broken['queue'].values()))['last_good']
        good['project']['name'] = 'Tampered Original Name'
        renamed = dict(project(), name='Current Display Name')
        self.assertFalse(hn.identity_matches(good, renamed))
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.refresh(existing=broken, projects=[renamed], request_budget=0)

    def test_repeated_display_renames_resume_proven_pending_pages(self):
        first = self.refresh()
        original_good = copy.deepcopy(next(iter(first['queue'].values()))['last_good'])
        calls = []
        def paged(url):
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            calls.append(n)
            response = page(url)
            response['hits'] = [dict(response['hits'][0], objectID=str(100 + n * 100 + i))
                                for i in range(100 if n < 2 else 1)]
            response.update(nbPages=3, nbHits=201)
            return response
        partial = self.refresh(existing=first, now=NOW + timedelta(days=1), force=True,
                               getter=paged, request_budget=1)
        renamed = dict(project(), name='Open Thing')
        partial = self.refresh(existing=partial, projects=[renamed], now=NOW + timedelta(days=2),
                               getter=paged, request_budget=1)
        record = next(iter(partial['queue'].values()))
        self.assertEqual(record['last_good'], original_good)
        self.assertEqual(record['pending_identity_key'], original_good['identity_key'])
        self.assertEqual(partial['projects'][0]['name'], renamed['name'])
        renamed_again = dict(renamed, name='Open Thing Display')
        result = self.refresh(existing=partial, projects=[renamed_again], now=NOW + timedelta(days=3),
                              getter=paged, request_budget=1)
        self.assertEqual(calls, [0, 1, 2])
        self.assertEqual(result['projects'][0]['story_count'], 201)
        self.assertEqual(result['projects'][0]['name'], renamed_again['name'])
        self.assertEqual(result['budget']['lane_requests']['continuation'], 1)

    def test_unprovable_or_changed_pending_identity_restarts_safely(self):
        calls = []
        def paged(url):
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            calls.append(n)
            response = page(url)
            response['hits'] = [dict(response['hits'][0], objectID=str(100 + n * 100 + i))
                                for i in range(100 if n == 0 else 1)]
            response.update(nbPages=2, nbHits=101)
            return response
        # A first, incomplete legacy attempt has no complete identity payload to
        # prove that its opaque hash differs only by the name.
        partial_only = self.refresh(getter=paged, request_budget=1)
        # A completed payload can prove the old identity, but never a genuinely
        # changed matching rule or a different monthly window.
        completed = self.refresh()
        partial_good = self.refresh(existing=completed, now=NOW + timedelta(days=1),
                                    force=True, getter=paged, request_budget=1)
        cases = [
            (partial_only, dict(project(), name='Renamed'), NOW + timedelta(days=1)),
            (partial_good, dict(project(), name='Renamed', title_context_pattern='required'), NOW + timedelta(days=2)),
            (partial_good, dict(project(), name='Renamed'), NOW.replace(month=11)),
        ]
        for previous, changed, now in cases:
            with self.subTest(name=changed['name'], context=changed.get('title_context_pattern'), month=now.month):
                calls.clear()
                result = self.refresh(existing=previous, projects=[changed], now=now,
                                      getter=paged, request_budget=1)
                self.assertEqual(calls, [0])
                self.assertEqual(result['projects'], [])
                record = next(iter(result['queue'].values()))
                self.assertEqual(record['pending_identity_key'], hn.identity_key(changed))

    def test_budget_persists_same_day_and_invocation_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budget.json'
            first = self.refresh(request_budget=1, invocation_budget_file=path)
            for snapshot in (first, empty()):
                with patch.object(hn, 'fetch_page', side_effect=AssertionError('network')):
                    result = self.refresh(existing=snapshot, getter=None, force=True, request_budget=1,
                                          invocation_budget_file=path)
                self.assertEqual(result['selection_report']['attempted_projects'], 0)

    def test_corrupt_or_unwritable_invocation_budget_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budget.json'
            path.write_text(json.dumps({'utc_date': '2026-10-14', 'requests_used': -10, 'limit': 80, 'paused': False}))
            with self.assertRaises(ValueError):
                self.refresh(invocation_budget_file=path)
            path.unlink()
            with patch.object(hn, 'write_evidence', side_effect=OSError('read only')):
                with self.assertRaises(RuntimeError):
                    self.refresh(invocation_budget_file=path)

    def test_rate_limit_pauses_later_projects_and_same_day_runs(self):
        def limited(url):
            raise HTTPError(url, 429, 'rate limited', {}, None)
        result = self.refresh(projects=[project(), project('OpenOther')], getter=limited)
        self.assertEqual(result['selection_report']['attempted_projects'], 1)
        self.assertTrue(result['budget']['paused'])
        again = self.refresh(existing=result, force=True)
        self.assertEqual(again['selection_report']['attempted_projects'], 0)

    def test_unseen_high_stars_then_oldest_attempt(self):
        projects = [project('OpenA'), project('OpenB'), project('OpenC')]
        metadata = {'repositories': {'org/openb': {'stargazers_count': 500}}}
        first = self.refresh(projects=projects, metadata=metadata, max_projects=1)
        self.assertEqual(first['projects'][0]['name'], 'OpenB')
        second = self.refresh(projects=projects, metadata=metadata, existing=first, max_projects=1, now=NOW + timedelta(days=1), force=True)
        self.assertEqual(set(p['name'] for p in second['projects']), {'OpenA', 'OpenB'})
        third = self.refresh(projects=projects, metadata=metadata, existing=second, max_projects=1, now=NOW + timedelta(days=2), force=True)
        self.assertEqual(len(third['projects']), 3)

    def test_corrupt_local_queue_fails_before_network(self):
        first = self.refresh()
        next(iter(first['queue'].values()))['pending'] = {'https://evil.example': {}}
        with self.assertRaises(ValueError):
            self.refresh(existing=first)

    def test_invalid_upstream_preserves_good_and_continues(self):
        first = self.refresh()
        result = self.refresh(existing=first, now=NOW + timedelta(days=1), force=True, getter=lambda url: {'hits': [], 'nbPages': 'bad', 'nbHits': 0})
        self.assertEqual(result['projects'], first['projects'])
        self.assertEqual(next(iter(result['queue'].values()))['status'], 'unavailable')

    def test_removed_catalog_identity_removed_from_cache(self):
        first = self.refresh()
        result = self.refresh(existing=first, projects=[])
        self.assertEqual(result['projects'], [])
        self.assertEqual(result['queue'], {})

    def test_browse_link_uses_broad_alias_with_same_window(self):
        p = dict(project(), domains=['openthing.org'], title_context_pattern='SST')
        result = self.refresh(projects=[p])
        query = parse_qs(urlsplit(result['projects'][0]['search_url']).query)
        self.assertEqual(query['q'], ['OpenThing'])
        self.assertEqual(query['dateEnd'], [str(int(hn.window(NOW)[1].timestamp()) - 1)])

    def test_inconsistent_pagination_cannot_replace_good(self):
        first = self.refresh()
        result = self.refresh(existing=first, now=NOW + timedelta(days=1), force=True,
                              getter=lambda url: {'hits': [], 'nbPages': 0, 'nbHits': 100})
        self.assertEqual(result['projects'], first['projects'])
        self.assertEqual(next(iter(result['queue'].values()))['status'], 'unavailable')

    def test_corrupt_last_good_counts_and_fingerprint_fail(self):
        first = self.refresh()
        for field, value in [('story_count', 999), ('scope_note', 'changed identity')]:
            broken = copy.deepcopy(first)
            next(iter(broken['queue'].values()))['last_good']['project'][field] = value
            with self.assertRaises(ValueError):
                self.refresh(existing=broken, request_budget=0)

    def test_changed_pagination_discards_old_pages_for_recovery(self):
        calls = []
        def changing(url):
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            calls.append(n)
            count = 101 if n == 0 else 102
            result = page(url)
            result['hits'] = [dict(result['hits'][0], objectID=str(100 + n * 100 + i))
                              for i in range(100 if n == 0 else 2)]
            result.update(nbHits=count, nbPages=2)
            return result
        result = self.refresh(getter=changing)
        self.assertEqual(result['projects'], [])
        self.assertEqual(next(iter(result['queue'].values()))['pending'], {})
        recovered = self.refresh(existing=result, now=NOW + timedelta(days=1))
        self.assertEqual(len(recovered['projects']), 1)

    def test_duplicate_page_and_outside_interval_preserve_good(self):
        first = self.refresh()
        def duplicate(url):
            result = page(url)
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            result['hits'] = [dict(result['hits'][0], objectID=str(100 + i))
                              for i in range(100 if n == 0 else 1)]
            result.update(nbHits=101, nbPages=2)
            return result
        def outside(url):
            result = page(url)
            result['hits'][0]['created_at_i'] = int(hn.window(NOW)[1].timestamp())
            return result
        for getter in (duplicate, outside):
            result = self.refresh(existing=first, now=NOW + timedelta(days=1), force=True, getter=getter)
            self.assertEqual(result['projects'], first['projects'])
            self.assertEqual(next(iter(result['queue'].values()))['status'], 'unavailable')

    def test_partial_work_resumes_before_unseen_catalog(self):
        def paged(url):
            result = page(url)
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            result['hits'] = [dict(result['hits'][0], objectID=str(100 + n * 100 + i))
                              for i in range(100 if n == 0 else 1)]
            result.update(nbHits=101, nbPages=2)
            return result
        first = self.refresh(getter=paged, request_budget=1)
        second = self.refresh(existing=first, projects=[project(), project('OpenA')],
                              getter=paged, now=NOW + timedelta(days=1), request_budget=1)
        self.assertEqual(second['projects'][0]['name'], 'OpenThing')

    def test_schema_two_is_readable_by_catalog(self):
        import build_catalog
        result = self.refresh()
        self.assertIn(hn.canonical_url(project()['readme_url']), build_catalog._hn_evidence(result))

    def test_main_checkpoints_without_rendering(self):
        result = self.refresh()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            with patch.object(hn, 'EVIDENCE_PATH', path), patch.object(hn, 'refresh', return_value=result), \
                 patch.object(hn, 'render', side_effect=AssertionError('render')), patch('sys.argv', ['update_hn.py']):
                hn.main()
            self.assertEqual(json.loads(path.read_text()), result)


if __name__ == '__main__':
    unittest.main()
