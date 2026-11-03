"""Offline fresh-main retry handoff regressions."""
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


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.first = hn.refresh(now=NOW, existing=empty(), projects=[project()], metadata={}, getter=page)
        self.archive = observations.add_hn(observations.empty(), self.first)
        self.key = hn.canonical_url(project()['readme_url'])

    def retry(self, **kwargs):
        args = dict(now=NOW + timedelta(minutes=1), existing=empty(), projects=[project()],
                    metadata={}, retry_archive=self.archive,
                    getter=lambda url: self.fail('Retry must not request upstream'))
        args.update(kwargs)
        with tempfile.TemporaryDirectory() as directory:
            budget = Path(directory) / 'budget.json'
            hn.write_evidence(budget, self.first['budget'])
            return hn.refresh(invocation_budget_file=budget, **args)

    def test_fresh_main_retry_preserves_result_dates_and_all_charges(self):
        result = self.retry()
        self.assertEqual(result['projects'], self.first['projects'])
        self.assertEqual(result['queue'][self.key]['last_good'], self.first['queue'][self.key]['last_good'])
        self.assertEqual(result['queue'][self.key]['checked_at'], NOW.isoformat())
        self.assertEqual(result['budget'], self.first['budget'])
        self.assertEqual(result['selection_report']['attempted_projects'], 0)

    def test_reject_changed_query_identity_window_and_removed_project(self):
        for field in ('queries', 'domains', 'readme_url'):
            changed = copy.deepcopy(project())
            changed[field] = ['changed'] if field != 'readme_url' else 'https://example.com/other'
            records = {}
            hn.reconcile_retry_results(records, [changed], hn.window(NOW)[2], NOW, self.archive)
            self.assertEqual(records, {})
        for projects, months in (([], hn.window(NOW)[2]), ([project()], hn.window(NOW + timedelta(days=32))[2])):
            records = {}
            hn.reconcile_retry_results(records, projects, months, NOW, self.archive)
            self.assertEqual(records, {})

    def test_preserve_equal_newer_main_attempts_and_newer_good(self):
        for delta in (0, 1):
            existing = copy.deepcopy(self.first)
            existing['queue'][self.key]['checked_at'] = (NOW + timedelta(seconds=delta)).isoformat()
            existing['queue'][self.key]['status'] = 'unavailable'
            result = self.retry(existing=existing)
            self.assertEqual(result['queue'], existing['queue'])
        records = copy.deepcopy(self.first['queue'])
        records[self.key]['checked_at'] = (NOW - timedelta(days=1)).isoformat()
        before = copy.deepcopy(records)
        hn.reconcile_retry_results(records, [project()], hn.window(NOW)[2], NOW, self.archive)
        self.assertEqual(records, before)

    def test_future_undated_and_partial_results_stay_unavailable(self):
        for mode in ('future', 'undated', 'partial'):
            document = copy.deepcopy(self.first)
            good = document['queue'][self.key]['last_good']
            if mode == 'future':
                good['collected_at'] = (NOW + timedelta(days=1)).isoformat()
            elif mode == 'undated':
                good.pop('collected_at')
            else:
                document['queue'][self.key].pop('last_good')
                document['projects'] = []
            archive = observations.add_hn(observations.empty(), document)
            result = self.retry(retry_archive=archive)
            self.assertEqual(result['projects'], [])
            self.assertEqual(result['queue'][self.key]['status'], 'unavailable')
            self.assertEqual(result['budget'], self.first['budget'])

    def test_malformed_archive_fails_before_request(self):
        damaged = copy.deepcopy(self.archive)
        next(iter(damaged['objects'].values()))['value'] = {}
        with self.assertRaises(ValueError):
            self.retry(retry_archive=damaged)

    def test_cli_handoff_survives_discarded_worktree_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / 'hn_evidence.json'
            guard = root / 'invocation' / 'hn-budget.json'
            guard.parent.mkdir()
            original_refresh = hn.refresh
            def refresh(**kwargs):
                return original_refresh(now=NOW, projects=[project()], metadata={}, **kwargs)
            with patch.object(hn, 'EVIDENCE_PATH', evidence), patch.object(hn, 'refresh', side_effect=refresh), \
                    patch.object(hn, 'fetch_page', side_effect=page) as fetch, patch.object(hn.time, 'sleep'), \
                    patch('sys.argv', ['update_hn.py', '--invocation-budget-file', str(guard)]):
                hn.write_evidence(evidence, empty())
                hn.main()
                first = json.loads(evidence.read_text())
                calls = fetch.call_count
                # A fresh-main worktree replaces the entire cache/archive.
                hn.write_evidence(evidence, empty())
                (root / 'chart_observations.json').unlink()
                hn.main()
                result = json.loads(evidence.read_text())
            self.assertEqual(fetch.call_count, calls)
            self.assertEqual(result['projects'], first['projects'])
            self.assertEqual(result['budget'], first['budget'])
            self.assertEqual(result['queue'][self.key]['last_good'], first['queue'][self.key]['last_good'])
            self.assertEqual(result['queue'][self.key]['checked_at'], first['queue'][self.key]['checked_at'])
