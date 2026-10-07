import unittest
from datetime import date
import tempfile
from pathlib import Path
from unittest.mock import patch
import urllib.error

import update_stats as stats


class UpdateStatsTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(stats, "utc_today", return_value=date(2026, 10, 3))
        clock.start()
        self.addCleanup(clock.stop)
        self.record = {
            "created_at": "2022-11-11T12:00:00Z",
            "pushed_at": "2026-10-02T15:00:00Z",
            "license": {"spdx_id": "MIT"},
            "stargazers_count": 111000,
        }
        self.row = (
            "| [OpenExample](https://github.com/Example/OpenExample) | "
            "CRM tool for customer relations. <!-- STATS:START -->Pending.<!-- STATS:END --> |\n"
        )
        self.header = "<!-- STARS:START -->\nStars: 0\n<!-- STARS:END -->\n"
        self.data = {"example/openexample": self.record}

    def test_only_marked_content_changes_and_cross_listings_match(self):
        external = "| [OpenOther](https://example.com) | Keep this description. |\n"
        original = self.header + self.row + external + self.row
        updated = stats.update_text(original, self.data)
        expected = "<br><sub>2022-11-11 -- 2026-10-02 / MIT / 111k</sub>"
        self.assertEqual(updated.count(expected), 2)
        self.assertIn(external, updated)
        self.assertEqual(updated.count("CRM tool for customer relations."), 2)
        self.assertEqual(stats.update_text(updated, self.data), updated)
        self.assertEqual(stats.repositories(original), ["example/openexample"])

    def test_list_star_block_is_ignored_if_present(self):
        updated = stats.update_text(self.header + self.row, self.data)
        self.assertTrue(updated.startswith(self.header))

    def test_project_metadata_updates_without_list_star_block(self):
        updated = stats.update_text(self.row, self.data)
        self.assertIn(" / MIT / 111k</sub>", updated)
        self.assertNotIn("<!-- STARS:", updated)
        self.assertEqual(stats.repositories(self.row), ["example/openexample"])

    def test_metadata_uses_subscript_and_slash_separators(self):
        record = dict(self.record, created_at="2022-02-14T00:00:00Z",
                      pushed_at="2026-10-03T00:00:00Z",
                      license={"spdx_id": "Apache-2.0"}, stargazers_count=5400)
        self.assertEqual(stats.metadata(record),
                         "<br><sub>2022-02-14 -- 2026-10-03 / Apache-2.0 / 5.4k</sub>")

    def test_last_push_emphasis_at_calendar_year_boundary(self):
        for pushed, today, bold in [
            ("2025-10-04", date(2026, 10, 3), False),
            ("2025-10-03", date(2026, 10, 3), True),
            ("2024-10-03", date(2026, 10, 3), True),
            ("2026-10-04", date(2026, 10, 3), False),
            ("2024-02-29", date(2025, 2, 27), False),
            ("2024-02-29", date(2025, 2, 28), True),
            ("2023-03-01", date(2024, 2, 29), False),
            ("2023-03-01", date(2024, 3, 1), True),
        ]:
            with self.subTest(pushed=pushed, today=today):
                result = stats.metadata(dict(self.record, pushed_at=pushed + "T23:59:59Z"), today=today)
                expected = f"<b>{pushed}</b>" if bold else pushed
                self.assertEqual(result, f"<br><sub>2022-11-11 -- {expected} / MIT / 111k</sub>")

    def test_missing_or_unknown_push_never_receives_emphasis(self):
        for pushed in [None, "", "Unknown", "2025-02-30"]:
            with self.subTest(pushed=pushed):
                record = dict(self.record, pushed_at=pushed)
                self.assertNotIn("<b>", stats.metadata(record))
        record = dict(self.record)
        del record["pushed_at"]
        self.assertNotIn("<b>", stats.metadata(record))

    def test_stale_emphasis_refreshes_and_regenerates_stably(self):
        data = {"example/openexample": dict(self.record, pushed_at="2025-10-03T23:59:59Z")}
        recent = stats.update_text(self.row, data, today=date(2026, 10, 2))
        self.assertNotIn("<b>", recent)
        stale = stats.update_text(recent, data, today=date(2026, 10, 3))
        self.assertIn(" -- <b>2025-10-03</b> /", stale)
        self.assertEqual(stats.update_text(stale, data, today=date(2026, 10, 3)), stale)
        data["example/openexample"]["pushed_at"] = "2026-10-03T23:59:59Z"
        self.assertNotIn("<b>", stats.update_text(stale, data, today=date(2026, 10, 3)))

    def test_update_uses_one_utc_date_for_all_rows(self):
        with patch.object(stats, "utc_today", return_value=date(2026, 10, 3)) as clock:
            stats.update_text(self.row + self.row, self.data)
        clock.assert_called_once_with()

    def test_star_formatting(self):
        for count, expected in [(0, "0"), (999, "999"), (1000, "1k"), (111111, "111.1k"),
                                (999999, "1m"), (1234567, "1.2m")]:
            with self.subTest(count=count):
                self.assertEqual(stats.star_count(count), expected)

    def test_unknown_license_and_push_date_are_not_invented(self):
        for license_value in [None, {"spdx_id": "NOASSERTION"}]:
            record = dict(self.record, license=license_value, pushed_at=None)
            result = stats.metadata(record)
            self.assertNotIn("Not identified", result)
            self.assertNotIn("NOASSERTION", result)
            self.assertEqual(result, "<br><sub>2022-11-11 -- Unknown / 111k</sub>")

    def test_api_text_cannot_break_table(self):
        record = dict(self.record, license={"spdx_id": "MIT | <script>\n"})
        result = stats.metadata(record)
        self.assertNotIn("|", result)
        self.assertNotIn("<", result.removeprefix("<br><sub>").removesuffix("</sub>"))
        self.assertNotIn("\n", result)

    def test_missing_or_duplicate_markers_fail(self):
        for text in [self.row.replace("<!-- STATS:END -->", ""),
                     self.row.replace("Pending.", "<!-- STATS:END --><!-- STATS:START -->")]:
            with self.assertRaises(ValueError):
                stats.update_text(text, self.data)

    def test_missing_repository_does_not_return_partial_update(self):
        with self.assertRaises(KeyError):
            stats.update_text(self.header + self.row, {})

    def test_top_three_is_per_category_and_preserves_order(self):
        rows = [self.row.replace("OpenExample", name) for name in ["A", "B", "C", "D"]]
        data = {"example/" + name.lower(): dict(self.record, stargazers_count=count)
                for name, count in zip(["A", "B", "C", "D"], [10, 40, 30, 20])}
        original = "## One\n" + "".join(rows) + "## Two\n" + rows[0]
        updated = stats.update_text(original, data)
        first, second = updated.split("## Two")
        self.assertIn("| [A]", first)
        for name in ["B", "C", "D"]:
            self.assertIn("| **[" + name + "]", first)
        self.assertIn("| **[A]", second)
        self.assertEqual([stats.ROW.match(x)[1] for x in first.splitlines() if stats.ROW.match(x)],
                         ["A", "B", "C", "D"])
        self.assertEqual(stats.update_text(updated, data), updated)

    def test_ties_use_repo_path_and_remove_stale_bold(self):
        names = ["D", "C", "B", "A"]
        rows = [self.row.replace("OpenExample", name) for name in names]
        rows[0] = rows[0].replace("| [D]", "| **[D]").replace(") |", ")** |")
        data = {"example/" + name.lower(): self.record for name in names}
        updated = stats.update_text("".join(rows), data)
        self.assertIn("| [D]", updated)
        self.assertNotIn("**[D]", updated)
        self.assertEqual(updated.count("| **["), 3)

    def test_chart_and_bold_are_independent(self):
        chart = ' <!-- HN:START --><br>[![HN discussions / 2y](assets/hn/example.svg)](https://hn.algolia.com/)<!-- HN:END -->'
        row = self.row.replace(") |", ")" + chart + " |")
        updated = stats.update_text(row, self.data)
        self.assertIn(")**" + chart + " |", updated)
        self.assertEqual(stats.update_text(updated, self.data), updated)

    def test_unknown_license_is_omitted(self):
        for value in [None, {"spdx_id": "NOASSERTION"}, {"spdx_id": "OTHER"}, {"spdx_id": ""}]:
            self.assertEqual(stats.metadata(dict(self.record, license=value)),
                             "<br><sub>2022-11-11 -- 2026-10-02 / 111k</sub>")

    def test_concurrent_readme_edit_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "README.source.md"
            path.write_text(self.row)
            changed = self.row + "A concurrent contribution.\n"
            def fetch(repo, token):
                path.write_text(changed)
                return self.record
            with patch.object(stats, "ROOT", root), patch.object(stats, "fetch", side_effect=fetch), patch.dict(stats.os.environ, {"GH_TOKEN": "test"}):
                with self.assertRaisesRegex(RuntimeError, "README.source.md changed"):
                    stats.main()
            self.assertEqual(path.read_text(), changed)

    def test_failed_collection_preserves_snapshot_and_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            (root / 'README.source.md').write_text(self.row)
            (root / 'README.md').write_text('Published output.\n')
            snapshot = root / 'data/github_metrics.json'
            snapshot.write_text('previous snapshot\n')
            with patch.object(stats, 'ROOT', root), \
                    patch.object(stats, 'fetch', side_effect=RuntimeError('API unavailable')), \
                    patch.dict(stats.os.environ, {'GH_TOKEN': 'test'}):
                with self.assertRaisesRegex(RuntimeError, 'API unavailable'):
                    stats.main()
            self.assertEqual(snapshot.read_text(), 'previous snapshot\n')
            self.assertEqual((root / 'README.md').read_text(), 'Published output.\n')

    def test_successful_collection_only_replaces_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            (root / 'README.source.md').write_text(self.row)
            (root / 'README.md').write_text('Published output.\n')
            with patch.object(stats, 'ROOT', root), \
                    patch.object(stats, 'fetch', return_value=self.record), \
                    patch.dict(stats.os.environ, {'GH_TOKEN': 'test'}):
                stats.main()
            self.assertTrue((root / 'data/github_metrics.json').exists())
            self.assertEqual((root / 'README.md').read_text(), 'Published output.\n')
            self.assertEqual((root / 'README.source.md').read_text(), self.row)

    @patch.object(stats.time, "sleep")
    @patch.object(stats.urllib.request, "urlopen")
    def test_transient_api_errors_retry_then_fail(self, urlopen, sleep):
        urlopen.side_effect = urllib.error.HTTPError("url", 503, "Unavailable", {}, None)
        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            stats.fetch("example/openexample", "test-token")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.object(stats.urllib.request, "urlopen")
    def test_missing_repository_fails_without_retry(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError("url", 404, "Not found", {}, None)
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            stats.fetch("example/openexample", "test-token")
        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
