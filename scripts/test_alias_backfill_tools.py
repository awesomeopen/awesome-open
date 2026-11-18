"""Offline fixtures for alias rotation, source discovery and stop boundaries."""
import base64
from datetime import date
import hashlib
import json
import socket
import unittest
from unittest.mock import patch

import select_alias_backfill as planner
import resolve_alias_source as source


def project(n):
    url = f'https://github.com/example/open{n}'
    return {'id': hashlib.sha256(url.encode()).hexdigest(), 'url': url, 'name': f'Open{n}'}


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.projects = sorted([project(n) for n in range(25)], key=lambda p: p['id'])
        self.ids = [p['id'] for p in self.projects]

    def plan(self, projects=None, **kwargs):
        return planner.plan_batch({'projects': self.projects if projects is None else projects},
                                  kwargs.pop('aliases', None), day='2026-11-18', slot=1, **kwargs)

    def test_insertion_points_and_wrap(self):
        for cursor in [self.ids[0], self.ids[12], self.ids[-1], 'f' * 64, '0' * 64]:
            expected = [x for x in self.ids if x > cursor] + [x for x in self.ids if x <= cursor]
            self.assertEqual([p['id'] for p in self.plan(after=cursor)['entries']], expected[:10])
        removed = self.ids[12]
        plan = self.plan([p for p in self.projects if p['id'] != removed], after=removed)
        self.assertEqual(plan['entries'][0]['id'], self.ids[13])

    def test_empty_small_deduplicated(self):
        self.assertEqual(self.plan([])['entries'], [])
        plan = self.plan(self.projects[:3] * 2, after=self.ids[1])
        self.assertEqual(len(plan['entries']), 3)
        self.assertEqual(len({p['id'] for p in plan['entries']}), 3)

    def test_formula_all_slots_and_growth(self):
        day = '2026-11-18'
        for slot in range(3):
            for size in (3, 25):
                plan = planner.plan_batch({'projects': self.projects[:size]}, None, day=day, slot=slot)
                offset = ((3 * (date.fromisoformat(day) - date(1970, 1, 1)).days + slot) * 10) % size
                self.assertEqual(plan['entries'][0]['id'], self.ids[offset])

    def test_growth_after_preserved_cursor(self):
        initial = self.projects[:5] + self.projects[6:]
        old = self.plan(initial, after=self.ids[4])
        grown = self.plan(after=self.ids[4])
        self.assertEqual(old['entries'][0]['id'], self.ids[6])
        self.assertEqual(grown['entries'][0]['id'], self.ids[5])
        self.assertEqual(grown['cursor'], self.ids[4])

    def test_existing_and_active_exclusions(self):
        alias = {'schema_version': 1, 'projects': [{'project_url': self.projects[0]['url'],
                 'aliases': [{'name': 'Alias', 'source_url': 'https://example.org/docs'}],
                 'checked_at': '2026-11-18', 'reviewed_by': 'Junge (AI)'}]}
        plan = self.plan(after='0' * 64, aliases=alias, excluded=[self.ids[1]])
        self.assertEqual(plan['entries'][0]['id'], self.ids[2])
        self.assertEqual(plan['existing_ids'], [self.ids[0]])
        self.assertEqual(plan['excluded_ids'], [self.ids[1]])

    def test_plan_and_interrupted_checkpoint(self):
        plan = self.plan(after=self.ids[4])
        self.assertEqual(plan['cursor'], self.ids[4])
        self.assertEqual(planner.checkpoint(plan, [])['cursor'], self.ids[4])
        outcomes = [{'id': p['id'], 'outcome': status, 'reason': 'fixture', 'prepared': {'kept': True}}
                    for p, status in zip(plan['entries'], ['unsupported', 'unresolved', 'proposed'])]
        report = planner.checkpoint(plan, outcomes)
        self.assertEqual(report['cursor'], self.ids[7])
        self.assertEqual(len(report['unresearched_ids']), 7)
        self.assertEqual(report['considered'][2]['prepared'], {'kept': True})
        with self.assertRaises(ValueError):
            planner.checkpoint(plan, outcomes[1:])

    def test_later_sweep_retries_and_boundaries(self):
        plan = self.plan(self.projects[:3], after=self.ids[1])
        outcomes = [{'id': p['id'], 'outcome': 'unsupported', 'reason': 'no evidence'} for p in plan['entries']]
        report = planner.checkpoint(plan, outcomes)
        self.assertEqual(report['sweep_boundaries'][0]['before_id'], self.ids[0])
        self.assertFalse(report['complete_sweep'])
        again = self.plan(self.projects[:3], after=report['cursor'])
        self.assertEqual(again['entries'], plan['entries'])

    def test_targeted_revisit_keeps_cursor_and_cap(self):
        plan = self.plan(after=self.ids[10], revisit={self.ids[1]: 'https://example.org/new-evidence'})
        self.assertEqual(len(plan['entries']), 10)
        first = {'id': self.ids[1], 'outcome': 'reviewed', 'reason': 'new official evidence'}
        self.assertEqual(planner.checkpoint(plan, [first])['cursor'], self.ids[10])
        self.assertEqual(len({p['id'] for p in plan['entries']}), 10)
        with self.assertRaises(ValueError):
            self.plan(limit=11)
        with self.assertRaises(ValueError):
            self.plan(after='short')


class SourceTests(unittest.TestCase):
    def fixture(self, name='TwilightDuck/OpenQuill', branch='develop', path='README', redirect=False):
        metadata = {'full_name': name, 'default_branch': branch, 'id': 1413392799}
        readme = {'path': path, 'encoding': 'base64',
                  'content': base64.b64encode(b'Open Quill, formerly Open Whisper and Wisper Flow.').decode(),
                  'html_url': f'https://github.com/{name}/blob/{branch}/{path}'}
        responses = [(200, {}, json.dumps(metadata).encode()), (200, {}, json.dumps(readme).encode())]
        if redirect:
            responses.insert(0, (301, {'Location': 'https://api.github.com/repositories/1413392799'}, b''))
        calls = []
        def fetch(url):
            calls.append(url)
            return responses.pop(0)
        return source.Reader(fetch, clock=lambda: '2026-11-18T00:00:00Z'), calls

    def test_real_filename_branch_and_rename(self):
        reader, calls = self.fixture(redirect=True)
        result = source.resolve('https://github.com/TwilightDuck/OpenWhisper', reader)
        self.assertEqual(result['status'], 'read')
        self.assertEqual((result['branch'], result['path']), ('develop', 'README'))
        self.assertTrue(calls[-1].endswith('/OpenQuill/readme?ref=develop'))
        self.assertEqual(result['canonical_url'], 'https://github.com/TwilightDuck/OpenWhisper')
        self.assertFalse(result['identity_verified'])
        self.assertNotIn('aliases', result)
        self.assertEqual(result['events'][0]['http_status'], 301)
        self.assertEqual(result['events'][0]['method'], 'GET')

    def test_distinct_identity_and_no_automatic_naming(self):
        reader, _ = self.fixture(name='OpenWhispr/openwhispr')
        result = source.resolve('https://github.com/OpenWhispr/openwhispr', reader)
        self.assertNotEqual(result['canonical_url'], 'https://github.com/TwilightDuck/OpenWhisper')
        # Even explicit words in text require operator review. Commercial Wispr
        # Flow cannot be inferred from this fixture's former Wisper Flow name.
        self.assertFalse(result['identity_verified'])
        self.assertNotIn('aliases', result)

    def test_connector_fallback_and_hard_stops(self):
        reader, calls = self.fixture()
        result = source.resolve('https://github.com/TwilightDuck/OpenWhisper', reader, prior_error='connector')
        self.assertEqual(result['events'][0]['category'], 'connector')
        self.assertIsNone(result['events'][0]['http_status'])
        self.assertEqual(result['status'], 'read')
        for category in ('authentication', 'denial', 'quota'):
            reader, calls = self.fixture()
            result = source.resolve('https://github.com/TwilightDuck/OpenWhisper', reader, prior_error=category)
            self.assertEqual((result['status'], calls), ('blocked', []))

    def test_status_categories_and_no_fallback(self):
        for status, headers, category in [(404, {}, 'not_found'), (401, {}, 'authentication'),
                (403, {}, 'denial'), (429, {}, 'quota'), (403, {'Retry-After': '60'}, 'quota'),
                (403, {'X-RateLimit-Remaining': '0'}, 'quota'), (500, {}, 'http_error')]:
            calls = []
            def fetch(url):
                calls.append(url)
                return status, headers, b'{}'
            result = source.resolve('https://github.com/a/b', source.Reader(fetch))
            self.assertEqual(result['error'], category)
            self.assertEqual(result['events'][0]['http_status'], status)
            self.assertEqual(len(calls), 1)

    def test_loops_unsafe_and_bounded_redirects(self):
        for target, error in [('https://api.github.com/repos/a/b', 'redirect_loop'),
                              ('http://github.com/a/b', 'unsafe_target'),
                              ('https://127.0.0.1/a', 'unsafe_target'),
                              ('https://github.com.evil.test/a', 'unsafe_target'),
                              ('https://user:password@github.com/a', 'unsafe_target')]:
            result = source.resolve('https://github.com/a/b', source.Reader(lambda url: (302, {'Location': target}, b'')))
            self.assertEqual(result['error'], error)
        reader = source.Reader(lambda url: (302, {'Location': url + '/next'}, b''), max_redirects=2)
        self.assertEqual(source.resolve('https://github.com/a/b', reader)['error'], 'redirect_limit')
        self.assertEqual(len(reader.events), 3)

    def test_dns_private_address_denied(self):
        for address in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1']:
            with patch('resolve_alias_source.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]):
                with self.assertRaises(source.SourceFailure):
                    source.public_addresses('api.github.com')

    def test_transport_failure_and_unreadable(self):
        def fail(url):
            raise OSError('private diagnostic never logged')
        result = source.resolve('https://github.com/a/b', source.Reader(fail))
        self.assertEqual(result['error'], 'transport')
        self.assertNotIn('private diagnostic', json.dumps(result))
        result = source.resolve('https://github.com/a/b', source.Reader(lambda url: (200, {}, b'not JSON')))
        self.assertEqual(result['error'], 'unreadable')


if __name__ == '__main__':
    unittest.main()
