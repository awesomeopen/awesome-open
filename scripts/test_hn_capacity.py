"""Offline capacity, daily budget and stars-first scheduling regressions."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import update_hn as hn
from test_hn_queue import NOW, empty, page, project


def projects(prefix, count):
    return [project(f'Open{prefix}{i:03}') for i in range(count)]


def collect(items, **kwargs):
    options = dict(now=NOW, projects=items, existing=empty(), metadata={}, getter=page)
    options.update(kwargs)
    return hn.refresh(**options)


class CapacityTests(unittest.TestCase):
    def test_defaults_and_config_ceiling(self):
        self.assertEqual((hn.DEFAULT_PROJECTS, hn.DEFAULT_REQUESTS, hn.DEFAULT_SECONDS), (50, 160, 300))
        result = collect(projects('New', 60))
        self.assertEqual(result['budget']['projects_used'], 50)
        self.assertEqual(result['budget']['requests_used'], 50)
        self.assertEqual(len(result['projects']), 50)
        with self.assertRaises(ValueError):
            collect([], max_projects=51)

    def test_daily_project_limit_across_runs_and_next_day_reset(self):
        items = projects('New', 60)
        first = collect(items, max_projects=20)
        second = collect(items, existing=first, max_projects=50)
        self.assertEqual(second['selection_report']['attempted_projects'], 30)
        self.assertEqual(second['budget']['projects_used'], 50)
        third = collect(items, existing=second)
        self.assertEqual(third['selection_report']['attempted_projects'], 0)
        self.assertEqual(third['budget'], second['budget'])
        tomorrow = collect(items, existing=third, now=NOW + timedelta(days=1))
        self.assertEqual(tomorrow['selection_report']['attempted_projects'], 10)
        self.assertEqual(tomorrow['budget']['projects_used'], 10)
        self.assertEqual(len(tomorrow['projects']), 60)

    def test_invocation_guard_survives_lost_snapshot(self):
        items = projects('New', 60)
        with tempfile.TemporaryDirectory() as directory:
            guard = Path(directory) / 'budget.json'
            first = collect(items, max_projects=20, invocation_budget_file=guard)
            second = collect(items, existing=empty(), invocation_budget_file=guard)
            self.assertEqual(second['selection_report']['attempted_projects'], 30)
            self.assertEqual(second['budget']['projects_used'], 50)
            self.assertEqual(len(set(second['budget']['attempted_urls'])), 50)
            self.assertEqual(second['budget']['requests_used'], 50)
            self.assertTrue(set(first['budget']['attempted_urls']).issubset(second['budget']['attempted_urls']))
            self.assertEqual(second['selection_report']['never_attempted_projects'], 10)
            old_key = first['budget']['attempted_urls'][0]
            self.assertEqual(second['queue'][old_key]['status'], 'unavailable')

    def test_new_backlog_stars_descending_zero_before_unknown(self):
        items = projects('New', 5)
        metadata = {'repositories': {
            items[0]['repositories'][0]: {'stargazers_count': None},
            items[1]['repositories'][0]: {'stargazers_count': 0},
            items[2]['repositories'][0]: {'stargazers_count': 99},
            items[3]['repositories'][0]: {'stargazers_count': 99},
        }}
        seen = []
        def getter(url):
            seen.append(parse_qs(urlsplit(url).query)['query'][0])
            return page(url)
        collect(items, metadata=metadata, getter=getter)
        self.assertEqual(seen, [items[i]['name'] for i in (2, 3, 1, 0, 4)])

    def test_refresh_share_survives_large_new_backlog(self):
        old = projects('Old', 40)
        new = projects('New', 70)
        cache = collect(old, now=NOW - timedelta(days=31))
        result = collect(new + old, existing=cache)
        lanes = result['budget']['lane_projects']
        self.assertGreaterEqual(lanes['new'], 20)
        self.assertGreaterEqual(lanes['refresh'], 25)
        self.assertEqual(sum(lanes.values()), 50)
        # Fresh records are not counted merely because they were inspected.
        again = collect(new + old, existing=result)
        self.assertEqual(again['selection_report']['attempted_projects'], 0)

    def test_failed_new_identity_rotates_into_refresh_lane(self):
        items = projects('New', 60)
        def failing(url):
            raise OSError('offline')
        first = collect(items, getter=failing)
        result = collect(items, existing=first, now=NOW + timedelta(days=1))
        self.assertEqual(result['budget']['lane_projects']['new'], 10)
        self.assertGreater(result['budget']['lane_projects']['refresh'], 0)

    def test_request_reserves_prevent_large_continuation_from_consuming_day(self):
        continuation = project('OpenBig')
        def crowded(url):
            n = int(parse_qs(urlsplit(url).query)['page'][0])
            result = page(url)
            result['hits'] = [dict(result['hits'][0], objectID=str(100 + n * 100 + i)) for i in range(100)]
            result.update(nbHits=900, nbPages=9)
            return result
        continuation['queries'] = ['OpenBig ' + str(i) for i in range(6)]
        first = collect([continuation], getter=crowded, request_budget=1)
        old = projects('Old', 40)
        old_cache = collect(old, now=NOW - timedelta(days=31))
        first['queue'].update(old_cache['queue'])
        new = projects('New', 60)
        def mixed(url):
            return crowded(url) if 'OpenBig' in url else page(url)
        result = collect([continuation] + old + new, existing=first,
                         now=NOW + timedelta(days=1), getter=mixed)
        self.assertLessEqual(result['budget']['requests_used'], 160)
        self.assertGreaterEqual(result['budget']['lane_projects']['new'], 20)
        self.assertGreaterEqual(result['budget']['lane_projects']['refresh'], 25)
        self.assertGreater(result['budget']['lane_requests']['continuation'], 0)

    def test_stranded_reservations_release_without_exceeding_daily_caps(self):
        new = projects('New', 50)
        for item in new:
            item['queries'] = [item['name'] + ' query' + str(i) for i in range(24)]
        old = projects('Old', 50)
        cache = collect(old, now=NOW - timedelta(days=31))
        result = collect(new + old, existing=cache)
        self.assertEqual(result['budget']['requests_used'], 160)
        self.assertLessEqual(result['budget']['projects_used'], 50)
        self.assertGreaterEqual(result['budget']['lane_projects']['refresh'], 25)
        self.assertGreater(result['budget']['lane_projects']['new'], 0)

    def test_slow_new_project_leaves_time_for_refresh(self):
        old = project('OpenOld')
        new = project('OpenNew')
        new['queries'] = [new['name'] + ' query' + str(i) for i in range(30)]
        cache = collect([old], now=NOW - timedelta(days=31))
        clock = [0]
        def slow(url):
            clock[0] += 15
            return page(url)
        result = collect([new, old], existing=cache, getter=slow, monotonic=lambda: clock[0])
        self.assertEqual(result['budget']['lane_projects']['new'], 1)
        self.assertEqual(result['budget']['lane_projects']['refresh'], 1)
        self.assertLessEqual(clock[0], 300)

    def test_cached_skips_and_expired_deadline_do_not_consume_attempts(self):
        first = collect([project()])
        second = collect([project()], existing=first, now=NOW + timedelta(days=1))
        self.assertEqual(second['budget']['projects_used'], 0)
        self.assertEqual(second['budget']['requests_used'], 0)
        ticks = iter([0, 0, 1000])
        expired = collect([project()], monotonic=lambda: next(ticks), seconds=1)
        self.assertEqual(expired['selection_report']['attempted_projects'], 0)
        self.assertEqual(expired['budget']['projects_used'], 0)
        self.assertEqual(expired['queue'], {})

    def test_month_rollover_resets_daily_quota_and_invalidates_old_partial_pages(self):
        items = [project()]
        first = collect(items)
        rollover = NOW.replace(month=11, day=1)
        seen = []
        def getter(url):
            seen.append(url)
            response = page(url)
            response['hits'][0]['created_at_i'] = int(hn.window(rollover)[0].timestamp())
            return response
        result = collect(items, existing=first, now=rollover, getter=getter)
        self.assertEqual(result['budget']['projects_used'], 1)
        self.assertEqual(result['budget']['requests_used'], 1)
        self.assertEqual(result['budget']['lane_projects']['refresh'], 1)
        self.assertEqual(result['months'][-1], '2026-10')
        self.assertTrue(seen)

    def test_force_cannot_reconsume_same_day_project(self):
        first = collect([project()])
        second = collect([project()], existing=first, force=True)
        self.assertEqual(second['selection_report']['attempted_projects'], 0)
        self.assertEqual(second['budget']['projects_used'], 1)

    def test_legacy_same_day_attempt_is_not_repeated(self):
        first = collect([project()])
        first['budget'] = {'utc_date': NOW.date().isoformat(), 'requests_used': 1, 'limit': 80, 'paused': False}
        result = collect([project()], existing=first, force=True)
        self.assertEqual(result['selection_report']['attempted_projects'], 0)
        self.assertEqual(result['budget']['projects_used'], 1)
        self.assertEqual(result['budget']['requests_used'], 1)

    def test_requests_stop_at_midnight_without_phantom_attempt(self):
        from datetime import datetime
        class CrossingClock(datetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return NOW if cls.calls < 3 else NOW + timedelta(days=1)
        with patch.object(hn, 'datetime', CrossingClock):
            result = collect([project()], now=None)
        self.assertEqual(result['budget']['projects_used'], 0)
        self.assertEqual(result['budget']['requests_used'], 0)
        self.assertEqual(result['queue'], {})

    def test_corrupt_project_guard_fails_before_request(self):
        first = collect([project()])
        first['budget']['projects_used'] = -1
        with self.assertRaises(ValueError):
            collect([project()], existing=first)


if __name__ == '__main__':
    unittest.main()
