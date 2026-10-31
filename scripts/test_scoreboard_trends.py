"""Static history renderer regression tests; no network."""
import unittest
from datetime import date

from scoreboard_trends import (month_keys, monthly_series, svg_chart, series_html,
                               rename_html, creation_html, monthly_stories_html, streak_html)


def observation(day, points):
    return {'recorded_on': day, 'source_sha': 'a' * 40, 'coverage': 'all-eligible',
            'metrics': {'github-stars': {'eligible_count': len(points), 'points': points}}}


def synthetic_series():
    """Multiple actual captures with an explicit missing month for browser QA."""
    row = {'id': 'example', 'name': 'Synthetic project', 'value': 9, 'details': {}}
    metric = {'id': 'github-stars', 'title': 'Cached stars', 'unit': 'stars'}
    view = {'observations': [
        observation('2026-06-12', [['example', 0, {'metrics_observed_at': '2026-06-10'}]]),
        observation('2026-07-28', [['example', 4, {'metrics_observed_at': '2026-07-27'}]]),
        observation('2026-08-10', []),
        observation('2026-09-04', [['example', 7, {'metrics_observed_at': '2026-09-02'}]]),
        observation('2026-10-31', [['example', 9, {'metrics_observed_at': '2026-10-30'}]])]}
    return series_html(view, metric, row, date(2026, 10, 31))


class TrendsTests(unittest.TestCase):
    def test_months_cross_year(self):
        self.assertEqual(month_keys(date(2026, 2, 1), 3), ['2025-12', '2026-01', '2026-02'])

    def test_latest_missing_is_not_carried_forward(self):
        view = {'observations': [
            observation('2026-10-01', [['p', 2, {}]]),
            observation('2026-10-20', []),
            observation('2026-11-01', [['p', 8, {}]])]}
        series = monthly_series(view, 'github-stars', 'p', date(2026, 10, 31))
        self.assertEqual(series[-1][1]['recorded_on'], '2026-10-20')
        self.assertIsNone(series[-1][2])

    def test_points_zero_and_gap(self):
        html = svg_chart('Example', ['2026-08', '2026-09', '2026-10'], [0, None, 3], 'stars')
        self.assertEqual(html.count('class="score-point"'), 2)
        self.assertNotIn('class="score-series"', html)
        self.assertIn('0 stars', html)

    def test_actual_capture_positions_and_release(self):
        html = svg_chart('Gap', ['2026-09', '2026-10'], [1, 4], 'days',
                         [('2026-09-12T00:00:00Z', 'Release 1')],
                         ['2026-09-30', '2026-10-31'])
        self.assertIn('data-captured="2026-09-30"', html)
        self.assertEqual(html.count('class="score-series"'), 1)
        self.assertEqual(html.count('class="score-release"'), 1)
        self.assertIn('2026-09-12T00:00:00Z', html)

    def test_fixture_preserves_missing_and_source_dates(self):
        html = synthetic_series()
        self.assertEqual(html.count('class="score-series"'), 2)
        self.assertEqual(html.count('class="score-point"'), 4)
        self.assertIn('No retained value', html)
        self.assertIn('source dated 2026-06-10', html)
        self.assertIn('2026-06-12', html)

    def test_one_point_not_growth(self):
        view = {'observations': [observation('2026-10-31', [['p', 2, {}]])]}
        html = series_html(view, {'id': 'github-stars', 'title': 'Stars', 'unit': 'stars'},
                           {'id': 'p', 'name': 'Name'}, date(2026, 10, 31))
        self.assertIn('One point is available', html)
        self.assertNotIn('class="score-series"', html)

    def test_rename_dates_distinct_and_escaped(self):
        html = rename_html({'details': {'events': [{
            'old_name': '<old>', 'new_name': 'New', 'occurred': {'value': '2020', 'precision': 'year'},
            'checked_at': '2026-10-31', 'first_observed_at': '2026-10-01',
            'sources': [{'url': 'https://example.org', 'title': 'Evidence'}]}]}})
        self.assertIn('2020 (year)', html)
        self.assertIn('First recorded: 2026-10-01', html)
        self.assertIn('Evidence reviewed: 2026-10-31', html)
        self.assertIn('&lt;old&gt;', html)
        self.assertNotIn('<svg', html)

    def test_single_day_streak_is_one_point(self):
        html = streak_html({'value': 1, 'details': {'first_day': '2026-10-01', 'last_day': '2026-10-01'}},
                           {'hn_window': {'start': '2024-10-01', 'end_exclusive': '2026-10-31'}})
        self.assertEqual(html.count('class="score-point"'), 1)
        self.assertNotIn('class="score-series"', html)

    def test_release_gap_step_and_source_title_fallback(self):
        html = svg_chart('Gap', ['2026-09', '2026-10'], [2, 4], 'days', step=True)
        self.assertIn(' H', html)
        self.assertNotIn(' L', html)
        renamed = rename_html({'details': {'events': [{'old_name': 'A', 'new_name': 'B',
                              'sources': [{'url': 'https://example.org'}]}]}})
        self.assertIn('https://example.org</a>', renamed)

    def test_creation_is_date_comparison(self):
        html = creation_html([{'name': 'A', 'details': {'created_at': '2008-01-03T00:00:00Z'}},
                              {'name': 'B', 'details': {'created_at': '2010-02-04T00:00:00Z'}}])
        self.assertIn('2008-01-03', html)
        self.assertNotIn('class="score-series"', html)

    def test_legacy_monthly_unknown_not_zero(self):
        html = monthly_stories_html({'details': {}}, {})
        self.assertIn('not retained', html)
        self.assertNotIn('<rect', html)

    def test_monthly_bins_preserved_not_cumulative(self):
        html = monthly_stories_html({'details': {'monthly_stories': [
            {'month': '2026-09', 'value': 0}, {'month': '2026-10', 'value': 4}],
            'collected_at': '2026-10-30', 'coverage': 'exact'}}, {})
        self.assertEqual(html.count('class="score-bar"'), 2)
        self.assertIn('2026-09: 0 stories', html)
        self.assertIn('2026-10: 4 stories', html)


if __name__ == '__main__':
    unittest.main()
