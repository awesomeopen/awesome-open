"""Offline ranking, freeze and trophy contracts for the weekly scoreboard."""
from copy import deepcopy
from datetime import date
import hashlib
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from build_catalog import canonical_url
import weekly_scoreboard as scoreboard


TODAY = date(2026, 10, 30)


def project(slug='one', **github):
    url = 'https://github.com/example/' + slug
    return {'id': hashlib.sha256(canonical_url(url).encode()).hexdigest(),
            'name': 'Open ' + slug, 'url': url, 'github': github}


def catalog(*projects):
    return {'metrics_as_of': '2026-10-28', 'projects': list(projects)}


def evidence(*projects):
    return {'window_start': '2026-10-01', 'window_end_exclusive': '2026-10-29',
            'projects': list(projects)}


def hn(p, *stories):
    return {'readme_url': p['url'], 'search_url': 'https://hn.algolia.com/',
            'coverage': 'reviewed', 'stories': list(stories)}


def story(identifier, timestamp):
    return {'id': identifier, 'created_at': timestamp}


def release(p, timestamp):
    p['signals'] = {'release': {'status': 'fresh', 'last_good': {
        'fetched_at': '2026-10-28T12:00:00Z', 'value': {'published_at': timestamp}}}}
    return p


def board(doc, key):
    return next(m for m in doc['metrics'] if m['id'] == key)


def rename(identifier, kind='software_rename'):
    return {'id': identifier, 'kind': kind, 'old_name': 'Old', 'new_name': 'Open New',
            'sources': [{'url': 'https://example.com/announcement'}],
            'occurred': {'value': '2020-01-01', 'precision': 'day'}}


class ScoreboardTests(unittest.TestCase):
    def snapshot(self, *projects, hn_evidence=None, today=TODAY):
        return scoreboard.snapshot(catalog(*projects), hn_evidence or evidence(), today)

    def test_six_boards_present_even_without_evidence(self):
        doc = self.snapshot(project())
        self.assertEqual([m['id'] for m in doc['metrics']], [
            'oldest-repository', 'release-push-gap', 'software-renames',
            'hn-streak', 'hn-stories', 'github-stars'])
        self.assertTrue(all(m['rows'] == [] and m['eligible_count'] == 0 for m in doc['metrics']))

    def test_oldest_uses_metrics_snapshot_day_not_recording_day(self):
        p = project(created_at='2026-10-01T23:30:00-02:00')
        a = self.snapshot(p)
        b = self.snapshot(p, today=date(2030, 1, 1))
        self.assertEqual(board(a, 'oldest-repository')['rows'][0]['value'], 26)
        self.assertEqual(a['metrics'], b['metrics'])

    def test_future_and_unavailable_repository_dates_excluded(self):
        doc = self.snapshot(project('future', created_at='2026-10-29'),
                            project('unknown', created_at='2020-01-01', status='unavailable'))
        self.assertEqual(board(doc, 'oldest-repository')['rows'], [])

    def test_release_gap_is_signed_positive_utc_calendar_days(self):
        valid = release(project('valid', pushed_at='2026-10-20T23:30:00-02:00'),
                        '2026-10-18T23:30:00-02:00')
        same = release(project('same', pushed_at='2026-10-20T23:00:00Z'),
                       '2026-10-20T00:00:00Z')
        negative = release(project('negative', pushed_at='2026-10-19'), '2026-10-20')
        missing_release = project('missing-release', pushed_at='2026-10-20')
        missing_push = release(project('missing-push'), '2026-10-20')
        future = release(project('future', pushed_at='2026-10-29'), '2026-10-20')
        doc = self.snapshot(valid, same, negative, missing_release, missing_push, future)
        rows = board(doc, 'release-push-gap')['rows']
        self.assertEqual([(r['id'], r['value']) for r in rows], [(valid['id'], 2)])

    def test_only_unique_software_renames_count(self):
        p = project()
        p['history'] = [rename('a'), rename('a'), rename('b'),
                        rename('c', 'repository_rename'), rename('d', 'owner_transfer')]
        row = board(self.snapshot(p), 'software-renames')['rows'][0]
        self.assertEqual(row['value'], 2)
        self.assertEqual({e['id'] for e in row['details']['events']}, {'a', 'b'})

    def test_streak_unique_consecutive_utc_days_and_window_boundaries(self):
        stories = [story(0, '2026-09-30T12:00:00Z'), story(1, '2026-10-01T00:00:00Z'),
                   story(2, '2026-10-01T23:30:00-02:00'),
                   story(3, '2026-10-02T18:00:00Z'), story(3, '2026-10-02T18:00:00Z'),
                   story(4, '2026-10-04'), story(5, '2026-10-28'),
                   story(6, '2026-10-29T00:00:00Z'), story(7, 'invalid')]
        self.assertEqual(scoreboard.longest_streak(stories, date(2026, 10, 1), date(2026, 10, 29)),
                         (2, '2026-10-01', '2026-10-02'))
        self.assertEqual(scoreboard.longest_streak([], date(2026, 10, 1), date(2026, 10, 29)),
                         (0, None, None))

    def test_streak_equal_runs_keep_earliest_dates(self):
        stories = [story(i, '2026-10-%02d' % day) for i, day in enumerate([7, 8, 2, 3])]
        self.assertEqual(scoreboard.longest_streak(stories, date(2026, 10, 1), date(2026, 10, 29)),
                         (2, '2026-10-02', '2026-10-03'))

    def test_hn_stories_deduplicate_ids_and_streak_deduplicates_days(self):
        p = project()
        rows = [story(1, '2026-10-01'), story('1', '2026-10-01'),
                story(2, '2026-10-01'), story(3, '2026-10-02')]
        doc = self.snapshot(p, hn_evidence=evidence(hn(p, *rows)))
        self.assertEqual(board(doc, 'hn-stories')['rows'][0]['value'], 3)
        self.assertEqual(board(doc, 'hn-streak')['rows'][0]['value'], 2)

    def test_competition_ranks_and_stable_id_tie_order(self):
        projects = [project('z', stars=10), project('a', stars=10), project('c', stars=9)]
        rows = board(self.snapshot(*projects), 'github-stars')['rows']
        self.assertEqual([r['rank'] for r in rows], [1, 1, 3])
        self.assertEqual([r['id'] for r in rows[:2]], sorted(p['id'] for p in projects[:2]))
        for p in projects:
            p['name'] = 'Changed display name'
        changed = board(self.snapshot(*reversed(projects)), 'github-stars')['rows']
        self.assertEqual([r['id'] for r in changed], [r['id'] for r in rows])

    def test_ties_at_tenth_place_all_included(self):
        projects = [project(str(i), stars=100-i) for i in range(9)]
        projects += [project('tied-' + str(i), stars=1) for i in range(4)]
        projects += [project('below', stars=0)]
        metric = board(self.snapshot(*projects), 'github-stars')
        self.assertEqual(metric['eligible_count'], 14)
        self.assertEqual(len(metric['rows']), 13)
        self.assertEqual([r['rank'] for r in metric['rows'][-4:]], [10]*4)
        all_tied = board(self.snapshot(*(project(str(i), stars=0) for i in range(15))), 'github-stars')
        self.assertEqual([r['rank'] for r in all_tied['rows']], [1]*15)

    def test_star_values_include_zero_and_stale_but_exclude_unavailable_and_bool(self):
        doc = self.snapshot(project('zero', stars=0), project('stale', stars=5, status='stale'),
                            project('unavailable', stars=10, status='unavailable'),
                            project('boolean', stars=True), project('negative', stars=-1))
        self.assertEqual([r['value'] for r in board(doc, 'github-stars')['rows']], [5, 0])

    def test_first_run_and_same_week_freeze_are_independent_copies(self):
        c = catalog(project(stars=5))
        doc = scoreboard.advance(None, c, evidence(), date(2026, 10, 26))
        self.assertEqual(doc['week'], '2026-10-26')
        self.assertEqual(doc['recorded_on'], '2026-10-26')
        c['projects'][0]['github']['stars'] = 999
        frozen = scoreboard.advance(doc, c, evidence(), date(2026, 11, 1))
        self.assertEqual(frozen, doc)
        frozen['metrics'][0]['title'] = 'Mutated copy'
        self.assertNotEqual(frozen, doc)

    def test_next_week_refreshes_and_missed_weeks_are_not_backfilled(self):
        c = catalog(project(stars=5))
        doc = scoreboard.advance(None, c, evidence(), TODAY)
        c['projects'][0]['github']['stars'] = 9
        for day, week in [(date(2026, 11, 2), '2026-11-02'), (date(2026, 12, 9), '2026-12-07')]:
            with self.subTest(day=day):
                next_doc = scoreboard.advance(doc, c, evidence(), day)
                self.assertEqual(next_doc['week'], week)
                self.assertEqual(next_doc['recorded_on'], day.isoformat())
                self.assertEqual(board(next_doc, 'github-stars')['rows'][0]['value'], 9)

    def test_clock_backwards_rejected_even_within_same_week(self):
        doc = self.snapshot(project())
        for day in [date(2026, 10, 29), date(2026, 10, 19)]:
            with self.subTest(day=day), self.assertRaises(ValueError):
                scoreboard.advance(doc, catalog(), evidence(), day)

    def test_trophies_use_frozen_top_three_and_only_current_ids(self):
        projects = [project(str(i), stars=10-i) for i in range(5)]
        doc = self.snapshot(*projects)
        current = catalog(deepcopy(projects[0]), deepcopy(projects[2]), deepcopy(projects[3]),
                          project('new', stars=10000))
        for p in current['projects']:
            p['github']['stars'] = 999
            p['scoreboard_trophies'] = [{'metric': 'obsolete'}]
        scoreboard.attach(current, doc)
        for p, rank, value in [(current['projects'][0], 1, 10), (current['projects'][1], 3, 8)]:
            trophy = p['scoreboard_trophies'][0]
            self.assertEqual((trophy['rank'], trophy['value'], trophy['week']), (rank, value, doc['week']))
        self.assertNotIn('scoreboard_trophies', current['projects'][2])
        self.assertNotIn('scoreboard_trophies', current['projects'][3])
        scoreboard.attach(current, None)
        self.assertTrue(all('scoreboard_trophies' not in p for p in current['projects']))

    def test_tied_top_three_trophies_follow_competition_places(self):
        projects = [project(str(i), stars=10 if i < 3 else 9) for i in range(4)]
        c = catalog(*projects)
        scoreboard.attach(c, self.snapshot(*projects))
        self.assertEqual([p['scoreboard_trophies'][0]['rank'] for p in projects[:3]], [1, 1, 1])
        self.assertNotIn('scoreboard_trophies', projects[3])

    def test_validation_rejects_bad_identity_rank_order_and_duplicates(self):
        original = self.snapshot(project('a', stars=10), project('b', stars=10), project('c', stars=9))
        mutations = [lambda rows: rows[0].update(id='a'*64),
                     lambda rows: rows[0].update(url='https://example.com/wrong'),
                     lambda rows: rows[0].update(rank=2),
                     lambda rows: rows[2].update(rank=2),
                     lambda rows: rows.reverse(),
                     lambda rows: rows.__setitem__(1, deepcopy(rows[0]))]
        for mutate in mutations:
            doc = deepcopy(original)
            mutate(board(doc, 'github-stars')['rows'])
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                scoreboard.validate(doc)


class ScoreboardIntegrationTests(unittest.TestCase):
    def valid_evidence(self):
        months = ['%04d-%02d' % (year, month) for year in (2024, 2025) for month in range(1, 13)]
        return {'schema_version': 2, 'months': months, 'projects': [],
                'window_start': '2024-01-01', 'window_end_exclusive': '2026-01-01', 'queue': {}}

    def root_fixture(self, directory):
        root = Path(directory)
        (root / 'data').mkdir()
        (root / 'README.source.md').write_text('Synthetic catalog')
        (root / 'data/hn_evidence.json').write_text(json.dumps(self.valid_evidence()))
        return root

    def test_publisher_orders_scoreboard_after_collectors_and_render_with_attempt_sha(self):
        import publish_readme as publisher
        root = Path('/synthetic-checkout')
        with patch.object(publisher, 'run') as run, patch.object(
                publisher, 'git', return_value=SimpleNamespace(stdout='a'*40 + '\n')) as git:
            publisher.collect_and_render(root)
        scripts = [call.args[2] for call in run.call_args_list]
        scoreboard_index = scripts.index('scripts/weekly_scoreboard.py')
        for script in ('update_stats', 'update_hn', 'update_signals', 'update_star_history', 'render_readme'):
            self.assertLess(scripts.index('scripts/' + script + '.py'), scoreboard_index)
        self.assertEqual(run.call_args_list[scoreboard_index].args[-2:], ('--source-sha', 'a'*40))
        git.assert_called_once_with(root, 'rev-parse', 'HEAD')

    def test_publisher_generated_allowlist_has_exact_scoreboard_path(self):
        import publish_readme as publisher
        self.assertTrue(publisher.allowed_path('data/weekly_scoreboard.json'))
        for path in ('data/other_scoreboard.json', 'data/weekly_scoreboard.json.tmp',
                     'data/weekly_scoreboard.json/extra', 'data/private.json'):
            with self.subTest(path=path):
                self.assertFalse(publisher.allowed_path(path))

    def test_update_reload_preserves_same_week_snapshot_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root_fixture(directory)
            c = catalog(project(stars=5))
            with patch.object(scoreboard, 'build_catalog', return_value=c):
                first = scoreboard.update(root, 'a'*40, TODAY)
            path = root / scoreboard.PATH
            original = path.read_bytes()
            c['projects'][0]['github']['stars'] = 900
            with patch.object(scoreboard, 'build_catalog', return_value=c):
                second = scoreboard.update(root, 'b'*40, date(2026, 11, 1))
            self.assertEqual(second, first)
            self.assertEqual(scoreboard.load(path), first)
            self.assertEqual(path.read_bytes(), original)

    def test_update_rejects_target_race_and_new_optional_input(self):
        for mutated in (scoreboard.PATH, 'data/project_history.json'):
            with self.subTest(mutated=mutated), tempfile.TemporaryDirectory() as directory:
                root = self.root_fixture(directory)
                with patch.object(scoreboard, 'build_catalog', return_value=catalog(project(stars=5))):
                    scoreboard.update(root, 'a'*40, TODAY)
                original = (root / scoreboard.PATH).read_bytes()
                actual_advance = scoreboard.advance
                def racing_advance(*args, **kwargs):
                    result = actual_advance(*args, **kwargs)
                    (root / mutated).write_text('{}')
                    return result
                with patch.object(scoreboard, 'build_catalog', return_value=catalog(project(stars=5))), \
                        patch.object(scoreboard, 'advance', side_effect=racing_advance), \
                        self.assertRaisesRegex(ValueError, 'inputs changed'):
                    scoreboard.update(root, 'b'*40, date(2026, 11, 2))
                if mutated == scoreboard.PATH:
                    self.assertEqual((root / scoreboard.PATH).read_text(), '{}')
                else:
                    self.assertEqual((root / scoreboard.PATH).read_bytes(), original)

    def test_update_rejects_invalid_raw_hn_before_building_catalog(self):
        for invalid in ({'schema_version': 999}, {'schema_version': 2, 'projects': []}):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = self.root_fixture(directory)
                (root / 'data/hn_evidence.json').write_text(json.dumps(invalid))
                with patch.object(scoreboard, 'build_catalog') as builder, self.assertRaises(ValueError):
                    scoreboard.update(root, 'a'*40, TODAY)
                builder.assert_not_called()
                self.assertFalse((root / scoreboard.PATH).exists())

    def test_hn_window_must_agree_with_twenty_four_month_sequence(self):
        scoreboard.validate_evidence(self.valid_evidence())
        for field, value in [('window_start', '2024-01-02'), ('window_end_exclusive', '2026-02-01'),
                             ('months', ['2023-12'] + self.valid_evidence()['months'][1:])]:
            doc = self.valid_evidence()
            doc[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                scoreboard.validate_evidence(doc)

    def test_site_empty_cache_does_not_compute_trophies_but_explicit_preview_is_labeled(self):
        import build_site
        import build_scoreboard
        class StopAfterCatalog(Exception):
            pass
        for preview in (False, True):
            with self.subTest(preview=preview), tempfile.TemporaryDirectory() as directory:
                root = self.root_fixture(directory)
                (root / 'data/github_metrics.json').write_text('{}')
                (root / 'data/alternatives.json').write_text('{}')
                (root / 'site').mkdir()
                (root / 'site/catalog.js').write_text('// synthetic runtime')
                c = catalog(project(stars=5))
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(build_site, 'build_catalog', return_value=c))
                    for name in ('load_function_summaries', 'attach_specimen_art', 'attach_category_art',
                                 'attach_specimen_cutouts', 'attach_specimen_variants'):
                        stack.enter_context(patch.object(build_site, name, return_value={}))
                    stack.enter_context(patch.object(build_site, 'discover_footer_art', return_value={}))
                    stack.enter_context(patch.object(build_site, 'display_hn_evidence', return_value={'shared_monthly_maximum': 0}))
                    renderer = stack.enter_context(patch.object(build_site, 'render_html', side_effect=StopAfterCatalog))
                    compute = stack.enter_context(patch.object(scoreboard, 'snapshot', wraps=scoreboard.snapshot))
                    with self.assertRaises(StopAfterCatalog):
                        build_site.build(root / 'output', root=root, scoreboard_preview=preview)
                renderer.assert_called_once()
                if preview:
                    compute.assert_called_once()
                    self.assertTrue(c['scoreboard_edition']['preview'])
                    self.assertTrue(c['projects'][0]['scoreboard_trophies'][0]['preview'])
                    self.assertIn('Preview', build_scoreboard.trophy_links(c['projects'][0]))
                else:
                    compute.assert_not_called()
                    self.assertIsNone(c['scoreboard_edition'])
                    self.assertNotIn('scoreboard_trophies', c['projects'][0])
                    self.assertEqual(build_scoreboard.trophy_links(c['projects'][0]), '')
                self.assertFalse((root / scoreboard.PATH).exists())

    def test_scoreboard_route_empty_and_preview_output(self):
        import build_scoreboard
        root = Path(__file__).resolve().parents[1]
        c = catalog(project(stars=5))
        doc = scoreboard.snapshot(c, self.valid_evidence(), TODAY)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            build_scoreboard.build(c, doc, output, root, preview=True)
            page = (output / 'scoreboard/index.html').read_text()
            self.assertIn('Provisional preview.', page)
            self.assertTrue(json.loads((output / 'scoreboard/snapshot.json').read_text())['preview'])
            for key, _, _, _ in scoreboard.METRICS:
                self.assertIn('id="' + key + '"', page)
            build_scoreboard.build(c, None, output, root)
            page = (output / 'scoreboard/index.html').read_text()
            self.assertIn('first weekly edition', page)
            self.assertNotIn('Download snapshot', page)
            self.assertFalse((output / 'scoreboard/snapshot.json').exists())

    def test_production_cli_forbids_provisional_scoreboard(self):
        script = Path(__file__).with_name('build_site.py')
        result = subprocess.run([sys.executable, str(script), '--production', '--scoreboard-preview'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Provisional Scoreboard is not a production edition', result.stderr)


if __name__ == '__main__':
    unittest.main()
