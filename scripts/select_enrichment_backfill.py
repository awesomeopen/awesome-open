#!/usr/bin/env python3
"""Plan a bounded, illustrated-first summary or feature research batch offline."""

import argparse
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

from build_site import attach_specimen_art

ROOT = Path(__file__).resolve().parents[1]
MAX_BATCH = 40
ID = re.compile(r"[0-9a-f]{64}\Z")
TIERS = ("illustrated", "unillustrated")


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("Expected a full lowercase canonical project ID")
    return value


def _rotate(ids, after, day, slot):
    if not ids:
        return [], 0, "empty"
    if after is not None:
        offset = next((i for i, pid in enumerate(ids) if pid > after), 0)
        reason = "after cursor"
    else:
        ordinal = (day - date(1970, 1, 1)).days
        # A unit step avoids locking small reserved tiers to the same IDs
        # when history is unavailable and their size divides the batch bound.
        offset = (ordinal * 3 + slot) % len(ids)
        reason = "UTC-day/slot fallback"
    return ids[offset:] + ids[:offset], offset, reason


def select_plan(catalog, summaries, *, job, day, slot, limit=MAX_BATCH,
                excluded=(), after=None, cursors=None):
    """Return a proposal queue; the caller records actual consideration separately.

    Catalog artwork must already be attached by the site's approved-asset loader.
    Existing records of every status are reserved from the summary job. Feature
    candidates need an approved record with absent/empty features. Malformed
    records are skipped, and canonical duplicates with conflicting identity fail.
    """
    if job not in {"summaries", "features"}:
        raise ValueError("job must be summaries or features")
    if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError("limit must be between 1 and 40")
    if type(slot) is not int or slot not in (0, 1, 2):
        raise ValueError("slot must be 0, 1 or 2")
    if type(day) is not date:
        raise ValueError("day must be a date")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("projects"), list):
        raise ValueError("Expected a built catalog projects list")
    if (not isinstance(summaries, dict) or summaries.get("schema_version") != 1
            or not isinstance(summaries.get("summaries"), dict)):
        raise ValueError("Expected function summaries schema 1")
    excluded = {_id(pid) for pid in excluded}
    cursors = dict(cursors or {})
    if set(cursors) - set(TIERS):
        raise ValueError("Unknown cursor tier")
    if after is not None:
        _id(after)
        if cursors:
            raise ValueError("Use a legacy cursor or per-tier cursors, not both")
        cursors = dict.fromkeys(TIERS, after)
    for value in cursors.values():
        if value is not None:
            _id(value)
    records = summaries["summaries"]
    projects, skipped = {}, []
    queues = {tier: [] for tier in TIERS}
    for project in catalog["projects"]:
        if not isinstance(project, dict):
            raise ValueError("Expected catalog project object")
        pid = _id(project.get("id"))
        if any(not isinstance(project.get(k), str) or not project[k] for k in ("name", "url")):
            raise ValueError("Expected project name and URL")
        if pid in projects:
            if any(project.get(k) != projects[pid].get(k) for k in ("name", "url", "artwork")):
                raise ValueError("Conflicting duplicate canonical project: " + pid)
            continue
        projects[pid] = project
        reason = None
        record = records.get(pid)
        if pid in excluded:
            reason = "reserved by open PR or active work"
        elif job == "summaries" and pid in records:
            reason = "existing summary record"
        elif job == "features":
            if not isinstance(record, dict):
                reason = "missing or malformed summary"
            elif record.get("review_status") != "approved":
                reason = "summary is not approved"
            elif "features" in record and not isinstance(record["features"], list):
                reason = "malformed feature list"
            elif record.get("features"):
                reason = "existing feature list"
        if reason:
            skipped.append({"id": pid, "reason": reason})
        else:
            queues["illustrated" if project.get("artwork") else "unillustrated"].append(pid)
    rotation = {}
    for tier in TIERS:
        queues[tier], offset, reason = _rotate(sorted(queues[tier]), cursors.get(tier), day, slot)
        rotation[tier] = {"after": cursors.get(tier), "offset": offset, "reason": reason}
    # At the normal 40-project bound, reserve 10 places for the unillustrated
    # queue so repeated source failures in the priority tier cannot starve it.
    reserve = min(len(queues["unillustrated"]), (limit + 3) // 4) if limit > 1 else 0
    illustrated_count = min(len(queues["illustrated"]), limit - reserve)
    unillustrated_count = min(len(queues["unillustrated"]), limit - illustrated_count)
    illustrated_count = min(len(queues["illustrated"]), limit - unillustrated_count)
    selected = {"illustrated": queues["illustrated"][:illustrated_count],
                "unillustrated": queues["unillustrated"][:unillustrated_count]}
    candidates = [{"id": pid, "name": projects[pid]["name"], "url": projects[pid]["url"],
                   "tier": tier} for tier in TIERS for pid in selected[tier]]
    return {"job": job, "date": day.isoformat(), "slot": slot, "limit": limit,
            "source_sha": catalog.get("source_sha"),
            "eligible_counts": {tier: len(queues[tier]) for tier in TIERS},
            "rotation": rotation, "candidates": candidates,
            "eligibility_skips": sorted(skipped, key=lambda item: item["id"]),
            "research_groups": [[p["id"] for p in candidates[i:i + 10]]
                                for i in range(0, len(candidates), 10)],
            "planned_cursors": {tier: selected[tier][-1] if selected[tier]
                                else cursors.get(tier) for tier in TIERS},
            "cursor_rule": "Advance through each tier's completed contiguous prefix, including source skips; "
                           "retain later completed work after a gap. Planned IDs are not considered."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", choices=("summaries", "features"), required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--slot", type=int, choices=(0, 1, 2), required=True,
                        help="Nominal 08:00, 15:00 or 19:00 New York run index")
    parser.add_argument("--limit", type=int, default=MAX_BATCH)
    parser.add_argument("--after", help="Legacy scalar cursor; seeds both tiers")
    parser.add_argument("--after-illustrated")
    parser.add_argument("--after-unillustrated")
    parser.add_argument("--exclude-ids", type=Path, help="JSON list of full IDs reserved by PRs/active work")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        # Recompute displayable artwork from current files instead of trusting
        # a stale catalog's attached artwork or raw manifest review status.
        catalog = deepcopy(catalog)
        if not isinstance(catalog, dict) or not isinstance(catalog.get("projects"), list):
            raise ValueError("Expected a built catalog projects list")
        for project in catalog["projects"]:
            if not isinstance(project, dict):
                raise ValueError("Expected catalog project object")
            project.pop("artwork", None)
        attach_specimen_art(catalog, args.root)
        summaries = json.loads((args.root / "data/function_summaries.json").read_text(encoding="utf-8"))
        excluded = json.loads(args.exclude_ids.read_text(encoding="utf-8")) if args.exclude_ids else []
        if not isinstance(excluded, list):
            raise ValueError("--exclude-ids must contain a JSON list")
        cursors = {tier: value for tier, value in (
            ("illustrated", args.after_illustrated), ("unillustrated", args.after_unillustrated))
                   if value is not None}
        plan = select_plan(catalog, summaries, job=args.job, day=args.date, slot=args.slot,
                           limit=args.limit, excluded=excluded, after=args.after, cursors=cursors)
        output = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
