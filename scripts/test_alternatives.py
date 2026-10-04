"""Manual alternatives must survive both independent generated decorations."""
from datetime import date
import json
from pathlib import Path
import unittest

import update_stats as stats
import update_hn as hn

ROOT = Path(__file__).resolve().parents[1]


class AlternativesTests(unittest.TestCase):
    def setUp(self):
        self.links = [("One", "https://example.com/comparison"),
                      ("Two", "https://example.com/migration"),
                      ("Three", "https://example.com/alternatives")]
        self.record = dict(created_at="2020-01-01", pushed_at="2024-01-01",
                           license={"spdx_id": "MIT"}, stargazers_count=100)
        self.project = dict(readme_url="https://github.com/example/open",
                            slug="open", eligible=True, search_url="https://hn.algolia.com/?q=Open")

    def row(self, count):
        alternative = "<br>Alternative to: " + ", ".join(
            f"[{name}]({url})" for name, url in self.links[:count]) if count else ""
        return ("| [Open](https://github.com/example/open) | Original description."
                + alternative + " <!-- STATS:START --><!-- STATS:END --> |\n")

    def test_zero_through_three_survive_repeated_regeneration_in_both_orders(self):
        for count in range(4):
            with self.subTest(count=count):
                text = "## One\n" + self.row(count) + "## Two\n" + self.row(count)
                expected = self.links[:count]
                for _ in range(3):
                    text = stats.update_text(text, {"example/open": self.record}, today=date(2026, 10, 3))
                    text = hn.decorate_readme(text, {"projects": [self.project]})
                    for row in text.splitlines():
                        if stats.ROW.match(row):
                            self.assertEqual(stats.alternatives(row), expected)
                            self.assertNotIn("Alternative to:", stats.STATS.search(row)[0])
                            self.assertIn("Original description.", row)
                            self.assertIn("<sub>2020-01-01 -- <b>2024-01-01</b> / MIT / 100</sub>", row)
                    self.assertEqual(text.count("Alternative to:"), 2 if count else 0)
                without_chart = hn.decorate_readme(text, {"projects": []})
                self.assertEqual(without_chart.count("Alternative to:"), 2 if count else 0)

    def test_non_github_entry_without_metrics(self):
        row = "| [Open](https://example.com) | Description.<br>Alternative to: [One](https://example.com/comparison) |\n"
        self.assertEqual(stats.alternatives(row), self.links[:1])
        self.assertEqual(stats.update_text(row, {}), row)
        self.assertEqual(hn.decorate_readme(row, {"projects": []}), row)

    def test_reject_empty_excess_or_misplaced_alternatives(self):
        good = self.row(1)
        bad = [good.replace("[One](https://example.com/comparison)", ""),
               good.replace("[One](https://example.com/comparison)", ", ".join(["[One](https://example.com/comparison)"] * 4)),
               good.replace("<br>Alternative to:", "<!-- STATS:START --><br>Alternative to:"),
               good.replace("Original description.<br>Alternative to:", "Original description.Alternative to:")]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(ValueError):
                stats.update_text(row, {"example/open": self.record})

    def test_checked_in_evidence_matches_every_occurrence(self):
        evidence = json.loads((ROOT / "data/alternatives.json").read_text())
        expected = {}
        for project in evidence["projects"]:
            key = project["readme_url"].removeprefix("https://github.com/").lower()
            self.assertNotIn(key, expected)
            expected[key] = [(a["name"], a["source_url"]) for a in project["alternatives"]]
            self.assertTrue(1 <= len(expected[key]) <= 3)
            for alternative in project["alternatives"]:
                date.fromisoformat(alternative["checked_utc_date"])
                self.assertTrue(alternative["scope"])
        counts = dict.fromkeys(expected, 0)
        for row in (ROOT / "README.md").read_text().splitlines():
            match = stats.ROW.match(row)
            if match:
                key = match[2].lower()
                self.assertEqual(stats.alternatives(row), expected.get(key, []))
                if key in counts:
                    counts[key] += 1
                    self.assertEqual(len(row.split(" | ")), 2)
        self.assertTrue(all(count > 0 for count in counts.values()),
                        "Every evidence project must occur in the README")


if __name__ == "__main__":
    unittest.main()
