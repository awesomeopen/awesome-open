"""Actual, bounded-cadence measurement history for Scoreboard trends."""
from copy import deepcopy
from datetime import date
import unittest

import weekly_scoreboard as scoreboard
from test_weekly_scoreboard import catalog, project, evidence, hn, story, rename, board

DAY = date(2026, 10, 31)
NEXT = date(2026, 11, 2)


def legacy(document):
    result = deepcopy(document)
    result['schema_version'] = 1
    for field in ('history', 'history_projects', 'history_details', 'recorded_at'):
        result.pop(field, None)
    return result


class ScoreboardHistoryTests(unittest.TestCase):
    def capture(self, *projects, day=DAY, hn_evidence=None):
        return scoreboard.snapshot(catalog(*projects), hn_evidence or evidence(), day, 'a' * 40)

    def test_full_capture_keeps_below_top_ten_and_known_zero(self):
        projects = [project(str(i), stars=i) for i in range(14)]
        doc = self.capture(*projects)
        self.assertEqual(doc['schema_version'], 2)
        self.assertEqual(len(board(doc, 'github-stars')['rows']), 10)
        observation = scoreboard.history_view(doc)['observations'][0]
        metric = observation['metrics']['github-stars']
        self.assertEqual(observation['coverage'], 'all-eligible')
        self.assertEqual(metric['eligible_count'], 14)
        self.assertEqual(len(metric['points']), 14)
        self.assertEqual(sorted(point[1] for point in metric['points']), list(range(14)))

    def test_missing_measurement_has_no_point(self):
        known, unknown = project('zero', stars=0), project('unknown')
        metric = scoreboard.history_view(self.capture(known, unknown))['observations'][0]['metrics']['github-stars']
        self.assertEqual(metric['points'][0][:2], [known['id'], 0])
        self.assertEqual(len(metric['points']), 1)

    def test_legacy_view_is_exact_partial_not_invented_full_measurements(self):
        doc = legacy(self.capture(*(project(str(i), stars=i) for i in range(14))))
        before = deepcopy(doc)
        view = scoreboard.history_view(doc)
        self.assertEqual(view['observations'][0]['coverage'], 'top-10-only')
        metric = view['observations'][0]['metrics']['github-stars']
        self.assertEqual(len(metric['points']), 10)
        self.assertEqual(metric['eligible_count'], 14)
        self.assertIsNone(view['observations'][0]['recorded_at'])
        self.assertEqual(doc, before)

    def test_legacy_same_week_does_not_migrate_or_rewrite_measurements(self):
        c = catalog(project(stars=1))
        doc = legacy(scoreboard.snapshot(c, evidence(), DAY, 'a' * 40))
        c['projects'][0]['github']['stars'] = 99
        current = scoreboard.advance(doc, c, evidence(), date(2026, 11, 1), 'b' * 40)
        self.assertEqual(current, doc)
        self.assertEqual(current['schema_version'], 1)

    def test_first_new_week_preserves_prior_partial_and_appends_full_capture(self):
        c = catalog(*(project(str(i), stars=i) for i in range(14)))
        old = legacy(scoreboard.snapshot(c, evidence(), DAY, 'a' * 40))
        frozen = deepcopy(old)
        newer = scoreboard.advance(old, c, evidence(), NEXT, 'b' * 40)
        self.assertEqual([h['coverage'] for h in newer['history']], ['top-10-only', 'all-eligible'])
        self.assertEqual([len(h['metrics']['github-stars']['points']) for h in newer['history']], [10, 14])
        self.assertEqual(scoreboard.history_view(newer)['observations'][0], scoreboard.history_view(old)['observations'][0])
        self.assertEqual(old, frozen)

    def test_missing_weeks_are_not_filled_and_past_observation_is_preserved(self):
        c = catalog(project(stars=1))
        old = self.capture(c['projects'][0])
        frozen = deepcopy(old['history'][0])
        c['projects'][0]['github']['stars'] = 5
        newer = scoreboard.advance(old, c, evidence(), date(2027, 1, 4), 'b' * 40)
        self.assertEqual(len(newer['history']), 2)
        self.assertEqual(newer['history'][0], frozen)
        self.assertEqual(newer['history'][1]['week'], '2027-01-04')
        newer['history'][0]['metrics']['github-stars']['points'][0][1] = 999
        self.assertEqual(old['history'][0], frozen)

    def test_registry_keeps_removed_identity_without_new_measurement(self):
        old_project = project('removed', stars=3)
        old = self.capture(old_project)
        newer = scoreboard.advance(old, catalog(), evidence(), NEXT, 'b' * 40)
        self.assertIn(old_project['id'], scoreboard.history_view(newer)['projects'])
        self.assertEqual(newer['history'][-1]['metrics']['github-stars']['points'], [])
        self.assertEqual(newer['history'][0]['metrics']['github-stars']['points'][0][1], 3)

    def test_source_dates_window_counts_and_real_capture_instant_remain(self):
        c = catalog(project(stars=1))
        doc = scoreboard.snapshot(c, evidence(), DAY, 'a' * 40,
                                  recorded_at='2026-10-31T05:00:00+00:00')
        observation = doc['history'][0]
        self.assertEqual(observation['recorded_on'], '2026-10-31')
        self.assertEqual(observation['recorded_at'], '2026-10-31T05:00:00+00:00')
        self.assertEqual(observation['source_sha'], 'a' * 40)
        self.assertEqual(observation['metrics_as_of'], c['metrics_as_of'])
        self.assertEqual(observation['hn_window']['end_exclusive'], '2026-10-29')
        for bad in ['2026-10-31T05:00:00', '2026-11-03T05:00:00Z', True]:
            broken = deepcopy(doc)
            broken['history'][0]['recorded_at'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scoreboard.validate(broken)

    def test_monthly_hn_counts_are_deduplicated_source_evidence(self):
        p = project()
        e = evidence(hn(p, story(1, '2026-10-01'), story('1', '2026-10-01'),
                        story(2, '2026-10-02')))
        doc = self.capture(p, hn_evidence=e)
        point = scoreboard.history_view(doc)['observations'][0]['metrics']['hn-stories']['points'][0]
        self.assertEqual(point[1], 2)
        self.assertEqual(point[2]['monthly_stories'], [{'month': '2026-10', 'value': 2}])
        broken = deepcopy(doc)
        view = scoreboard.history_view(broken)
        view['observations'][0]['metrics']['hn-stories']['points'][0][2]['monthly_stories'][0]['value'] = 0
        broken['history_projects'], broken['history'] = view['projects'], view['observations']
        scoreboard.pack_history(broken)
        with self.assertRaisesRegex(ValueError, 'monthly HN counts'):
            scoreboard.validate(broken)

    def test_rename_occurrence_review_and_first_observation_stay_distinct(self):
        p = project()
        event = rename('one')
        event.update(checked_at='2026-10-30', first_observed_at='2026-10-29')
        p['history'] = [event]
        recorded = scoreboard.history_view(self.capture(p))['observations'][0]['metrics']['software-renames']['points'][0][2]['events'][0]
        self.assertEqual(recorded['occurred']['value'], '2020-01-01')
        self.assertEqual(recorded['checked_at'], '2026-10-30')
        self.assertEqual(recorded['first_observed_at'], '2026-10-29')

    def test_trophies_include_actual_update_date(self):
        p = project(stars=2)
        c = catalog(p)
        doc = self.capture(p)
        scoreboard.attach(c, doc)
        self.assertEqual(p['scoreboard_trophies'][0]['recorded_on'], '2026-10-31')
        self.assertEqual(p['scoreboard_trophies'][0]['week'], '2026-10-26')

    def test_history_validation_rejects_malformed_coverage_identity_value_and_chronology(self):
        original = self.capture(*(project(str(i), stars=i) for i in range(14)))
        def points(d):
            return d['history'][0]['metrics']['github-stars']['points']
        mutations = [
            lambda d: points(d).pop(),
            lambda d: points(d).append(deepcopy(points(d)[0])),
            lambda d: points(d)[0].__setitem__(0, 'f' * 64),
            lambda d: points(d)[0].__setitem__(1, True),
            lambda d: points(d)[0].__setitem__(1, -1),
            lambda d: d['history'].append(deepcopy(d['history'][0])),
            lambda d: d['history'][0].update(source_sha='not-a-sha'),
            lambda d: d['history'][0].update(coverage='guessed'),
            lambda d: d['history'][0].update(recorded_on='2027-01-01'),
            lambda d: d['history_projects'].append(['bad', 'bad', 'https://example.com']),
            lambda d: points(d)[-1].__setitem__(1, 999),
        ]
        for change in mutations:
            broken = deepcopy(original)
            change(broken)
            with self.subTest(change=change), self.assertRaises(ValueError):
                scoreboard.validate(broken)


    def test_compact_reference_types_ranges_kinds_and_digests_are_strict(self):
        original = self.capture(project(stars=10))
        def point(d):
            return d['history'][0]['metrics']['github-stars']['points'][0]
        mutations = [
            lambda d: point(d).__setitem__(0, True),
            lambda d: point(d).__setitem__(0, -1),
            lambda d: point(d).__setitem__(0, len(d['history_projects'])),
            lambda d: point(d).__setitem__(2, True),
            lambda d: point(d).__setitem__(2, -1),
            lambda d: point(d).__setitem__(2, len(d['history_details'])),
            lambda d: point(d).__setitem__(2, point(d)[3]),
            lambda d: d['history_details'][0].__setitem__(0, '0' * 64),
            lambda d: d['history_details'][0][2].update(invented='changed'),
            lambda d: d['history_details'].append(deepcopy(d['history_details'][0])),
        ]
        for change in mutations:
            broken = deepcopy(original)
            change(broken)
            with self.subTest(change=change), self.assertRaises(ValueError):
                scoreboard.validate(broken)

    def test_compact_pools_append_without_rewriting_old_references(self):
        p = project('existing', stars=10, last_success_at='2026-10-30T12:00:00Z')
        c = catalog(p)
        old = self.capture(p)
        pool, ids, history = deepcopy(old['history_details']), deepcopy(old['history_projects']), deepcopy(old['history'])
        p['github']['last_success_at'] = '2026-11-02T12:00:00Z'
        c['projects'].append(project('new', stars=5))
        newer = scoreboard.advance(old, c, evidence(), NEXT, 'b' * 40)
        self.assertEqual(newer['history_details'][:len(pool)], pool)
        self.assertEqual(newer['history_projects'][:len(ids)], ids)
        self.assertEqual(newer['history'][:len(history)], history)
        self.assertGreater(len(newer['history_details']), len(pool))
        self.assertEqual(old['history_details'], pool)

    def test_resolved_history_is_an_isolated_copy(self):
        doc = self.capture(project(stars=10))
        original = deepcopy(doc)
        view = scoreboard.history_view(doc)
        view['observations'][0]['metrics']['github-stars']['points'][0][2]['metrics_status'] = 'changed'
        next(iter(view['projects'].values()))['name'] = 'Changed'
        self.assertEqual(doc, original)

    def test_provenance_field_partition_cannot_override_facts(self):
        doc = self.capture(project(stars=10))
        item = doc['history_details'][0]
        item[2]['metrics_status'] = 'fresh'
        item[0] = scoreboard.detail_digest(item[1], item[2])
        with self.assertRaisesRegex(ValueError, 'partition'):
            scoreboard.validate(doc)


if __name__ == '__main__':
    unittest.main()
