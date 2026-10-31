#!/usr/bin/env python3
"""Offline helper for the deployment-evidence job (backfill and maintenance modes).

Subcommands, all network-free and deterministic:

  select        plan the next bounded batch for the ledger's current mode
  update-state  apply one run's outcomes (and an optional mode switch) to the ledger
  merge-state   union the main-branch ledger with the carry-branch ledger
  status        mode, switch readiness and carry/backlog counts as JSON
  validate      check the ledger against the catalog and evidence file
  coverage      print the current mode's KPIs as JSON

The ledger is automation/state/deployment-evidence-backfill.json. It is job
state, never site input: no build step reads it. See
automation/backfill-deployment-evidence.md.
"""

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = "automation/state/deployment-evidence-backfill.json"
JOB = "deployment-evidence-backfill"
SCHEMA = 2
MAX_BATCH = 25                  # new projects per run, both modes
REMAINING_SHARE = 0.3           # share of backfill slots reserved for projects without artwork
DEFAULT_REVERIFY = 3            # oldest approved records re-verified per maintenance run (~21/week)
MAX_REVERIFY = 5
REVERT_THRESHOLD = 75           # eligible new projects that send maintenance back to backfill
MAX_RUNS_KEPT = 60
MODES = ("backfill", "maintenance")
ID = re.compile(r"[0-9a-f]{64}\Z")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TIERS = ("illustrated", "remaining")
EDITORIAL = {"no_official_setup_source", "no_schema_fit", "identity_uncertain", "conflicting_sources"}
TRANSIENT = {"sources_unreachable", "overlaps_other_work", "deferred_budget"}
SKIP_REASONS = EDITORIAL | TRANSIENT
RECHECK_DAYS = {**{r: 90 for r in EDITORIAL}, **{r: 14 for r in TRANSIENT}}
# Outcome -> (applies to a project with an evidence record?, reason required?)
OUTCOMES = {
    "proposed": (False, False),          # new record in this run's PR
    "skipped": (False, True),            # no record proposed; recheck later
    "verified_unchanged": (True, False), # maintenance: sources still support the record
    "update_proposed": (True, False),    # maintenance: record changed in this run's PR
    "verify_deferred": (True, True),     # maintenance: could not re-verify (transient reasons only)
}
RUN_KEYS = {"run_id", "date", "agent", "source_sha", "mode", "selected", "proposed", "skipped",
            "verified", "updated", "deferred", "pr", "notes"}
ENTRY_KEYS = {"project_url", "outcome", "reason", "checked_at", "recheck_after", "run_id", "agent"}


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("Expected a full lowercase canonical project ID: %r" % (value,))
    return value


def _day(value, label):
    if not isinstance(value, str) or not DAY.fullmatch(value):
        raise ValueError(label + " must be YYYY-MM-DD")
    return date.fromisoformat(value)


def empty_state(since="2026-10-31"):
    return {"schema_version": SCHEMA, "job": JOB, "contract_version": 2, "mode": "backfill",
            "mode_since": since, "mode_history": [{"mode": "backfill", "since": since, "reason": "initial"}],
            "considered": {}, "runs": []}


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def validate_state(state, catalog_ids=None, evidence_ids=None):
    """Raise ValueError on any malformed field. Returns a list of warnings."""
    warnings = []
    top = {"schema_version", "job", "contract_version", "mode", "mode_since", "mode_history", "considered", "runs"}
    if not isinstance(state, dict) or set(state) != top:
        raise ValueError("Ledger must have exactly: " + ", ".join(sorted(top)))
    if state["schema_version"] != SCHEMA or state["job"] != JOB:
        raise ValueError("Unknown ledger schema or job")
    if type(state["contract_version"]) is not int or state["contract_version"] < 1:
        raise ValueError("contract_version must be a positive integer")
    if state["mode"] not in MODES:
        raise ValueError("mode must be backfill or maintenance")
    _day(state["mode_since"], "mode_since")
    history = state["mode_history"]
    if not isinstance(history, list) or not history:
        raise ValueError("mode_history must be a nonempty list")
    for item in history:
        if not isinstance(item, dict) or set(item) != {"mode", "since", "reason"} or item["mode"] not in MODES:
            raise ValueError("mode_history entries need mode, since, reason")
        _day(item["since"], "mode_history since")
        if not isinstance(item["reason"], str) or not item["reason"].strip():
            raise ValueError("mode_history reason must be nonempty")
    if history[-1]["mode"] != state["mode"] or history[-1]["since"] != state["mode_since"]:
        raise ValueError("mode and mode_since must match the last mode_history entry")
    if not isinstance(state["considered"], dict) or not isinstance(state["runs"], list):
        raise ValueError("considered must be an object and runs a list")
    run_ids = set()
    for run in state["runs"]:
        if not isinstance(run, dict) or set(run) != RUN_KEYS:
            raise ValueError("Run entries need exactly: " + ", ".join(sorted(RUN_KEYS)))
        if not isinstance(run["run_id"], str) or not run["run_id"] or run["run_id"] in run_ids:
            raise ValueError("run_id must be a unique nonempty string")
        run_ids.add(run["run_id"])
        _day(run["date"], "run date")
        if run["mode"] not in MODES:
            raise ValueError("run mode must be backfill or maintenance")
        if not isinstance(run["agent"], str) or not run["agent"].strip():
            raise ValueError("run agent must name the truthful agent identity")
        if not isinstance(run["source_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", run["source_sha"]):
            raise ValueError("run source_sha must be a full commit SHA")
        counts = ("selected", "proposed", "skipped", "verified", "updated", "deferred")
        if any(type(run[k]) is not int or run[k] < 0 for k in counts):
            raise ValueError("run counts must be non-negative integers")
        if sum(run[k] for k in counts[1:]) > run["selected"]:
            raise ValueError("outcome counts cannot exceed selected")
        if run["pr"] is not None and (type(run["pr"]) is not int or run["pr"] < 1):
            raise ValueError("run pr must be null or a positive integer")
        if not isinstance(run["notes"], str) or len(run["notes"]) > 600:
            raise ValueError("run notes must be a string of at most 600 characters")
    if len(state["runs"]) > MAX_RUNS_KEPT:
        raise ValueError("Keep at most %d run entries" % MAX_RUNS_KEPT)
    for pid, entry in state["considered"].items():
        _id(pid)
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise ValueError("Considered entries need exactly: " + ", ".join(sorted(ENTRY_KEYS)))
        if entry["outcome"] not in OUTCOMES:
            raise ValueError("Unknown outcome for " + pid)
        checked = _day(entry["checked_at"], "checked_at")
        _, needs_reason = OUTCOMES[entry["outcome"]]
        if needs_reason:
            allowed = TRANSIENT if entry["outcome"] == "verify_deferred" else SKIP_REASONS
            if entry["reason"] not in allowed:
                raise ValueError("Invalid reason for %s outcome on %s" % (entry["outcome"], pid))
            if _day(entry["recheck_after"], "recheck_after") <= checked:
                raise ValueError("recheck_after must follow checked_at for " + pid)
        elif entry["reason"] is not None or entry["recheck_after"] is not None:
            raise ValueError("This outcome uses null reason and recheck_after: " + pid)
        if not isinstance(entry["agent"], str) or not entry["agent"].strip():
            raise ValueError("Considered entries need an agent")
        if entry["run_id"] not in run_ids:
            warnings.append("considered %s refers to a pruned or unknown run %s" % (pid, entry["run_id"]))
        if catalog_ids is not None and pid not in catalog_ids:
            warnings.append("considered %s is no longer in the catalog" % pid)
        if evidence_ids is not None and entry["outcome"] in ("proposed", "update_proposed") and pid not in evidence_ids:
            warnings.append("%s %s has no evidence record on this revision (pending or rejected PR?)" % (entry["outcome"], pid))
    return warnings


def _illustrated(art):
    records = (art or {}).get("artworks", {})
    return {pid for pid, record in records.items()
            if isinstance(record, dict) and record.get("review_status") == "approved"}


def _stars(project):
    github = project.get("github")
    value = github.get("stars") if isinstance(github, dict) else None
    return value if type(value) is int and value >= 0 else None


def _check_inputs(catalog, evidence, state):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("projects"), list):
        raise ValueError("Expected a built catalog with a projects list")
    if not isinstance(evidence, dict) or evidence.get("schema_version") != 1 or not isinstance(evidence.get("projects"), dict):
        raise ValueError("Expected deployment evidence schema 1")
    validate_state(state)


def _new_queue(catalog, evidence, art, state, day, excluded):
    """Projects without any evidence record that are due for research, by tier."""
    illustrated = _illustrated(art)
    existing = set(evidence["projects"])
    queues = {tier: [] for tier in TIERS}
    counts = {"has_record": 0, "excluded": 0, "proposed_pending": 0, "recheck_not_due": 0}
    seen = set()
    for project in catalog["projects"]:
        pid = _id(project.get("id"))
        if pid in seen:
            raise ValueError("Duplicate catalog ID " + pid)
        seen.add(pid)
        if pid in existing:
            counts["has_record"] += 1
            continue
        if pid in excluded:
            counts["excluded"] += 1
            continue
        entry = state["considered"].get(pid)
        if entry and entry["outcome"] == "proposed":
            counts["proposed_pending"] += 1
            continue
        if entry and entry["outcome"] == "skipped" and date.fromisoformat(entry["recheck_after"]) > day:
            counts["recheck_not_due"] += 1
            continue
        tier = "illustrated" if pid in illustrated else "remaining"
        stars = _stars(project)
        queues[tier].append(((0, -stars) if stars is not None else (1, 0), pid, project))
    for tier in TIERS:
        queues[tier].sort(key=lambda item: (item[0], item[1]))
    return queues, counts


def last_verified(pid, record, state):
    """Latest of the record's own review date and any later ledger verification."""
    dates = [date.fromisoformat(record["checked_at"])]
    entry = state["considered"].get(pid)
    if entry and entry["outcome"] in ("verified_unchanged", "update_proposed", "proposed"):
        dates.append(date.fromisoformat(entry["checked_at"]))
    return max(dates)


def _reverify_queue(catalog, evidence, state, day, excluded):
    ids = {p["id"] for p in catalog["projects"]}
    queue = []
    for pid, record in evidence["projects"].items():
        if pid not in ids or pid in excluded or record.get("review_status") != "approved":
            continue
        entry = state["considered"].get(pid)
        if entry and entry["outcome"] == "update_proposed" and entry["checked_at"] > record["checked_at"]:
            continue  # an update is pending review
        if entry and entry["outcome"] == "verify_deferred" and date.fromisoformat(entry["recheck_after"]) > day:
            continue
        queue.append((last_verified(pid, record, state), pid, record))
    queue.sort(key=lambda item: (item[0], item[1]))
    return queue


def _item(tier, project, stars=None):
    return {"id": project["id"], "project_url": project["url"], "name": project.get("name"), "tier": tier,
            "stars": _stars(project), "has_function_summary": bool(project.get("function_summary"))}


def select_plan(catalog, evidence, art, state, *, day, limit=MAX_BATCH, reverify=DEFAULT_REVERIFY, excluded=()):
    """Return the ordered plan for the ledger's mode. Pure function: no I/O, no clock, no network."""
    if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError("limit must be between 1 and %d" % MAX_BATCH)
    if type(reverify) is not int or not 0 <= reverify <= MAX_REVERIFY:
        raise ValueError("reverify must be between 0 and %d" % MAX_REVERIFY)
    if type(day) is not date:
        raise ValueError("day must be a date")
    _check_inputs(catalog, evidence, state)
    excluded = {_id(pid) for pid in excluded}
    queues, counts = _new_queue(catalog, evidence, art, state, day, excluded)
    mode = state["mode"]
    if mode == "backfill":
        reserve = min(int(limit * REMAINING_SHARE + 0.5), len(queues["remaining"]), limit)
        take_ill = min(len(queues["illustrated"]), limit - reserve)
        take_rem = min(len(queues["remaining"]), limit - take_ill)
        chosen = ([("illustrated", it) for it in queues["illustrated"][:take_ill]] +
                  [("remaining", it) for it in queues["remaining"][:take_rem]])
        new = [_item(tier, it[2]) for tier, it in chosen]
        again = []
    else:
        # Maintenance: newest gaps first is not knowable offline; use the same
        # deterministic order without a tier reserve, then the oldest records.
        merged = sorted(queues["illustrated"] + queues["remaining"], key=lambda it: (it[0], it[1]))
        new = [_item("new", it[2]) for it in merged[:limit]]
        by_id = {p["id"]: p for p in catalog["projects"]}
        again = [{"id": pid, "project_url": record["project_url"], "name": by_id[pid].get("name"),
                  "tier": "reverify", "last_verified": when.isoformat(),
                  "age_days": (day - when).days} for when, pid, record in
                 _reverify_queue(catalog, evidence, state, day, excluded)[:reverify]]
    return {"job": JOB, "mode": mode, "date": day.isoformat(), "limit": limit,
            "batch": new, "reverify": again,
            "eligible": {tier: len(queues[tier]) for tier in TIERS}, "not_eligible": counts}


def status(catalog, evidence, art, state, *, day, carry=None):
    """Mode, switch readiness and carry counts. Pure."""
    _check_inputs(catalog, evidence, state)
    queues, _ = _new_queue(catalog, evidence, art, state, day, set())
    ids = {p["id"] for p in catalog["projects"]}
    existing = set(evidence["projects"]) & ids
    uncovered = ids - existing
    editorial = {pid for pid in uncovered if state["considered"].get(pid, {}).get("outcome") == "skipped"
                 and state["considered"][pid]["reason"] in EDITORIAL}
    transient = {pid for pid, e in state["considered"].items()
                 if e["outcome"] == "skipped" and e["reason"] in TRANSIENT and pid in uncovered}
    pending = {pid for pid, e in state["considered"].items() if e["outcome"] == "proposed" and pid not in existing}
    eligible_new = len(queues["illustrated"]) + len(queues["remaining"])
    ready_maintenance = (state["mode"] == "backfill" and not pending and not transient
                         and uncovered == editorial)
    ready_backfill = state["mode"] == "maintenance" and eligible_new > REVERT_THRESHOLD
    result = {"mode": state["mode"], "mode_since": state["mode_since"], "projects": len(ids),
              "with_record": len(existing), "uncovered": len(uncovered), "editorial_skips": len(editorial),
              "transient_skips": len(transient), "proposed_pending": len(pending), "eligible_new": eligible_new,
              "switch_to_maintenance_ready": ready_maintenance, "switch_to_backfill_ready": ready_backfill}
    if carry is not None:
        validate_state(carry)
        result["carry_only_entries"] = sum(1 for pid, e in carry["considered"].items()
                                           if state["considered"].get(pid) != e)
        known = {r["run_id"] for r in state["runs"]}
        result["carry_only_runs"] = sum(1 for r in carry["runs"] if r["run_id"] not in known)
    return result


def update_state(state, outcomes, *, catalog, evidence, art=None):
    """Apply one run's outcomes and optional mode switch. Returns a new ledger; never mutates input."""
    validate_state(state)
    required = {"run_id", "date", "agent", "source_sha", "pr", "notes", "projects"}
    optional = {"set_mode", "pr_links"}
    if not isinstance(outcomes, dict) or not required <= set(outcomes) or set(outcomes) - required - optional:
        raise ValueError("Outcomes need: " + ", ".join(sorted(required)) + " (optional: set_mode, pr_links)")
    run_day = _day(outcomes["date"], "run date")
    catalog_ids = {p["id"] for p in catalog["projects"]}
    record_ids = set(evidence["projects"])
    new = json.loads(json.dumps(state))
    counts = dict.fromkeys(("proposed", "skipped", "verified", "updated", "deferred"), 0)
    key = {"proposed": "proposed", "skipped": "skipped", "verified_unchanged": "verified",
           "update_proposed": "updated", "verify_deferred": "deferred"}
    if not isinstance(outcomes["projects"], list) or len(outcomes["projects"]) > MAX_BATCH + MAX_REVERIFY:
        raise ValueError("A run records at most %d projects" % (MAX_BATCH + MAX_REVERIFY))
    ids = set()
    for item in outcomes["projects"]:
        if not isinstance(item, dict) or set(item) - {"id", "project_url", "outcome", "reason"} or not {"id", "project_url", "outcome"} <= set(item):
            raise ValueError("Project outcomes need id, project_url, outcome and optional reason")
        pid = _id(item["id"])
        if pid in ids:
            raise ValueError("Duplicate project in one run: " + pid)
        ids.add(pid)
        if pid not in catalog_ids:
            raise ValueError("Project is not in the current catalog: " + pid)
        outcome = item["outcome"]
        if outcome not in OUTCOMES:
            raise ValueError("Unknown outcome " + str(outcome))
        on_record, needs_reason = OUTCOMES[outcome]
        if on_record and pid not in record_ids:
            raise ValueError("%s applies only to an existing record: %s" % (outcome, pid))
        if not on_record and pid in record_ids:
            raise ValueError("%s applies only to a project without a record: %s" % (outcome, pid))
        if outcome in ("verified_unchanged", "update_proposed", "verify_deferred") and new["mode"] != "maintenance":
            raise ValueError("Re-verification outcomes require maintenance mode")
        reason = item.get("reason")
        recheck = None
        if needs_reason:
            allowed = TRANSIENT if outcome == "verify_deferred" else SKIP_REASONS
            if reason not in allowed:
                raise ValueError("Outcome %s needs a valid reason: %s" % (outcome, pid))
            recheck = (run_day + timedelta(days=RECHECK_DAYS[reason])).isoformat()
        elif reason is not None:
            raise ValueError("Outcome %s takes no reason: %s" % (outcome, pid))
        counts[key[outcome]] += 1
        new["considered"][pid] = {"project_url": item["project_url"], "outcome": outcome, "reason": reason,
                                  "checked_at": outcomes["date"], "recheck_after": recheck,
                                  "run_id": outcomes["run_id"], "agent": outcomes["agent"]}
    for link in outcomes.get("pr_links", []):
        if not isinstance(link, dict) or set(link) != {"run_id", "pr"} or type(link["pr"]) is not int or link["pr"] < 1:
            raise ValueError("pr_links entries need run_id and a positive pr")
        for run in new["runs"]:
            if run["run_id"] == link["run_id"]:
                run["pr"] = link["pr"]
    new["runs"].append({"run_id": outcomes["run_id"], "date": outcomes["date"], "agent": outcomes["agent"],
                        "source_sha": outcomes["source_sha"], "mode": new["mode"], "selected": len(ids),
                        **counts, "pr": outcomes["pr"], "notes": outcomes["notes"]})
    new["runs"] = new["runs"][-MAX_RUNS_KEPT:]
    new["considered"] = dict(sorted(new["considered"].items()))
    switch = outcomes.get("set_mode")
    if switch is not None:
        if not isinstance(switch, dict) or set(switch) != {"mode", "reason"} or switch["mode"] not in MODES:
            raise ValueError("set_mode needs mode and reason")
        report = status(catalog, evidence, art or {"artworks": {}}, new, day=run_day)
        if switch["mode"] == new["mode"]:
            raise ValueError("Ledger is already in " + new["mode"])
        needed = "switch_to_maintenance_ready" if switch["mode"] == "maintenance" else "switch_to_backfill_ready"
        if not report[needed]:
            raise ValueError("Switch condition not met: " + json.dumps(report, sort_keys=True))
        new["mode"], new["mode_since"] = switch["mode"], outcomes["date"]
        new["mode_history"].append({"mode": switch["mode"], "since": outcomes["date"], "reason": switch["reason"]})
    validate_state(new)
    return new


def merge_state(base, carry):
    """Union two ledgers (main and the carry branch). Idempotent and order-independent for equal inputs."""
    validate_state(base)
    validate_state(carry)
    merged = json.loads(json.dumps(base))
    for pid, entry in carry["considered"].items():
        current = merged["considered"].get(pid)
        if current is None or (entry["checked_at"], entry["run_id"]) > (current["checked_at"], current["run_id"]):
            merged["considered"][pid] = entry
    runs = {r["run_id"]: r for r in base["runs"]}
    for run in carry["runs"]:
        if run["run_id"] in runs and {k: v for k, v in runs[run["run_id"]].items() if k != "pr"} != {k: v for k, v in run.items() if k != "pr"}:
            raise ValueError("Conflicting run entries for " + run["run_id"])
        if run["run_id"] not in runs or (runs[run["run_id"]]["pr"] is None and run["pr"] is not None):
            runs[run["run_id"]] = run
    merged["runs"] = sorted(runs.values(), key=lambda r: (r["date"], r["run_id"]))[-MAX_RUNS_KEPT:]
    history = {(h["since"], h["mode"]): h for h in base["mode_history"] + carry["mode_history"]}
    merged["mode_history"] = [history[k] for k in sorted(history)]
    merged["mode"], merged["mode_since"] = merged["mode_history"][-1]["mode"], merged["mode_history"][-1]["since"]
    merged["contract_version"] = max(base["contract_version"], carry["contract_version"])
    merged["considered"] = dict(sorted(merged["considered"].items()))
    validate_state(merged)
    return merged


def coverage(catalog, evidence, art, state, *, day):
    ids = {p["id"] for p in catalog["projects"]}
    records = evidence["projects"]
    approved = {pid for pid, r in records.items() if r.get("review_status") == "approved" and pid in ids}
    illustrated = _illustrated(art) & ids
    ranked = sorted((p for p in catalog["projects"] if _stars(p) is not None), key=lambda p: (-_stars(p), p["id"]))
    top100 = {p["id"] for p in ranked[:100]}
    facts = [sum(len(r.get(f, [])) for f in ("run_modes", "install_methods", "platforms", "external_services", "packages", "requirements"))
             for pid, r in records.items() if pid in approved]
    sizes = [len(json.dumps(records[pid], ensure_ascii=False, separators=(",", ":"))) for pid in approved]
    skips = {}
    for entry in state["considered"].values():
        if entry["outcome"] == "skipped":
            skips[entry["reason"]] = skips.get(entry["reason"], 0) + 1
    pct = lambda a, b: round(100.0 * a / b, 1) if b else None
    median = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    week = [r for r in state["runs"] if 0 <= (day - date.fromisoformat(r["date"])).days < 7]
    result = {"mode": state["mode"], "projects": len(ids), "approved_records": len(approved),
              "coverage_pct": pct(len(approved), len(ids)),
              "illustrated_coverage_pct": pct(len(approved & illustrated), len(illustrated)),
              "top100_stars_coverage_pct": pct(len(approved & top100), len(top100)),
              "median_facts_per_record": median(facts), "median_record_bytes": median(sizes),
              "skips_by_reason": dict(sorted(skips.items())), "runs_recorded": len(state["runs"])}
    if state["mode"] == "maintenance":
        ages = sorted((day - last_verified(pid, records[pid], state)).days for pid in approved)
        queues, _ = _new_queue(catalog, evidence, art, state, day, set())
        result.update({"eligible_new_now": len(queues["illustrated"]) + len(queues["remaining"]),
                       "verified_last_7_days": sum(r["verified"] + r["updated"] for r in week),
                       "updated_last_7_days": sum(r["updated"] for r in week),
                       "oldest_verification_age_days": ages[-1] if ages else None,
                       "median_verification_age_days": median(ages)})
    else:
        result.update({"proposed_last_7_days": sum(r["proposed"] for r in week),
                       "yield_last_7_days": pct(sum(r["proposed"] for r in week), sum(r["selected"] for r in week))})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--catalog", type=Path, required=True, help="Output of scripts/build_catalog.py")
    common.add_argument("--evidence", type=Path, default=ROOT / "data/deployment_evidence.json")
    common.add_argument("--art", type=Path, default=ROOT / "data/specimen_art.json")
    common.add_argument("--state", type=Path, default=ROOT / STATE_PATH)
    dated = argparse.ArgumentParser(add_help=False)
    dated.add_argument("--date", required=True, help="Actual UTC run date, YYYY-MM-DD")
    s = sub.add_parser("select", parents=[common, dated])
    s.add_argument("--limit", type=int, default=MAX_BATCH)
    s.add_argument("--reverify", type=int, default=DEFAULT_REVERIFY)
    s.add_argument("--exclude-ids", type=Path, help="JSON array of IDs reserved by open PRs or active work")
    s.add_argument("--output", type=Path, required=True)
    u = sub.add_parser("update-state", parents=[common])
    u.add_argument("--outcomes", type=Path, required=True)
    m = sub.add_parser("merge-state")
    m.add_argument("--base", type=Path, required=True)
    m.add_argument("--carry", type=Path, required=True)
    m.add_argument("--output", type=Path, required=True)
    st = sub.add_parser("status", parents=[common, dated])
    st.add_argument("--carry", type=Path)
    sub.add_parser("validate", parents=[common])
    sub.add_parser("coverage", parents=[common, dated])
    args = parser.parse_args(argv)

    if args.command == "merge-state":
        base = load_json(args.base)
        carry = load_json(args.carry, base)
        merged = merge_state(base, carry)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Merged ledger: %d considered, %d runs, mode %s" % (len(merged["considered"]), len(merged["runs"]), merged["mode"]))
        return 0
    catalog = load_json(args.catalog)
    evidence = load_json(args.evidence, {"schema_version": 1, "projects": {}})
    art = load_json(args.art, {"artworks": {}})
    state = load_json(args.state, empty_state())
    if args.command == "select":
        excluded = load_json(args.exclude_ids) if args.exclude_ids else []
        plan = select_plan(catalog, evidence, art, state, day=_day(args.date, "--date"),
                           limit=args.limit, reverify=args.reverify, excluded=excluded)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Mode %s: %d new, %d re-verify (eligible: %s)" % (plan["mode"], len(plan["batch"]), len(plan["reverify"]), plan["eligible"]))
    elif args.command == "update-state":
        new = update_state(state, load_json(args.outcomes), catalog=catalog, evidence=evidence, art=art)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Ledger updated: mode %s, %d considered, %d runs" % (new["mode"], len(new["considered"]), len(new["runs"])))
    elif args.command == "status":
        carry = load_json(args.carry) if args.carry and Path(args.carry).exists() else None
        print(json.dumps(status(catalog, evidence, art, state, day=_day(args.date, "--date"), carry=carry), indent=2))
    elif args.command == "validate":
        warnings = validate_state(state, {p["id"] for p in catalog["projects"]}, set(evidence["projects"]))
        for warning in warnings:
            print("warning: " + warning)
        print("Ledger valid: mode %s, %d considered, %d runs, %d warnings" % (state["mode"], len(state["considered"]), len(state["runs"]), len(warnings)))
    else:
        print(json.dumps(coverage(catalog, evidence, art, state, day=_day(args.date, "--date")), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
