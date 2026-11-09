"""Offline recovery of completed observations lost from publisher caches."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chart_observations as observations
import update_hn as hn
from test_hn_queue import NOW, empty, page, project


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.completed = hn.refresh(now=NOW, existing=empty(), projects=[project()],
                                    metadata={}, getter=page)
        self.archive = observations.add_hn(observations.empty(), self.completed)
        self.key = hn.canonical_url(project()['readme_url'])
        self.good = copy.deepcopy(self.completed['queue'][self.key]['last_good'])
        self.placeholder = {'status': 'unavailable', 'checked_at': (NOW + timedelta(minutes=1)).isoformat(),
                            'error': hn.LOST_RESULT, 'pending': {}, 'pending_months': self.good['months'],
                            'pending_identity_key': self.good['identity_key']}

    def recover(self, record=None, archive=None, **kwargs):
        records = {self.key: copy.deepcopy(self.placeholder if record is None else record)}
        before = copy.deepcopy(records)
        args = dict(projects=[project()], months=hn.window(NOW)[2], now=NOW + timedelta(minutes=2))
        args.update(kwargs)
        result = hn.recover_lost_results(records, archive=self.archive if archive is None else archive, **args)
        return result, records, before

    def test_restore_exact_payload_and_preserve_attempt_provenance(self):
        result, records, before = self.recover()
        self.assertEqual(set(result), {self.key})
        self.assertEqual(observations.materialize(self.archive, self.archive['observations'][result[self.key]]), self.good)
        self.assertEqual(records[self.key].pop('last_good'), self.good)
        self.assertEqual(records, before)

    def test_recovery_is_idempotent(self):
        _, records, _ = self.recover()
        result, after, before = self.recover(records[self.key])
        self.assertEqual(result, {})
        self.assertEqual(after, before)

    def test_only_synthetic_lost_results_are_recovered(self):
        for update in ({'status': 'ok'}, {'status': 'deferred'}, {'error': 'Algolia collection failed'},
                       {'pending': {'incomplete': {}}}):
            with self.subTest(update=update):
                result, after, before = self.recover({**self.placeholder, **update})
                self.assertEqual(result, {})
                self.assertEqual(after, before)

    def test_current_or_undated_good_is_preserved(self):
        for good in (self.good, {k: v for k, v in self.good.items() if k != 'collected_at'}):
            result, after, before = self.recover({**self.placeholder, 'last_good': good})
            self.assertEqual(result, {})
            self.assertEqual(after, before)

    def test_previous_window_good_can_be_replaced_by_newer_completed_result(self):
        previous = copy.deepcopy(self.good)
        previous['months'] = hn.window(NOW - timedelta(days=31))[2]
        previous['collected_at'] = (NOW - timedelta(days=31)).isoformat()
        result, after, _ = self.recover({**self.placeholder, 'last_good': previous})
        self.assertEqual(set(result), {self.key})
        self.assertEqual(after[self.key]['last_good'], self.good)

    def test_undated_older_window_can_be_replaced_without_inventing_dates(self):
        previous = copy.deepcopy(self.good)
        previous['months'] = hn.window(NOW - timedelta(days=31))[2]
        previous.pop('collected_at')
        result, after, before = self.recover({**self.placeholder, 'last_good': previous})
        self.assertEqual(set(result), {self.key})
        self.assertEqual(after[self.key]['last_good'], self.good)
        self.assertNotIn('collected_at', before[self.key]['last_good'])

    def test_newer_previous_good_is_preserved(self):
        previous = copy.deepcopy(self.good)
        previous['months'] = hn.window(NOW - timedelta(days=31))[2]
        previous['collected_at'] = (NOW + timedelta(seconds=1)).isoformat()
        result, after, before = self.recover({**self.placeholder, 'last_good': previous})
        self.assertEqual(result, {})
        self.assertEqual(after, before)

    def test_current_and_future_windows_are_preserved_even_for_changed_identity(self):
        for months in (hn.window(NOW)[2], hn.window(NOW + timedelta(days=32))[2]):
            previous = copy.deepcopy(self.good)
            previous['months'] = months
            previous['identity_key'] = 'a' * 64
            previous.pop('collected_at')
            result, after, before = self.recover({**self.placeholder, 'last_good': previous})
            self.assertEqual(result, {})
            self.assertEqual(after, before)

    def test_malformed_previous_window_fails_before_mutation(self):
        previous = copy.deepcopy(self.good)
        previous['months'][0], previous['months'][1] = previous['months'][1], previous['months'][0]
        records = {self.key: {**self.placeholder, 'last_good': previous}}
        before = copy.deepcopy(records)
        with self.assertRaisesRegex(ValueError, 'previous HN recovery window'):
            hn.recover_lost_results(records, [project()], self.good['months'], NOW, self.archive)
        self.assertEqual(records, before)

    def test_identity_window_and_catalog_removal_are_rechecked(self):
        for field in ('queries', 'domains', 'readme_url', 'name'):
            changed = copy.deepcopy(project())
            changed[field] = ['changed'] if field in ('queries', 'domains') else 'changed'
            if field == 'readme_url':
                changed[field] = 'https://example.com/changed'
            with self.subTest(field=field):
                result, after, before = self.recover(projects=[changed])
                self.assertEqual(result, {})
                self.assertEqual(after, before)
        for args in ({'projects': []}, {'months': hn.window(NOW + timedelta(days=32))[2]}):
            result, after, before = self.recover(**args)
            self.assertEqual(result, {})
            self.assertEqual(after, before)

    def test_future_or_post_attempt_evidence_is_ignored(self):
        for args in ({'now': NOW - timedelta(seconds=1)},
                     {'record': {**self.placeholder, 'checked_at': (NOW - timedelta(seconds=1)).isoformat()}}):
            result, after, before = self.recover(**args)
            self.assertEqual(result, {})
            self.assertEqual(after, before)

    def test_undated_and_partial_archive_has_no_recoverable_result(self):
        for mode in ('undated', 'partial'):
            doc = copy.deepcopy(self.completed)
            if mode == 'undated':
                doc['queue'][self.key]['last_good'].pop('collected_at')
            else:
                doc['queue'][self.key].pop('last_good')
                doc['projects'] = []
            archive = observations.add_hn(observations.empty(), doc)
            result, after, before = self.recover(archive=archive)
            self.assertEqual(result, {})
            self.assertEqual(after, before)

    def test_latest_valid_observation_wins_independent_of_archive_order(self):
        newer = copy.deepcopy(self.completed)
        newer['queue'][self.key]['last_good']['collected_at'] = (NOW + timedelta(seconds=1)).isoformat()
        archive = observations.add_hn(copy.deepcopy(self.archive), newer)
        for reverse in (False, True):
            if reverse:
                archive['observations'] = dict(reversed(list(archive['observations'].items())))
            _, records, _ = self.recover(archive=archive)
            self.assertEqual(records[self.key]['last_good'], newer['queue'][self.key]['last_good'])

    def test_same_timestamp_conflict_requires_review(self):
        conflicting = copy.deepcopy(self.completed)
        conflicting['queue'][self.key]['last_good']['project']['search_url'] += '&conflict=1'
        archive = observations.add_hn(copy.deepcopy(self.archive), conflicting)
        result, after, before = self.recover(archive=archive)
        self.assertEqual(result, {})
        self.assertEqual(after, before)

    def test_corrupt_archive_fails_without_mutating_records(self):
        damaged = copy.deepcopy(self.archive)
        next(iter(damaged['objects'].values()))['value'] = {}
        records = {self.key: copy.deepcopy(self.placeholder)}
        before = copy.deepcopy(records)
        with self.assertRaises(ValueError):
            hn.recover_lost_results(records, [project()], self.good['months'], NOW, damaged)
        self.assertEqual(records, before)

    def test_refresh_recovers_without_requests_or_quota_changes(self):
        existing = copy.deepcopy(self.completed)
        existing['queue'][self.key] = copy.deepcopy(self.placeholder)
        existing['projects'] = []
        before = copy.deepcopy(existing)
        archive = copy.deepcopy(self.archive)
        result = hn.refresh(now=NOW + timedelta(minutes=2), existing=existing, projects=[project()],
                            metadata={}, recovery_archive=archive,
                            getter=lambda url: self.fail('Recovery must not query upstream'))
        self.assertEqual(result['projects'], self.completed['projects'])
        self.assertEqual(result['budget'], existing['budget'])
        self.assertEqual(result['selection_report']['attempted_projects'], 0)
        self.assertEqual(result['queue'][self.key], {**self.placeholder, 'last_good': self.good})
        self.assertEqual(existing, before)
        self.assertEqual(archive, self.archive)

    def test_cli_uses_durable_archive_without_invocation_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / 'hn_evidence.json'
            old = copy.deepcopy(self.completed)
            old['queue'][self.key] = copy.deepcopy(self.placeholder)
            old['projects'] = []
            hn.write_evidence(evidence, old)
            observations.save(root / 'chart_observations.json', self.archive)
            original_refresh = hn.refresh
            def refresh(**kwargs):
                return original_refresh(now=NOW + timedelta(minutes=2), projects=[project()], metadata={}, **kwargs)
            with patch.object(hn, 'EVIDENCE_PATH', evidence), patch.object(hn, 'refresh', side_effect=refresh), \
                    patch.object(hn, 'fetch_page', side_effect=AssertionError('Must not query upstream')), \
                    patch('sys.argv', ['update_hn.py']):
                hn.main()
            result = json.loads(evidence.read_text())
            self.assertEqual(result['projects'], self.completed['projects'])
            self.assertEqual(result['budget'], old['budget'])
            self.assertEqual(observations.load(root / 'chart_observations.json'), self.archive)
