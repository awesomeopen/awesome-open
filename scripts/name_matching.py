"""Reviewed display-name equivalence and offline, review-only suggestions.

A shared spelling never changes catalog identity, aliases or HN attribution.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from build_catalog import canonical_url

REVIEWED_EQUIVALENCES = {
  "schema_version": 1,
  "groups": [
    {
      "id": "opentask-plural",
      "reason": "plural",
      "basis": "The current displayed names differ by the plural suffix s. This preserves the previously reviewed OpenTask/OpenTasks grouping.",
      "checked_at": "2026-10-31",
      "reviewed_by": "Junge (AI)",
      "members": [
        {
          "project_url": "https://github.com/AristideDongo/opentask",
          "name": "OpenTask",
          "source_url": "https://github.com/AristideDongo/opentask"
        },
        {
          "project_url": "https://github.com/dmfs/opentasks",
          "name": "OpenTasks",
          "source_url": "https://github.com/dmfs/opentasks"
        }
      ]
    }
  ]
}
SEPARATORS = re.compile(r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000_-]")
REASONS = {"plural", "spelling"}


def name_key(name):
    return SEPARATORS.sub("", name.lower())


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 for c in value)


def _https(value):
    if not _text(value) or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        parsed.port  # Reject malformed/out-of-range ports.
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def load_reviewed(catalog, data=None):
    """Validate the authored registry against current names, without changing identities.

    An explicit document is accepted for unit tests, not from a runtime file.
    Registry groups absent from a partial/fixture catalog are not applicable.
    """
    builtin = data is None
    if builtin:
        data = REVIEWED_EQUIVALENCES
    if not isinstance(data, dict) or set(data) != {"schema_version", "groups"} or type(data["schema_version"]) is not int or data["schema_version"] != 1 or not isinstance(data["groups"], list):
        raise ValueError("Invalid name-equivalence document")
    projects = {canonical_url(p["url"]): p for p in catalog["projects"]}
    result, ids = {}, set()
    for group in data["groups"]:
        required = {"id", "reason", "basis", "checked_at", "reviewed_by", "members"}
        if not isinstance(group, dict) or set(group) != required:
            raise ValueError("Invalid name-equivalence group")
        gid = group["id"]
        if not isinstance(gid, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", gid) or gid in ids:
            raise ValueError("Duplicate or invalid name-equivalence ID")
        ids.add(gid)
        if not isinstance(group["reason"], str) or group["reason"] not in REASONS or not _text(group["basis"]) or not _text(group["reviewed_by"]):
            raise ValueError("Name equivalence requires reviewed reason and basis")
        try:
            if not isinstance(group["checked_at"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", group["checked_at"]):
                raise ValueError("Invalid date")
            date.fromisoformat(group["checked_at"])
        except (TypeError, ValueError):
            raise ValueError("Invalid name-equivalence review date") from None
        members = group["members"]
        if not isinstance(members, list) or not 2 <= len(members) <= 20:
            raise ValueError("Name equivalence requires two to twenty reviewed members")
        if builtin and not any(isinstance(member, dict) and
                               canonical_url(member.get("project_url", "")) in projects
                               for member in members):
            continue
        seen_urls, keys = set(), set()
        for member in members:
            if not isinstance(member, dict) or set(member) != {"project_url", "name", "source_url"} or not _https(member["source_url"]) or not _https(member["project_url"]) or not _text(member["name"]):
                raise ValueError("Invalid name-equivalence member/source")
            url = canonical_url(member["project_url"])
            current = projects.get(url)
            if not current or url in seen_urls or current["name"] != member["name"]:
                raise ValueError("Unknown, repeated or renamed name-equivalence identity")
            seen_urls.add(url)
            key = name_key(member["name"])
            if not key:
                raise ValueError("Empty name-equivalence key")
            keys.add(key)
        if len(keys) < 2 or keys & result.keys():
            raise ValueError("Name equivalence must join distinct keys without overlapping groups")
        if group["reason"] == "plural":
            if len(keys) != 2 or not any(key + "s" in keys for key in keys):
                raise ValueError("Plural review requires a singular/suffix-s pair")
        # Every exact normalized spelling has one reviewed key. Other canonical
        # projects displaying that same spelling join without creating chains.
        for key in keys:
            result[key] = {"key": "reviewed:" + gid, "reason": group["reason"]}
    return result


def annotate(projects, reviewed):
    """Return copies carrying only the reviewed key/reason needed by both renderers."""
    return [dict(p, name_match=dict(reviewed[name_key(p["name"])]))
            if name_key(p["name"]) in reviewed else dict(p)
            for p in projects]


def one_edit(left, right):
    """One insertion/deletion/substitution only; no broad phonetic inference."""
    if left == right or abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    shorter, longer = sorted((left, right), key=len)
    for i, (a, b) in enumerate(zip(shorter, longer)):
        if a != b:
            return shorter[i:] == longer[i + 1:]
    return True


def candidates(projects, reviewed=None):
    """Current ASCII Open-name suggestions for review; never shared-name input."""
    reviewed = reviewed or {}
    unique = {p["id"]: p for p in projects}
    rows = sorted(unique.values(), key=lambda p: (p["name"], p["id"]))
    suggestions = []
    for i, left in enumerate(rows):
        lk = name_key(left["name"])
        if not re.fullmatch(r"open[a-z]{4,}", lk):
            continue
        for right in rows[i + 1:]:
            rk = name_key(right["name"])
            if not re.fullmatch(r"open[a-z]{4,}", rk) or lk == rk:
                continue
            if lk in reviewed and rk in reviewed and reviewed[lk]["key"] == reviewed[rk]["key"]:
                continue
            if one_edit(lk[4:], rk[4:]):
                suggestions.append({
                    "status": "needs_review",
                    "reason": "one-letter-edit",
                    "projects": [{"id": p["id"], "name": p["name"], "project_url": p["url"]}
                                 for p in (left, right)],
                })
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Suggest current name matches for review; writes no curated records.")
    parser.add_argument("--catalog", type=Path, required=True, help="Existing built catalog JSON")
    parser.add_argument("--metrics", type=Path, help="Optional existing GitHub metrics JSON; no collection")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    reviewed = load_reviewed(catalog)
    repository_changes = []
    if args.metrics:
        from render_readme import validate_snapshot
        from update_stats import repository_change_candidates
        snapshot = json.loads(args.metrics.read_text(encoding="utf-8"))
        validate_snapshot(snapshot)
        repository_changes = repository_change_candidates(snapshot)
    print(json.dumps({"schema_version": 1, "status": "needs_review",
                      "source_sha": catalog.get("source_sha"),
                      "candidates": candidates(catalog["projects"], reviewed),
                      "repository_changes": repository_changes}, indent=2))


if __name__ == "__main__":
    main()

