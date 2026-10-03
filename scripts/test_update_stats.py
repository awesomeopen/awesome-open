import unittest
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
        expected = "Created: 2022-11-11. Updated: 2026-10-02. License: MIT. Stars: 111k."
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
        self.assertIn("Stars: 111k.", updated)
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
            self.assertIn("License: Not identified.", result)
            self.assertIn("Updated: Unknown.", result)

    def test_api_text_cannot_break_table(self):
        record = dict(self.record, license={"spdx_id": "MIT | <script>\n"})
        result = stats.metadata(record)
        self.assertNotIn("|", result)
        self.assertNotIn("<", result)
        self.assertNotIn("\n", result)

    def test_missing_or_duplicate_markers_fail(self):
        for text in [self.row.replace("<!-- STATS:END -->", ""),
                     self.row.replace("Pending.", "<!-- STATS:END --><!-- STATS:START -->")]:
            with self.assertRaises(ValueError):
                stats.update_text(text, self.data)

    def test_missing_repository_does_not_return_partial_update(self):
        with self.assertRaises(KeyError):
            stats.update_text(self.header + self.row, {})

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
