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

    def test_missing_site_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(SystemExit):
            check_budget.main([directory])


if __name__ == '__main__':
    unittest.main()
