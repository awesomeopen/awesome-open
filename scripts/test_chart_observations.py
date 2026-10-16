"""Offline retention regressions; generated fixtures never query production APIs."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import chart_observations as archive
import recover_chart_observations as recovery
import update_hn as hn
import update_star_history as stars
from test_hn_queue import NOW as HN_NOW, empty as hn_empty, page, project
from test_update_star_history import NOW, SHA, PROJECT, weekly_series, pager


def star_cache(now=NOW, rows=None):
    return stars.refresh([PROJECT], now=now, source_sha=SHA,
                         getter=pager(rows if rows is not None else weekly_series()))


def window_page(url):
    result = page(url)
    filters = parse_qs(urlsplit(url).query)['numericFilters'][0]
    result['hits'][0]['created_at_i'] = int(filters.split(',')[0].split('>=')[1])
    return result


def hn_cache(now=HN_NOW, identity=None, existing=None, retain=None):
    return hn.refresh(now, projects=[identity or project()], existing=existing or hn_empty(),
                      metadata={}, getter=window_page, retain=retain)


class ArchiveTests(unittest.TestCase):
    def test_current_snapshots_roundtrip_without_changing_original_evidence(self):
        root = Path(__file__).resolve().parents[1]
        data = archive.empty()
        hn_data = json.loads((root / 'data/hn_evidence.json').read_text())
        star_data = json.loads((root / 'data/star_history.json').read_text())
        archive.add_hn(data, hn_data)
        archive.add_stars(data, star_data)
        archive.validate(data)
        for observation in data['observations'].values():
            materialized = archive.materialize(data, observation)
            if observation['kind'] == 'hn':
                expected = hn_data['queue'][observation['identity']]['last_good']
            else:
                materialized = materialized['last_good']
                expected = star_data['repositories'][observation['identity']]['last_good']
            self.assertEqual(materialized, expected)

    def test_identical_cache_deduplicates_and_refresh_reuses_raw_bins(self):
        cache = star_cache()
        data = archive.add_stars(archive.empty(), cache)
        first = deepcopy(data)
        archive.add_stars(data, cache)
        self.assertEqual(data, first)
        later = deepcopy(cache)
        later['repositories'][PROJECT['repo']]['last_good']['fetched_at'] = (NOW + timedelta(days=1)).isoformat()
        archive.add_stars(data, later)
        self.assertEqual(len(data['observations']), 2)
        self.assertEqual(data['objects'], first['objects'])
        archive.validate(data)

    def test_unstars_preserve_both_observations_without_summing_or_rewriting(self):
        first = star_cache()
        rows = weekly_series()
        rows[20]['days'][0] = 0
        rows[20]['total'] -= 1
        second = star_cache(now=NOW + timedelta(days=1), rows=rows)
        data = archive.add_stars(archive.empty(), first)
        archive.add_stars(data, second)
        archive.validate(data)
        values = sorted(sum(archive.materialize(data, o)['last_good']['monthly_counts'])
                        for o in data['observations'].values())
        self.assertEqual(values, [729, 730])
        self.assertEqual(len([v for v in data['objects'].values() if v['kind'] == 'star_week']), 109)

    def test_star_rollover_retains_old_months_and_all_original_raw_bins(self):
        first = star_cache()
        second = star_cache(now=NOW + timedelta(days=33), rows=weekly_series(offset=35 * stars.DAY))
        data = archive.add_stars(archive.empty(), first)
        archive.add_stars(data, second)
        archive.validate(data)
        reconstructed = [archive.materialize(data, o)['last_good'] for o in data['observations'].values()]
        self.assertEqual({g['months'][0] for g in reconstructed}, {'2024-10', '2024-11'})
        self.assertEqual(reconstructed[0]['weeks'], first['repositories'][PROJECT['repo']]['last_good']['weeks'])
        self.assertIn('2024-10', archive.coverage(data)['stars']['months'])

    def test_failed_job_artifact_is_bounded_to_the_recovery_archive(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/update-stats.yml').read_text()
        step = workflow.split('      - name: Preserve unpublished chart observations on failure\n')[1].split('      - name:', 1)[0]
        self.assertIn('if: failure() || cancelled()', step)
        self.assertIn('path: tmp/chart-observations/archive.json', step)
        self.assertIn('retention-days: 14', step)
        self.assertNotIn('permissions:', step)

    def test_hn_identity_revisions_and_rollover_are_separate_observations(self):
        first = hn_cache()
        revised = project()
        revised['scope_note'] = 'Reviewed identity revision, same observed stories.'
        second = hn_cache(now=HN_NOW + timedelta(days=1), identity=revised, existing=first)
        november = HN_NOW.replace(month=11)
        third = hn_cache(now=november, identity=revised, existing=second)
        data = archive.empty()
        for item in (first, second, third):
            archive.add_hn(data, item)
        archive.validate(data)
        self.assertEqual(len(data['observations']), 3)
        goods = [archive.materialize(data, o) for o in data['observations'].values()]
        self.assertEqual(len({g['identity_key'] for g in goods}), 2)
        self.assertEqual({g['months'][0] for g in goods}, {'2024-10', '2024-11'})
        self.assertIn('2024-10', archive.coverage(data)['hn']['months'])

    def test_legacy_dates_keep_precision_and_failed_attempts_cannot_redate(self):
        snapshot = hn_cache()
        key, record = next(iter(snapshot['queue'].items()))
        record['last_good'].pop('collected_at')
        data = archive.add_hn(archive.empty(), snapshot)
        observation = next(iter(data['observations'].values()))
        self.assertIsNone(observation['observed_at'])
        record.update(checked_at='2026-11-15T00:00:00+00:00', status='unavailable')
        archive.add_hn(data, snapshot)
        self.assertEqual(len(data['observations']), 1)
        legacy = {'schema_version': 1, 'months': snapshot['months'],
                  'projects': snapshot['projects'], 'refreshed_utc_date': '2026-10-15'}
        archive.add_hn(data, legacy)
        dated = [o for o in data['observations'].values() if o['observed_at']]
        self.assertEqual(dated[0]['observed_at'], {'value': '2026-10-15', 'precision': 'day',
                                                   'field': 'snapshot.refreshed_utc_date'})
        self.assertNotIn('collected_at', archive.materialize(data, dated[0]))
        archive.validate(data)

    def test_unknown_history_is_not_zero_and_deleted_identity_stays_archived(self):
        unknown = {'schema_version': 1, 'repositories': {
            PROJECT['repo']: {**PROJECT, 'status': 'unavailable',
                             'source_url': stars.API + PROJECT['repo'] + '/stargazers/history'}}}
        data = archive.add_stars(archive.empty(), unknown)
        self.assertEqual(data, archive.empty())
        archive.add_stars(data, star_cache())
        before = deepcopy(data)
        archive.add_stars(data, {'schema_version': 1, 'repositories': {}})
        self.assertEqual(data, before)

    def test_merge_is_commutative_idempotent_and_checks_hashes(self):
        left = archive.add_hn(archive.empty(), hn_cache())
        right = archive.add_stars(archive.empty(), star_cache())
        self.assertEqual(archive.merge(left, right), archive.merge(right, left))
        self.assertEqual(archive.merge(left, left), left)
        corrupt = deepcopy(left)
        next(iter(corrupt['objects'].values()))['value']['unexpected'] = True
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            archive.merge(left, corrupt)

    def test_valid_hash_cannot_hide_missing_references_or_wrong_identity(self):
        data = archive.add_stars(archive.empty(), star_cache())
        observation = deepcopy(next(iter(data['observations'].values())))
        observation['identity'] = 'org/another'
        data['observations'] = {archive.digest(observation): observation}
        with self.assertRaises(ValueError):
            archive.validate(data)
        data = archive.add_stars(archive.empty(), star_cache())
        key = next(k for k, v in data['objects'].items() if v['kind'] == 'star_week')
        del data['objects'][key]
        with self.assertRaisesRegex(ValueError, 'Missing'):
            archive.validate(data)

    def test_atomic_save_noop_and_failed_validation_preserve_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'archive.json'
            data = archive.add_hn(archive.empty(), hn_cache())
            archive.save(path, data)
            original, mtime = path.read_bytes(), path.stat().st_mtime_ns
            archive.save(path, data)
            self.assertEqual(path.stat().st_mtime_ns, mtime)
            corrupt = deepcopy(data)
            corrupt['schema_version'] = 2
            with self.assertRaises(ValueError):
                archive.save(path, corrupt)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(archive.load(path), data)

    def test_hn_retains_before_cache_checkpoint_and_retention_failure_is_fatal(self):
        old = hn_cache()
        sequence = []
        def retain(key, good):
            self.assertEqual(old['queue'][key]['last_good']['collected_at'], HN_NOW.isoformat())
            sequence.append('archive')
        hn.refresh(HN_NOW + timedelta(days=31), existing=old, projects=[project()],
                   metadata={}, getter=window_page, retain=retain,
                   checkpoint=lambda d: sequence.append('cache'))
        self.assertEqual(sequence, ['archive', 'cache'])
        with self.assertRaisesRegex(OSError, 'archive failed'):
            hn_cache(now=HN_NOW + timedelta(days=31), existing=old,
                     retain=lambda *a: (_ for _ in ()).throw(OSError('archive failed')))

    def test_stars_retains_before_return_and_retention_failure_is_fatal(self):
        old = star_cache()
        kept = []
        result = stars.refresh([PROJECT], existing=old, now=NOW + timedelta(days=1), force=True,
                               getter=pager(weekly_series()), retain=lambda repo, r: kept.append(deepcopy(r)))
        self.assertEqual(kept[0], result['repositories'][PROJECT['repo']])
        self.assertEqual(old['repositories'][PROJECT['repo']]['last_good']['fetched_at'], NOW.isoformat())
        with self.assertRaisesRegex(OSError, 'archive failed'):
            stars.refresh([PROJECT], existing=old, now=NOW + timedelta(days=1), force=True,
                          getter=pager(weekly_series()),
                          retain=lambda *a: (_ for _ in ()).throw(OSError('archive failed')))

    def test_published_archive_is_valid_and_contains_every_current_good(self):
        root = Path(__file__).resolve().parents[1]
        data = archive.load(root / archive.ARCHIVE)
        required = archive.empty()
        archive.add_hn(required, json.loads((root / 'data/hn_evidence.json').read_text()))
        archive.add_stars(required, json.loads((root / 'data/star_history.json').read_text()))
        self.assertTrue(set(required['observations']) <= set(data['observations']))


class RecoveryTests(unittest.TestCase):
    def test_invalid_blob_is_skipped_transactionally_including_malformed_json(self):
        first = hn_cache()
        second = hn_cache(identity=project('OpenOther'))
        first['queue'].update(second['queue'])
        list(first['queue'].values())[1]['last_good']['collected_at'] = 'corrupt date'
        for payload in (json.dumps(first), '{ malformed json'):
            def fake_git(root, *args):
                return {'rev-parse': 'a' * 40, 'log': 'a' * 40,
                        'ls-tree': '100644 blob ' + 'b' * 40 + '\tdata/hn_evidence.json',
                        'cat-file': payload}[args[0]]
            with patch.object(recovery, 'git', side_effect=fake_git):
                data, report = recovery.recover(Path('.'), 'main')
            self.assertEqual(report['sources'], [])
            self.assertEqual(len(report['skipped']), 1)
            self.assertEqual(data['observations'], {})
            self.assertEqual(data['objects'], {})

    def test_bounded_recovery_uses_payload_dates_not_commit_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', '-b', 'main', directory], check=True)
            def commit(snapshot):
                path = root / 'data/hn_evidence.json'
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(snapshot))
                subprocess.run(['git', 'add', '.'], cwd=root, check=True)
                subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                'commit', '-qm', 'fixture'], cwd=root, check=True)
            first = hn_cache()
            commit(first)
            second = hn_cache(now=HN_NOW + timedelta(days=31), existing=first)
            commit(second)
            data, report = recovery.recover(root, 'main', 1)
            self.assertTrue(report['history_truncated'])
            self.assertEqual(len(data['observations']), 1)
            data, report = recovery.recover(root, 'main', 10)
            self.assertFalse(report['history_truncated'])
            self.assertEqual(report['snapshot_commits_scanned'], 2)
            self.assertEqual(archive.coverage(data)['hn']['retrieval_days'], ['2026-10-15', '2026-11-15'])
            repeated, _ = recovery.recover(root, 'main', 10, data)
            self.assertEqual(repeated, data)
