#!/usr/bin/env python3
"""Refresh marked metadata and independent category star highlights."""

import concurrent.futures
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


def metadata(data):
    license_id = (data.get("license") or {}).get("spdx_id")
    if not license_id or license_id in {"NOASSERTION", "OTHER"}:
        license_id = ""
    # Escape API text so it cannot introduce Markdown columns or HTML.
    license_id = re.sub(r"[^a-zA-Z0-9.+() -]", "", license_id)
    created = data["created_at"][:10]
    updated = (data.get("pushed_at") or "Unknown")[:10]
    stars = star_count(data["stargazers_count"])
    parts = [f"{created} - {updated}"]
    if license_id:
        parts.append(license_id)
    parts.append(stars)
    return "<br>" + ", ".join(parts)


def repositories(text):
    repos = set()
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            if len(STATS.findall(line)) != 1:
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
        category: set(sorted(repos, key=lambda repo: (-data[repo]["stargazers_count"], repo))[:3])
        for category, repos in categories.items()
    }


def update_text(text, data):
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
            block = "<!-- STATS:START -->" + metadata(data[repo]) + "<!-- STATS:END -->"
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
    path = ROOT / "README.md"
    original = path.read_text(encoding="utf-8")
    repos = repositories(original)
    # Fetch once per repository, including projects listed in multiple categories.
    # A failed request aborts before writing, preserving the previous snapshot.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda repo: fetch(repo, token), repos))
    updated = update_text(original, dict(zip(repos, results)))
    if path.read_text(encoding="utf-8") != original:
        raise RuntimeError("README changed during metadata collection; rerun against the latest content.")
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        print(f"Updated metadata for {len(repos)} repositories.")
    else:
        print("README metadata is already current.")


if __name__ == "__main__":
    main()
