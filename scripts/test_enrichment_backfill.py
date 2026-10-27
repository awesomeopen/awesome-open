"""Offline enrichment queue limits, fairness, eligibility and cursor safety."""
from contextlib import redirect_stderr
from copy import deepcopy
from datetime import date
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import select_enrichment_backfill as selector


def pid(number):
    return f"{number:064x}"


def project(number, illustrated=False):
    item = {"id": pid(number), "name": f"Open {number}",
            "url": f"https://example.org/open/{number}"}
    if illustrated:
        item["artwork"] = {"path": f"specimens/{pid(number)}.webp"}
    return item


class EnrichmentSelectionTests(unittest.TestCase):
    def plan(self, projects, records=None, **kwargs):
        options = {"job": "summaries", "day": date(2026, 10, 27), "slot": 0,
                   "after": pid(0)}
        options.update(kwargs)
        return selector.select_plan({"projects": projects, "source_sha": "a" * 40},
                                    {"schema_version": 1, "summaries": records or {}}, **options)

    def test_forty_limit_priority_fairness_and_disjoint_groups(self):
        projects = [project(i, i <= 60) for i in range(1, 101)]
        result = self.plan(projects)
        selected = result["candidates"]
        self.assertEqual(len(selected), 40)
        self.assertEqual([p["tier"] for p in selected], ["illustrated"] * 30 + ["unillustrated"] * 10)
        groups = result["research_groups"]
        self.assertEqual([len(g) for g in groups], [10] * 4)
        self.assertEqual(len(set(sum(groups, []))), 40)
        self.assertEqual(result["planned_cursors"], {"illustrated": pid(30), "unillustrated": pid(70)})

    def test_independent_cursor_progress_avoids_starvation(self):
        projects = [project(i, i <= 60) for i in range(1, 101)]
        first = self.plan(projects)
        second = self.plan(projects, after=None, cursors=first["planned_cursors"])
        self.assertEqual([p["id"] for p in second["candidates"][:30]], [pid(i) for i in range(31, 61)])
        self.assertEqual([p["id"] for p in second["candidates"][30:]], [pid(i) for i in range(71, 81)])

    def test_unused_quota_borrowing_and_small_limit(self):
        only_art = self.plan([project(i, True) for i in range(1, 50)])
        only_plain = self.plan([project(i) for i in range(1, 50)])
        self.assertEqual(len(only_art["candidates"]), 40)
        self.assertEqual(len(only_plain["candidates"]), 40)
        sparse = self.plan([project(i, i <= 2) for i in range(1, 50)])
        self.assertEqual(len(sparse["candidates"]), 40)
        self.assertEqual(sum(p["tier"] == "illustrated" for p in sparse["candidates"]), 2)
        self.assertEqual(self.plan([project(1), project(2, True)], limit=1)["candidates"][0]["id"], pid(2))

    def test_existing_summary_of_any_status_is_reserved(self):
        records = {pid(1): {"review_status": "approved"}, pid(2): {"review_status": "pending"},
                   pid(3): {"review_status": "rejected"}, pid(4): None}
        result = self.plan([project(i) for i in range(1, 6)], records)
        self.assertEqual([p["id"] for p in result["candidates"]], [pid(5)])
        self.assertEqual(len(result["eligibility_skips"]), 4)

    def test_feature_eligibility_preserves_existing_lists(self):
        records = {pid(1): {"review_status": "approved"},
                   pid(2): {"review_status": "approved", "features": []},
                   pid(3): {"review_status": "approved", "features": [{"text": "existing"}]},
                   pid(4): {"review_status": "pending"},
                   pid(5): {"review_status": "rejected"},
                   pid(6): {"review_status": "approved", "features": None}}
        result = self.plan([project(i) for i in range(1, 8)], records, job="features")
        self.assertEqual([p["id"] for p in result["candidates"]], [pid(1), pid(2)])
        self.assertEqual(len(result["eligibility_skips"]), 5)

    def test_exclusions_and_cross_category_dedup(self):
        first = project(1, True)
        duplicate = dict(first, categories=["another"])
        result = self.plan([first, duplicate, project(2)], excluded=[pid(2)])
        self.assertEqual(len(result["candidates"]), 1)
        self.assertIn("reserved", result["eligibility_skips"][0]["reason"])
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            self.plan([first, dict(first, url="https://example.net/other")])

    def test_empty_tier_preserves_cursor_and_wrap(self):
        result = self.plan([], after=None, cursors={"illustrated": pid(99)})
        self.assertEqual(result["research_groups"], [])
        self.assertEqual(result["planned_cursors"]["illustrated"], pid(99))
        wrapped = self.plan([project(1), project(2)], after=pid(99))
        self.assertEqual([p["id"] for p in wrapped["candidates"]], [pid(1), pid(2)])

    def test_legacy_cursor_and_deterministic_fallback(self):
        projects = [project(i, i % 2 == 0) for i in range(1, 101)]
        legacy = self.plan(projects, after=pid(42))
        explicit = self.plan(projects, after=None, cursors=dict.fromkeys(selector.TIERS, pid(42)))
        self.assertEqual(legacy, explicit)
        first = self.plan(projects, after=None)
        self.assertEqual(first, self.plan(projects, after=None))
        later = self.plan(projects, after=None, slot=1)
        self.assertNotEqual(first["candidates"], later["candidates"])
        self.assertEqual(first["rotation"]["illustrated"]["reason"], "UTC-day/slot fallback")

    def test_fallback_without_history_does_not_starve_reserved_tier(self):
        projects = [project(i, i <= 40) for i in range(1, 81)]
        seen = set()
        for window in range(40):
            day = date.fromordinal(date(2026, 10, 27).toordinal() + window // 3)
            result = self.plan(projects, after=None, day=day, slot=window % 3)
            seen.update(p["id"] for p in result["candidates"] if p["tier"] == "unillustrated")
        self.assertEqual(seen, {pid(i) for i in range(41, 81)})

    def test_inputs_unchanged(self):
        projects = [project(1, True)]
        records = {pid(2): {"review_status": "rejected"}}
        before = deepcopy((projects, records))
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")):
            self.plan(projects, records)
        self.assertEqual((projects, records), before)

    def test_invalid_inputs_fail_closed(self):
        for kwargs in ({"limit": 0}, {"limit": 41}, {"limit": True}, {"slot": 3},
                       {"job": "art"}, {"day": "2026-10-27"}, {"after": "short"},
                       {"excluded": ["bad"]}, {"cursors": {"unknown": pid(1)}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.plan([project(1)], **kwargs)

    def test_cli_approved_existing_artwork_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "site/specimens").mkdir(parents=True)
            projects = [project(i, True) for i in range(1, 5)]  # stale attached flags ignored
            manifest = {"schema_version": 1, "artworks": {}}
            for number, status in ((1, "approved"), (2, "pending"), (3, "approved")):
                entry = {"project_url": projects[number - 1]["url"], "review_status": status,
                         "path": f"specimens/{pid(number)}.webp", "alt": "A specimen", "width": 1, "height": 1}
                manifest["artworks"][pid(number)] = entry
                if number != 3:  # missing approved file is not displayable
                    (root / "site" / entry["path"]).write_bytes(b"RIFF0000WEBP")
            (root / "data/specimen_art.json").write_text(json.dumps(manifest))
            (root / "data/function_summaries.json").write_text(json.dumps({"schema_version": 1, "summaries": {}}))
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"projects": projects}))
            output = root / "plan.json"
            args = ["--job", "summaries", "--catalog", str(catalog), "--root", str(root),
                    "--date", "2026-10-27", "--slot", "0", "--output", str(output)]
            with self.assertWarnsRegex(UserWarning, "Skipping missing specimen"):
                selector.main(args)
            result = json.loads(output.read_text())
            self.assertEqual(result["eligible_counts"], {"illustrated": 1, "unillustrated": 3})
            self.assertEqual(len(result["candidates"]), 4)
            self.assertEqual(result["candidates"][0]["id"], pid(1))
            reserved = root / "reserved.json"
            reserved.write_text("{}")
            with redirect_stderr(StringIO()), self.assertWarns(UserWarning), self.assertRaises(SystemExit):
                selector.main(args + ["--exclude-ids", str(reserved)])


if __name__ == "__main__":
    unittest.main()
