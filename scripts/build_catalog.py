#!/usr/bin/env python3
"""Build the deterministic, offline website catalog from the curated README."""

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit, urlunsplit

import render_readme as readme
import update_stats as stats

ROOT = Path(__file__).resolve().parents[1]
ALTERNATIVES_LABEL = "<br>Alternative to: "
TABLE_HEADER = "| Project | Description |"
TABLE_SEPARATOR = re.compile(r"^\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|$")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")


def canonical_url(value):
    """Validate an absolute HTTP(S) URL and normalize only known identity rules.

    Host names are case insensitive. GitHub owner/repository paths are too;
    other path segments, query strings, and fragments remain case sensitive.
    Only root paths and GitHub repository URLs normalize a trailing slash;
    a generic /tool and /tool/ may identify different resources.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a nonempty HTTP(S) URL")
    # Check before urlsplit, which otherwise silently removes some controls.
    if any(char.isspace() or unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("Whitespace or control character in URL")
    if "\\" in value or any(unicodedata.category(char) == "Cc" for char in unquote(value)):
        raise ValueError("Unsafe control character or backslash in URL")
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
    except ValueError as error:
        raise ValueError("Invalid HTTP(S) URL: " + value) from error
    if parsed.scheme not in {"http", "https"} or not host:
        raise ValueError("Expected an absolute HTTP(S) URL: " + value)
    if parsed.username is not None or parsed.password is not None or "%" in parsed.netloc:
        raise ValueError("Credentials or encoded host in URL")
    host = host.lower()
    netloc = "[" + host + "]" if ":" in host else host
    if port is not None and (parsed.scheme, port) not in {("http", 80), ("https", 443)}:
        netloc += ":" + str(port)
    path = "" if parsed.path == "/" else parsed.path
    if host == "github.com":
        segments = path.split("/")
        segments[1:3] = [part.lower() for part in segments[1:3]]
        path = "/".join(segments)
        if re.fullmatch(r"/[\w.-]+/[\w.-]+/", path):
            path = path[:-1]
    return urlunsplit((parsed.scheme, netloc, path, parsed.query, parsed.fragment))


def category_id(name):
    """GitHub-style heading anchor for the catalog's plain category headings."""
    without_tags = re.sub(r"<[^>]*>", "", name)
    return re.sub(r"[^\w -]", "", without_tags.lower()).replace(" ", "-")


def _nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty " + label)
    return value


def _projects(document, label, require_schema=True):
    if not isinstance(document, dict):
        raise ValueError("Expected " + label + " object")
    if document.get("schema_version", None if require_schema else 1) != 1:
        raise ValueError("Unsupported " + label + " schema")
    projects = document.get("projects")
    if not isinstance(projects, list) or not all(isinstance(item, dict) for item in projects):
        raise ValueError("Expected " + label + " projects list")
    return projects


def _alternative_evidence(document):
    by_url = {}
    for project in _projects(document, "alternatives"):
        url = canonical_url(project.get("readme_url"))
        if url in by_url:
            raise ValueError("Duplicate alternatives evidence for " + url)
        alternatives = project.get("alternatives")
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 3:
            raise ValueError("Expected one to three reviewed alternatives for " + url)
        names = set()
        for alternative in alternatives:
            if not isinstance(alternative, dict):
                raise ValueError("Expected a reviewed alternative object")
            name = _nonempty_text(alternative.get("name"), "alternative name")
            if name in names:
                raise ValueError("Duplicate alternative name for " + url)
            names.add(name)
            source_url = canonical_url(alternative.get("source_url"))
            if not source_url.startswith("https://"):
                raise ValueError("Alternative evidence must use HTTPS")
            checked = _nonempty_text(alternative.get("checked_utc_date"), "checked UTC date")
            if date.fromisoformat(checked).isoformat() != checked:
                raise ValueError("Expected an ISO checked UTC date")
            _nonempty_text(alternative.get("scope"), "alternative scope")
            # Preserve complete reviewed evidence, including optional claimant,
            # source_quote, confidence, and target_url, without interpreting HTML.
            for key, value in alternative.items():
                if key.endswith("_url"):
                    canonical_url(value)
        by_url[url] = deepcopy(alternatives)
    return by_url


def _hn_evidence(document):
    by_url = {}
    slugs = set()
    for project in _projects(document, "HN evidence", require_schema=False):
        url = canonical_url(project.get("readme_url"))
        slug = project.get("slug")
        if not isinstance(slug, str) or SLUG.fullmatch(slug) is None:
            raise ValueError("Invalid HN asset slug")
        if slug in slugs or url in by_url:
            raise ValueError("Duplicate HN evidence URL or asset slug")
        slugs.add(slug)
        if type(project.get("eligible")) is not bool:
            raise ValueError("Expected boolean HN eligibility")
        by_url[url] = None
        if project["eligible"]:
            count = project.get("story_count")
            if type(count) is not int or count < 0:
                raise ValueError("Expected a nonnegative HN story count")
            canonical_url(project.get("search_url"))
            by_url[url] = {
                "slug": slug,
                "chart_url": "assets/hn/" + slug + ".svg",
                "search_url": project["search_url"],
                "total_stories": count,
            }
    return by_url


def _github_metadata(url, snapshot):
    # Reuse the README repository grammar after case/slash normalization.
    # HTTP links identify the same kind of repository but retain their own URL.
    lookup_url = "https://" + url[len("http://"):] if url.startswith("http://") else url
    match = stats.ROW.match("| [Project](" + lookup_url + ") |")
    if not match:
        return None
    repo = match[2].lower()
    record = snapshot["repositories"].get(repo)
    if record is None:
        return None
    license_id = (record.get("license") or {}).get("spdx_id")
    if not license_id or license_id in {"NOASSERTION", "OTHER"}:
        license_id = None
    return {
        "repo": repo,
        "stars": record["stargazers_count"],
        "license": license_id,
        "created_at": record["created_at"],
        "pushed_at": record.get("pushed_at"),
    }


def build_catalog(source, snapshot, alternatives, evidence, source_sha=None):
    """Return a fresh JSON-compatible catalog; never fetch data or read a clock.

    Category order follows the source, projects sort by name and canonical URL,
    and each category membership is counted once. Empty project tables remain
    usable categories with count zero; non-catalog headings are excluded.
    """
    if source_sha is not None and (not isinstance(source_sha, str)
            or re.fullmatch(r"[0-9a-fA-F]{40}", source_sha) is None):
        raise ValueError("source_sha must be a full 40-character Git commit SHA")
    readme.validate_source(source)
    metrics_as_of = readme.validate_snapshot(snapshot).isoformat()
    by_alternative = _alternative_evidence(alternatives)
    by_hn = _hn_evidence(evidence)
    categories, projects = {}, {}
    heading_ids = set()
    current = None
    in_project_table = False

    def ensure_category():
        if current is None:
            raise ValueError("Project table or entry must follow a level-two category heading")
        if current["id"] not in categories:
            categories[current["id"]] = {**current, "count": 0}
        return current["id"]

    for line_number, line in enumerate(source.splitlines(), 1):
        if line.startswith("## "):
            name = _nonempty_text(line[3:].strip(), "category heading")
            base = category_id(name)
            if not base:
                raise ValueError("Category heading must have a nonempty anchor")
            anchor, suffix = base, 0
            while anchor in heading_ids:
                suffix += 1
                anchor = base + "-" + str(suffix)
            heading_ids.add(anchor)
            current = {"id": anchor, "name": name}
            in_project_table = False
            continue
        if line == TABLE_HEADER:
            ensure_category()
            in_project_table = True
            continue
        if TABLE_SEPARATOR.fullmatch(line):
            continue
        match = readme.ENTRY.fullmatch(line)
        if match is None:
            if line.lstrip().startswith("|") and (in_project_table or line.lstrip().startswith(("| [", "| **["))):
                raise ValueError(f"Malformed project row at line {line_number}: {line}")
            if line.strip() and not line.startswith("|"):
                in_project_table = False
            continue
        category = ensure_category()
        in_project_table = True
        name, url, description = match.groups()
        _nonempty_text(name, "project name")
        url = canonical_url(url)
        inline_alternatives = stats.alternatives(line)
        if inline_alternatives:
            description = description.split(ALTERNATIVES_LABEL, 1)[0]
        description = _nonempty_text(description.strip(), "project description")
        reviewed = by_alternative.get(url, [])
        expected = [(item["name"], item["source_url"]) for item in reviewed]
        if inline_alternatives != expected:
            raise ValueError("Missing or inconsistent reviewed alternatives for " + url)
        if url in projects:
            project = projects[url]
            if any(project[key] != value for key, value in
                   (("name", name), ("description", description), ("alternatives", reviewed))):
                raise ValueError("Conflicting cross-listed project data for " + url)
        else:
            project = projects[url] = {
                "id": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                "name": name,
                "url": url,
                "description": description,
                "categories": [],
                "github": _github_metadata(url, snapshot),
                "alternatives": deepcopy(reviewed),
                "hn": deepcopy(by_hn.get(url)),
            }
        if category not in project["categories"]:
            project["categories"].append(category)
            categories[category]["count"] += 1
    unused = sorted(by_alternative.keys() - projects.keys())
    if unused:
        raise ValueError("Reviewed alternatives refer to unlisted projects: " + ", ".join(unused))
    return {
        "schema_version": 1,
        "metrics_as_of": metrics_as_of,
        "source_sha": source_sha.lower() if source_sha is not None else None,
        "category_memberships": sum(item["count"] for item in categories.values()),
        "categories": list(categories.values()),
        "projects": sorted(projects.values(), key=lambda item: (item["name"].casefold(), item["name"], item["url"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/site/catalog.json")
    parser.add_argument("--source-sha", help="Optional full source commit SHA; never inferred from checkout")
    args = parser.parse_args()
    source = (ROOT / "README.source.md").read_text(encoding="utf-8")
    snapshot, alternatives, evidence = (
        json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
        for filename in ("github_metrics.json", "alternatives.json", "hn_evidence.json")
    )
    catalog = build_catalog(source, snapshot, alternatives, evidence, args.source_sha)
    output = json.dumps(catalog, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"Built {args.output} offline: {len(catalog['projects'])} projects, "
          f"{catalog['category_memberships']} category memberships.")


if __name__ == "__main__":
    main()
