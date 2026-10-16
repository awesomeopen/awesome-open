import io
import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import backfill_star_history as b
import update_star_history as h
import chart_observations as observations
from test_update_star_history import NOW, OPENREMOTE, PROJECT, SHA, pager, weekly_series


def archive_of(*records):
    archive = observations.empty()
    for record in records:
        observations.add_stars(archive, {'schema_version': 1, 'repositories': {record['repo']: record}})
    return archive


def later(record, days=1):
    record = deepcopy(record)
    fetched = h.parse_time(record['last_good']['fetched_at']) + timedelta(days=days)
    record['last_good']['fetched_at'] = record['checked_at'] = fetched.isoformat()
    return record


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
        for status in [401, 403, 404, 301, 302, 307, 308]:
            with self.subTest(status=status):
                t, calls, _ = self.transport([Response({}), self.error(status, 'permission denied')])
                with self.assertRaises(b.StopBackfill) as caught:
                    t(URL)
                self.assertFalse(caught.exception.resumable)
                self.assertEqual(len(calls), 2)
                self.assertEqual(caught.exception.context, {'request_url': URL, 'http_status': status})
                self.assertNotIn('permission denied', str(caught.exception))
                if status in [301, 302, 307, 308]:
                    self.assertIn('redirect refused', str(caught.exception))
                elif status == 401:
                    self.assertIn('authentication failed', str(caught.exception))

    def test_failure_diagnostics_exclude_upstream_urls_bodies_and_credentials(self):
        secret = 'sensitive-test-token'
        error = HTTPError('https://other.example/' + secret, 301, secret,
                          {'Location': 'https://other.example/' + secret}, io.BytesIO(secret.encode()))
        t, calls, _ = self.transport([Response({}), error])
        with self.assertRaises(b.StopBackfill) as caught:
            t(URL)
        diagnostic = str(caught.exception) + json.dumps(caught.exception.context)
        self.assertNotIn(secret, diagnostic)
        self.assertNotIn('other.example', diagnostic)
        self.assertEqual([url for _, url in calls], [b.RATE_URL, URL])
        t, _, _ = self.transport([Response({})] + [URLError(secret)] * 4)
        with self.assertRaises(b.StopBackfill) as caught:
            t(URL)
        self.assertNotIn(secret, str(caught.exception) + json.dumps(caught.exception.context))
        self.assertEqual(caught.exception.context, {'request_url': URL, 'http_status': None})

    def test_quota_probe_failure_identifies_its_actual_endpoint(self):
        t, _, _ = self.transport([self.error(401, 'secret')])
        with self.assertRaises(b.StopBackfill) as caught:
            t(URL)
        self.assertEqual(caught.exception.context, {'request_url': b.RATE_URL, 'http_status': 401})

    def test_backfill_uses_reviewed_endpoint_and_retains_catalog_identity(self):
        rows = weekly_series()
        t, calls, _ = self.transport([Response({})] + [Response(rows[i:i + 30]) for i in range(0, len(rows), 30)])
        flushed = []
        with tempfile.TemporaryDirectory() as directory:
            state = b.collect([OPENREMOTE], {'schema_version': 1, 'repositories': {}}, {}, t,
                              SHA, Path(directory) / 'c.json', lambda records: flushed.append(deepcopy(records)), NOW)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['failures'], [])
        self.assertEqual(set(state['records']), {'openremote/openremote'})
        record = state['records'][OPENREMOTE['repo']]
        self.assertEqual(record['readme_url'], OPENREMOTE['readme_url'])
        self.assertEqual(record['source_url'], h.API + 'openremote/core/stargazers/history')
        self.assertTrue(all('/openremote/core/' in url for _, url in calls[1:]))
        self.assertEqual(flushed[-1][OPENREMOTE['repo']], record)

    def test_blocked_checkpoint_and_summary_identify_repository_status_and_reason(self):
        for status in [301, 401, 403, 404]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                checkpoint = Path(directory) / 'checkpoint.json'
                t, _, _ = self.transport([Response({}), self.error(status, 'do not log this body')])
                state = b.collect([OPENREMOTE], {'schema_version': 1, 'repositories': {}}, {}, t,
                                  SHA, checkpoint, lambda records: None, NOW)
                self.assertEqual(state, json.loads(checkpoint.read_text()))
                self.assertEqual(state['status'], 'blocked')
                self.assertEqual(state['failed_repositories'], [OPENREMOTE['repo']])
                failure = state['failures'][0]
                self.assertEqual(failure['repo'], OPENREMOTE['repo'])
                self.assertEqual(failure['http_status'], status)
                self.assertEqual(failure['request_url'], h.history_source_url(OPENREMOTE['repo']) + '?per_page=30&page=1')
                self.assertNotIn('do not log', json.dumps(state))
                summary = b.failure_summary(state)
                self.assertIn('Repository openremote/openremote', summary)
                self.assertIn('openremote/core', summary)
                self.assertIn('HTTP ' + str(status), summary)
                self.assertIn(failure['reason'], summary)

    def test_coverage_failure_records_completed_response_without_stale_context(self):
        t, _, _ = self.transport([Response({}), Response([])])
        with tempfile.TemporaryDirectory() as directory:
            state = b.collect([OPENREMOTE], {'schema_version': 1, 'repositories': {}}, {}, t,
                              SHA, Path(directory) / 'c.json', lambda records: None, NOW)
        failure = state['failures'][0]
        self.assertEqual(failure['http_status'], 200)
        self.assertEqual(failure['request_url'], h.history_source_url(OPENREMOTE['repo']) + '?per_page=30&page=1')
        self.assertIn('Empty history', failure['reason'])
        # A later preflight failure must not borrow the preceding response.
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'collect_repository', side_effect=h.HistoryError('Invalid preflight')):
            state = b.collect([PROJECT], {'schema_version': 1, 'repositories': {}}, {}, t,
                              SHA, Path(directory) / 'c.json', lambda records: None, NOW)
        self.assertEqual(state['failures'][0]['request_url'], None)
        self.assertEqual(state['failures'][0]['http_status'], None)

    def test_record_validation_failure_reports_repository_without_raw_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'collect_repository', return_value={}), \
                patch.object(h, 'validate_cache', side_effect=ValueError('secret local details')):
            state = b.collect([OPENREMOTE], {'schema_version': 1, 'repositories': {}}, {},
                              type('Transport', (), {'attempts': 1})(), SHA, Path(directory) / 'c.json',
                              lambda records: None, NOW)
        self.assertEqual(state['status'], 'blocked')
        self.assertEqual(state['failed_repositories'], [OPENREMOTE['repo']])
        self.assertIn('local validation', state['failures'][0]['reason'])
        self.assertNotIn('secret', json.dumps(state))
        self.assertEqual(state['records'], {})

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
        good = h.collect_repository(PROJECT['repo'], NOW, getter=pager(weekly_series()), source_sha=SHA)
        record = {**PROJECT, 'source_url': h.API + PROJECT['repo'] + '/stargazers/history',
                  'checked_at': NOW.isoformat(), 'source_sha': SHA, 'status': 'ok', 'last_good': good}
        cache = {'schema_version': 1, 'repositories': {record['repo']: record},
                 'budget': {'utc_date': NOW.date().isoformat(), 'requests_used': 4, 'limit': 16}}
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
        self.assertEqual(state['failures'], [{'repo': 'a/b', 'http_status': None,
                                             'request_url': None, 'reason': 'bad coverage'}])
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
        self.assertEqual(result['failed_repositories'], [])
        self.assertEqual(result['failures'], [])
        self.assertEqual(b.failure_summary(result), '')

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

    def no_tests(self, root, *args, **kwargs):
        if args[:2] == ('python3', '-m'):
            return self.subprocess.CompletedProcess(args, 0)
        return self.original_run(root, *args, **kwargs)

    def remote_archive(self):
        return json.loads(self.git(self.origin, 'show', 'main:' + str(b.publisher.ARCHIVE_PATH)))

    def remote_cache(self):
        return json.loads(self.git(self.origin, 'show', 'main:data/star_history.json'))

    def seed(self, cache=None, archive=None):
        self.git(self.actor, 'pull', '--ff-only', 'origin', 'main')
        if cache is not None:
            h.write_cache(self.actor / 'data/star_history.json', cache)
        if archive is not None:
            observations.save(self.actor / b.publisher.ARCHIVE_PATH, archive)
        self.git(self.actor, 'add', '.')
        self.git(self.actor, 'commit', '-m', 'Current evidence fixture')
        self.git(self.actor, 'push', 'origin', 'main')

    def flush(self, records, load=None):
        self.original_run = b.publisher.run
        with patch.object(b, 'load', side_effect=load or self.load), patch.object(
                b.publisher, 'run', side_effect=self.no_tests):
            b.flush(self.checkout, records)

    def assert_worktree_removed(self):
        self.assertEqual(self.git(self.checkout, 'worktree', 'list', '--porcelain').count('worktree '), 1)

    def test_overwritten_cache_and_new_evidence_share_one_atomic_commit(self):
        self.seed(cache={**self.cache, 'repositories': {self.record['repo']: self.record}})
        incoming = later(self.record)
        self.flush({incoming['repo']: incoming})
        self.assertEqual(self.remote_archive(), archive_of(self.record, incoming))
        self.assertEqual(self.remote_cache()['repositories'][incoming['repo']]['last_good'], incoming['last_good'])
        changed = self.git(self.origin, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'main').splitlines()
        self.assertEqual(set(changed), {'data/star_history.json', str(b.publisher.ARCHIVE_PATH)})
        self.assert_worktree_removed()

    def test_older_complete_record_is_archived_without_replacing_newer_cache(self):
        current = later(self.record)
        cache = {**self.cache, 'repositories': {current['repo']: current}}
        self.seed(cache=cache)
        self.flush({self.record['repo']: self.record})
        self.assertEqual(self.remote_archive(), archive_of(current, self.record))
        self.assertEqual(self.remote_cache(), cache)
        changed = self.git(self.origin, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'main').splitlines()
        self.assertEqual(changed, [str(b.publisher.ARCHIVE_PATH)])

    def test_removed_repository_is_archived_without_reentering_current_cache(self):
        def ineligible(root):
            return [], self.load(root)[1], {}
        self.flush({self.record['repo']: self.record}, load=ineligible)
        self.assertEqual(self.remote_archive(), archive_of(self.record))
        self.assertEqual(self.remote_cache(), self.cache)
        before = self.git(self.origin, 'rev-parse', 'main')
        self.flush({self.record['repo']: self.record}, load=ineligible)
        self.assertEqual(self.git(self.origin, 'rev-parse', 'main'), before)

    def test_invalid_incoming_record_fails_before_fetching_or_replacing_cache(self):
        invalid = deepcopy(self.record)
        invalid['last_good']['monthly_counts'][0] += 1
        with patch.object(b.publisher, 'latest_main') as fetch:
            with self.assertRaises(ValueError):
                b.flush(self.checkout, {invalid['repo']: invalid})
        fetch.assert_not_called()

    def test_fetch_failure_retains_complete_incoming_observations(self):
        before = self.git(self.origin, 'rev-parse', 'main')
        with patch.object(b.publisher, 'latest_main', side_effect=RuntimeError('Fixture fetch failure')):
            with self.assertRaisesRegex(RuntimeError, 'Fixture fetch failure'):
                b.flush(self.checkout, {self.record['repo']: self.record})
        self.assertEqual(observations.load(self.checkout / b.publisher.RECOVERY_PATH), archive_of(self.record))
        self.assertEqual(self.git(self.origin, 'rev-parse', 'main'), before)
        self.assert_worktree_removed()

    def test_corrupt_archive_fails_closed_and_removes_worktree(self):
        (self.actor / b.publisher.ARCHIVE_PATH).write_text('{broken archive')
        self.git(self.actor, 'add', '.')
        self.git(self.actor, 'commit', '-m', 'Corrupt archive fixture')
        self.git(self.actor, 'push', 'origin', 'main')
        before = self.git(self.origin, 'rev-parse', 'main')
        with self.assertRaises(ValueError):
            self.flush({self.record['repo']: self.record})
        self.assertEqual(self.git(self.origin, 'rev-parse', 'main'), before)
        self.assert_worktree_removed()

    def test_corrupt_recovery_blocks_work_without_overwriting_it(self):
        path = self.checkout / b.publisher.RECOVERY_PATH
        path.parent.mkdir(parents=True)
        path.write_text('{corrupt recovery')
        with patch.object(b.publisher, 'latest_main') as fetch:
            with self.assertRaises(ValueError):
                b.flush(self.checkout, {self.record['repo']: self.record})
        fetch.assert_not_called()
        self.assertEqual(path.read_text(), '{corrupt recovery')

    def test_denied_push_retains_recovery_without_publishing(self):
        before = self.git(self.origin, 'rev-parse', 'main')
        original_git = b.publisher.git

        def git(root, *args, **kwargs):
            if args[:1] == ('push',):
                return self.subprocess.CompletedProcess(args, 1, '', 'Fixture write denied')
            return original_git(root, *args, **kwargs)

        with patch.object(b.publisher, 'git', side_effect=git):
            with self.assertRaisesRegex(b.StopBackfill, 'Checkpoint push blocked'):
                self.flush({self.record['repo']: self.record})
        self.assertEqual(observations.load(self.checkout / b.publisher.RECOVERY_PATH), archive_of(self.record))
        self.assertEqual(self.git(self.origin, 'rev-parse', 'main'), before)
        self.assert_worktree_removed()

    def test_retry_exhaustion_retains_recovery_without_publishing(self):
        self.original_run = b.publisher.run
        attempts = []

        def run(root, *args, **kwargs):
            if args[:2] == ('python3', '-m'):
                attempts.append(root)
                self.git(self.actor, 'pull', '--ff-only', 'origin', 'main')
                (self.actor / 'README.source.md').write_text('Source iteration ' + str(len(attempts)))
                self.git(self.actor, 'add', 'README.source.md')
                self.git(self.actor, 'commit', '-m', 'Concurrent source iteration')
                self.git(self.actor, 'push', 'origin', 'main')
                return self.subprocess.CompletedProcess(args, 0)
            return self.original_run(root, *args, **kwargs)

        with patch.object(b, 'load', side_effect=self.load), patch.object(b.publisher, 'run', side_effect=run):
            with self.assertRaisesRegex(b.StopBackfill, 'Main kept advancing'):
                b.flush(self.checkout, {self.record['repo']: self.record})
        self.assertEqual(len(attempts), 5)
        self.assertEqual(observations.load(self.checkout / b.publisher.RECOVERY_PATH), archive_of(self.record))
        self.assertEqual(self.remote_cache(), self.cache)
        self.assertNotIn(str(b.publisher.ARCHIVE_PATH), self.git(self.origin, 'ls-tree', '-r', '--name-only', 'main'))
        self.assert_worktree_removed()

    def test_checkpoint_rejects_similarly_named_or_unrelated_paths(self):
        original = h.write_cache
        for unexpected in ('data/chart_observations.json.tmp', 'data/nested/chart_observations.json',
                           'README.source.md'):
            with self.subTest(path=unexpected):
                before = self.git(self.origin, 'rev-parse', 'main')
                def write(path, cache):
                    original(path, cache)
                    target = Path(path).parents[1] / unexpected
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('Unauthorized checkpoint output')
                with patch.object(h, 'write_cache', side_effect=write):
                    with self.assertRaisesRegex(b.StopBackfill, 'unauthorized path'):
                        self.flush({self.record['repo']: self.record})
                self.assertEqual(self.git(self.origin, 'rev-parse', 'main'), before)
                self.assert_worktree_removed()

    def test_push_race_refetches_and_preserves_current_source(self):
        self.seed(cache={**self.cache, 'repositories': {self.record['repo']: self.record}})
        incoming, concurrent = later(self.record), later(self.record, days=2)
        concurrent['name'] = 'Concurrent name'
        original = b.publisher.git
        raced = False
        def git(root, *args, **kwargs):
            nonlocal raced
            if args[:1] == ('push',) and not raced:
                raced = True
                (self.actor / 'README.source.md').write_text('Concurrent name')
                h.write_cache(self.actor / 'data/star_history.json',
                              {**self.cache, 'repositories': {concurrent['repo']: concurrent}})
                observations.save(self.actor / b.publisher.ARCHIVE_PATH, archive_of(concurrent))
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
            b.flush(self.checkout, {incoming['repo']: incoming})
        self.assertTrue(raced)
        self.assertEqual(self.git(self.origin, 'show', 'main:README.source.md'), 'Concurrent name')
        cache = json.loads(self.git(self.origin, 'show', 'main:data/star_history.json'))
        self.assertEqual(cache['repositories'][self.record['repo']]['name'], 'Concurrent name')
        self.assertEqual(cache['repositories'][self.record['repo']]['last_good'], concurrent['last_good'])
        self.assertEqual(cache['budget'], self.cache['budget'])
        self.assertEqual(self.remote_archive(), archive_of(self.record, incoming, concurrent))
        self.assert_worktree_removed()

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
        self.assertEqual(observations.load(self.checkout / b.publisher.RECOVERY_PATH), archive_of(self.record))
        self.assert_worktree_removed()
