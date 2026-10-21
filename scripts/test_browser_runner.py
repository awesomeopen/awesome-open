"""Offline regression coverage for bounded, exhaustive browser orchestration."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

from run_browser_checks import CHUNK_SIZE, execute, make_plan, run_suite


def catalog(count):
    return dict(source_sha='revision', projects=[dict(id=f'{i:064x}', name='Same name', artwork=True)
                                                for i in reversed(range(count))])


class BrowserRunnerTests(unittest.TestCase):
    def test_partition_is_deterministic_exactly_once_and_bounded(self):
        for count in (0, 1, 31, 32, 33, 176, 525):
            with self.subTest(count=count):
                plan = make_plan(catalog(count))
                chunks = [s for s in plan['suites'] if 'ids' in s]
                self.assertEqual(len(chunks), math.ceil(count / CHUNK_SIZE))
                self.assertTrue(all(0 < len(s['ids']) <= CHUNK_SIZE for s in chunks))
                ids = [i for s in chunks for i in s['ids']]
                self.assertEqual(ids, sorted(p['id'] for p in catalog(count)['projects']))
                self.assertEqual(len(set(f'specimen-{i}.png' for i in ids)), count)
                self.assertGreater(plan['timeout_minutes'] * 60, sum(s['seconds'] + 5 for s in plan['suites']))

    def test_duplicate_ids_fail(self):
        data = catalog(1)
        data['projects'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            make_plan(data)

    def test_missing_and_unapproved_artwork_are_not_invented(self):
        data = catalog(1)
        data['projects'] += [dict(id='missing'), dict(id='empty', artwork=None)]
        self.assertEqual(len(make_plan(data)['artworkIds']), 1)

    def test_failure_and_timeout_continue_and_fail_aggregate(self):
        plan = make_plan(catalog(0))
        called = []
        def runner(suite, output):
            called.append(suite['name'])
            return dict(name=suite['name'], status={'core': 'failed', 'fonts': 'timed_out'}.get(suite['name'], 'passed'))
        with tempfile.TemporaryDirectory() as directory:
            report = execute(plan, Path(directory), runner)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(called, [s['name'] for s in plan['suites']])
            self.assertEqual(json.loads((Path(directory) / 'browser-suites.json').read_text()), report)

    def test_artifact_coverage_must_match_the_plan(self):
        plan = make_plan(catalog(33))
        def runner(suite, output):
            if 'ids' in suite:
                for project in suite['ids']:
                    (output / f'specimen-{project}.png').touch()
                (output / (suite['name'] + '.json')).write_text(json.dumps(dict(
                    status='passed', sourceSha='revision', expectedIds=suite['ids'],
                    projects=[dict(id=i) for i in suite['ids']],
                    screenshots=[dict(file=f'specimen-{i}.png') for i in suite['ids']])))
            return dict(name=suite['name'], status='passed')
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(execute(plan, Path(directory), runner)['status'], 'passed')
            def wrong(suite, output):
                result = runner(suite, output)
                if 'ids' in suite:
                    (output / f"specimen-{suite['ids'][0]}.png").unlink()
                return result
            self.assertEqual(execute(plan, Path(directory), wrong)['status'], 'failed')

    def test_real_subprocess_success_failure_signal_timeout_and_spawn_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for code, expected in [('pass', 'passed'), ('raise SystemExit(7)', 'failed'),
                                   ('import os, signal; os.kill(os.getpid(), signal.SIGTERM)', 'failed'),
                                   ('import time; time.sleep(10)', 'timed_out')]:
                result = run_suite(dict(name='probe', seconds=.1), output, [sys.executable, '-c', code])
                self.assertEqual(result['status'], expected)
                self.assertLess(result['elapsedSeconds'], 4)
            self.assertEqual(run_suite(dict(name='missing', seconds=1), output,
                                      ['/definitely-missing-browser-runner'])['status'], 'unavailable')

    def test_timeout_kills_descendant_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'survived'
            child = f"import time; from pathlib import Path; time.sleep(.5); Path({str(marker)!r}).touch()"
            parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
            result = run_suite(dict(name='descendant', seconds=.15), Path(directory),
                               [sys.executable, '-c', parent])
            self.assertEqual(result['status'], 'timed_out')
            import time
            time.sleep(.6)
            self.assertFalse(marker.exists(), 'Grandchild must be terminated with its timed-out suite')

    def test_malformed_art_manifest_fails_but_does_not_stop_later_chunks(self):
        calls = []
        def runner(suite, output):
            calls.append(suite['name'])
            if 'ids' in suite:
                (output / (suite['name'] + '.json')).write_text(json.dumps(dict(
                    status='passed', sourceSha='revision', expectedIds=suite['ids'], projects=None)))
            return dict(name=suite['name'], status='passed')
        with tempfile.TemporaryDirectory() as directory:
            report = execute(make_plan(catalog(33)), Path(directory), runner)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(calls[-1], 'artwork-1')

    def test_cancellation_is_reported_and_stops_remaining_work(self):
        def cancelled(suite, output):
            raise SystemExit(143)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                execute(make_plan(catalog(0)), Path(directory), cancelled)
            report = json.loads((Path(directory) / 'browser-suites.json').read_text())
            self.assertEqual(report['status'], 'cancelled')
            self.assertEqual(report['suites'], [dict(name='core', status='cancelled')])

    def test_extracted_artwork_keeps_assertions_and_identity_filenames(self):
        root = Path(__file__).resolve().parent
        art = (root / 'check_artwork_browser.cjs').read_text()
        for token in ['catalog.json', 'data.source_sha', "page.on('pageerror'", 'project.function_summary.text',
                      "'.function-provenance a'", 'project.description', 'img.complete && img.naturalWidth > 0',
                      "'specimen-' + project.id + '.png'", 'document.fonts.ready', 'page.viewportSize()',
                      'report.expectedIds', 'report.projects.map(p => p.id)']:
            self.assertIn(token, art)
        self.assertNotIn('project.name.toLowerCase()', art)
        core = (root / 'check_site_browser.cjs').read_text()
        self.assertNotIn('for (const project of data.projects.filter(p => p.artwork))', core)
        self.assertNotIn("require('./check_fonts_browser.cjs')", core)
        self.assertNotIn("require('./check_observatory_browser.cjs')", core)


if __name__ == '__main__':
    unittest.main()
