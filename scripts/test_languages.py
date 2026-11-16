"""Repository byte-composition evidence and its offline projections."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from unittest.mock import Mock
import signals
import update_signals
import build_site
import build_webmcplet_list
import plate_grid
import test_signal_site

REPO = 'example/openexample'
AT = '2026-11-16T00:00:00Z'
NOW = signals.timestamp(AT)

class LanguagesTests(unittest.TestCase):
    def collect(self, payload=None, previous=None, **kwargs):
        options = dict(now=NOW, providers=('languages',), token='test-token',
                       sleep=lambda _: None, fetch=Mock(return_value=(200, {'ETag': '"v1"'}, payload)))
        options.update(kwargs)
        return update_signals.collect([REPO], previous, **options)[0]

    def test_empty_success_and_unknown_are_distinct(self):
        doc = self.collect({})
        record = doc['repositories'][REPO]['languages']
        self.assertEqual(record['status'], 'available')
        self.assertEqual(record['last_good']['value'], {})
        self.assertIn('None detected', plate_grid.languages_box({'signals': {'languages': record}}))
        self.assertIn('Unknown', plate_grid.languages_box({}))
        failed = self.collect(fetch=Mock(return_value=(404, {}, None)))
        self.assertIsNone(failed['repositories'][REPO]['languages']['last_good'])

    def test_byte_counts_punctuation_validation_and_escaping(self):
        doc = self.collect({'C++': 300, 'C#': 200, 'HTML': 100, '<test>': 1})
        record = doc['repositories'][REPO]['languages']
        html = plate_grid.languages_box({'signals': {'languages': record}})
        for text in ('C++', 'C#', '300 bytes', '+1 more', '&lt;test&gt;', AT, '/languages'):
            self.assertIn(text, html)
        for bad in ([], None, {'C': True}, {'C': -1}, {'C': 0}, {'C': 1.2}, {'': 1}, {'C\n': 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): self.collect(bad)

    def test_cache_revalidation_failure_ttl_and_identity(self):
        doc = self.collect({'C++': 5, 'C#': 2})
        fetch = Mock(return_value=(304, {}, None))
        again = self.collect(previous=doc, now=NOW+timedelta(days=7), fetch=fetch)
        self.assertEqual(fetch.call_args.args[1]['If-None-Match'], '"v1"')
        self.assertEqual(again['repositories'][REPO]['languages']['last_good'], doc['repositories'][REPO]['languages']['last_good'])
        failed = self.collect(previous=doc, now=NOW+timedelta(days=8), fetch=Mock(return_value=(503, {}, None)))
        self.assertEqual(failed['repositories'][REPO]['languages']['status'], 'stale')
        early = Mock(side_effect=AssertionError('TTL'))
        self.collect(previous=doc, now=NOW+timedelta(days=6), fetch=early)
        doc['repositories'][REPO]['languages']['source_url'] += '/other'
        with self.assertRaises(ValueError): self.collect(previous=doc)

    def test_legacy_migration_validates_before_adding_missing_provider(self):
        doc = signals.empty_snapshot(AT)
        doc['provider_retry_after'].pop('languages')
        doc['repositories'][REPO] = {p: signals.empty_signal(REPO,p) for p in ('release','scorecard')}
        before = deepcopy(doc)
        new = self.collect({'Python': 100}, previous=doc)
        self.assertEqual(doc, before)
        self.assertEqual(new['repositories'][REPO]['languages']['status'], 'available')
        doc['repositories'][REPO]['release']['source_url'] = 'https://example.com'
        with self.assertRaises(ValueError): self.collect({}, previous=doc)

    def test_budget_rotation_and_github_shared_backoff(self):
        repos = ['a/project', 'b/project']
        opts = dict(now=NOW, providers=('languages',), token='x', sleep=lambda _:None,
                    languages_budget=1, fetch=Mock(return_value=(200, {}, {'C#': 2})))
        first, _ = update_signals.collect(repos, **opts)
        second, _ = update_signals.collect(repos, first, **opts)
        self.assertEqual(second['repositories']['b/project']['languages']['status'], 'available')
        fetch = Mock(return_value=(429, {'Retry-After':'7200'}, None))
        result, _ = update_signals.collect(repos, now=NOW, providers=('release','languages'), token='x', fetch=fetch, sleep=lambda _:None)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(result['provider_retry_after']['release'],result['provider_retry_after']['languages'])

    def test_catalog_index_static_record_and_webmcplet(self):
        fixture = test_signal_site.SignalSiteTests(); fixture.setUp()
        signal = self.collect({'C++': 300, 'C#': 200})['repositories'][REPO]['languages']
        signal['source_url'] = signals.source_url(fixture.repo,'languages')
        fixture.optional['collected_at'] = AT
        # Other providers age with this snapshot too.
        fixture.optional['repositories'][fixture.repo]['languages'] = signal
        for name, record in fixture.optional['repositories'][fixture.repo].items():
            record['status'] = signals.effective_status(record,name,AT)
        catalog = fixture.catalog(fixture.optional)
        project = next(p for p in catalog['projects'] if (p.get('github') or {}).get('repo') == fixture.repo)
        self.assertEqual(project['languages'], ['C++','C#'])
        index = build_site.search_index(catalog)
        self.assertEqual(next(p for p in index['projects'] if p['id']==project['id'])['languages'], ['C++','C#'])
        self.assertIn('300 bytes', plate_grid.render(project))
        item = build_webmcplet_list.item(project,'https://example.com/')
        self.assertEqual(item['fields']['languages'], ['C++','C#'])
        self.assertTrue(build_webmcplet_list.fields(catalog)['languages']['filter'])
        self.assertTrue(build_webmcplet_list.fields(catalog)['languages']['search'])
        self.assertLess(len(json.dumps(index)), len(json.dumps(catalog)))

    def test_full_population_compact_budget_and_lossless_counts(self):
        from pathlib import Path
        import gzip
        import build_catalog
        fixture = test_signal_site.SignalSiteTests(); fixture.setUp()
        optional = signals.load_optional(fixture.root / 'data/project_signals.json')
        catalog = build_catalog.build_catalog(fixture.source, fixture.metrics, fixture.alternatives, fixture.hn,
                                              optional_signals=optional)
        counts = {'C++': 1234567, 'JavaScript': 123456, 'C#': 12345, 'Shell': 1234, 'Python': 123}
        for project in catalog['projects']:
            github = project.get('github')
            if not github: continue
            signal = self.collect(counts)['repositories'][REPO]['languages']
            signal['source_url'] = signals.source_url(github['repo'], 'languages')
            project.setdefault('signals', {})['languages'] = signal
            project.update(languages=list(counts), language_status='available')
        original = deepcopy(catalog)
        published = build_site.published_catalog(catalog)
        self.assertEqual(catalog, original)
        self.assertLess(len(build_site.compact_json(published).encode()), len(catalog['projects'])*4096)
        # Metadata grows the index modestly; full byte breakdowns stay out of it.
        index = build_site.compact_json(build_site.search_index(catalog)).encode()
        self.assertNotIn(b'1234567', index)
        self.assertLess(len(gzip.compress(index)), 384*len(catalog['projects']))
        for project in published['projects']:
            if project.get('github'):
                record = project['signals']['languages']
                self.assertEqual(record['last_good']['value'], counts)
                self.assertEqual(record['checked_at'], AT)
                self.assertEqual(record['last_good']['fetched_at'], AT)
                self.assertNotIn('etag', record)
