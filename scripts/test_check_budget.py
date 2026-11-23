import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import check_budget


class CheckBudgetTests(unittest.TestCase):
    def site(self, directory, index_bytes=1000):
        site = Path(directory)
        (site / 'specimens').mkdir()
        (site / 'index.html').write_bytes(b'<!doctype html>' + b'a' * index_bytes)
        (site / 'catalog.json').write_text('{}')
        (site / 'specimens/cutouts').mkdir()
        (site / 'records').mkdir()
        for record in ('a', 'b'):
            (site / f'records/{record}.html').write_text('<!doctype html>')
        (site / 'specimens/one.webp').write_bytes(b'w' * 2048)
        (site / 'specimens/cutouts/one.webp').write_bytes(b'c' * 1024)
        (site / 'specimens/two.webp').write_bytes(b'w' * 3072)
        return site

    def run_check(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = check_budget.main([str(arg) for arg in args])
        return code, output.getvalue()

    def test_within_budget_reports_every_measure_and_passes(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''}):
            code, text = self.run_check(self.site(directory))
        self.assertEqual(code, 0)
        for label, *_ in check_budget.BUDGET:
            self.assertIn(f'| {label} |', text)
        self.assertIn('Largest specimen artwork | 3.0 KiB', text)

    def test_artwork_counts_per_illustrated_project_and_leaves_the_rest(self):
        with tempfile.TemporaryDirectory() as directory:
            values, _ = check_budget.measure(self.site(directory))
        self.assertEqual(values['specimen_average'], 3072)
        self.assertEqual(values['other_bytes'], values['total_bytes'] - 6144)

    def test_per_record_limits_grow_with_the_static_records(self):
        budget = [('catalog.json', 'catalog_bytes', check_budget.per_record(0, 1), 'reason')]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(check_budget, 'BUDGET', budget):
            site = self.site(directory)
            self.assertEqual(self.run_check(site)[0], 0)
            (site / 'records/b.html').unlink()
            code, text = self.run_check(site)
        self.assertEqual(code, 1)
        self.assertIn('Static records: 1', text)
        self.assertIn('| catalog.json | 2 B | 1 B | Over |', text)

    def test_exceeded_limit_fails_unless_warn_only(self):
        budget = [(label, key, 100 if key == 'index_bytes' else limit, reason)
                  for label, key, limit, reason in check_budget.BUDGET]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(check_budget, 'BUDGET', budget):
            site = self.site(directory)
            self.assertEqual(self.run_check(site)[0], 1)
            code, text = self.run_check(site, '--warn-only')
        self.assertEqual(code, 0)
        self.assertIn('| index.html | 1015 B | 100 B | Over |', text)
        self.assertIn('::warning::Size budget exceeded: index.html', text)

    def test_appends_table_to_step_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / 'summary.md'
            (Path(directory) / 'site').mkdir()
            site = self.site(Path(directory) / 'site')
            with mock.patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}):
                self.run_check(site)
            self.assertIn('## Site size budget', summary.read_text())

    def test_hn_budget_is_separate_and_other_files_keep_their_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            site = self.site(directory)
            (site / 'data').mkdir()
            hn = site / 'data/hn_evidence.json'
            hn.write_bytes(b'x' * (2 * 96 * 1024))
            self.assertEqual(self.run_check(site)[0], 0)
            hn.write_bytes(hn.read_bytes() + b'x')
            self.assertIn('HN evidence', check_budget.report(site)[1])
            hn.write_bytes(b'{}')
            (site / 'data/other.json').write_bytes(b'x' * (2 * 8 * 1024 + 1))
            self.assertEqual(check_budget.report(site)[1], ['Largest other file'])

    def test_enriched_catalog_boundary_still_rejects_bloat(self):
        with tempfile.TemporaryDirectory() as directory:
            site = self.site(directory)
            catalog = site / 'catalog.json'
            catalog.write_bytes(b'x' * (2 * 6 * check_budget.KIB))
            self.assertEqual(self.run_check(site)[0], 0)
            catalog.write_bytes(catalog.read_bytes() + b'x')
            self.assertEqual(check_budget.report(site)[1], ['catalog.json'])
            self.assertEqual(self.run_check(site)[0], 1)

    def test_only_exact_hn_download_leaves_remainder(self):
        with tempfile.TemporaryDirectory() as directory:
            site = self.site(directory)
            baseline, _ = check_budget.measure(site)
            (site / 'data').mkdir()
            (site / 'data/hn_evidence.json').write_bytes(b'x' * 100)
            for name in ('hn_evidence.json', 'data/hn_evidence.json.copy',
                         'data/hn_evidence.html'):
                (site / name).write_bytes(b'x' * 30)
            values, _ = check_budget.measure(site)
            self.assertEqual(values['other_bytes'], baseline['other_bytes'] + 90)
            self.assertEqual(values['total_bytes'], baseline['total_bytes'] + 190)
            budget = [('Remainder', 'other_bytes', values['other_bytes'], 'test')]
            with mock.patch.object(check_budget, 'BUDGET', budget):
                self.assertEqual(self.run_check(site)[0], 0)
                (site / 'extra').write_bytes(b'x')
                self.assertEqual(check_budget.report(site)[1], ['Remainder'])

    def test_hn_still_counts_toward_total_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            site = self.site(directory)
            (site / 'data').mkdir()
            hn = site / 'data/hn_evidence.json'
            hn.write_bytes(b'x' * 100)
            values, _ = check_budget.measure(site)
            budget = [('Total', 'total_bytes', values['total_bytes'], 'test')]
            with mock.patch.object(check_budget, 'BUDGET', budget):
                self.assertEqual(self.run_check(site)[0], 0)
                hn.write_bytes(b'x' * 101)
                self.assertEqual(check_budget.report(site)[1], ['Total'])
            rows = {key: limit for _, key, limit, _ in check_budget.BUDGET}
            self.assertEqual(rows['total_bytes'], 640 * check_budget.MIB)

    def test_missing_site_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(SystemExit):
            check_budget.main([directory])

    def test_deployment_download_has_its_own_per_catalog_record_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            site = self.site(directory)
            (site / 'data').mkdir()
            download = site / 'data/deployment_evidence.json'
            download.write_bytes(b'x' * (2 * 3 * check_budget.KIB))
            values, _ = check_budget.measure(site)
            self.assertEqual(values['deployment_bytes'], 6144)
            self.assertEqual(values['largest_other'], 3072)
            self.assertEqual(self.run_check(site)[0], 0)
            download.write_bytes(download.read_bytes() + b'x')
            code, text = self.run_check(site)
            self.assertEqual(code, 1)
            self.assertIn('| Where it runs (data) | 6.0 KiB | 6.0 KiB | Over |', text)


if __name__ == '__main__':
    unittest.main()


class HnPlanningAllowanceTests(unittest.TestCase):
    def test_only_hn_gets_multiyear_allowance(self):
        rows = {key:limit for _,key,limit,_ in check_budget.BUDGET}
        self.assertEqual(rows['hn_bytes'](1000), 98304000)
        self.assertEqual(rows['other_bytes'](587), 55834624)
        self.assertEqual(rows['catalog_bytes'](587), 587*6144)
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site/'records').mkdir(); (site/'records/a.html').write_text('')
            (site/'data').mkdir(); (site/'index.html').write_text('')
            hn = site/'data/hn_evidence.json'
            hn.write_bytes(b' ' * 98304)
            self.assertNotIn('HN evidence', check_budget.report(site)[1])
            hn.write_bytes(b' ' * 98305)
            self.assertIn('HN evidence', check_budget.report(site)[1])
