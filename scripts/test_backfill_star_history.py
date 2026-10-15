import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import backfill_star_history as b
import update_star_history as h


class Response:
    def __init__(self, value, remaining=900, reset=2000):
        self.headers = {'X-RateLimit-Remaining': str(remaining), 'X-RateLimit-Reset': str(reset)}
        self.body = json.dumps(value).encode()
    def read(self, limit):
        return self.body[:limit]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Clock:
    value = 1000
    def __call__(self):
        return self.value
    def sleep(self, seconds):
        self.value += seconds


URL = h.API + 'o/r/stargazers/history?per_page=30&page=1'


class BackfillTests(unittest.TestCase):
    def transport(self, responses, reserve=556, seconds=900):
        clock = Clock()
        calls = []
        def opened(request, timeout):
            calls.append((clock(), request.full_url))
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return b.Transport('test-token', reserve, seconds, opened, clock, clock.sleep), calls, clock

    def error(self, status, body, remaining=900, reset=2000, retry=None):
        headers = {'X-RateLimit-Remaining': str(remaining), 'X-RateLimit-Reset': str(reset)}
        if retry is not None:
            headers['Retry-After'] = retry
        return HTTPError(URL, status, 'error', headers, io.BytesIO(body.encode()))

    def test_quota_floor_returns_reset_for_external_continuation(self):
        t, calls, clock = self.transport([Response({}, 20, 1100)])
        with self.assertRaises(b.StopBackfill) as caught:
            t(URL)
        self.assertTrue(caught.exception.resumable)
        self.assertEqual(t.reset, 1100)
        self.assertEqual(clock(), 1000)
        self.assertEqual(len(calls), 1)

    def test_quota_wait_yields_at_bounded_deadline(self):
        t, calls, _ = self.transport([Response({}, 555, 5000)], seconds=60)
        with self.assertRaises(b.StopBackfill) as caught:
            t(URL)
        self.assertTrue(caught.exception.resumable)
        self.assertEqual(len(calls), 1)

    def test_secondary_retry_after_and_exponential_backoff(self):
        t, calls, _ = self.transport([Response({}), self.error(429, 'secondary rate limit', retry='120'),
                                      self.error(403, 'secondary rate limit'), Response([])])
        t(URL)
        self.assertEqual([c[0] for c in calls], [1000, 1000, 1120, 1240])

    def test_primary_obeys_reset(self):
        t, calls, clock = self.transport([Response({}), self.error(403, 'rate limit', 0, 1200)])
        with self.assertRaises(b.StopBackfill):
            t(URL)
        self.assertEqual(len(calls), 2)
        self.assertEqual(clock(), 1000)
        self.assertGreaterEqual(t.not_before, 1202)

    def test_auth_unexpected_and_non_rate_403_stop(self):
        for status in [401, 403, 404, 302]:
            with self.subTest(status=status):
                t, calls, _ = self.transport([Response({}), self.error(status, 'permission denied')])
                with self.assertRaises(b.StopBackfill) as caught:
                    t(URL)
                self.assertFalse(caught.exception.resumable)
                self.assertEqual(len(calls), 2)

    def test_invalid_headers_fail_closed(self):
        response = Response([])
        response.headers = {}
        t, _, _ = self.transport([response])
        with self.assertRaises(b.StopBackfill):
            t(URL)

    def test_retry_count_is_bounded(self):
        t, calls, _ = self.transport([Response({})] + [self.error(429, 'secondary')] * 4)
        with self.assertRaises(b.StopBackfill):
            t(URL)
        self.assertEqual(len(calls), 5)

    def test_api_scope_and_missing_token(self):
        with self.assertRaises(b.StopBackfill):
            b.Transport('', 556)
        t, _, _ = self.transport([])
        with self.assertRaises(ValueError):
            t('https://example.org/')

    def fixtures(self):
        root = Path(__file__).resolve().parents[1]
        cache = json.loads((root / 'data/star_history.json').read_text())
        records = [r for r in cache['repositories'].values() if r.get('last_good')]
        record = records[0]
        return cache, record

    def test_merge_preserves_budget_newer_evidence_and_removed_identities(self):
        cache, record = self.fixtures()
        project = {key: record[key] for key in ['repo', 'name', 'readme_url']}
        merged = b.merge_records(cache, [project], {record['repo']: record})
        self.assertEqual(merged, cache)
        merged = b.merge_records(cache, [], {record['repo']: record})
        self.assertEqual(merged, cache)
        empty = dict(cache, repositories={})
        merged = b.merge_records(empty, [project], {record['repo']: record})
        self.assertEqual(merged['budget'], cache['budget'])
        self.assertEqual(merged['repositories'][record['repo']], record)

    def test_partial_page_failure_keeps_completed_checkpoint(self):
        cache, record = self.fixtures()
        projects = [{key: record[key] for key in ['repo', 'name', 'readme_url']},
                    {'repo': 'a/b', 'name': 'b', 'readme_url': 'https://github.com/a/b'}]
        # Put the successful source fixture first in the star-priority ordering.
        metadata = {'repositories': {record['repo']: {'stargazers_count': 100}}}
        transport = type('Transport', (), {'attempts': 5})()
        flushed = []
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'collect_repository', side_effect=[record['last_good'], b.StopBackfill('paused', True)]):
            checkpoint = Path(directory) / 'checkpoint.json'
            state = b.collect(projects, {'schema_version': 1, 'repositories': {}}, metadata, transport,
                              record['source_sha'], checkpoint, lambda r: flushed.append(dict(r)),
                              now=h.parse_time(record['last_good']['fetched_at']))
            self.assertEqual(state['status'], 'partial')
            self.assertEqual(state['remaining'], 1)
            self.assertEqual(len(json.loads(checkpoint.read_text())['records']), 1)
            self.assertEqual(len(flushed[-1]), 1)

    def test_bad_coverage_does_not_starve_other_repositories(self):
        cache, record = self.fixtures()
        projects = [{'repo': 'a/b', 'name': 'b', 'readme_url': 'https://github.com/a/b'},
                    {key: record[key] for key in ['repo', 'name', 'readme_url']}]
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'collect_repository', side_effect=[h.HistoryError('bad coverage'), record['last_good']]):
            state = b.collect(projects, {'schema_version': 1, 'repositories': {}},
                {'repositories': {'a/b': {'stargazers_count': 999999999}}},
                type('Transport', (), {'attempts': 5})(), record['source_sha'], Path(directory) / 'c.json', lambda records: None,
                now=h.parse_time(record['last_good']['fetched_at']))
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['failed_repositories'], ['a/b'])
        self.assertIn(record['repo'], state['records'])
        self.assertEqual(state['remaining'], 1)

    def test_failed_flush_is_blocked(self):
        cache, record = self.fixtures()
        project = {key: record[key] for key in ['repo', 'name', 'readme_url']}
        def fail(records):
            raise RuntimeError('test failure')
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'collect_repository', return_value=record['last_good']):
            result = b.collect([project], {'schema_version': 1, 'repositories': {}}, {},
                type('Transport', (), {'attempts': 4})(), record['source_sha'], Path(directory) / 'c.json', fail,
                now=h.parse_time(record['last_good']['fetched_at']))
        self.assertEqual(result['status'], 'blocked')

    def test_workflow_keeps_single_writer_and_no_automatic_fast_schedule(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/update-stats.yml').read_text()
        self.assertIn('group: publish-readme-main', workflow)
        self.assertIn('always() && github.event_name', workflow)
        self.assertIn('default: false', workflow)
        self.assertNotIn('actions: write', workflow)
        self.assertIn('publish_readme.py --cached', workflow)
        self.assertEqual(h.DEFAULT_REQUEST_BUDGET, 16)


if __name__ == '__main__':
    unittest.main()

class CheckpointGitTests(unittest.TestCase):
    def setUp(self):
        import subprocess
        self.subprocess = subprocess
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.origin, self.actor, self.checkout = [self.root / name for name in ('origin.git', 'actor', 'checkout')]
        self.git(self.root, 'init', '--bare', '--initial-branch=main', str(self.origin))
        self.git(self.root, 'init', '--initial-branch=main', str(self.actor))
        self.git(self.actor, 'config', 'user.name', 'Fixture')
        self.git(self.actor, 'config', 'user.email', 'fixture@example.invalid')
        cache, self.record = BackfillTests().fixtures()
        self.cache = dict(cache, repositories={})
        (self.actor / 'data').mkdir()
        (self.actor / 'data/star_history.json').write_text(json.dumps(self.cache))
        (self.actor / 'README.source.md').write_text('Original name')
        self.git(self.actor, 'add', '.')
        self.git(self.actor, 'commit', '-m', 'Initial')
        self.git(self.actor, 'remote', 'add', 'origin', str(self.origin))
        self.git(self.actor, 'push', 'origin', 'main')
        self.git(self.root, 'clone', str(self.origin), str(self.checkout))

    def git(self, root, *args):
        return self.subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()

    def load(self, root):
        project = {key: self.record[key] for key in ('repo', 'name', 'readme_url')}
        project['name'] = (Path(root) / 'README.source.md').read_text()
        return [project], json.loads((Path(root) / 'data/star_history.json').read_text()), {}

    def test_push_race_refetches_and_preserves_current_source(self):
        original = b.publisher.git
        raced = False
        def git(root, *args, **kwargs):
            nonlocal raced
            if args[:1] == ('push',) and not raced:
                raced = True
                (self.actor / 'README.source.md').write_text('Concurrent name')
                self.git(self.actor, 'add', '.')
                self.git(self.actor, 'commit', '-m', 'Concurrent curated update')
                self.git(self.actor, 'push', 'origin', 'main')
            return original(root, *args, **kwargs)
        original_run = b.publisher.run
        def run(root, *args, **kwargs):
            if args[:2] == ('python3', '-m'):
                return self.subprocess.CompletedProcess(args, 0)
            return original_run(root, *args, **kwargs)
        with patch.object(b, 'load', side_effect=self.load), patch.object(b.publisher, 'git', side_effect=git), patch.object(b.publisher, 'run', side_effect=run):
            b.flush(self.checkout, {self.record['repo']: self.record})
        self.assertTrue(raced)
        self.assertEqual(self.git(self.origin, 'show', 'main:README.source.md'), 'Concurrent name')
        cache = json.loads(self.git(self.origin, 'show', 'main:data/star_history.json'))
        self.assertEqual(cache['repositories'][self.record['repo']]['name'], 'Concurrent name')
        self.assertEqual(cache['budget'], self.cache['budget'])

    def test_validation_failure_never_pushes(self):
        before = self.git(self.origin, 'rev-parse', 'main')
        original_run = b.publisher.run
        def run(root, *args, **kwargs):
            if args[:2] == ('python3', '-m'):
                raise RuntimeError('Validation failed')
            return original_run(root, *args, **kwargs)
        with patch.object(b, 'load', side_effect=self.load), patch.object(b.publisher, 'run', side_effect=run):
            with self.assertRaises(RuntimeError):
                b.flush(self.checkout, {self.record['repo']: self.record})
        self.assertEqual(before, self.git(self.origin, 'rev-parse', 'main'))
