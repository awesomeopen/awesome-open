"""Offline tests for the deployment-evidence job helper. Synthetic fixtures only."""
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_deployment_backfill as job  # noqa: E402

SHA = "a" * 40
DAY = date(2026, 11, 2)


def pid(n):
    return hashlib.sha256(("https://example.org/open%d" % n).encode()).hexdigest()


def url(n):
    return "https://example.org/open%d" % n


def catalog(n=40, stars=lambda i: 1000 - i):
    return {"projects": [{"id": pid(i), "url": url(i), "name": "Open%d" % i,
                          "github": {"stars": stars(i)} if stars(i) is not None else None}
                         for i in range(n)]}


def art(ids):
    return {"artworks": {i: {"review_status": "approved"} for i in ids}}


def evidence(records=None):
    return {"schema_version": 1, "projects": records or {}}


def record(n, checked="2026-10-13", status="approved"):
    return {"project_url": url(n), "review_status": status, "checked_at": checked}


def outcomes(projects, run_id="r1", day="2026-11-02", **extra):
    return {"run_id": run_id, "date": day, "agent": "Kanzler (AI)", "source_sha": SHA, "pr": None,
            "notes": "", "projects": projects, **extra}


def apply(state, projects, cat, ev, **kw):
    return job.update_state(state, outcomes(projects, **kw), catalog=cat, evidence=ev)


def maintenance_state(cat, ev):
    """Reach maintenance legitimately: skip every uncovered project editorially, then switch."""
    ids = set(ev["projects"])
    skips = [{"id": p["id"], "project_url": p["url"], "outcome": "skipped", "reason": "no_schema_fit"}
             for p in cat["projects"] if p["id"] not in ids]
    state = job.empty_state()
    for start in range(0, max(len(skips), 1), 25):
        chunk = skips[start:start + 25]
        if chunk:
            state = apply(state, chunk, cat, ev, run_id="s%d" % start, day="2026-11-01")
    return apply(state, [], cat, ev, run_id="switch", day="2026-11-01",
                 set_mode={"mode": "maintenance", "reason": "full coverage"})


class BackfillSelectTests(unittest.TestCase):
    def test_batch_of_25_with_30_percent_reserve(self):
        cat = catalog()
        plan = job.select_plan(cat, evidence(), art([pid(i) for i in range(10, 40)]), job.empty_state(), day=DAY)
        tiers = [b["tier"] for b in plan["batch"]]
        self.assertEqual(len(tiers), 25)
        self.assertEqual(tiers.count("remaining"), 8)
        self.assertEqual(tiers.count("illustrated"), 17)
        self.assertEqual(plan["batch"][0]["id"], pid(10))
        self.assertEqual(plan["reverify"], [])

    def test_small_limit_and_bounds(self):
        plan = job.select_plan(catalog(), evidence(), art([pid(1)]), job.empty_state(), day=DAY, limit=5)
        self.assertEqual(len(plan["batch"]), 5)
        for bad in (0, 26):
            with self.assertRaises(ValueError):
                job.select_plan(catalog(), evidence(), art([]), job.empty_state(), day=DAY, limit=bad)

    def test_unknown_stars_last_ids_break_ties(self):
        cat = catalog(5, stars=lambda i: None if i == 0 else 5)
        plan = job.select_plan(cat, evidence(), art([]), job.empty_state(), day=DAY, limit=5)
        self.assertEqual(plan["batch"][-1]["id"], pid(0))
        tied = [b["id"] for b in plan["batch"][:-1]]
        self.assertEqual(tied, sorted(tied))

    def test_exclusions_pending_and_not_due(self):
        cat = catalog(6)
        ev = evidence({pid(0): record(0, status="rejected")})
        state = apply(job.empty_state(), [
            {"id": pid(1), "project_url": url(1), "outcome": "proposed"},
            {"id": pid(2), "project_url": url(2), "outcome": "skipped", "reason": "no_schema_fit"}], cat, ev)
        plan = job.select_plan(cat, ev, art([]), state, day=date(2026, 11, 3), excluded=[pid(3)])
        self.assertEqual({b["id"] for b in plan["batch"]}, {pid(4), pid(5)})
        self.assertEqual(plan["not_eligible"], {"has_record": 1, "excluded": 1, "proposed_pending": 1, "recheck_not_due": 1})

    def test_transient_skip_returns_after_14_days(self):
        cat = catalog(1)
        state = apply(job.empty_state(), [{"id": pid(0), "project_url": url(0), "outcome": "skipped",
                                           "reason": "sources_unreachable"}], cat, evidence())
        self.assertEqual(state["considered"][pid(0)]["recheck_after"], "2026-11-16")
        self.assertEqual(job.select_plan(cat, evidence(), art([]), state, day=date(2026, 11, 15))["batch"], [])
        self.assertEqual(len(job.select_plan(cat, evidence(), art([]), state, day=date(2026, 11, 16))["batch"]), 1)

    def test_deterministic(self):
        a = job.select_plan(catalog(), evidence(), art([pid(3)]), job.empty_state(), day=DAY)
        b = job.select_plan(catalog(), evidence(), art([pid(3)]), job.empty_state(), day=DAY)
        self.assertEqual(a, b)


class ModeTests(unittest.TestCase):
    def test_switch_refused_until_condition_met(self):
        cat = catalog(3)
        ev = evidence({pid(0): record(0)})
        with self.assertRaises(ValueError):
            apply(job.empty_state(), [], cat, ev, set_mode={"mode": "maintenance", "reason": "early"})
        # A transient skip blocks the switch even when everything was considered.
        state = apply(job.empty_state(), [
            {"id": pid(1), "project_url": url(1), "outcome": "skipped", "reason": "no_schema_fit"},
            {"id": pid(2), "project_url": url(2), "outcome": "skipped", "reason": "deferred_budget"}], cat, ev)
        self.assertFalse(job.status(cat, ev, art([]), state, day=DAY)["switch_to_maintenance_ready"])
        with self.assertRaises(ValueError):
            apply(state, [], cat, ev, run_id="r2", set_mode={"mode": "maintenance", "reason": "x"})

    def test_switch_and_revert(self):
        cat = catalog(4)
        ev = evidence({pid(0): record(0), pid(1): record(1)})
        state = maintenance_state(cat, ev)
        self.assertEqual(state["mode"], "maintenance")
        self.assertEqual(state["mode_history"][-1], {"mode": "maintenance", "since": "2026-11-01", "reason": "full coverage"})
        self.assertFalse(job.status(cat, ev, art([]), state, day=DAY)["switch_to_backfill_ready"])
        big = catalog(4 + job.REVERT_THRESHOLD + 1)
        self.assertTrue(job.status(big, ev, art([]), state, day=DAY)["switch_to_backfill_ready"])

    def test_maintenance_selects_new_rows_and_oldest_records(self):
        cat = catalog(8)
        ev = evidence({pid(i): record(i, checked="2026-10-%02d" % (10 + i)) for i in range(6)})
        state = maintenance_state(catalog(6), ev)  # rows 6 and 7 are "newly added" afterwards
        plan = job.select_plan(cat, ev, art([]), state, day=DAY)
        self.assertEqual([b["id"] for b in plan["batch"]], [pid(6), pid(7)])
        self.assertEqual([r["id"] for r in plan["reverify"]], [pid(0), pid(1), pid(2)])
        self.assertEqual(plan["reverify"][0]["age_days"], (DAY - date(2026, 10, 10)).days)
        # Verifying the oldest moves it to the back of the rotation.
        state = apply(state, [{"id": pid(0), "project_url": url(0), "outcome": "verified_unchanged"},
                              {"id": pid(1), "project_url": url(1), "outcome": "update_proposed"},
                              {"id": pid(2), "project_url": url(2), "outcome": "verify_deferred",
                               "reason": "sources_unreachable"}], cat, ev, run_id="m1")
        plan = job.select_plan(cat, ev, art([]), state, day=date(2026, 11, 3))
        self.assertEqual([r["id"] for r in plan["reverify"]], [pid(3), pid(4), pid(5)])

    def test_reverify_outcomes_need_maintenance_and_a_record(self):
        cat = catalog(2)
        ev = evidence({pid(0): record(0)})
        with self.assertRaises(ValueError):
            apply(job.empty_state(), [{"id": pid(0), "project_url": url(0), "outcome": "verified_unchanged"}], cat, ev)
        with self.assertRaises(ValueError):
            apply(job.empty_state(), [{"id": pid(0), "project_url": url(0), "outcome": "proposed"}], cat, ev)
        state = maintenance_state(cat, ev)
        with self.assertRaises(ValueError):
            apply(state, [{"id": pid(1), "project_url": url(1), "outcome": "verified_unchanged"}], cat, ev, run_id="m")
        with self.assertRaises(ValueError):
            apply(state, [{"id": pid(0), "project_url": url(0), "outcome": "verify_deferred",
                           "reason": "no_schema_fit"}], cat, ev, run_id="m")


class StateTests(unittest.TestCase):
    def test_rejects_unknown_reason_and_foreign_ids(self):
        cat = catalog(1)
        with self.assertRaises(ValueError):
            apply(job.empty_state(), [{"id": pid(0), "project_url": "u", "outcome": "skipped", "reason": "looks_abandoned"}], cat, evidence())
        with self.assertRaises(ValueError):
            apply(job.empty_state(), [{"id": pid(9), "project_url": "u", "outcome": "proposed"}], cat, evidence())

    def test_runs_bounded_and_pr_links(self):
        cat = catalog(1)
        state = job.empty_state()
        for n in range(job.MAX_RUNS_KEPT + 5):
            state = apply(state, [], cat, evidence(), run_id="r%02d" % n)
        self.assertEqual(len(state["runs"]), job.MAX_RUNS_KEPT)
        state = apply(state, [], cat, evidence(), run_id="next", pr_links=[{"run_id": "r64", "pr": 240}])
        self.assertEqual(next(r for r in state["runs"] if r["run_id"] == "r64")["pr"], 240)

    def test_merge_is_idempotent_and_keeps_latest(self):
        cat = catalog(3)
        main = apply(job.empty_state(), [{"id": pid(0), "project_url": url(0), "outcome": "skipped",
                                          "reason": "deferred_budget"}], cat, evidence())
        carry = apply(main, [{"id": pid(0), "project_url": url(0), "outcome": "skipped", "reason": "no_schema_fit"},
                             {"id": pid(1), "project_url": url(1), "outcome": "skipped", "reason": "no_schema_fit"}],
                      cat, evidence(), run_id="r2", day="2026-11-03")
        merged = job.merge_state(main, carry)
        self.assertEqual(merged["considered"][pid(0)]["reason"], "no_schema_fit")
        self.assertEqual(len(merged["runs"]), 2)
        self.assertEqual(job.merge_state(merged, carry), merged)
        self.assertEqual(job.merge_state(carry, main)["considered"], merged["considered"])
        report = job.status(cat, evidence(), art([]), main, day=DAY, carry=carry)
        self.assertEqual((report["carry_only_entries"], report["carry_only_runs"]), (2, 1))

    def test_merge_rejects_conflicting_runs(self):
        cat = catalog(1)
        a = apply(job.empty_state(), [], cat, evidence(), run_id="x", day="2026-11-02")
        b = apply(job.empty_state(), [], cat, evidence(), run_id="x", day="2026-11-03")
        with self.assertRaises(ValueError):
            job.merge_state(a, b)

    def test_validate_warnings(self):
        cat = catalog(1)
        state = apply(job.empty_state(), [{"id": pid(0), "project_url": url(0), "outcome": "proposed"}], cat, evidence())
        self.assertEqual(len(job.validate_state(state, catalog_ids=set(), evidence_ids=set())), 2)

    def test_checked_in_initial_ledger_is_valid(self):
        for path in (Path(__file__).resolve().parents[1] / "state/deployment-evidence-backfill.json",
                     Path(__file__).resolve().parents[1] / job.STATE_PATH):
            if path.exists():
                self.assertEqual(job.validate_state(json.loads(path.read_text())), [])


class CliTests(unittest.TestCase):
    def test_cli_round_trip_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "catalog.json").write_text(json.dumps(catalog(12)))
            (folder / "evidence.json").write_text(json.dumps(evidence()))
            (folder / "art.json").write_text(json.dumps(art([pid(5)])))
            script = str(Path(job.__file__))
            base = ["--catalog", str(folder / "catalog.json"), "--evidence", str(folder / "evidence.json"),
                    "--art", str(folder / "art.json"), "--state", str(folder / "state.json")]
            run = lambda *a: subprocess.run([sys.executable, script, *a], check=True, capture_output=True, text=True)
            run("select", *base, "--date", "2026-11-02", "--output", str(folder / "plan.json"))
            plan = json.loads((folder / "plan.json").read_text())
            self.assertEqual(plan["batch"][0]["id"], pid(5))
            (folder / "out.json").write_text(json.dumps(outcomes([{"id": pid(5), "project_url": url(5), "outcome": "skipped",
                                                                     "reason": "no_schema_fit"}])))
            run("update-state", *base, "--outcomes", str(folder / "out.json"))
            run("merge-state", "--base", str(folder / "state.json"), "--carry", str(folder / "missing.json"),
                "--output", str(folder / "merged.json"))
            self.assertEqual(json.loads((folder / "merged.json").read_text()), json.loads((folder / "state.json").read_text()))
            report = json.loads(run("status", *base, "--date", "2026-11-02").stdout)
            self.assertEqual(report["editorial_skips"], 1)
            kpis = json.loads(run("coverage", *base, "--date", "2026-11-02").stdout)
            self.assertEqual((kpis["mode"], kpis["approved_records"]), ("backfill", 0))
            self.assertIn("Ledger valid", run("validate", *base).stdout)


if __name__ == "__main__":
    unittest.main()
