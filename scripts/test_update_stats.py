import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import urllib.error

import update_stats as stats


class UpdateStatsTests(unittest.TestCase):
    def setUp(self):
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
        expected = "<br>2022-11-11 - 2026-10-02, MIT, 111k"
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
        self.assertIn(", MIT, 111k", updated)
        self.assertNotIn("<!-- STARS:", updated)
        self.assertEqual(stats.repositories(self.row), ["example/openexample"])

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
            self.assertEqual(result, "<br>2022-11-11 - Unknown, 111k")

    def test_api_text_cannot_break_table(self):
        record = dict(self.record, license={"spdx_id": "MIT | <script>\n"})
        result = stats.metadata(record)
        self.assertNotIn("|", result)
        self.assertNotIn("<", result.removeprefix("<br>"))
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
                             "<br>2022-11-11 - 2026-10-02, 111k")

    def test_concurrent_readme_edit_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "README.md"
            path.write_text(self.row)
            changed = self.row + "A concurrent contribution.\n"
            def fetch(repo, token):
                path.write_text(changed)
                return self.record
            with patch.object(stats, "ROOT", root), patch.object(stats, "fetch", side_effect=fetch), patch.dict(stats.os.environ, {"GH_TOKEN": "test"}):
                with self.assertRaisesRegex(RuntimeError, "README changed"):
                    stats.main()
            self.assertEqual(path.read_text(), changed)

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
