"""Offline contracts for optional release and OpenSSF Scorecard evidence."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import http.client
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

import signals
import update_signals as updater


REPO = 'example/openexample'
AT = '2026-10-10T12:00:00Z'
NOW = signals.timestamp(AT)
SOURCE_SHA = 'a' * 40
SCAN_SHA = 'b' * 40
TOOL_SHA = 'c' * 40


def release(repo=REPO, **changes):
    value = {
        'id': 123, 'tag_name': 'v2.0',
        'html_url': 'https://github.com/' + repo + '/releases/tag/v2.0',
        'published_at': '2026-10-08T09:30:00Z',
        # Deliberately newer than publication: this is not release evidence.
        'created_at': '2026-10-09T20:00:00Z',
        'draft': False, 'prerelease': False,
    }
    value.update(changes)
    return value


def scorecard(repo=REPO, **changes):
    value = {
        'date': '2026-10-08',
        'repo': {'name': 'github.com/' + repo, 'commit': SCAN_SHA},
        'scorecard': {'version': 'v5.3.0', 'commit': TOOL_SHA},
        # The published aggregate is deliberately not the checks' mean.
        'score': 7.3,
        'checks': [
            {'name': 'Code-Review', 'score': 10, 'reason': 'Reviewed changes'},
            {'name': 'Token-Permissions', 'score': 0, 'reason': 'Broad token permissions'},
        ],
    }
    value.update(changes)
    return value


class Clock:
    """Deterministic elapsed time, including simulated fetch and sleep costs."""
    def __init__(self):
        self.elapsed = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


class OfflineCase(unittest.TestCase):
    def setUp(self):
        # All tests, including CLI tests, must stay offline even after refactors.
        network = patch.object(updater.urllib.request.OpenerDirector, 'open',
                               side_effect=AssertionError('Unexpected network request'))
        network.start()
        self.addCleanup(network.stop)
        self.clock = Clock()
        self.calls = []

    def successful_fetch(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        if url.startswith('https://api.github.com/repos/'):
            repo = url.removeprefix('https://api.github.com/repos/').removesuffix('/releases/latest')
            return 200, {'ETag': '"release-v1"'}, release(repo)
        repo = url.removeprefix('https://api.scorecard.dev/projects/github.com/')
        return 200, {'ETag': '"scorecard-v1"'}, scorecard(repo)

    def collect(self, repos=(REPO,), previous=None, **kwargs):
        options = dict(now=NOW, token='private-github-token', fetch=self.successful_fetch,
                       monotonic=self.clock.monotonic, sleep=self.clock.sleep)
        options.update(kwargs)
        return updater.collect(repos, previous, **options)

    def snapshot(self, now=NOW, repos=(REPO,)):
        def historical_fetch(url, headers, timeout):
            code, response_headers, payload = self.successful_fetch(url, headers, timeout)
            if 'published_at' in payload and signals.timestamp(payload['published_at']) > now:
                payload['published_at'] = signals.iso(now - timedelta(days=2))
            if 'date' in payload and signals.timestamp(payload['date'] + 'T00:00:00Z') > now:
                payload['date'] = (now - timedelta(days=2)).strftime('%Y-%m-%d')
            return code, response_headers, payload
        result, _ = self.collect(repos, now=now, fetch=historical_fetch)
        self.calls.clear()
        self.clock = Clock()
        return result


class NormalizationTests(OfflineCase):
    def test_release_uses_publication_and_retains_designated_latest_metadata(self):
        payload = release()
        good = updater.normalize_release(payload, REPO, AT)
        self.assertEqual(good['observed_at'], payload['published_at'])
        self.assertEqual(good['fetched_at'], AT)
        self.assertEqual(good['value'], {
            'release_id': 123, 'tag_name': 'v2.0',
            'published_at': payload['published_at'], 'html_url': payload['html_url'],
        })
        self.assertIsNone(good['source_commit'])
        self.assertIsNone(good['tool_version'])
        self.assertIsNone(good['tool_commit'])
        self.assertNotIn('created_at', json.dumps(good))

    def test_release_does_not_fall_back_to_created_at(self):
        for published in (None, '', '2026-10-08', '2026-02-30T00:00:00Z'):
            with self.subTest(published_at=published), self.assertRaises(ValueError):
                updater.normalize_release(release(published_at=published), REPO, AT)
        payload = release()
        del payload['published_at']
        with self.assertRaises(ValueError):
            updater.normalize_release(payload, REPO, AT)

    def test_release_rejects_drafts_prereleases_and_unasserted_flags(self):
        for key in ('draft', 'prerelease'):
            for value in (True, None, 0, 'false'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    updater.normalize_release(release(**{key: value}), REPO, AT)
            payload = release()
            del payload[key]
            with self.assertRaises(ValueError):
                updater.normalize_release(payload, REPO, AT)

    def test_release_rejects_other_repository_or_unsafe_source_url(self):
        for url in (
            'https://github.com/another/project/releases/tag/v2.0',
            'https://github.com/example/openexample-extra/releases/tag/v2.0',
            'https://github.com.evil.test/example/openexample/releases/tag/v2.0',
            'http://github.com/example/openexample/releases/tag/v2.0',
            'https://github.com/example/openexample/issues/123',
            'https://github.com/example/openexample/releases/tag/v2.0?secret=yes',
            'https://github.com/example/openexample/releases/tag/v2.0#fragment',
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                updater.normalize_release(release(html_url=url), REPO, AT)

    def test_release_ids_and_tags_are_required(self):
        for value in (0, -1, True, '123', None):
            with self.subTest(release_id=value), self.assertRaises(ValueError):
                updater.normalize_release(release(id=value), REPO, AT)
        for value in ('', '  ', None, 'tag\nforged'):
            with self.subTest(tag=value), self.assertRaises(ValueError):
                updater.normalize_release(release(tag_name=value), REPO, AT)

    def test_scorecard_matches_case_insensitively_and_preserves_scan_provenance(self):
        payload = scorecard()
        payload['repo']['name'] = 'GitHub.com/Example/OpenExample'
        good = updater.normalize_scorecard(payload, REPO, AT)
        self.assertEqual(good['value']['repository'], 'github.com/' + REPO)
        self.assertEqual(good['observed_at'], '2026-10-08T00:00:00Z')
        self.assertEqual(good['fetched_at'], AT)
        self.assertEqual(good['source_commit'], SCAN_SHA)
        self.assertEqual(good['tool_version'], 'v5.3.0')
        self.assertEqual(good['tool_commit'], TOOL_SHA)

    def test_scorecard_preserves_aggregate_and_returned_check_coverage(self):
        good = updater.normalize_scorecard(scorecard(), REPO, AT)
        self.assertEqual(good['value']['score'], 7.3)
        self.assertEqual(good['value']['checks'], scorecard()['checks'])
        self.assertEqual(len(good['value']['checks']), 2)
        self.assertNotEqual(good['value']['score'], sum(c['score'] for c in good['value']['checks']) / 2)
        self.assertNotIn('Packaging', [c['name'] for c in good['value']['checks']])
        self.assertEqual(updater.normalize_scorecard(scorecard(checks=[]), REPO, AT)['value']['checks'], [])

    def test_scorecard_inconclusive_minus_one_is_null_never_zero(self):
        checks = scorecard()['checks']
        checks[0]['score'] = -1
        good = updater.normalize_scorecard(scorecard(score=-1, checks=checks), REPO, AT)
        self.assertIsNone(good['value']['score'])
        self.assertIsNone(good['value']['checks'][0]['score'])
        self.assertEqual(good['value']['checks'][1]['score'], 0)
        self.assertEqual(good['value']['checks'][0]['reason'], 'Reviewed changes')

    def test_scorecard_rejects_identity_mismatch_even_with_valid_other_fields(self):
        for name in ('github.com/example/other', 'gitlab.com/' + REPO,
                     'https://github.com/' + REPO, 'github.com/' + REPO + '/', None):
            payload = scorecard()
            payload['repo']['name'] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.normalize_scorecard(payload, REPO, AT)

    def test_scorecard_rejects_invalid_numeric_scores(self):
        for value in (True, False, -2, 10.1, float('nan'), float('inf'), '-1', None):
            for location in ('aggregate', 'check'):
                payload = scorecard()
                if location == 'aggregate':
                    payload['score'] = value
                else:
                    payload['checks'][0]['score'] = value
                with self.subTest(value=value, location=location), self.assertRaises(ValueError):
                    updater.normalize_scorecard(payload, REPO, AT)

    def test_scorecard_requires_repository_commit_and_tool_version(self):
        for section, key, value in (
            ('repo', 'commit', None), ('repo', 'commit', 'not-a-commit'),
            ('scorecard', 'version', None), ('scorecard', 'version', ''),
            ('scorecard', 'commit', 'invalid'),
        ):
            payload = scorecard()
            payload[section][key] = value
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ValueError):
                updater.normalize_scorecard(payload, REPO, AT)
        payload = scorecard()
        del payload['scorecard']['commit']
        self.assertIsNone(updater.normalize_scorecard(payload, REPO, AT)['tool_commit'])

    def test_scorecard_rejects_duplicate_or_malformed_checks(self):
        malformed = (None, {}, [None], [{'name': '', 'score': 1, 'reason': 'reason'}],
                     [{'name': 'Check', 'score': 1, 'reason': ''}], scorecard()['checks'] * 2)
        for checks in malformed:
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                updater.normalize_scorecard(scorecard(checks=checks), REPO, AT)


class SnapshotTests(OfflineCase):
    def test_absent_snapshot_and_absent_repository_are_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(signals.load_optional(Path(directory) / 'absent.json'))
        self.assertIsNone(signals.for_repository(None, REPO))
        self.assertIsNone(signals.for_repository(signals.empty_snapshot(AT), REPO))
        self.assertEqual(signals.validate_snapshot(signals.empty_snapshot(AT))['repositories'], {})

    def test_corrupt_json_and_unsupported_schema_are_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            for contents in ('{broken', 'null', '[]', '{}'):
                path.write_text(contents)
                with self.subTest(contents=contents), self.assertRaises((ValueError, TypeError)):
                    signals.load_optional(path)
        for key, value in (('schema_version', 2), ('schema_version', True),
                           ('schema_version', 1.0), ('method_version', '2'),
                           ('source_sha', 'bad'), ('collected_at', '2026-10-10'),
                           ('provider_retry_after', {'release': None})):
            document = signals.empty_snapshot(AT)
            document[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                signals.validate_snapshot(document)

    def test_missing_required_snapshot_record_and_value_fields_are_fatal(self):
        base = self.snapshot()
        for key in ('schema_version', 'method_version', 'collected_at',
                    'source_sha', 'repositories', 'provider_retry_after'):
            document = deepcopy(base)
            del document[key]
            with self.subTest(level='snapshot', key=key), self.assertRaises(ValueError):
                signals.validate_snapshot(document)
        for provider in signals.PROVIDERS:
            for key in ('source_url', 'status', 'fetch_status', 'checked_at',
                        'last_success_at', 'http_status', 'retry_after', 'etag', 'error', 'last_good'):
                document = deepcopy(base)
                del document['repositories'][REPO][provider][key]
                with self.subTest(provider=provider, level='record', key=key), self.assertRaises(ValueError):
                    signals.validate_snapshot(document)
            for key in ('observed_at', 'fetched_at', 'source_commit', 'tool_version', 'tool_commit', 'value'):
                document = deepcopy(base)
                del document['repositories'][REPO][provider]['last_good'][key]
                with self.subTest(provider=provider, level='last_good', key=key), self.assertRaises(ValueError):
                    signals.validate_snapshot(document)

    def test_omitted_scorecard_scores_cannot_masquerade_as_inconclusive(self):
        for location in ('aggregate', 'check'):
            document = self.snapshot()
            record = document['repositories'][REPO]['scorecard']
            target = record['last_good']['value']
            if location == 'check':
                target = target['checks'][0]
            del target['score']
            record['status'] = 'partial'
            with self.subTest(location=location), self.assertRaises(ValueError):
                signals.validate_snapshot(document)

    def test_last_success_cannot_be_later_than_last_check_or_snapshot(self):
        for provider in signals.PROVIDERS:
            document = self.snapshot()
            document['repositories'][REPO][provider]['last_success_at'] = '2026-10-11T12:00:00Z'
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                signals.validate_snapshot(document)

    def test_omitted_precision_defaults_to_seconds_and_day_precision_is_explicit(self):
        document = self.snapshot()
        for record in document['repositories'][REPO].values():
            record.pop('check_time_precision', None)
            record.pop('success_time_precision', None)
            record['last_good'].pop('fetch_time_precision', None)
        signals.validate_snapshot(document)
        for record in document['repositories'][REPO].values():
            record.update(checked_at='2026-10-10T00:00:00Z', last_success_at='2026-10-10T00:00:00Z',
                          check_time_precision='day', success_time_precision='day')
            record['last_good'].update(fetched_at='2026-10-10T00:00:00Z', fetch_time_precision='day')
        signals.validate_snapshot(document)
        self.assertEqual(document['repositories'][REPO]['scorecard']['last_good']['observed_at'],
                         '2026-10-08T00:00:00Z')

    def test_precision_rejects_unknown_enums_and_false_day_precision(self):
        base = self.snapshot()
        for key in ('check_time_precision', 'success_time_precision', 'fetch_time_precision'):
            for level in ('day', 'minute', None, True):
                document = deepcopy(base)
                target = document['repositories'][REPO]['release']
                if key == 'fetch_time_precision':
                    target = target['last_good']
                target[key] = level
                with self.subTest(key=key, level=level), self.assertRaises(ValueError):
                    signals.validate_snapshot(document)

    def test_snapshot_rejects_identity_status_and_provenance_corruption(self):
        base = self.snapshot()
        mutations = [
            lambda d: d['repositories'].__setitem__('Example/OpenExample', d['repositories'].pop(REPO)),
            lambda d: d['repositories'][REPO]['release'].__setitem__('source_url', 'https://api.github.com/repos/other/repo/releases/latest'),
            lambda d: d['repositories'][REPO]['scorecard']['last_good']['value'].__setitem__('repository', 'github.com/other/repo'),
            lambda d: d['repositories'][REPO]['release'].__setitem__('status', 'unavailable'),
            lambda d: d['repositories'][REPO]['scorecard'].__setitem__('fetch_status', 'invented'),
            lambda d: d['repositories'][REPO]['release'].__setitem__('http_status', True),
            lambda d: d['repositories'][REPO]['release'].__setitem__('checked_at', '2027-01-01T00:00:00Z'),
            lambda d: d['repositories'][REPO]['release']['last_good'].__setitem__('fetched_at', '2027-01-01T00:00:00Z'),
            lambda d: d['repositories'][REPO]['release']['last_good'].__setitem__('source_commit', SCAN_SHA),
        ]
        for index, mutate in enumerate(mutations):
            document = deepcopy(base)
            mutate(document)
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                signals.validate_snapshot(document)

    def test_success_without_last_good_and_inconsistent_release_observation_are_fatal(self):
        base = self.snapshot()
        for provider in signals.PROVIDERS:
            document = deepcopy(base)
            document['repositories'][REPO][provider]['last_good'] = None
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                signals.validate_snapshot(document)
        base['repositories'][REPO]['release']['last_good']['observed_at'] = AT
        with self.assertRaises(ValueError):
            signals.validate_snapshot(base)

    def test_for_repository_returns_independent_copy(self):
        document = self.snapshot()
        original = deepcopy(document)
        returned = signals.for_repository(document, REPO)
        returned['scorecard']['last_good']['value']['checks'][0]['score'] = 2
        self.assertEqual(document, original)

    def test_write_round_trip_is_valid_and_deterministic(self):
        document = self.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested' / 'snapshot.json'
            updater.write_snapshot(path, document)
            first = path.read_bytes()
            self.assertEqual(signals.load_optional(path), document)
            updater.write_snapshot(path, document)
            self.assertEqual(path.read_bytes(), first)
            self.assertTrue(first.endswith(b'\n'))
            self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_invalid_document_never_overwrites_existing_snapshot(self):
        document = self.snapshot()
        document['method_version'] = 'invalid'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            path.write_text('last good on disk\n')
            with self.assertRaises(ValueError):
                updater.write_snapshot(path, document)
            self.assertEqual(path.read_text(), 'last good on disk\n')
            self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_failed_atomic_replace_retains_old_file_and_removes_temporary(self):
        document = self.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            path.write_text('last good on disk\n')
            with patch.object(Path, 'replace', side_effect=OSError('replace failed')):
                with self.assertRaises(OSError):
                    updater.write_snapshot(path, document)
            self.assertEqual(path.read_text(), 'last good on disk\n')
            self.assertFalse(path.with_suffix('.json.tmp').exists())


class CollectionTests(OfflineCase):
    def test_success_uses_latest_endpoint_and_auth_only_for_github(self):
        document, summary = self.collect(source_sha=SOURCE_SHA)
        self.assertEqual(document['source_sha'], SOURCE_SHA)
        self.assertEqual(summary['release:requests'], 1)
        self.assertEqual(summary['scorecard:requests'], 1)
        self.assertEqual(len(self.calls), 2)
        url, github, timeout = self.calls[0]
        self.assertEqual(url, 'https://api.github.com/repos/' + REPO + '/releases/latest')
        self.assertEqual(github['Authorization'], 'Bearer private-github-token')
        self.assertEqual(github['X-GitHub-Api-Version'], '2022-11-28')
        url, public, timeout = self.calls[1]
        self.assertEqual(url, 'https://api.scorecard.dev/projects/github.com/' + REPO)
        self.assertNotIn('authorization', {key.lower() for key in public})
        self.assertNotIn('private-github-token', json.dumps(public))
        for provider in signals.PROVIDERS:
            record = document['repositories'][REPO][provider]
            self.assertEqual(record['status'], 'available')
            self.assertEqual(record['fetch_status'], 'ok')
            self.assertEqual(record['checked_at'], AT)
            self.assertEqual(record['last_success_at'], AT)
            self.assertEqual(record['http_status'], 200)

    def test_no_github_token_still_collects_public_scorecard(self):
        document, summary = self.collect(token=None)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.calls[0][0].startswith('https://api.scorecard.dev/'))
        self.assertEqual(summary['release:no_token'], 1)
        self.assertEqual(document['repositories'][REPO]['release']['status'], 'pending')
        self.assertEqual(document['repositories'][REPO]['scorecard']['status'], 'available')

    def test_availability_statuses_without_a_previous_value(self):
        cases = (
            (202, 'pending', 'pending', 'provider_pending', 1),
            (403, 'error', 'unavailable', 'http_403', 1),
            (404, 'not_found', 'unavailable', 'not_found', 1),
            (429, 'error', 'unavailable', 'http_429', 1),
            (500, 'error', 'unavailable', 'http_500', 2),
            (None, 'error', 'unavailable', 'transport_error', 2),
        )
        for provider in signals.PROVIDERS:
            for code, fetch_status, status, error, count in cases:
                with self.subTest(provider=provider, code=code):
                    fetch = Mock(return_value=(code, {}, None))
                    document, summary = self.collect(providers=(provider,), fetch=fetch)
                    record = document['repositories'][REPO][provider]
                    self.assertEqual(record['fetch_status'], fetch_status)
                    self.assertEqual(record['status'], status)
                    self.assertEqual(record['error'], error)
                    self.assertEqual(record['http_status'], code)
                    self.assertIsNone(record['last_good'])
                    self.assertIsNone(record['last_success_at'])
                    self.assertEqual(fetch.call_count, count)
                    self.assertEqual(summary[provider + ':requests'], count)

    def test_failures_and_404_retain_last_good_without_freshening_it(self):
        previous = self.snapshot(now=NOW - timedelta(days=15))
        original = deepcopy(previous)
        for provider in signals.PROVIDERS:
            for code in (202, 403, 404, 429, 500, None):
                with self.subTest(provider=provider, code=code):
                    document, _ = self.collect(previous=previous, providers=(provider,),
                                               fetch=Mock(return_value=(code, {}, None)))
                    before = previous['repositories'][REPO][provider]
                    after = document['repositories'][REPO][provider]
                    self.assertEqual(after['last_good'], before['last_good'])
                    self.assertEqual(after['last_success_at'], before['last_success_at'])
                    self.assertEqual(after['checked_at'], AT)
                    self.assertEqual(after['status'], 'stale')
                    if code == 404:
                        self.assertIsNone(after['etag'])
        self.assertEqual(previous, original)

    def test_304_preserves_observed_and_fetched_time_but_updates_success(self):
        previous = self.snapshot(now=NOW - timedelta(days=8))
        original = deepcopy(previous)
        fetch = Mock(return_value=(304, {}, None))
        document, summary = self.collect(previous=previous, fetch=fetch)
        self.assertEqual(fetch.call_count, 2)
        for provider in signals.PROVIDERS:
            before = previous['repositories'][REPO][provider]
            record = document['repositories'][REPO][provider]
            self.assertEqual(record['last_good'], before['last_good'])
            self.assertEqual(record['last_success_at'], AT)
            self.assertEqual(record['checked_at'], AT)
            self.assertEqual(record['fetch_status'], 'not_modified')
            self.assertEqual(record['status'], 'available')
            self.assertEqual(summary[provider + ':not_modified'], 1)
        for call in fetch.call_args_list:
            self.assertIn('If-None-Match', call.args[1])
        self.assertEqual(previous, original)

    def test_304_without_prior_value_or_validator_is_fatal(self):
        fetch = Mock(return_value=(304, {}, None))
        with self.assertRaisesRegex(ValueError, '304'):
            self.collect(providers=('release',), fetch=fetch)
        previous = self.snapshot(now=NOW - timedelta(days=8))
        previous['repositories'][REPO]['release']['etag'] = None
        with self.assertRaisesRegex(ValueError, '304'):
            self.collect(previous=previous, providers=('release',), fetch=fetch)

    def test_new_scan_and_revalidated_old_scan_both_remain_stale(self):
        payload = scorecard(date='2026-08-01')
        document, _ = self.collect(providers=('scorecard',),
                                   fetch=Mock(return_value=(200, {'ETag': '"old"'}, payload)))
        record = document['repositories'][REPO]['scorecard']
        self.assertEqual(record['last_success_at'], AT)
        self.assertEqual(record['status'], 'stale')
        later, _ = self.collect(previous=document, providers=('scorecard',),
                                now=NOW + timedelta(days=7), fetch=Mock(return_value=(304, {}, None)))
        record = later['repositories'][REPO]['scorecard']
        self.assertEqual(record['status'], 'stale')
        self.assertEqual(record['last_good']['observed_at'], '2026-08-01T00:00:00Z')
        self.assertEqual(record['last_good']['fetched_at'], AT)
        self.assertEqual(record['last_success_at'], '2026-10-17T12:00:00Z')

    def test_release_staleness_measures_cache_age_not_release_age(self):
        payload = release(published_at='2015-01-01T00:00:00Z')
        document, _ = self.collect(providers=('release',),
                                   fetch=Mock(return_value=(200, {'ETag': '"old-release"'}, payload)))
        self.assertEqual(document['repositories'][REPO]['release']['status'], 'available')
        for age, expected in ((3, 'available'), (4, 'stale')):
            aged, _ = self.collect(previous=document, providers=(), now=NOW + timedelta(days=age))
            self.assertEqual(aged['repositories'][REPO]['release']['status'], expected)
        refreshed, _ = self.collect(previous=document, providers=('release',), now=NOW + timedelta(days=8),
                                    fetch=Mock(return_value=(304, {}, None)))
        self.assertEqual(refreshed['repositories'][REPO]['release']['status'], 'available')

    def test_partial_status_preserves_zero_and_unknown_coverage(self):
        for unknown_at in ('aggregate', 'check'):
            payload = scorecard()
            if unknown_at == 'aggregate':
                payload['score'] = -1
            else:
                payload['checks'][0]['score'] = -1
            with self.subTest(unknown_at=unknown_at):
                document, _ = self.collect(providers=('scorecard',),
                                           fetch=Mock(return_value=(200, {}, payload)))
                record = document['repositories'][REPO]['scorecard']
                self.assertEqual(record['status'], 'partial')
                self.assertEqual(record['last_good']['value']['checks'][1]['score'], 0)
                self.assertEqual(len(record['last_good']['value']['checks']), 2)

    def test_missing_check_coverage_is_partial_even_when_aggregate_is_known(self):
        document, _ = self.collect(providers=('scorecard',),
                                   fetch=Mock(return_value=(200, {}, scorecard(checks=[]))))
        record = document['repositories'][REPO]['scorecard']
        self.assertEqual(record['status'], 'partial')
        self.assertEqual(record['last_good']['value']['score'], 7.3)
        self.assertEqual(record['last_good']['value']['checks'], [])

    def test_revalidation_of_day_precision_cache_only_freshens_exact_check_time(self):
        earlier = (NOW - timedelta(days=8)).replace(hour=0)
        previous = self.snapshot(now=earlier)
        for record in previous['repositories'][REPO].values():
            record.update(check_time_precision='day', success_time_precision='day')
            record['last_good']['fetch_time_precision'] = 'day'
        document, _ = self.collect(previous=previous, fetch=Mock(return_value=(304, {}, None)))
        for provider in signals.PROVIDERS:
            record = document['repositories'][REPO][provider]
            self.assertEqual(record['check_time_precision'], 'second')
            self.assertEqual(record['success_time_precision'], 'second')
            self.assertEqual(record['last_good']['fetch_time_precision'], 'day')
            self.assertEqual(record['last_good']['fetched_at'], signals.iso(earlier))
            self.assertEqual(record['checked_at'], AT)

    def test_new_success_replaces_day_precision_cache_with_exact_fetch(self):
        earlier = (NOW - timedelta(days=8)).replace(hour=0)
        previous = self.snapshot(now=earlier)
        for record in previous['repositories'][REPO].values():
            record.update(check_time_precision='day', success_time_precision='day')
            record['last_good']['fetch_time_precision'] = 'day'
        document, _ = self.collect(previous=previous)
        for record in document['repositories'][REPO].values():
            self.assertEqual(record['check_time_precision'], 'second')
            self.assertEqual(record['success_time_precision'], 'second')
            self.assertEqual(record['last_good'].get('fetch_time_precision', 'second'), 'second')
            self.assertEqual(record['last_good']['fetched_at'], AT)

    def test_scorecard_stale_boundary_is_scan_age(self):
        for delta, status in ((timedelta(days=30), 'available'),
                              (timedelta(days=30, seconds=1), 'stale')):
            payload = scorecard(date=signals.iso(NOW - delta))
            document, _ = self.collect(providers=('scorecard',),
                                       fetch=Mock(return_value=(200, {}, payload)))
            self.assertEqual(document['repositories'][REPO]['scorecard']['status'], status)

    def test_invalid_provider_payload_does_not_modify_previous_object(self):
        previous = self.snapshot(now=NOW - timedelta(days=15))
        original = deepcopy(previous)
        for provider, payload in (('release', release('other/repo')),
                                  ('scorecard', scorecard('other/repo')),
                                  ('release', []), ('scorecard', {'checks': []})):
            with self.subTest(provider=provider, payload=payload), self.assertRaises(ValueError):
                self.collect(previous=previous, providers=(provider,), fetch=Mock(return_value=(200, {}, payload)))
            self.assertEqual(previous, original)

    def test_redirects_require_review_instead_of_remapping_identity(self):
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'identity'):
                self.collect(providers=('release',), fetch=Mock(return_value=(code, {'Location': 'https://example.com'}, None)))
        self.assertIsNone(updater.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))

    def test_source_pruning_deduplicates_current_repositories_without_mutating_input(self):
        previous = self.snapshot(repos=(REPO, 'old/removed'))
        original = deepcopy(previous)
        document, _ = self.collect((REPO, REPO, 'new/added'), previous, providers=())
        self.assertEqual(set(document['repositories']), {REPO, 'new/added'})
        self.assertEqual(document['repositories'][REPO], previous['repositories'][REPO])
        self.assertEqual(document['repositories']['new/added']['release']['status'], 'pending')
        self.assertEqual(previous, original)

    def test_invalid_canonical_repository_and_unknown_provider_are_fatal(self):
        for repo in ('Example/OpenExample', 'example', 'a/b/c', 'https://github.com/a/b', 'a/b?x'):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                self.collect((repo,))
        with self.assertRaises(ValueError):
            self.collect(providers=('unknown',))


class BudgetAndBackoffTests(OfflineCase):
    def test_direct_collector_rejects_excessive_or_negative_budgets(self):
        for option, value in (('release_budget', 351), ('scorecard_budget', 51),
                              ('max_seconds', 301), ('release_budget', -1),
                              ('scorecard_budget', -1), ('max_seconds', -1)):
            fetch = Mock(side_effect=AssertionError('Invalid budgets must fail before fetch'))
            with self.subTest(option=option, value=value), self.assertRaises(ValueError):
                self.collect(fetch=fetch, **{option: value})
            fetch.assert_not_called()

    def test_retryable_errors_retry_once_and_count_against_budget(self):
        for code in (None, 500, 502, 503, 504):
            fetch = Mock(side_effect=[(code, {}, None), (200, {}, release())])
            with self.subTest(code=code):
                document, summary = self.collect(providers=('release',), fetch=fetch, release_budget=2)
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(summary['release:requests'], 2)
                self.assertEqual(document['repositories'][REPO]['release']['status'], 'available')
        self.assertEqual(self.clock.sleeps.count(1), 5)

    def test_one_request_budget_prevents_retry_and_defers_other_repositories(self):
        fetch = Mock(return_value=(500, {}, None))
        document, summary = self.collect(('a/project', 'b/project'), providers=('release',),
                                         fetch=fetch, release_budget=1)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(summary['release:requests'], 1)
        self.assertEqual(summary['release:budget_deferred'], 1)
        self.assertEqual(document['repositories']['b/project']['release']['checked_at'], None)
        self.assertEqual(document['repositories']['b/project']['release']['status'], 'pending')
        self.assertNotIn(1, self.clock.sleeps)

    def test_default_budgets_bound_requests_independently(self):
        repos = tuple('example/project%03d' % index for index in range(401))
        _, summary = self.collect(repos)
        self.assertEqual(summary['release:requests'], 350)
        self.assertEqual(summary['scorecard:requests'], 50)
        self.assertEqual(summary['release:budget_deferred'], 51)
        self.assertEqual(summary['scorecard:budget_deferred'], 351)
        self.assertEqual(len(self.calls), 400)

    def test_time_budget_is_shared_across_both_providers(self):
        def fetch(url, headers, timeout):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 10)
            response = self.successful_fetch(url, headers, timeout)
            self.clock.elapsed += timeout
            return response
        document, summary = self.collect(('a/project', 'b/project'), fetch=fetch, max_seconds=10)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(summary['release:requests'], 1)
        self.assertNotIn('scorecard:requests', summary)
        self.assertEqual(document['repositories']['a/project']['scorecard']['status'], 'pending')
        self.assertEqual(self.clock.sleeps, [])

    def test_zero_time_or_request_budgets_do_not_fetch_or_fake_a_check(self):
        for kwargs in ({'max_seconds': 0}, {'release_budget': 0, 'scorecard_budget': 0}):
            with self.subTest(kwargs=kwargs):
                fetch = Mock(side_effect=AssertionError('No budget'))
                document, summary = self.collect(fetch=fetch, **kwargs)
                fetch.assert_not_called()
                for provider in signals.PROVIDERS:
                    record = document['repositories'][REPO][provider]
                    self.assertIsNone(record['checked_at'])
                    self.assertEqual(record['fetch_status'], 'not_checked')
                    self.assertEqual(record['status'], 'pending')
                    self.assertEqual(summary[provider + ':budget_deferred'], 1)

    def test_request_timeout_is_clamped_to_remaining_wall_clock_budget(self):
        def fetch(url, headers, timeout):
            self.calls.append((url, headers, timeout))
            self.clock.elapsed += timeout
            return None, {}, None
        _, summary = self.collect(providers=('release',), fetch=fetch, max_seconds=0.5)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2], 0.5)
        self.assertEqual(summary['release:requests'], 1)
        self.assertEqual(self.clock.sleeps, [])

    def test_retry_after_seconds_http_date_and_reset_use_latest_safe_time(self):
        for headers, expected in (
            ({}, NOW + timedelta(hours=1)),
            ({'Retry-After': '7200'}, NOW + timedelta(hours=2)),
            ({'rEtRy-AfTeR': format_datetime(NOW + timedelta(hours=3))}, NOW + timedelta(hours=3)),
            ({'X-RateLimit-Reset': str(int((NOW + timedelta(hours=4)).timestamp()))}, NOW + timedelta(hours=4)),
            ({'Retry-After': '7200', 'X-RateLimit-Reset': str(int((NOW + timedelta(hours=4)).timestamp()))}, NOW + timedelta(hours=4)),
            ({'Retry-After': '-3'}, NOW + timedelta(hours=1)),
            ({'Retry-After': 'invalid', 'X-RateLimit-Reset': 'invalid'}, NOW + timedelta(hours=1)),
        ):
            with self.subTest(headers=headers):
                self.assertEqual(updater.retry_time(headers, NOW), signals.iso(expected))

    def test_rate_limit_stops_only_affected_provider_and_persists_backoff(self):
        for code in (403, 429):
            with self.subTest(code=code):
                calls = []
                def fetch(url, headers, timeout):
                    calls.append(url)
                    if url.startswith('https://api.github.com/'):
                        return code, {'Retry-After': '172800'}, None
                    return self.successful_fetch(url, headers, timeout)
                document, summary = self.collect(('a/project', 'b/project'), fetch=fetch)
                self.assertEqual(sum('api.github.com' in url for url in calls), 1)
                self.assertEqual(sum('api.scorecard.dev' in url for url in calls), 2)
                expected = '2026-10-12T12:00:00Z'
                self.assertEqual(document['provider_retry_after']['release'], expected)
                self.assertEqual(document['repositories']['a/project']['release']['retry_after'], expected)
                never = Mock(side_effect=AssertionError('Backoff must be honored'))
                later, summary = self.collect(('a/project', 'b/project'), document, now=NOW + timedelta(days=1),
                                              providers=('release',), fetch=never)
                never.assert_not_called()
                self.assertEqual(summary['release:backoff'], 1)
                self.assertEqual(later['provider_retry_after']['release'], expected)

    def test_retryable_503_with_retry_after_stops_batch_and_persists_provider_delay(self):
        calls = []
        def fetch(url, headers, timeout):
            calls.append(url)
            if url.startswith('https://api.github.com/'):
                return 503, {'Retry-After': '7200'}, None
            return self.successful_fetch(url, headers, timeout)
        document, summary = self.collect(('a/project', 'b/project'), fetch=fetch)
        self.assertEqual(sum('api.github.com' in url for url in calls), 1)
        self.assertEqual(sum('api.scorecard.dev' in url for url in calls), 2)
        self.assertNotIn(1, self.clock.sleeps)
        self.assertEqual(summary['release:requests'], 1)
        self.assertEqual(document['provider_retry_after']['release'], '2026-10-10T14:00:00Z')
        record = document['repositories']['a/project']['release']
        self.assertEqual(record['retry_after'], '2026-10-10T14:00:00Z')
        self.assertEqual(record['fetch_status'], 'error')
        self.assertEqual(record['error'], 'http_503')
        never = Mock(side_effect=AssertionError('503 Retry-After must be honored'))
        self.collect(('a/project', 'b/project'), document, providers=('release',),
                     now=NOW + timedelta(hours=1), fetch=never)
        never.assert_not_called()

    def test_expired_provider_backoff_allows_collection_and_clears_delay(self):
        document, _ = self.collect(providers=('release',),
                                   fetch=Mock(return_value=(429, {'Retry-After': '86400'}, None)))
        refreshed, summary = self.collect(previous=document, providers=('release',),
                                            now=NOW + timedelta(days=1))
        self.assertEqual(summary['release:requests'], 1)
        self.assertIsNone(refreshed['provider_retry_after']['release'])
        self.assertIsNone(refreshed['repositories'][REPO]['release']['retry_after'])
        self.assertEqual(refreshed['repositories'][REPO]['release']['status'], 'available')

    def test_scorecard_rate_limit_never_leaks_github_authorization(self):
        fetch = Mock(return_value=(429, {'Retry-After': '7200'}, None))
        document, _ = self.collect(('a/project', 'b/project'), providers=('scorecard',), fetch=fetch)
        self.assertEqual(fetch.call_count, 1)
        self.assertNotIn('Authorization', fetch.call_args.args[1])
        self.assertEqual(document['provider_retry_after']['scorecard'], '2026-10-10T14:00:00Z')

    def test_success_at_reserved_github_quota_stops_further_release_fetches(self):
        fetch = Mock(return_value=(200, {'X-RateLimit-Remaining': '100',
                                      'X-RateLimit-Reset': str(int((NOW + timedelta(hours=2)).timestamp()))}, release('a/project')))
        document, summary = self.collect(('a/project', 'b/project'), providers=('release',), fetch=fetch)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(summary['release:ok'], 1)
        self.assertEqual(document['repositories']['a/project']['release']['status'], 'available')
        self.assertEqual(document['repositories']['b/project']['release']['status'], 'pending')
        self.assertEqual(document['provider_retry_after']['release'], '2026-10-10T14:00:00Z')

    def test_pending_202_has_record_backoff_without_stopping_other_repositories(self):
        fetch = Mock(return_value=(202, {'Retry-After': '172800'}, None))
        document, _ = self.collect(('a/project', 'b/project'), providers=('scorecard',), fetch=fetch)
        self.assertEqual(fetch.call_count, 2)
        self.assertIsNone(document['provider_retry_after']['scorecard'])
        self.assertEqual(document['repositories']['a/project']['scorecard']['retry_after'], '2026-10-12T12:00:00Z')
        never = Mock(side_effect=AssertionError('Record backoff must be honored'))
        self.collect(('a/project', 'b/project'), document, now=NOW + timedelta(days=1),
                     providers=('scorecard',), fetch=never)
        never.assert_not_called()

    def test_scorecard_success_and_not_found_have_distinct_recheck_intervals(self):
        successful = self.snapshot()
        record = successful['repositories'][REPO]['scorecard']
        self.assertFalse(updater.due(record, 'scorecard', NOW + timedelta(days=6)))
        self.assertTrue(updater.due(record, 'scorecard', NOW + timedelta(days=7)))
        missing, _ = self.collect(providers=('scorecard',), fetch=Mock(return_value=(404, {}, None)))
        record = missing['repositories'][REPO]['scorecard']
        self.assertFalse(updater.due(record, 'scorecard', NOW + timedelta(days=13)))
        self.assertTrue(updater.due(record, 'scorecard', NOW + timedelta(days=14)))
        self.assertFalse(updater.due(successful['repositories'][REPO]['release'], 'release', NOW + timedelta(hours=23)))
        self.assertTrue(updater.due(successful['repositories'][REPO]['release'], 'release', NOW + timedelta(days=1)))

    def test_fairness_attempts_unchecked_then_least_recently_attempted(self):
        repos = ('a/project', 'b/project', 'c/project')
        first, _ = self.collect(repos, providers=('release',), release_budget=1,
                                fetch=Mock(return_value=(500, {}, None)))
        second_fetch = Mock(return_value=(500, {}, None))
        second, _ = self.collect(repos, first, providers=('release',), release_budget=1,
                                 now=NOW + timedelta(days=1), fetch=second_fetch)
        self.assertIn('/b/project/releases/latest', second_fetch.call_args.args[0])
        third_fetch = Mock(return_value=(500, {}, None))
        third, _ = self.collect(repos, second, providers=('release',), release_budget=1,
                                now=NOW + timedelta(days=2), fetch=third_fetch)
        self.assertIn('/c/project/releases/latest', third_fetch.call_args.args[0])
        fourth_fetch = Mock(return_value=(500, {}, None))
        self.collect(repos, third, providers=('release',), release_budget=1,
                     now=NOW + timedelta(days=3), fetch=fourth_fetch)
        self.assertIn('/a/project/releases/latest', fourth_fetch.call_args.args[0])

    def test_deferred_last_good_is_preserved_and_becomes_stale_with_age(self):
        previous = self.snapshot()
        document, summary = self.collect(previous=previous, now=NOW + timedelta(days=40),
                                          release_budget=0, scorecard_budget=0)
        for provider in signals.PROVIDERS:
            self.assertEqual(document['repositories'][REPO][provider]['last_good'], previous['repositories'][REPO][provider]['last_good'])
            self.assertEqual(document['repositories'][REPO][provider]['checked_at'], AT)
            self.assertEqual(document['repositories'][REPO][provider]['status'], 'stale')
            self.assertEqual(summary[provider + ':budget_deferred'], 1)


class RequestAndCliTests(OfflineCase):
    def response(self, status, body=b'', headers=None):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = status
        response.headers = headers or {}
        response.read.return_value = body
        return response

    def test_request_json_decodes_200_and_limits_response_size(self):
        response = self.response(200, b'{"ok": true}', {'ETag': '"v1"'})
        opener = Mock()
        opener.open.return_value = response
        with patch.object(updater.urllib.request, 'build_opener', return_value=opener) as build:
            self.assertEqual(updater.request_json('https://example.com', {'Accept': 'application/json'}, 4),
                             (200, {'ETag': '"v1"'}, {'ok': True}))
        build.assert_called_once_with(updater.NoRedirect)
        self.assertEqual(opener.open.call_args.kwargs, {'timeout': 4})
        response.read.assert_called_once_with(2_000_001)
        for body in (b'x' * 2_000_001, b'{broken'):
            response.read.return_value = body
            with patch.object(updater.urllib.request, 'build_opener', return_value=opener):
                with self.assertRaises(ValueError):
                    updater.request_json('https://example.com', {}, 4)

    def test_request_json_empty_202_is_pending_instead_of_invalid_json(self):
        opener = Mock()
        opener.open.return_value = self.response(202, b'', {'Retry-After': '86400'})
        with patch.object(updater.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(updater.request_json('https://example.com', {}, 4),
                             (202, {'Retry-After': '86400'}, None))

    def test_request_json_preserves_http_status_and_headers_without_parsing_error_body(self):
        for code in (304, 403, 404, 429, 500):
            opener = Mock()
            opener.open.side_effect = urllib.error.HTTPError('https://example.com', code, 'error', {'Retry-After': '3600'}, None)
            with self.subTest(code=code), patch.object(updater.urllib.request, 'build_opener', return_value=opener):
                self.assertEqual(updater.request_json('https://example.com', {}, 4),
                                 (code, {'Retry-After': '3600'}, None))

    def test_request_json_transport_timeouts_and_os_errors_are_fail_soft(self):
        for error in (TimeoutError('timed out'), urllib.error.URLError('offline'),
                      OSError('connection reset'), http.client.BadStatusLine('broken status line')):
            opener = Mock()
            opener.open.side_effect = error
            with self.subTest(error=error), patch.object(updater.urllib.request, 'build_opener', return_value=opener):
                self.assertEqual(updater.request_json('https://example.com', {}, 4), (None, {}, None))

    def test_request_json_truncated_response_body_is_fail_soft(self):
        response = self.response(200)
        response.read.side_effect = http.client.IncompleteRead(b'{"repo":', 200)
        opener = Mock()
        opener.open.return_value = response
        with patch.object(updater.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(updater.request_json('https://example.com', {}, 4), (None, {}, None))

    def cli_environment(self, root, output, extra=()):
        (root / 'README.source.md').write_text(
            '| [OpenExample](https://github.com/Example/OpenExample) | Example project. |\n')
        (root / 'README.md').write_text('Published README remains unchanged.\n')
        return ['update_signals.py', '--output', str(output), *extra]

    def run_main(self, root, argv, fetch=None):
        real_collect = updater.collect
        def offline_collect(repositories, previous, **kwargs):
            return real_collect(repositories, previous, now=NOW,
                                fetch=fetch or self.successful_fetch,
                                monotonic=self.clock.monotonic, sleep=self.clock.sleep, **kwargs)
        with patch.object(updater, 'ROOT', root), patch('sys.argv', argv), \
                patch.dict(updater.os.environ, {'GH_TOKEN': 'private-github-token'}), \
                patch.object(updater, 'collect', side_effect=offline_collect), patch('sys.stdout', new_callable=io.StringIO) as stdout:
            updater.main()
            return stdout.getvalue()

    def test_cli_absent_snapshot_is_created_without_touching_readmes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'data' / 'project_signals.json'
            argv = self.cli_environment(root, path, ('--source-sha', SOURCE_SHA))
            readmes = {p: p.read_bytes() for p in (root / 'README.md', root / 'README.source.md')}
            summary = json.loads(self.run_main(root, argv))
            document = signals.load_optional(path)
            self.assertEqual(document['source_sha'], SOURCE_SHA)
            self.assertEqual(set(document['repositories']), {REPO})
            self.assertEqual(summary['repositories'], 1)
            for readme, original in readmes.items():
                self.assertEqual(readme.read_bytes(), original)

    def test_cli_corrupt_local_snapshot_is_fatal_and_never_overwritten(self):
        wrong_identity = self.snapshot()
        wrong_identity['repositories'][REPO]['scorecard']['last_good']['value']['repository'] = 'github.com/other/project'
        missing_required = self.snapshot()
        del missing_required['repositories'][REPO]['release']['checked_at']
        for contents in ('{broken', json.dumps({'schema_version': 99}),
                         json.dumps(wrong_identity), json.dumps(missing_required)):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'project_signals.json'
                argv = self.cli_environment(root, path)
                path.write_text(contents)
                fetch = Mock(side_effect=AssertionError('Corrupt input must fail before fetching'))
                with self.assertRaises(ValueError):
                    self.run_main(root, argv, fetch)
                fetch.assert_not_called()
                self.assertEqual(path.read_text(), contents)
                self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_cli_bad_provider_schema_or_identity_does_not_replace_last_good_file(self):
        previous = self.snapshot(now=NOW - timedelta(days=15))
        for payload in (release('other/repo'), {'draft': False, 'prerelease': False}):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'project_signals.json'
                argv = self.cli_environment(root, path, ('--providers', 'release'))
                updater.write_snapshot(path, previous)
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    self.run_main(root, argv, Mock(return_value=(200, {}, payload)))
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_cli_enforces_hard_request_and_time_ceilings(self):
        for flag, excessive in (('--release-budget', '351'), ('--scorecard-budget', '51'), ('--max-seconds', '301')):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / 'project_signals.json'
                argv = self.cli_environment(root, path, (flag, excessive))
                with patch.object(updater, 'ROOT', root), patch('sys.argv', argv), \
                        patch.object(updater, 'collect', side_effect=AssertionError('Reject excessive budget before collection')), \
                        patch('sys.stderr', new_callable=io.StringIO):
                    with self.assertRaises(SystemExit) as raised:
                        updater.main()
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse(path.exists())

    def test_cli_rejects_negative_budgets(self):
        for flag in ('--release-budget', '--scorecard-budget', '--max-seconds'):
            with self.subTest(flag=flag), patch('sys.argv', ['update_signals.py', flag, '-1']), \
                    patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as raised:
                    updater.main()
                self.assertEqual(raised.exception.code, 2)


class ReviewEdgeCaseTests(OfflineCase):
    def test_deadline_between_checks_never_fabricates_an_attempt(self):
        fetch = Mock(side_effect=AssertionError('No request should start'))
        clock = Mock(side_effect=[0, 0, 1, 1])
        document, summary = self.collect(providers=('release',), max_seconds=1,
                                         fetch=fetch, monotonic=clock)
        fetch.assert_not_called()
        record = document['repositories'][REPO]['release']
        self.assertIsNone(record['checked_at'])
        self.assertEqual(record['fetch_status'], 'not_checked')
        self.assertEqual(summary, {'release:budget_deferred': 1})

    def test_oversized_retry_after_falls_back_without_losing_data(self):
        previous = self.snapshot(now=NOW - timedelta(days=8))
        fetch = Mock(return_value=(429, {'Retry-After': '9' * 200}, None))
        document, _ = self.collect(previous=previous, providers=('release',), fetch=fetch)
        record = document['repositories'][REPO]['release']
        self.assertEqual(record['last_good'], previous['repositories'][REPO]['release']['last_good'])
        self.assertEqual(record['retry_after'], signals.iso(NOW + timedelta(hours=1)))

    def test_304_updates_validator_without_changing_observation(self):
        previous = self.snapshot(now=NOW - timedelta(days=8))
        fetch = Mock(return_value=(304, {'ETag': '"new-validator"'}, None))
        document, _ = self.collect(previous=previous, fetch=fetch)
        for provider in signals.PROVIDERS:
            record = document['repositories'][REPO][provider]
            self.assertEqual(record['etag'], '"new-validator"')
            self.assertEqual(record['last_good'], previous['repositories'][REPO][provider]['last_good'])


if __name__ == '__main__':
    unittest.main()
