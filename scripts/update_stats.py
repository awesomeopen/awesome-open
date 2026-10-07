#!/usr/bin/env python3
"""Collect GitHub metrics; pure formatting helpers are used by render_readme.py."""

import concurrent.futures
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(
    r"^\| (?:\*\*)?\[([^\]]+)\]\(https://github\.com/([\w.-]+/[\w.-]+)/?\)(?:\*\*)?"
    r"(?= |<br>)"
)
STATS = re.compile(r"<!-- STATS:START -->.*?<!-- STATS:END -->")


def star_count(count):
    if count < 1000:
        return str(count)
    divisor, suffix = (1_000_000, "m") if count >= 999_950 else (1000, "k")
    return f"{count / divisor:.1f}".rstrip("0").rstrip(".") + suffix


def utc_today():
    return datetime.now(timezone.utc).date()


def stale_push_date(value, today):
    """Whether a UTC last-push date has reached its 12-month anniversary.

    A February 29 anniversary falls on February 28 in a non-leap year.
    Missing or invalid dates never receive emphasis.
    """
    try:
        pushed = date.fromisoformat(value[:10])
        try:
            anniversary = pushed.replace(year=pushed.year + 1)
        except ValueError:
            anniversary = pushed.replace(year=pushed.year + 1, day=28)
        return anniversary <= today
    except (TypeError, ValueError, OverflowError):
        return False


def metadata(data, today=None):
    if today is None:
        today = utc_today()
    license_id = (data.get("license") or {}).get("spdx_id")
    if not license_id or license_id in {"NOASSERTION", "OTHER"}:
        license_id = ""
    # Escape API text so it cannot introduce Markdown columns or HTML.
    license_id = re.sub(r"[^a-zA-Z0-9.+() -]", "", license_id)
    created = data["created_at"][:10]
    updated = (data.get("pushed_at") or "Unknown")[:10]
    if stale_push_date(data.get("pushed_at"), today):
        updated = f"<b>{updated}</b>"
    stars = star_count(data["stargazers_count"])
    parts = [f"{created} -- {updated}"]
    if license_id:
        parts.append(license_id)
    parts.append(stars)
    return "<br><sub>" + " / ".join(parts) + "</sub>"


def alternatives(line):
    """Parse manually reviewed links; never include them in generated metadata."""
    label = "<br>Alternative to: "
    if "Alternative to:" not in line:
        return []
    if line.count(label) != 1 or line.count("Alternative to:") != 1:
        raise ValueError("Expected one inline alternatives line")
    start = line.index(label)
    stats_start = line.find("<!-- STATS:START -->")
    if stats_start >= 0 and start >= stats_start:
        raise ValueError("Alternatives must precede the STATS block")
    # The first column holds the name and optional HN chart, never alternatives.
    if start < line.index(" | "):
        raise ValueError("Alternatives belong after the description")
    end = stats_start if stats_start >= 0 else line.rfind(" |")
    content = line[start + len(label):end].strip()
    links = re.findall(r"\[([^\]\n]+)\]\((https://[^\s()<>]+)\)", content)
    if not 1 <= len(links) <= 3 or content != ", ".join(
        f"[{name}]({url})" for name, url in links
    ):
        raise ValueError("Expected one to three official evidence links")
    return links


def repositories(text, require_markers=True):
    repos = set()
    for line in text.splitlines():
        if line.startswith("| "):
            alternatives(line)
        match = ROW.match(line)
        if match:
            if require_markers and len(STATS.findall(line)) != 1:
                raise ValueError(f"Expected one STATS block for {match[2]}")
            repos.add(match[2].lower())
    return sorted(repos)


def category_leaders(text, data):
    """Rank unique repositories per section, breaking exact ties by repo path.

    Headings, rather than table position, define category boundaries. A repo
    cross-listed in another category is ranked independently there.
    """
    categories = {}
    category = 0
    for line in text.splitlines():
        if line.startswith("## "):
            category += 1
        match = ROW.match(line)
        if match:
            categories.setdefault(category, set()).add(match[2].lower())
    return {
        category: set(sorted(repos & data.keys(), key=lambda repo: (-data[repo]["stargazers_count"], repo))[:3])
        for category, repos in categories.items()
    }


def update_text(text, data, today=None, allow_missing=False):
    if today is None:
        today = utc_today()
    repositories(text)  # Validate all markers before changing any content.
    leaders = category_leaders(text, data)
    lines = []
    category = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            category += 1
        match = ROW.match(line)
        if match:
            repo = match[2].lower()
            value = "" if allow_missing and repo not in data else metadata(data[repo], today=today)
            block = "<!-- STATS:START -->" + value + "<!-- STATS:END -->"
            line = STATS.sub(lambda _: block, line)
            # Only the name link is bold, never the independently managed chart.
            link = match[0][2:].removeprefix("**").removesuffix("**")
            if repo in leaders[category]:
                link = "**" + link + "**"
            line = "| " + link + line[len(match[0]):]
        lines.append(line)
    return "".join(lines)


def fetch(repo, token):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "awesome-open-stats",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {403, 429, 500, 502, 503, 504} or attempt == 2:
                raise RuntimeError(f"{repo}: GitHub returned HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                raise RuntimeError(f"{repo}: GitHub request failed") from error
        time.sleep(2 ** (attempt + 1))


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GH_TOKEN or GITHUB_TOKEN before updating stats.")
    path = ROOT / "README.source.md"
    original = path.read_text(encoding="utf-8")
    repos = repositories(original, require_markers=False)
    # Fetch once per repository, including projects listed in multiple categories.
    # A failed request aborts before writing, preserving the previous snapshot.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda repo: fetch(repo, token), repos))
    snapshot = {
        "schema_version": 1,
        "as_of": utc_today().isoformat(),
        "repositories": {
            repo: {key: result.get(key) for key in
                   ("created_at", "pushed_at", "license", "stargazers_count")}
            for repo, result in zip(repos, results)
        },
    }
    for record in snapshot["repositories"].values():
        if record["license"]:
            record["license"] = {"spdx_id": record["license"].get("spdx_id")}
    # Validate every record before replacing the previous snapshot.
    from render_readme import validate_snapshot
    validate_snapshot(snapshot)
    if path.read_text(encoding="utf-8") != original:
        raise RuntimeError("README.source.md changed during metadata collection; rerun against the latest content.")
    output = ROOT / "data/github_metrics.json"
    updated = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if not output.exists() or output.read_text(encoding="utf-8") != updated:
        temporary = output.with_suffix(".tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(output)
        print(f"Cached metadata for {len(repos)} repositories.")
    else:
        print("GitHub metrics snapshot is already current.")


if __name__ == "__main__":
    main()
