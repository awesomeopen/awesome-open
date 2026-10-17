#!/usr/bin/env python3
"""Build the complete, offline static catalog. No network, dependencies or deployment."""

import argparse
import base64
import hashlib
import html
import unicodedata
import json
import re
import warnings
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit
import shutil

from build_catalog import build_catalog, load_function_summaries
from render_readme import display_hn_evidence
import project_aliases
import update_hn as hn
import update_stats as stats
import signals
import star_history
import deployment
import qr
from footer_art import discover_footer_art
from category_art import (
    attach_category_art,
    category_image,
    copy_category_art,
)

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/awesomeopen/awesome-open"
FOOTER_PATTERN = "patterns/navypattern2.png"
BRAND_ASSETS = {
    "botanical-128.png": "image/png",
    "search-loupe.png": "image/png",
    "favicon.ico": "image/x-icon",
    "fruit-16.png": "image/png",
    "fruit-32.png": "image/png",
    "fruit-96.png": "image/png",
    "awesome-open-logo.png": "image/png",
}


def escape(value):
    return html.escape(str(value), quote=True)


def highlight_name(text, name):
    """Highlight the first complete name in plain prose, escaping every fragment."""
    match = re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE)
    if not match:
        return escape(text)
    return (
        escape(text[: match.start()])
        + '<mark class="tool-name">'
        + escape(match.group())
        + "</mark>"
        + escape(text[match.end() :])
    )


def source_url(catalog, path, anchor=""):
    ref = catalog.get("source_sha") or "main"
    return f"{REPOSITORY}/blob/{ref}/{path}{anchor}"


def json_for_html(value):
    """A JSON script is still parsed as raw HTML text; never allow a closing tag."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def search_index(catalog):
    """Project runtime fields and cache provenance; keep full evidence in HTML/downloads.

    Retain the runtime's existing shape and raw values so search folding, unknown
    metrics, date thresholds, setup filters and category leaders stay unchanged.
    Explicit unavailable records have no cached measurements; legacy records retain
    their existing presence semantics.
    """
    projects = []
    for project in catalog["projects"]:
        github = project.get("github")
        item = {
            key: project[key] for key in ("id", "name", "description", "categories")
        }
        if project.get("aliases"):
            item["aliases"] = [{"name": alias["name"]} for alias in project["aliases"]]
        item["leader_categories"] = project.get("leader_categories", [])
        item["github"] = (
            {
                key: github.get(key)
                for key in (
                    "license",
                    "stars",
                    "pushed_at",
                    "status",
                    "last_success_at",
                )
            }
            if github is not None
            else None
        )
        item["alternatives"] = [
            {"name": alternative["name"]}
            for alternative in project.get("alternatives", [])
        ]
        setup = project.get("deployment", {})
        item["deployment"] = {
            field: [{"value": fact["value"]} for fact in setup.get(field, [])]
            for field in ("run_modes", "install_methods")
        }
        projects.append(item)
    return {
        "metrics_as_of": catalog["metrics_as_of"],
        "categories": [
            {key: category[key] for key in ("id", "name")}
            for category in catalog["categories"]
        ],
        "projects": projects,
    }


def split_name(name):
    """The prefix treatment never changes the canonical name or identity."""
    if name[:4].lower() == "open":
        return f'<span class="name-prefix">{escape(name[:4])}</span><span class="name-stem">{escape(name[4:])}</span>'
    return f'<span class="name-stem">{escape(name)}</span>'


def signal_time(value, precision="second"):
    return value[:10] + " (date only)" if precision == "day" else value


def optional_signal_html(project, embed_setup=True):
    """Evidence stays in native drawers; unknown values never become zeroes."""
    records = project.get("signals")
    if not records and not (embed_setup and project.get("deployment")):
        return ""
    pieces = []
    for provider, title in (
        ("release", "GitHub release"),
        ("scorecard", "OpenSSF Scorecard"),
    ):
        if not records or provider not in records:
            if provider == "release" and embed_setup and project.get("deployment"):
                pieces.append(
                    '<section class="optional-signal evidence-note" data-signal="release"><h4>GitHub release</h4><p>Release not checked.</p>'
                    + deployment.render(project, embedded=True)
                    + "</section>"
                )
            continue
        record = records[provider]
        good = record["last_good"]
        state = record["status"].capitalize()
        if good is None:
            label = {
                "not_checked": "Not checked",
                "not_found": "No result returned",
                "pending": "Provider pending",
                "error": "Unavailable",
                "deferred": "Check deferred",
            }.get(record["fetch_status"], "Unavailable")
            content = f"<p>{escape(label)}</p>"
        elif provider == "release":
            value = good["value"]
            content = (
                f'<p><a class="note-value" href="{escape(value["html_url"])}">{escape(value["tag_name"])}</a>'
                f'Published <span class="metric-value">{escape(value["published_at"][:10])}</span></p>'
            )
        else:
            value = good["value"]
            scored = sum(check["score"] is not None for check in value["checks"])
            total = len(value["checks"])
            aggregate = (
                f"{value['score']:g}/10"
                if value["score"] is not None
                else "Aggregate inconclusive"
            )
            checks = "".join(
                f"<li><strong>{escape(c['name'])}</strong> · "
                + (f"{c['score']:g}/10" if c["score"] is not None else "Inconclusive")
                + f"<p>{escape(c['reason'])}</p></li>"
                for c in value["checks"]
            )
            commit = good["source_commit"]
            repo = value["repository"].removeprefix("github.com/")
            content = (
                f'<p><span class="note-value">{aggregate}</span>Scanned <span class="metric-value">{escape(good["observed_at"][:10])}</span> · '
                f"{scored} scored / {total} returned</p>"
                f'<details class="signal-checks"><summary>Check results and scan provenance</summary><ul>{checks}</ul>'
                f'<p class="fine-print">Repository commit <a href="https://github.com/{escape(repo)}/commit/{commit}">{commit[:12]}</a>'
                f" · Scorecard {escape(good['tool_version'])}</p></details>"
            )
        provenance = []
        if record["checked_at"]:
            provenance.append(
                "Checked "
                + signal_time(
                    record["checked_at"], record.get("check_time_precision", "second")
                )
            )
        if record["last_success_at"]:
            provenance.append(
                "Last successful fetch "
                + signal_time(
                    record["last_success_at"],
                    record.get(
                        "success_time_precision",
                        record.get("check_time_precision", "second"),
                    ),
                )
            )
        if good:
            provenance.append(
                "Value fetched "
                + signal_time(
                    good["fetched_at"], good.get("fetch_time_precision", "second")
                )
            )
        if record["fetch_status"] not in {"ok", "not_modified", "not_checked"}:
            provenance.append(
                "Latest attempt: " + record["fetch_status"].replace("_", " ")
            )
        provenance.append(
            f'<a href="{escape(record["source_url"])}">Provider source</a>'
        )
        setup = (
            deployment.render(project, embedded=True)
            if provider == "release" and embed_setup
            else ""
        )
        pieces.append(
            f'<section class="optional-signal evidence-note" data-signal="{provider}"><h4>{title} <span class="signal-status">{state}</span></h4>{content}{setup}<details class="note-provenance"><summary>View source &amp; retrieval history</summary><p class="fine-print">'
            + " · ".join(provenance)
            + "</p></details></section>"
        )
    return '<div class="optional-signals">' + "".join(pieces) + "</div>"


def attach_specimen_art(catalog, root):
    manifest = root / "data/specimen_art.json"
    if not manifest.exists():
        return
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(
        document.get("artworks"), dict
    ):
        raise ValueError("Invalid specimen art manifest")
    projects = {p["id"]: p for p in catalog["projects"]}
    for pid, entry in document["artworks"].items():
        if pid not in projects:
            warnings.warn("Specimen art has no current catalog record: " + pid)
            continue
        if entry.get("review_status") != "approved":
            continue
        expected = f"specimens/{pid}.webp"
        if (
            entry.get("path") != expected
            or entry.get("project_url") != projects[pid]["url"]
        ):
            raise ValueError("Specimen identity/path mismatch: " + pid)
        if not isinstance(entry.get("alt"), str) or not entry["alt"].strip():
            raise ValueError("Specimen artwork needs descriptive alt text: " + pid)
        asset = root / "site" / expected
        if not asset.is_file():
            warnings.warn("Skipping missing specimen artwork: " + expected)
            continue
        if asset.is_symlink():
            raise ValueError("Specimen assets must be regular repository files")
        data = asset.read_bytes()
        if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            raise ValueError("Expected a WebP specimen asset: " + expected)
        width, height = entry.get("width"), entry.get("height")
        if any(type(v) is not int or not 1 <= v <= 8192 for v in (width, height)):
            raise ValueError("Invalid specimen image dimensions: " + pid)
        projects[pid]["artwork"] = {
            k: entry[k] for k in ("path", "alt", "width", "height")
        }


def attach_specimen_cutouts(catalog, root):
    """Use a committed transparent derivative only while it still matches its approved source bytes."""
    path = root / "site/specimens/cutouts.json"
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(
        document.get("cutouts"), dict
    ):
        raise ValueError("Invalid specimen cut-out manifest")
    result = {}
    for project in catalog["projects"]:
        art = project.get("artwork")
        entry = document["cutouts"].get(project["id"])
        if not art or not entry:
            continue
        source, derivative = root / "site" / art["path"], root / "site" / entry["path"]
        if (
            entry["source"] != art["path"]
            or entry["path"] != f"specimens/cutouts/{project['id']}.webp"
        ):
            raise ValueError(
                "Specimen cut-out identity/path mismatch: " + project["id"]
            )
        if not derivative.is_file() or derivative.is_symlink():
            warnings.warn("Skipping missing specimen cut-out: " + entry["path"])
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["source_sha256"]:
            warnings.warn(
                "Specimen cut-out is older than its source; run build_specimen_cutouts.py: "
                + project["id"]
            )
            continue
        if hashlib.sha256(derivative.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(
                "Specimen cut-out bytes do not match the manifest: " + entry["path"]
            )
        result[project["id"]] = {"path": entry["path"], "bbox": entry["subject_bbox"]}
    return result


PERMALINK_BASE = "https://awesomeopen.github.io/awesome-open/#project-"


def qr_path(project):
    return f"assets/qr/{project['id'][:16]}.svg"


def timeline(created, release, pushed):
    """Repository timestamps on one axis; positions are literal dates, labels repeat them."""
    points = [("Repository created", created, "")]
    if release:
        points.append(("GitHub release", release[0], release[1]))
    if pushed:
        points.append(("Repository push", pushed, ""))
    try:
        dated = [
            (label, date.fromisoformat(value), tag) for label, value, tag in points
        ]
    except ValueError:
        return ""
    first = dated[0][1].year
    last = max(day for _, day, _ in dated).year + 1
    lo, hi = date(first, 1, 1), date(last, 1, 1)
    pct = lambda day: round((day - lo).days / (hi - lo).days * 100, 2)
    step = 2 if last - first > 8 else 1
    years = "".join(
        f'<span class="timeline-year" style="left:{pct(date(y, 1, 1))}%">{y}</span>'
        for y in range(first, last + 1, step)
    )
    marks, labels = [], []
    close_endpoints = bool(pushed) and abs(pct(dated[-1][1]) - pct(dated[0][1])) < 30
    for label, day, tag in dated:
        left = pct(day)
        side = "up" if tag else "down"
        anchor = (
            f"right:{round(100 - left, 2)}%;text-align:right"
            if left > 55
            else f"left:{left}%"
        )
        # Keep true timestamp positions, but separate labels for short-lived repositories.
        if close_endpoints and label == "Repository created":
            anchor = f"right:{round(100 - left, 2)}%;margin-right:8px;text-align:right"
        elif close_endpoints and label == "Repository push":
            anchor = f"left:{left}%;margin-left:8px;text-align:left"
        extra = f" · {escape(tag)}" if tag else ""
        marks.append(
            f'<span class="timeline-mark{" is-release" if tag else ""}" style="left:{left}%"></span>'
        )
        labels.append(
            f'<span class="timeline-label {side}{"" if tag else " repeats-vitals"}" style="{anchor}">{escape(label)}<br><span class="metric-value">{day.isoformat()}</span>{extra}</span>'
        )
    first_pct, last_pct = pct(dated[0][1]), max(pct(day) for _, day, _ in dated)
    span = f'<span class="timeline-span" style="left:{first_pct}%;width:{round(last_pct - first_pct, 2)}%"></span>'
    summary = "; ".join(
        f"{label} {day.isoformat()}" + (f" ({tag})" if tag else "")
        for label, day, tag in dated
    )
    return f'<div class="timeline" role="img" aria-label="{escape(summary)}"><span class="timeline-axis"></span>{span}{years}{"".join(marks)}{"".join(labels)}</div>'


def specimen_label(project, tags, number):
    pid, name = escape(project["id"]), escape(project["name"])
    github = project.get("github") or {}
    status = (
        '<span class="label-status">Archived on GitHub</span>'
        if github.get("archived") is True
        else '<span class="label-header">Awesome Open* · Field record</span>'
    )
    return (
        f'<div class="specimen-label specimen-identity"><a class="label-qr" href="{escape(PERMALINK_BASE + project["id"])}" aria-label="QR code: permalink to {name}">'
        f'<img src="{escape(qr_path(project))}" width="92" height="92" alt="" loading="lazy"></a><div class="label-lines">{status}'
        f'<span class="label-name">{name}</span>'
        f'<span><span class="registry" title="Registry ID">OP-{pid[:8].upper()}</span> · <span class="sheet-folio" title="Folio number">Folio {number:03d}</span></span>'
        f"<span>Domain: {tags}</span>"
        f'<nav class="specimen-links" aria-label="Record for {name}"><a class="permalink" href="#project-{pid}" aria-label="Permalink to {name}">Specimen: {name} (permalink)</a></nav></div></div>'
    )


def where_it_runs(project):
    record = project.get("deployment")
    if not record:
        return ""
    rows = []
    for field, label, names in (
        ("run_modes", "Run", deployment.RUN_MODES),
        ("install_methods", "Install", deployment.INSTALL_METHODS),
        ("platforms", "Documented platforms", None),
    ):
        facts = record.get(field, [])
        if facts:
            chips = "".join(
                f"<span>{escape(names[f['value']] if names else f['value'])}</span>"
                for f in facts
            )
            rows.append(
                f'<div><dt>{label}</dt><dd class="plate-chips">{chips}</dd></div>'
            )
    return f'<dl class="plate-kit">{"".join(rows)}</dl>' + deployment.render(
        project, embedded=True, overview=False
    )


def specimen_plate(
    project, number, tags, function_detail, vitals, chart, alternatives, cutout
):
    pid, name, url = (
        escape(project["id"]),
        escape(project["name"]),
        escape(project["url"]),
    )
    art = project.get("artwork")
    specimen = notes = ""
    if art:
        src = cutout["path"] if cutout else art["path"]
        bbox = " ".join(str(v) for v in (cutout["bbox"] if cutout else (0, 0, 1, 1)))
        specimen = (
            f'<div class="plate-specimen"><div class="plate-field" data-seed="{pid[:16]}" data-cutout="{"true" if cutout else "false"}" data-bbox="{bbox}">'
            f'<figure class="specimen-art plate-art"><img src="{escape(src)}" alt="{escape(art["alt"])}" width="{art["width"]}" height="{art["height"]}" loading="lazy" decoding="async"></figure></div></div>'
        )
        features = project.get("function_summary", {}).get("features", [])[:2]
        if features:
            items = "".join(
                f'<li class="plate-note"><span class="plate-crop{" is-tiny" if i else ""}" data-crop="{i}" aria-hidden="true"></span><div><span class="plate-index">{i + 1:02d} / Feature note</span>'
                f'<strong>{escape(f["title"])}</strong><p>{escape(f["text"])}</p><a class="feature-source" href="{escape(f["source_url"])}">Feature source ↗</a></div></li>'
                for i, f in enumerate(features)
            )
            notes = f'<ol class="plate-notes" aria-label="Feature notes">{items}</ol>'
    label = specimen_label(project, tags, number)
    runs = where_it_runs(project)
    numerals = iter(("II", "III", "IV", "V", "VI"))
    sections = [
        f'<section class="plate-band plate-register" aria-label="Repository facts"><span class="sheet-label">{next(numerals)} / Repository record</span>{vitals}</section>'
    ]
    if runs:
        sections.append(
            f'<section class="plate-band plate-runs" aria-label="Where it runs"><span class="sheet-label">{next(numerals)} / Where it runs</span>{runs}</section>'
        )
    evidence = (
        chart
        + star_history.render(project)
        + optional_signal_html(project, embed_setup=False)
    )
    if evidence:
        sections.append(
            f'<section class="plate-band diagnostics plate-evidence" aria-label="Observations and evidence"><span class="sheet-label">{next(numerals)} / Observations &amp; evidence</span><div class="evidence-notes">{evidence}</div></section>'
        )
    if alternatives:
        sections.append(
            f'<section class="plate-band plate-alternatives" aria-label="Reviewed alternatives"><span class="sheet-label">{next(numerals)} / Reviewed alternatives</span>{alternatives}</section>'
        )
    host = (
        "GitHub"
        if urlsplit(project["url"]).hostname in ("github.com", "www.github.com")
        else "its official site"
    )
    address = escape(project["url"].removeprefix("https://").removeprefix("http://"))
    return (
        f'<div class="specimen-interior specimen-plate{"" if art else " without-art"}" aria-labelledby="name-{pid}">'
        f'<div class="plate-heading"><span class="plate-index">Field notes / {number:03d}</span><span class="plate-index">{name}</span></div>'
        f'<div class="plate-study"><svg class="plate-leaders" aria-hidden="true"></svg>'
        f'<div class="plate-function"><span class="sheet-label">I / Function</span><p class="record-description">{escape(project["description"])}</p>{function_detail}</div>'
        f"{specimen}{notes}{label}</div>"
        + "".join(sections)
        + f'<nav class="plate-departure" aria-label="Explore {name}"><span class="sheet-label">In the wild</span><a href="{url}"><span>Explore {name} on {host}</span>'
        f'<span class="departure-arrow" aria-hidden="true">↗</span></a><span class="departure-address">{address}</span></nav></div>'
    )


def metrics_freshness(github, as_of):
    if not github:
        return "GitHub metrics: Unknown"
    status = github.get("status", "fresh")
    observed = github.get("last_success_at", as_of)
    attempt = github.get("last_attempt") or {}
    if status == "unavailable":
        return (
            "GitHub metrics unavailable; no successful observation. Last attempt: "
            + str(attempt.get("at") or "Unknown")
            + " UTC (repository unavailable)."
        )
    if status == "stale":
        return (
            "Stale GitHub metrics; last successful observation: "
            + str(observed or "Unknown")
            + " UTC. Last attempt: "
            + str(attempt.get("at") or "Unknown")
            + " UTC (repository unavailable)."
        )
    return ""


def project_html(project, categories, catalog, number=0, cutouts=None, position=None, deferred=False):
    position = number if position is None else position
    pid = escape(project["id"])
    github = project["github"]
    license_text = (github["license"] if github else None) or ""
    pushed = github["pushed_at"][:10] if github and github["pushed_at"] else "Unknown"
    created = (
        github["created_at"][:10] if github and github.get("created_at") else "Unknown"
    )
    stars = (
        f"{github['stars']:,}"
        if github and github.get("stars") is not None
        else "Unknown"
    )
    tags = " / ".join(
        f'<a class="tag" data-category="{escape(cid)}" href="{escape(source_url(catalog, "README.source.md", "#" + cid))}">{escape(categories[cid])}</a>'
        for cid in project["categories"]
    )
    evidence = "".join(
        f'<li><a href="{escape(a["source_url"])}">{escape(a["name"])}</a><span class="evidence-date">Checked {escape(a["checked_utc_date"])}</span><p>{escape(a["scope"])}</p></li>'
        for a in project["alternatives"]
    )
    alternatives = (
        f'<div class="comparison evidence-note"><ul>{evidence}</ul></div>'
        if evidence
        else ""
    )
    chart = ""
    inline_chart = ""
    if project["hn"]:
        attention = project["hn"]
        inline_chart = f'<img class="name-sparkline" src="{escape(attention["chart_url"])}" width="80" height="16" alt="HN discussions / 2y" title="HN discussions / 2y: {attention["total_stories"]} matched stories" loading="lazy">'
        chart = f'<div class="signal evidence-note"><h4>Hacker News stories</h4><a class="hn-chart" href="{escape(attention["search_url"])}" title="Hacker News stories"><img src="{escape(attention["chart_url"])}" width="120" height="24" alt="HN discussions / 2y" loading="lazy"><span>{attention["total_stories"]} submissions / past 2y</span></a></div>'
    if chart and project.get("star_history"):
        paired = project["star_history"]
        if paired.get("chart_url"):
            good = paired["last_good"]
            chart = chart.replace(
                "</a></div>",
                '</a><p class="fine-print star-window">'
                + escape(good["months"][0])
                + "&nbsp;–&nbsp;"
                + escape(good["months"][-1])
                + "<br>Square-root scale: 0–"
                + escape(paired["hn_monthly_maximum"])
                + " stories/month (shared across HN charts)</p></div>",
            )
    summary = project.get("function_summary")
    function_detail = ""
    if summary:
        sources = " / ".join(
            f'<a href="{escape(item["url"])}">{escape(item["title"])}</a>'
            for item in summary["sources"]
        )
        function_detail = f'<div class="function-detail"><p>{highlight_name(summary["text"], project["name"])}</p><p class="function-provenance">{sources} · Reviewed <span class="metric-value">{escape(summary["checked_at"])}</span></p></div>'
    leader_categories = project.get("leader_categories", [])
    leader_label = (
        " / ".join(categories[c] for c in leader_categories)
        if leader_categories
        else ""
    )
    good_release = (
        ((project.get("signals") or {}).get("release") or {}).get("last_good") or {}
    ).get("value")
    release = (
        (good_release["published_at"][:10], good_release["tag_name"])
        if good_release
        else None
    )
    vitals = f"""<dl class="vitals"><div><dt>Detected license</dt><dd>{escape(license_text or "Unknown")}</dd></div><div><dt>GitHub stars</dt><dd>{stars}</dd></div><div><dt>Repository created</dt><dd>{escape(created)}</dd></div><div><dt>Repository push</dt><dd>{escape(pushed)}</dd></div></dl>"""
    freshness = metrics_freshness(github, catalog.get("metrics_as_of"))
    if freshness:
        vitals += f'<p class="fine-print metrics-freshness">{escape(freshness)}</p>'
    if github:
        vitals += timeline(
            created, release, github["pushed_at"][:10] if github["pushed_at"] else None
        )
    interior = specimen_plate(
        project,
        number,
        tags,
        function_detail,
        vitals,
        chart,
        alternatives,
        (cutouts or {}).get(project["id"]),
    )
    if deferred:
        interior = (
            f'<div class="specimen-detail-host" data-detail-url="records/{pid}.html" data-project-id="{pid}">'
            f'<p class="detail-fallback"><a href="records/{pid}.html">Read or print the full record for {escape(project["name"])}</a></p></div>'
        )
    return f'''<article class="project-card" data-leader="{"true" if leader_categories else "false"}" id="project-{pid}" data-project-id="{pid}">
 <details class="specimen-drawer">
  <summary><span class="folio" title="Position in current results" aria-hidden="true">{position:03d}</span><span class="name-cell"><span class="specimen-name" id="name-{pid}">{split_name(project["name"])}</span>{inline_chart}<span class="leader-label"{"" if leader_categories else " hidden"}>{escape(leader_label)}</span></span><span class="description">{escape(project["description"])}</span><span class="license-readout">{escape(license_text)}</span><span class="drawer-sign" aria-hidden="true"></span></summary>
{interior}
 </details>
</article>'''


def render_html(catalog, cutouts=None, deferred=False):
    categories = {c["id"]: c["name"] for c in catalog["categories"]}
    count = len(catalog["projects"])
    nav = "".join(
        f'<a class="{"has-category-art" if c.get("artwork") else ""}" data-category="{escape(c["id"])}" href="{escape(source_url(catalog, "README.source.md", "#" + c["id"]))}">{category_image(c)}<span class="category-label">{escape(c["name"])}</span><span class="category-count">{c["count"]:02d}</span></a>'
        for c in catalog["categories"]
    )
    category_options = "".join(
        f'<option value="{escape(c["id"])}">{escape(c["name"])}</option>'
        for c in catalog["categories"]
    )
    licenses = sorted(
        {
            p["github"]["license"]
            for p in catalog["projects"]
            if p["github"] and p["github"]["license"]
        }
    )
    license_options = "".join(
        f'<option value="{escape(v)}">{escape(v)}</option>' for v in licenses
    )
    alternative_names = sorted(
        {a["name"] for p in catalog["projects"] for a in p["alternatives"]}
    )
    alternative_options = "".join(
        f'<option value="{escape(v)}">{escape(v)}</option>' for v in alternative_names
    )
    deployment_options = {}
    for field, labels in (
        ("run_modes", deployment.RUN_MODES),
        ("install_methods", deployment.INSTALL_METHODS),
    ):
        observed = {
            f["value"]
            for p in catalog["projects"]
            for f in p.get("deployment", {}).get(field, [])
        }
        deployment_options[field] = "".join(
            f'<option value="{escape(v)}">{escape(labels[v])}</option>'
            for v in sorted(observed)
        )
    footer_backgrounds = [quote(path, safe="/") for path in catalog.get("footer_backgrounds", [])]
    footer_sizes = catalog.get("footer_background_sizes", [])
    footer_size = footer_sizes[0] if footer_sizes else (2048, 682)
    footer_art = (
        f'<img class="footer-art" data-footer-background data-background-sizes="{escape(json.dumps(footer_sizes))}" data-backgrounds="{escape(json.dumps(footer_backgrounds))}" src="{escape(footer_backgrounds[0])}" width="{footer_size[0]}" height="{footer_size[1]}" alt="" loading="lazy" decoding="async">'
        if footer_backgrounds
        else ""
    )
    folios = {p["id"]: i + 1 for i, p in enumerate(catalog["projects"])}
    def star_order(project):
        stars = (project.get("github") or {}).get("stars")
        known = type(stars) is int and stars >= 0
        name = "".join(c for c in unicodedata.normalize("NFKD", project["name"])
                       if not "\u0300" <= c <= "\u036f").lower()
        return (not known, -stars if known else 0, name, project["id"])
    projects = "\n".join(
        project_html(p, categories, catalog, folios[p["id"]], cutouts, position, deferred=deferred)
        for position, p in enumerate(sorted(catalog["projects"], key=star_order), 1)
    )
    signal_projects = [p for p in catalog["projects"] if p.get("signals")]
    signal_coverage = []
    for provider, label in (("release", "Release"), ("scorecard", "Scorecard")):
        checked = sum(
            bool(p["signals"][provider]["checked_at"]) for p in signal_projects
        )
        values = sum(bool(p["signals"][provider]["last_good"]) for p in signal_projects)
        signal_coverage.append(f"{label}: {values} cached results / {checked} checked")
    optional_notes = (
        (
            '<ul class="coverage-notes">'
            + "".join(f"<li>{item}</li>" for item in signal_coverage)
            + f"<li>{len(signal_projects)} mapped GitHub repositories.</li>"
            + f"<li>Collection snapshot {escape(catalog.get('signals_collected_at'))}.</li></ul>"
            + '<p><a href="data/project_signals.json">Release and Scorecard evidence</a></p>'
        )
        if signal_projects
        else ""
    )
    star_note = ""
    if any(p.get("star_history") for p in catalog["projects"]):
        star_note = "<li>GitHub stars / past 2y: Stars per month that remained at last successful fetch.</li>"
        optional_notes += '<p><a id="star-evidence" href="data/star_history.json">GitHub star-history evidence</a></p>'
    sha = catalog.get("source_sha")
    revision = (
        f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>'
        if sha
        else "Local preview (revision not supplied)"
    )
    return f'''<!doctype html>
<html lang="en">
<head>
 <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
 <meta name="description" content="A natural-history field guide to software named Open, with searchable project records, repository data, and reviewed comparisons.">
 <meta name="color-scheme" content="light"><title>Awesome Open* Catalog</title>
 <link rel="icon" href="brand/favicon.ico" sizes="16x16 32x32 48x48">
 <link rel="icon" type="image/png" href="brand/fruit-16.png" sizes="16x16">
 <link rel="icon" type="image/png" href="brand/fruit-32.png" sizes="32x32">
 <link rel="stylesheet" href="vendor/fonts.css"><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="styles.css?v={escape(sha or "preview")}">
 <script src="catalog.js" defer></script>
</head>
<body>
<a class="skip-link" href="#catalog">Skip to specimen ledger</a>
<div class="page-shell">
<header class="site-header"><a class="brand" href="./" aria-label="Awesome Open home"><img class="brand-mark" src="brand/botanical-128.png" alt="" width="64" height="64"><span class="brand-name">Awesome Open<span class="brand-asterisk" aria-hidden="true">*</span></span></a><div class="search-field header-search" id="header-search" hidden><label for="search" class="visually-hidden">Search projects</label><div class="search-input"><input id="search" name="q" form="filters" type="search" autocomplete="off" aria-describedby="search-help"><button class="search-submit" type="submit" form="filters" aria-label="Search projects" title="Search projects"><img class="search-icon" src="brand/search-loupe.png" width="32" height="32" alt=""></button></div><span id="search-help" class="visually-hidden">Search names, descriptions, and reviewed alternative names. Results update as you type.</span></div><nav class="header-links" aria-label="Field guide"><a href="#catalog">Catalog</a><a href="#about">About</a><a href="observatory/">Observatory</a></nav></header>
<div class="layout">

 <main id="catalog" class="catalog-main" tabindex="-1">
  <h1 id="page-title" class="visually-hidden">Projects</h1>
  <div class="control-row">
 <aside class="sidebar" aria-label="Catalog categories"><details class="category-panel" name="catalog-controls"><summary>Table of contents <span aria-hidden="true">+</span></summary><nav class="category-nav" aria-label="Categories"><a data-category="" href="#catalog" aria-current="true"><span class="category-label">All</span><span class="category-count">{count}</span></a>{nav}</nav></details></aside>
  <form id="filters" class="catalog-toolbar" hidden aria-label="Filter projects">

   <details class="filter-options" name="catalog-controls"><summary>Filters <span aria-hidden="true">+</span></summary><div class="filter-body"><div class="diagnostic-filters"><div class="filter-field"><label for="push-window">Repository push window</label><select id="push-window" name="window"><option value="all">Any observed date</option><option value="recent">Within 90 days of snapshot</option><option value="older">More than 2 years before snapshot</option><option value="unknown">Push date unknown</option></select></div><div class="filter-field"><label for="alternative-filter">Reviewed alternative to</label><select id="alternative-filter" name="alternative"><option value="">Any / not recorded</option>{alternative_options}</select></div><div class="filter-field"><label for="license-filter">Detected license</label><select id="license-filter" name="license"><option value="all">Any / unknown</option><option value="known">Detected license available</option><option value="unknown">License unknown</option>{license_options}</select></div></div>
   <details class="more-filters"><summary>More filters <span aria-hidden="true">+</span></summary><div class="filter-grid"><div class="filter-field"><label for="run-mode-filter">Reviewed run mode</label><select id="run-mode-filter" name="run_mode"><option value="">Any / not reviewed</option><option value="unknown">Not recorded</option>{deployment_options["run_modes"]}</select></div><div class="filter-field"><label for="install-method-filter">Reviewed install method</label><select id="install-method-filter" name="install_method"><option value="">Any / not reviewed</option><option value="unknown">Not recorded</option>{deployment_options["install_methods"]}</select></div><div class="filter-field"><label for="category-filter">Function</label><select id="category-filter" name="category"><option value="">All categories</option>{category_options}</select></div><div class="filter-field"><label for="metrics-filter">Cached repository metrics</label><select id="metrics-filter" name="metrics"><option value="all">Present or missing</option><option value="present">Present</option><option value="missing">Missing</option></select></div><div class="filter-field"><label for="min-stars">Minimum GitHub stars</label><input id="min-stars" name="stars" type="number" min="0" step="1" placeholder="Any"></div><div class="filter-field"><label for="pushed-since">Last pushed on or after</label><input id="pushed-since" name="pushed" type="date"></div></div></details>
   <div class="toolbar-bottom"><p class="filter-note">Date filters use the {escape(catalog["metrics_as_of"])} UTC snapshot. Setup filters cover reviewed evidence only; unrecorded paths remain unknown.</p></div></div></details><button class="visually-hidden" type="submit" tabindex="-1">Apply filters</button>
  </form></div>
  <noscript><p class="no-script">All {count} projects are available below. Use your browser’s Find to search and open any specimen drawer. {"Follow its full-record link for evidence and printing. " if deferred else ""}Category links open the curated source sections. Enable JavaScript for filters and sorting.</p></noscript>
  <div class="results-heading"><h2 id="result-count" class="visually-hidden" role="status" aria-live="polite" aria-atomic="true">{count} projects</h2><div class="result-actions"><button id="clear-filters" type="button" disabled>Reset filters <span aria-hidden="true">↺</span></button><div class="sort-field"><label for="sort-order" class="visually-hidden">Sort projects</label><select id="sort-order" name="sort" disabled><option value="name">Name A–Z</option><option value="stars" selected>Most stars</option><option value="pushed">Latest push</option></select></div></div></div>
  <p id="project-link-notice" class="link-notice" role="status" hidden></p><p id="empty-state" class="empty-state" hidden>No projects match these filters. Try a broader search or reset filters.</p>
  <div id="project-list" class="project-list">{projects}</div>
 </main>
</div>
</div>
<div class="page-end" aria-hidden="true"><img src="brand/fruit-96.png" alt="" width="96" height="96" loading="lazy"></div>
<footer class="site-footer{" has-art" if footer_backgrounds else ""}" id="about">{footer_art}<div class="footer-actions"><a href="{escape(source_url(catalog, "CONTRIBUTING.md"))}">Submit a project</a><a href="standalone.html" download>Download</a><a href="draws/">Spotlight</a><a href="{REPOSITORY}">GitHub</a><a href="#catalog">Top</a></div><details class="data-notes" id="method" open><summary>About the data <span aria-hidden="true">+</span></summary><div class="colophon"><div><h2>Collection</h2><ul><li>Registry IDs come from canonical URLs</li><li>List numbers show position in current results</li><li>Folio numbers show alphabetical position</li><li>Bold: Top-3 per category (GitHub stars)</li><li>Specimen illustrations are original artwork</li></ul></div><div><h2>Evidence</h2><ul><li>Detected licenses: verify against current official terms</li><li>Repository dates refer to GitHub activity</li><li>HN charts: matched stories / 2 years, shared square-root scale</li>{star_note}<li>GitHub release: follows publisher</li><li>Scorecard: reports automated security-practice checks (combining aggregate, scored/returned coverage, scan date and reasons)</li><li>Stale: Old scan/cache or a retained result after an unsuccessful check</li></ul>{optional_notes}<p><a id="hn-evidence" href="data/hn_evidence.json">HN evidence</a> / <a href="data/alternatives.json">Comparison evidence</a> / <a href="catalog.json">Catalog JSON</a></p><p><br/ ><br/ ><br/ ><a href="https://buymeacoffee.com/jumpermcp.dev">Support this Awesome Open* list with a coffee</a></p></div></div></details><div class="footer-baseline"><span>Source revision: {revision} | {count} Projects</span><span>List: <a href="{escape(source_url(catalog, "LICENSE.md"))}">CC0-1.0</a></span></div></footer>
<script id="catalog-data" type="application/json">{json_for_html(search_index(catalog))}</script>
</body></html>
'''


def render_record(project, categories, catalog, number, cutouts=None):
    """A native no-JS record is also the same-origin fetch-on-open source.

    Keep asset paths identical to the ledger via the explicit base. The loader
    resolves them against this base before adopting only the validated plate.
    """
    pid = escape(project["id"])
    name = escape(project["name"])
    card = project_html(project, categories, catalog, number, cutouts, position=1)
    card = card.replace('<details class="specimen-drawer">', '<details class="specimen-drawer" open>', 1)
    sha = catalog.get("source_sha")
    revision = f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else "Local preview (revision not supplied)"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<base href="../"><meta name="color-scheme" content="light"><title>{name} · Awesome Open*</title>
<meta name="description" content="{escape(project['description'])}">
<link rel="icon" href="brand/favicon.ico"><link rel="stylesheet" href="vendor/fonts.css"><link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="styles.css?v={escape(sha or 'preview')}"><link rel="stylesheet" href="observatory/observatory.css">
<script src="catalog.js" defer></script></head>
<body class="observatory record-page"><a class="skip-link" href="records/{pid}.html#record">Skip to project record</a>
<div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="./">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Field guide"><a href="#catalog">Ledger</a><a href="#method">About</a><a href="observatory/">Observatory</a><a href="draws/">Weekly draws</a></nav></header></div>
<main class="obs-shell" id="record" tabindex="-1"><section class="obs-hero"><p><span class="obs-label">Project record</span></p><h1>{name}</h1></section>
<aside class="obs-finding"><p>Full catalog record, evidence and sources. <a href="#project-{pid}">Return to this project in the ledger</a>. Use your browser’s Print command to print this record.</p></aside>
{card}
<div class="obs-closing-mark"><img class="obs-logo" src="brand/botanical-128.png" width="128" height="128" alt="Awesome Open* botanical logo"></div></main>
<footer class="obs-footer"><div class="obs-shell"><p>Awesome Open* / Project record</p><ul class="obs-footer-links"><li><a href="./">Return to project ledger</a></li><li><a href="standalone.html" download>Download complete catalog</a></li><li><a href="{REPOSITORY}">GitHub</a></li><li>Source revision: {revision}</li></ul></div></footer></body></html>'''


def replace_literals_once(text, replacements):
    """Replace exact source literals without scanning newly embedded payloads.

    Insertion order gives a more specific literal priority over its prefix
    (for example, an evidence link before the generic downloadable href).
    A callable replacement preserves backslashes and other payload bytes.
    """
    if not replacements:
        return text
    pattern = re.compile("|".join(re.escape(literal) for literal in replacements))
    return pattern.sub(lambda match: replacements[match.group()], text)


def build(output, source_sha=None, root=ROOT):
    root = Path(root)
    output = Path(output).resolve()
    # Protect source directories from accidental --output . or --output site.
    for protected in (
        root,
        root / "site",
        root / "scripts",
        root / "data",
        root / "assets",
        root / ".github",
    ):
        if (
            output == protected.resolve()
            or output in protected.resolve().parents
            or (protected != root and protected.resolve() in output.parents)
        ):
            raise ValueError(
                "Use a separate generated output directory (default: tmp/site)"
            )
    source = (root / "README.source.md").read_text(encoding="utf-8")
    snapshot = json.loads(
        (root / "data/github_metrics.json").read_text(encoding="utf-8")
    )
    alternatives = json.loads(
        (root / "data/alternatives.json").read_text(encoding="utf-8")
    )
    evidence = json.loads((root / "data/hn_evidence.json").read_text(encoding="utf-8"))
    optional = signals.load_optional(root / "data/project_signals.json")
    catalog = build_catalog(
        source,
        snapshot,
        alternatives,
        evidence,
        source_sha=source_sha,
        optional_signals=optional,
        function_summaries=load_function_summaries(
            root / "data/function_summaries.json"
        ),
        deployment_evidence=deployment.load_optional(
            root / "data/deployment_evidence.json"
        ),
        star_evidence=star_history.load_optional(root / "data/star_history.json"),
        aliases=project_aliases.load_optional(root / project_aliases.PATH),
    )
    footer_assets = discover_footer_art(root)
    catalog["footer_backgrounds"] = list(footer_assets)
    catalog["footer_background_sizes"] = [list(size) for size in footer_assets.values()]
    attach_specimen_art(catalog, root)
    attach_category_art(catalog, root)
    cutouts = attach_specimen_cutouts(catalog, root)
    import weekly_draw
    draws = weekly_draw.load(root / weekly_draw.PATH)
    catalog["weekly_draws"] = draws
    page = render_html(catalog, cutouts)
    ledger = render_html(catalog, cutouts, deferred=True)
    # Validate charts before touching generated files. The renderer is shared with README.
    charts = {
        p["slug"]: hn.svg(p, evidence) for p in display_hn_evidence(source, evidence)["projects"] if p["eligible"]
    }
    star_charts = {
        p["star_history"]["chart_url"]: star_history.svg(p)
        for p in catalog["projects"]
        if p.get("star_history", {}).get("chart_url")
    }
    qr_codes = {
        qr_path(p): qr.svg(
            PERMALINK_BASE + p["id"], "QR code: permalink to " + p["name"]
        )
        for p in catalog["projects"]
    }
    assets = {
        name: (root / "site" / name).read_text(encoding="utf-8")
        for name in ("styles.css", "catalog.js")
    }
    assets["tokens.css"] = (root / "site/design/tokens.css").read_text(encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(ledger, encoding="utf-8")
    records = output / "records"
    shutil.rmtree(records, ignore_errors=True)
    records.mkdir()
    categories = {c["id"]: c["name"] for c in catalog["categories"]}
    for number, project in enumerate(catalog["projects"], 1):
        (records / (project["id"] + ".html")).write_text(
            render_record(project, categories, catalog, number, cutouts), encoding="utf-8"
        )
    (output / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for name, content in assets.items():
        (output / name).write_text(content, encoding="utf-8")
    (output / "assets/hn").mkdir(parents=True, exist_ok=True)
    for slug, chart in charts.items():
        (output / "assets/hn" / (slug + ".svg")).write_text(chart, encoding="utf-8")
    shutil.rmtree(output / "assets/stars", ignore_errors=True)
    (output / "assets/stars").mkdir(parents=True, exist_ok=True)
    for path, chart in star_charts.items():
        (output / path).write_text(chart, encoding="utf-8")
    shutil.rmtree(output / "assets/qr", ignore_errors=True)
    (output / "assets/qr").mkdir(parents=True, exist_ok=True)
    for path, code in qr_codes.items():
        (output / path).write_text(code, encoding="utf-8")
    (output / "data").mkdir(exist_ok=True)
    evidence_files = ["alternatives.json", "hn_evidence.json"]
    if (root / "data/star_history.json").exists():
        evidence_files.append("star_history.json")
    else:
        (output / "data/star_history.json").unlink(missing_ok=True)
    if optional is not None:
        evidence_files.append("project_signals.json")
    else:
        (output / "data/project_signals.json").unlink(missing_ok=True)
    for name in evidence_files:
        shutil.copyfile(root / "data" / name, output / "data" / name)
    (output / "vendor").mkdir(exist_ok=True)
    for name in ("fonts.css", "FONT-LICENSE.txt", "FONT-PROVENANCE.json"):
        shutil.copyfile(root / "site/vendor" / name, output / "vendor" / name)
    for old in (
        "motion.js",
        "vendor/gsap.min.js",
        "vendor/ScrollTrigger.min.js",
        "vendor/GSAP-PROVENANCE.txt",
    ):
        (output / old).unlink(missing_ok=True)
    shutil.rmtree(output / "specimens", ignore_errors=True)
    for project in catalog["projects"]:
        if "artwork" in project:
            asset = project["artwork"]["path"]
            (output / asset).parent.mkdir(exist_ok=True)
            shutil.copyfile(root / "site" / asset, output / asset)
    for cutout in cutouts.values():
        (output / cutout["path"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / "site" / cutout["path"], output / cutout["path"])
    shutil.rmtree(output / "footer-backgrounds", ignore_errors=True)
    for asset in (*catalog["footer_backgrounds"], FOOTER_PATTERN):
        (output / asset).parent.mkdir(exist_ok=True)
        shutil.copyfile(root / "site" / asset, output / asset)
    (output / "brand").mkdir(exist_ok=True)
    for name in BRAND_ASSETS:
        shutil.copyfile(root / "site/brand" / name, output / "brand" / name)
    copy_category_art(catalog, root, output)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    # A phone/download-friendly edition: every runtime asset and evidence download
    # is embedded, so opening one HTML file never depends on adjacent files.
    # Collect substitutions against the original page, then expand it once.
    # Repeated replacements used to rescan the growing base64-heavy document.
    replacements = {
        'href="data/hn_evidence.json">View evidence':
        'href="#hn-evidence">View evidence',
    }
    for category in catalog["categories"]:
        if category.get("artwork"):
            replacements[category_image(category)] = category_image(
                category, offline=True, root=root
            )
    footer_urls = [quote(path, safe="/") for path in catalog["footer_backgrounds"]]
    embedded_backgrounds = []
    for asset in catalog["footer_backgrounds"]:
        mime_type = "image/png" if asset.lower().endswith(".png") else "image/webp"
        encoded = base64.b64encode((output / asset).read_bytes()).decode("ascii")
        embedded_backgrounds.append(f"data:{mime_type};base64,{encoded}")
    replacements[f'data-backgrounds="{escape(json.dumps(footer_urls))}"'] = (
        f'data-backgrounds="{escape(json.dumps(embedded_backgrounds))}"'
    )
    if embedded_backgrounds:
        replacements[f'src="{escape(footer_urls[0])}"'] = (
            f'src="{embedded_backgrounds[0]}"'
        )
    for name, mime_type in BRAND_ASSETS.items():
        encoded = base64.b64encode((output / "brand" / name).read_bytes()).decode(
            "ascii"
        )
        for attribute in ("src", "href"):
            replacements[f'{attribute}="brand/{name}"'] = (
                f'{attribute}="data:{mime_type};base64,{encoded}"'
            )
    for name in ("vendor/fonts.css", "tokens.css", "styles.css"):
        href = f"{name}?v={source_sha or 'preview'}" if name == "styles.css" else name
        css = (output / name).read_text(encoding="utf-8")
        if name == "styles.css":
            encoded = base64.b64encode((output / FOOTER_PATTERN).read_bytes()).decode("ascii")
            css = css.replace(f"url({FOOTER_PATTERN})", f"url(data:image/png;base64,{encoded})")
        replacements[f'<link rel="stylesheet" href="{href}">'] = (
            "<style>" + css + "</style>"
        )
    for name in ("catalog.js",):
        # Keep parser ordering identical to deferred scripts: initialize after DOM.
        code = (output / name).read_text(encoding="utf-8")
        encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
        replacements[f'src="{name}"'] = f'src="data:text/javascript;base64,{encoded}"'
    for project in catalog["projects"]:
        if "artwork" in project:
            asset = (
                cutouts[project["id"]]["path"]
                if project["id"] in cutouts
                else project["artwork"]["path"]
            )
            encoded = base64.b64encode((output / asset).read_bytes()).decode("ascii")
            replacements[f'src="{asset}"'] = f'src="data:image/webp;base64,{encoded}"'
    for path, code in qr_codes.items():
        encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
        replacements[f'src="{path}"'] = f'src="data:image/svg+xml;base64,{encoded}"'
    replacements['<a href="standalone.html" download>Download</a>'] = ""
    for slug, chart in charts.items():
        encoded = base64.b64encode(chart.encode("utf-8")).decode("ascii")
        replacements[f'src="assets/hn/{slug}.svg"'] = (
            f'src="data:image/svg+xml;base64,{encoded}"'
        )
    for path, chart in star_charts.items():
        encoded = base64.b64encode(chart.encode("utf-8")).decode("ascii")
        replacements[f'src="{path}"'] = f'src="data:image/svg+xml;base64,{encoded}"'
    for name in ["catalog.json", *("data/" + item for item in evidence_files)]:
        encoded = base64.b64encode((output / name).read_bytes()).decode("ascii")
        replacements[f'href="{name}"'] = (
            f'download="{Path(name).name}" href="data:application/json;base64,{encoded}"'
        )
    replacements['href="./"'] = 'href="#page-title"'
    replacements['href="observatory/"'] = (
        'href="https://awesomeopen.github.io/awesome-open/observatory/"'
    )
    replacements['href="draws/"'] = 'href="https://awesomeopen.github.io/awesome-open/draws/"'
    standalone = replace_literals_once(page, replacements)
    (output / "standalone.html").write_text(standalone, encoding="utf-8")
    from build_observatory import build as build_observatory

    build_observatory(catalog, evidence, output, root)
    from build_draw_archive import build as build_draw_archive
    build_draw_archive(catalog, draws, output, root)
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/site")
    parser.add_argument(
        "--source-sha",
        help="Explicit full source commit SHA, supplied by the caller; never inferred",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use the reviewed specimen hero on the main entry point",
    )
    args = parser.parse_args()
    catalog = build(args.output, args.source_sha)
    if args.production:
        from build_jar_preview import build as build_hero

        build_hero(args.output, production=True)
    print(
        f"Built {len(catalog['projects'])} projects / {catalog['category_memberships']} category memberships in {args.output}"
    )
    print(
        f"Cached GitHub metrics as of {catalog['metrics_as_of']}; no data fetched or deployed."
    )


if __name__ == "__main__":
    main()

