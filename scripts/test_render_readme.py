"""Source-only changes and reproducible offline rendering contracts."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import render_readme as render
import update_hn as hn
import update_stats as stats


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.row = "| [Open](https://github.com/example/open) | Original description. |\n"
        self.source = "## One\n\n| Project | Description |\n| --- | --- |\n" + self.row
        self.record = dict(created_at="2020-01-01T00:00:00Z", pushed_at="2025-10-07T00:00:00Z",
                           license={"spdx_id": "MIT"}, stargazers_count=1234)
        self.snapshot = dict(schema_version=1, as_of="2026-10-07",
                             repositories={"example/open": self.record})
        self.evidence = {"projects": []}

    def test_exact_parity_with_existing_transformers(self):
        legacy = self.source.replace("Original description.",
            "Original description. <!-- STATS:START --><!-- STATS:END -->")
        expected = stats.update_text(legacy, self.snapshot["repositories"], today=date(2026, 10, 7))
        expected = hn.decorate_readme(expected, self.evidence)
        self.assertEqual(render.render_text(self.source, self.snapshot, self.evidence), render.NOTICE + expected)

    def test_render_is_offline_and_uses_snapshot_date(self):
        with patch.object(stats, "utc_today", side_effect=AssertionError("No wall clock")), \
                patch.object(stats.urllib.request, "urlopen", side_effect=AssertionError("No network")):
            first = render.render_text(self.source, self.snapshot, self.evidence)
            self.assertEqual(first, render.render_text(self.source, self.snapshot, self.evidence))
        self.assertIn("<b>2025-10-07</b>", first)
        earlier = deepcopy(self.snapshot)
        earlier["as_of"] = "2026-10-06"
        self.assertNotIn("<b>2025-10-07</b>", render.render_text(self.source, earlier, self.evidence))

    def test_new_source_only_entry_omits_unknown_metrics_and_ranking(self):
        new = "| [OpenNew](https://github.com/example/new) | New entry. |\n"
        rendered = render.render_text(self.source + new, self.snapshot, self.evidence)
        line = next(line for line in rendered.splitlines() if "OpenNew" in line)
        self.assertIn("New entry.", line)
        self.assertNotIn("<sub>", line)
        self.assertNotIn("**", line)
        self.assertNotIn("Pending", rendered)
        self.assertEqual(render.validate_source(self.source + new), ["example/new", "example/open"])

    def test_removed_source_entry_does_not_reappear_from_stale_snapshot(self):
        self.assertEqual(render.render_text("## Empty\n", self.snapshot, self.evidence), render.NOTICE + "## Empty\n")

    def test_source_only_alternatives_survive_regeneration(self):
        alternative = "<br>Alternative to: [Other](https://example.com/migrate)"
        source = self.source.replace("description.", "description." + alternative)
        output = render.render_text(source, self.snapshot, self.evidence)
        self.assertIn("description." + alternative + " <!-- STATS:START -->", output)
        self.assertNotIn("Alternative to:", stats.STATS.search(output)[0])

    def test_unknown_license_omission_and_non_github_row(self):
        self.record["license"] = {"spdx_id": "NOASSERTION"}
        external = "| [OpenSite](https://example.com) | Hosted service. |\n"
        output = render.render_text(self.source + external, self.snapshot, self.evidence)
        self.assertIn(" / 1.2k</sub>", output)
        self.assertNotIn("NOASSERTION", output)
        self.assertIn(external, output)

    def test_source_rejects_generated_decorations_or_third_column(self):
        for row in [self.row.replace("| [Open]", "| **[Open]").replace(") |", ")** |"),
                    self.row.replace("description.", "description. <!-- STATS:START --><!-- STATS:END -->"),
                    self.row.replace("description.", "description. | Extra column"),
                    self.row.replace("description.", "description.|Extra column"),
                    self.row.replace(") |", ")<br><!-- HN:START --><!-- HN:END --> |")]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                render.validate_source(row)

    def test_invalid_snapshot_fails(self):
        for bad in [True, -1, "100", 1.5]:
            snapshot = deepcopy(self.snapshot)
            snapshot["repositories"]["example/open"]["stargazers_count"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                render.validate_snapshot(snapshot)

    def test_preview_does_not_touch_tracked_readme_or_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "README.md").write_text("Previous published README\n")
            (root / "README.source.md").write_text(self.source)
            (root / "data/github_metrics.json").write_text(json.dumps(self.snapshot))
            (root / "data/hn_evidence.json").write_text(json.dumps(self.evidence))
            output = root / "tmp/preview/README.md"
            with patch.object(render, "ROOT", root), patch("sys.argv", ["render_readme.py", "--output", str(output)]):
                render.main()
            self.assertEqual((root / "README.md").read_text(), "Previous published README\n")
            self.assertEqual((root / "README.source.md").read_text(), self.source)
            self.assertEqual(output.read_text(), render.render_text(self.source, self.snapshot, self.evidence))

    def test_checked_in_source_and_snapshot_render_without_curated_changes(self):
        source = (render.ROOT / "README.source.md").read_text()
        snapshot = json.loads((render.ROOT / "data/github_metrics.json").read_text())
        evidence = json.loads((render.ROOT / "data/hn_evidence.json").read_text())
        output = render.render_text(source, snapshot, evidence).removeprefix(render.NOTICE)
        output = hn.MARKER.sub("", output)
        output = re.sub(r" <!-- STATS:START -->.*?<!-- STATS:END -->", "", output)
        output = re.sub(r"^(\| )\*\*(\[[^\]]+\]\([^)]+\))\*\*", r"\1\2", output, flags=re.M)
        self.assertEqual(output, source)


if __name__ == "__main__":
    unittest.main()
