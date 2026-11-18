#!/usr/bin/env python3
"""Build the complete, offline static catalog. No network, dependencies or deployment."""

import argparse
from font_assets import content_url, font_asset_url
import hashlib
import html
import unicodedata
import json
import math
import os
import re
import warnings
from datetime import date
from pathlib import Path
from urllib.parse import quote
import shutil

from build_catalog import build_catalog, category_id, load_function_summaries
from render_readme import display_hn_evidence
import published_hn
import project_aliases
import project_history
import history_view
import update_hn as hn
import signals
import star_history
import deployment
import build_webmcplet_list
import plate_grid
import collection_log
import qr
from repository_hosts import repository_host
from footer_art import discover_footer_art
from category_art import (
    attach_category_art,
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


def compact_json(value):
    """Site JSON downloads carry no indentation; repository copies stay indented for review."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"


def published_catalog(catalog):
    """Publish compact references to the combined star and deployment downloads.

    Each project's `star_history` keeps its status and chart link; its `repo` keys
    the counts in that file's `repositories`, as `hn.slug` does for HN evidence.
    """
    projects = []
    for project in catalog["projects"]:
        record = project.get("star_history")
        if record and "last_good" in record:
            record = {key: value for key, value in record.items() if key != "last_good"}
            project = {**project, "star_history": record}
        setup = project.get("deployment")
        if setup:
            project = {**project, "deployment": {
                "review_status": setup["review_status"],
                "checked_at": setup["checked_at"],
                **{field: [{"value": fact["value"]} for fact in setup.get(field, [])]
                   for field in ("run_modes", "install_methods")},
                "record": f'records/{project["id"]}.html',
            }}
        # Null optional-provider metadata repeats across every record. Keep
        # last_good explicit; the evidence download retains the collector schema.
        if project.get("signals"):
            compact_signals = {}
            for provider, record in project["signals"].items():
                record = {key: val for key, val in record.items() if val is not None or key == "last_good"}
                if provider == "languages":
                    record = {key: val for key, val in record.items()
                              if key not in {"etag", "retry_after", "http_status"}
                              and not (key.endswith("time_precision") and val == "second")}
                if record.get("last_good") is not None:
                    good = {key: val for key, val in record["last_good"].items() if val is not None}
                    if provider == "languages":
                        good.pop("observed_at", None)  # Same timestamp as fetched_at by contract.
                    record["last_good"] = good
                compact_signals[provider] = record
            project = {**project, "signals": compact_signals}
        if project.get("github") and project["github"].get("primary_language") is None:
            project = {**project, "github": {k: v for k, v in project["github"].items() if k != "primary_language"}}
        projects.append(project)
    return {**catalog, "projects": projects}


def load_site_catalog(site):
    """Restore full evidence for preview/rendering consumers of a built catalog."""
    catalog = json.loads((Path(site) / "catalog.json").read_text(encoding="utf-8"))
    path = Path(site) / "data/star_history.json"
    repositories = json.loads(path.read_text(encoding="utf-8"))["repositories"] if path.exists() else {}
    slim = [p for p in catalog["projects"] if "record" in p.get("deployment", {})]
    if slim:
        # Missing downloads/records fail visibly rather than rendering partial facts.
        setups = json.loads((Path(site) / "data/deployment_evidence.json").read_text(encoding="utf-8"))["projects"]
        for project in slim:
            project["deployment"] = setups[project["id"]]
    signals_path = Path(site) / "data/project_signals.json"
    full_signals = signals.load_optional(signals_path)
    for project in catalog["projects"]:
        if project.get("github"):
            project["github"].setdefault("primary_language", None)
        if project.get("signals"):
            repo = (project.get("github") or {}).get("repo")
            project["signals"] = signals.for_repository(full_signals, repo)
            if project["signals"] is None:
                raise ValueError("Missing full optional signal download")
        record = project.get("star_history")
        if record and "last_good" in repositories.get(record["repo"], {}):
            record["last_good"] = repositories[record["repo"]]["last_good"]
    return catalog


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
        former_names = sorted({event["old_name"] for event in project.get("history", [])
                               if event["kind"] == "software_rename"})
        if former_names:
            item["former_names"] = former_names
        item["languages"] = project.get("languages")
        item["language_status"] = project.get("language_status", "unknown")
        item["leader_categories"] = project.get("leader_categories", [])
        item["github"] = (
            {
                key: github.get(key)
                for key in (
                    "license",
                    "stars",
                    "pushed_at",
                    "status",
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


def search_text(catalog):
    """Function summaries and feature notes, fetched on a visitor's first search.

    Embedding them would nearly double the initial gzip transfer of index.html.
    """
    projects = {}
    for project in catalog["projects"]:
        summary = project.get("function_summary")
        if summary:
            projects[project["id"]] = {
                "summary": summary["text"],
                "features": [f'{feature["title"]} {feature["text"]}' for feature in summary.get("features", [])],
            }
    return compact_json({"source_sha": catalog.get("source_sha") or "", "projects": projects})


SITE_URL = "https://awesomeopen.github.io/awesome-open/"


def origin_trial_meta():
    """Chrome's WebMCP origin-trial token for SITE_URL's origin, from GOOGLE_ORIGIN_TRIAL_TOKEN."""
    token = os.environ.get("GOOGLE_ORIGIN_TRIAL_TOKEN", "").strip()
    return f'<meta http-equiv="origin-trial" content="{html.escape(token)}">' if token else ""


def webmcplet_list(catalog):
    """The catalog as a WebMCPlet list document, loaded at the first tool call or panel use."""
    return compact_json(build_webmcplet_list.build(catalog, SITE_URL))


def split_name(name):
    """The prefix treatment never changes the canonical name or identity."""
    if name[:4].lower() == "open":
        return f'<span class="name-prefix">{escape(name[:4])}</span><span class="name-stem">{escape(name[4:])}</span>'
    return f'<span class="name-stem">{escape(name)}</span>'


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
        result[project["id"]] = {"path": entry["path"], "bbox": entry.get("subject_bbox")}
    return result


def attach_specimen_variants(root):
    """Responsive candidates per plate source, used only while the source still matches.

    Returns {source path: [(path, width), ...]} ending with the source itself, the
    widest candidate. See scripts/build_specimen_variants.py.
    """
    path = root / "site/specimens/responsive.json"
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("sources"), dict):
        raise ValueError("Invalid specimen variant manifest")
    result = {}
    for source, entry in document["sources"].items():
        if not (root / "site" / source).is_file():
            continue
        if hashlib.sha256((root / "site" / source).read_bytes()).hexdigest() != entry["sha256"]:
            warnings.warn("Specimen variants are older than their source; run build_specimen_variants.py: " + source)
            continue
        candidates = []
        for variant in entry["variants"]:
            if not variant["path"].startswith("specimens/responsive/"):
                raise ValueError("Specimen variant outside specimens/responsive/: " + variant["path"])
            if hashlib.sha256((root / "site" / variant["path"]).read_bytes()).hexdigest() != variant["sha256"]:
                raise ValueError("Specimen variant bytes do not match the manifest: " + variant["path"])
            candidates.append((variant["path"], variant["width"]))
        result[source] = candidates + [(source, entry["width"])]
    return result


# The plate stage is at most 627 px wide and spans the phone viewport.
PLATE_SIZES = "(max-width: 660px) 100vw, 627px"

PERMALINK_BASE = "https://awesomeopen.github.io/awesome-open/#project-"


def qr_path(project):
    return f"assets/qr/{project['id'][:16]}.svg"


def qr_codes(projects, cache=None):
    """Permalink QR SVGs by output path; `cache` is an optional directory reused across builds.

    Entries are keyed by the encoder's source and the encoded text and label, so an
    encoder change misses every entry. Entries this build does not use are removed.
    """
    encoder = Path(qr.__file__).read_bytes()
    codes, used = {}, set()
    for p in projects:
        text, label = PERMALINK_BASE + p["id"], "QR code: permalink to " + p["name"]
        if cache is None:
            codes[qr_path(p)] = qr.svg(text, label)
            continue
        key = hashlib.sha256(encoder + b"\0" + text.encode() + b"\0" + label.encode()).hexdigest()
        entry = Path(cache) / (key + ".svg")
        used.add(entry.name)
        if entry.is_file():
            codes[qr_path(p)] = entry.read_text(encoding="utf-8")
        else:
            codes[qr_path(p)] = qr.svg(text, label)
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text(codes[qr_path(p)], encoding="utf-8")
    if cache is not None:
        for stale in Path(cache).glob("*.svg"):
            if stale.name not in used:
                stale.unlink()
    return codes


def timeline(created, release, pushed, events=()):
    """Repository timestamps on one axis; positions are literal dates, labels repeat them.

    Reviewed name changes (date, title, details HTML) join the axis above it; their
    "(i)" disclosure carries the evidence. Upper labels that would collide stack.
    """
    points = [("Repository created", created, "")]
    if release:
        points.append(("GitHub release", release[0], release[1]))
    if pushed:
        points.append(("Repository push", pushed, ""))
    dated = []
    for label, value, tag in points:
        try:
            dated.append((label, date.fromisoformat(value), tag))
        except (TypeError, ValueError):
            if not events:
                return ""
    if not dated and not events:
        return ""
    days = [day for _, day, _ in dated] + [day for day, _, _ in events]
    first = min(days).year
    last = max(days).year + 1
    lo, hi = date(first, 1, 1), date(last, 1, 1)
    pct = lambda day: round((day - lo).days / (hi - lo).days * 100, 2)
    step = 2 if last - first > 8 else 1
    years = "".join(
        f'<span class="timeline-year" style="left:{pct(date(y, 1, 1))}%">{y}</span>'
        for y in range(first, last + 1, step)
    )
    marks, labels, rows = [], [], []

    def upper_row(left, lowest=0):
        # True positions stay; only the label climbs a row when neighbours are close.
        while len(rows) < lowest:
            rows.append([])
        row = next((i for i, taken in enumerate(rows) if i >= lowest and all(abs(left - x) >= 30 for x in taken)), len(rows))
        if row == len(rows):
            rows.append([])
        rows[row].append(left)
        return row

    created_day = dated[0][1] if dated and dated[0][0] == "Repository created" else None
    pushed_day = dated[-1][1] if dated and dated[-1][0] == "Repository push" else None
    close_endpoints = bool(created_day and pushed_day) and abs(pct(pushed_day) - pct(created_day)) < 30
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
        if tag:
            anchor += f";bottom:{58 + 34 * upper_row(left)}px"
        extra = f" · {escape(tag)}" if tag else ""
        marks.append(
            f'<span class="timeline-mark{" is-release" if tag else ""}" style="left:{left}%"></span>'
        )
        labels.append(
            f'<span class="timeline-label {side}{"" if tag else " repeats-vitals"}" style="{anchor}">{escape(label)}<br><span class="metric-value">{day.isoformat()}</span>{extra}</span>'
        )
    for day, title, details in events:
        left = pct(day)
        right = left > 55
        anchor = (
            f"right:{round(100 - left, 2)}%;text-align:right;max-width:{left}%;--room:{left}"
            if right
            else f"left:{left}%;max-width:{round(100 - left, 2)}%;--room:{round(100 - left, 2)}"
        )
        # Rename labels sit above the release row; label widths are unknown on narrow screens.
        anchor += f";bottom:{58 + 34 * upper_row(left, 1 if release else 0)}px"
        marks.append(f'<span class="timeline-mark is-rename" style="left:{left}%"></span>')
        labels.append(
            f'<span class="timeline-label up is-rename{" is-right" if right else ""}" style="{anchor}">{escape(title)} '
            f'<details class="timeline-info"><summary aria-label="Details: {escape(title)}">(i)</summary>'
            f'<div class="timeline-info-panel">{details}</div></details>'
            f'<span class="metric-value timeline-date">{day.isoformat()}</span></span>'
        )
    span = ""
    repository = [day for _, day, _ in dated]
    if created_day:
        first_pct, last_pct = pct(created_day), max(pct(day) for day in repository)
        span = f'<span class="timeline-span" style="left:{first_pct}%;width:{round(last_pct - first_pct, 2)}%"></span>'
    summary = "; ".join(
        f"{label} {day.isoformat()}" + (f" ({tag})" if tag else "")
        for label, day, tag in dated
    )
    raised = f' style="margin-top:{34 * (len(rows) - 1)}px"' if len(rows) > 1 else ""
    # Rename details are interactive, so that variant cannot be a single image.
    role = (
        f'role="group" aria-label="Repository timeline: {escape(summary)}"'
        if events
        else f'role="img" aria-label="{escape(summary)}"'
    )
    spacer = ""
    if not dated and len(events) == 1:
        day, title, _ = events[0]
        position = pct(day)
        room = position if position > 55 else round(100 - position, 2)
        # Match the anchored label's wrap width; its bottom is 34px below the
        # timeline's top. The invisible copy reserves its actual text height.
        spacer = (f'<div class="timeline-rename-space" aria-hidden="true">'
                  f'<div style="width:{room}%">{escape(title)} (i)'
                  f'<span class="timeline-date">{day.isoformat()}</span></div></div>')
    return spacer + f'<div class="timeline" {role}{raised}><span class="timeline-axis"></span>{span}{years}{"".join(marks)}{"".join(labels)}</div>'


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
        f'<nav class="specimen-links" aria-label="Record for {name}"><a class="permalink" href="#project-{pid}" aria-label="Permalink to {name}">Specimen: <span class="permalink-name">{name}</span></a></nav></div></div>'
    )


def specimen_geometry(art, bbox):
    """Compose from stored bounds, without sampling or cropping image pixels.

    The alpha > .5 box describes the main subject, not every faint mark. Keep
    eight percent of source height on each side and leave overflow visible.
    Missing/malformed bounds conservatively retain the complete canvas.
    """
    valid = (isinstance(bbox, (list, tuple)) and len(bbox) == 4
             and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                     and math.isfinite(v) for v in bbox)
             and 0 <= bbox[0] < bbox[2] <= 1
             and 0 <= bbox[1] < bbox[3] <= 1)
    box = list(bbox) if valid else [0, 0, 1, 1]
    top = max(0, box[1] - .08) if valid else 0
    bottom = min(1, box[3] + .08) if valid else 1
    extent = bottom - top
    ratio = art["height"] / art["width"]
    ground = (box[3] - top) / extent if valid else .86
    return {"bbox": box, "top": top, "bottom": bottom,
            "height": extent * ratio, "offset": -top / extent,
            "ground": ground,
            "fade_start": max(.5, ground - .24),
            "fade_end": max(.5, ground - .08)}


def plate_aliases(project):
    """Reviewed alternate names, adjacent to the canonical plate heading."""
    display_name = project_aliases.name_key(project["name"])
    aliases = [alias for alias in project.get("aliases", [])
               if project_aliases.name_key(alias["name"]) != display_name]
    if not aliases:
        return ""
    items = "".join(
        f'<li>{"Also known as: " if i == 0 else ""}'
        f'<a href="{escape(alias["source_url"])}">{escape(alias["name"])}</a></li>'
        for i, alias in enumerate(aliases)
    )
    return f'<ul class="plate-aliases" aria-label="Also known as">{items}</ul>'


def specimen_plate(project, number, tags, function_detail, grid, cutout, variants=None):
    from build_scoreboard import trophy_count
    pid, name, url = (
        escape(project["id"]),
        escape(project["name"]),
        escape(project["url"]),
    )
    art = project.get("artwork")
    specimen = notes = ""
    label = specimen_label(project, tags, number)
    if art:
        src = cutout["path"] if cutout else art["path"]
        candidates = (variants or {}).get(src)
        responsive = (
            f' srcset="{escape(", ".join(f"{path} {width}w" for path, width in candidates))}" sizes="{PLATE_SIZES}"'
            if candidates else ""
        )
        geometry = specimen_geometry(art, cutout.get("bbox") if cutout else None)
        bbox = " ".join(str(v) for v in geometry["bbox"])
        stage_style = (
            f'--plate-height:{geometry["height"]:.6f};'
            f'--plate-offset:{geometry["offset"] * 100:.6f}%;'
            f'--plate-ground:{geometry["ground"] * 100:.6f}%;'
            f'--plate-fade-start:{geometry["fade_start"] * 100:.6f}%;'
            f'--plate-fade-end:{geometry["fade_end"] * 100:.6f}%'
        )
        specimen = (
            f'<div class="plate-specimen"><div class="plate-field" data-seed="{pid[:16]}" data-cutout="{"true" if cutout else "false"}" data-bbox="{bbox}">'
            f'<div class="plate-stage" style="{stage_style}" data-height="{geometry["height"]:.6f}" data-ground="{geometry["ground"]:.6f}">'
            f'<figure class="specimen-art plate-art"><img src="{escape(src)}"{responsive} alt="{escape(art["alt"])}" width="{art["width"]}" height="{art["height"]}" loading="lazy" decoding="async"></figure></div></div>{label}</div>'
        )
        features = project.get("function_summary", {}).get("features", [])[:2]
        if features:
            items = "".join(
                f'<li class="plate-note"><span class="plate-crop{" is-tiny" if i else ""}" data-crop="{i}" aria-hidden="true"></span><div><span class="plate-index">{i + 1:02d} / Feature note</span>'
                f'<strong>{escape(f["title"])}</strong><p>{escape(f["text"])}</p><a class="feature-source" href="{escape(f["source_url"])}">Feature source ↗</a></div></li>'
                for i, f in enumerate(features)
            )
            notes = f'<ol class="plate-notes" aria-label="Feature notes">{items}</ol>'
        label = ""
    host = repository_host(project["url"])
    departure_label = f"{name}" + (f" on {host}" if host else "")
    address = escape(project["url"].removeprefix("https://").removeprefix("http://"))
    return (
        f'<div class="specimen-interior specimen-plate{"" if art else " without-art"}" aria-labelledby="name-{pid}">'
        f'<div class="plate-heading"><span class="plate-index">Field notes / {number:03d}</span><span class="plate-index">{name}</span></div>'
        f'{plate_aliases(project)}'
        f'<div class="plate-study"><svg class="plate-leaders" aria-hidden="true"></svg>'
        f'<div class="plate-function"><span class="sheet-label">I / Function</span><p class="record-description{" is-long" if len(project["description"]) > 90 else ""}">{escape(project["description"])}</p>{trophy_count(project)}{function_detail}</div>'
        f"{specimen}{notes}{label}</div>"
        + f'<div class="plate-grid">{grid}'
        f'<nav class="plate-departure" aria-label="Explore {name}"><span class="sheet-label">Explore</span><a href="{url}"><span>{departure_label}</span>'
        f'<span class="departure-arrow" aria-hidden="true">↗</span></a><span class="departure-address">{address}</span></nav></div></div>'
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


def hn_window(catalog, project):
    """The shared HN chart window; older catalogs fall back to the paired star window."""
    if catalog.get("hn_window"):
        return catalog["hn_window"]
    paired = project.get("star_history") or {}
    if paired.get("chart_url"):
        months = paired["last_good"]["months"]
        return {"first": months[0], "last": months[-1], "monthly_maximum": paired.get("hn_monthly_maximum")}
    return None


def plate_html(project, categories, catalog, number, cutouts, variants=None):
    github = project["github"]
    created = (
        github["created_at"][:10] if github and github.get("created_at") else "Unknown"
    )
    tags = " / ".join(
        f'<a class="tag" data-category="{escape(cid)}" href="{escape(source_url(catalog, "README.source.md", "#" + category_id(categories[cid])))}">{escape(categories[cid])}</a>'
        for cid in project["categories"]
    )
    summary = project.get("function_summary")
    function_detail = ""
    if summary:
        sources = " / ".join(
            f'<a href="{escape(item["url"])}">{escape(item["title"])}</a>'
            for item in summary["sources"]
        )
        function_detail = f'<div class="function-detail"><p>{highlight_name(summary["text"], project["name"])}</p><p class="function-provenance">{sources} · Reviewed <span class="metric-value">{escape(summary["checked_at"])}</span></p></div>'
    good_release = (
        ((project.get("signals") or {}).get("release") or {}).get("last_good") or {}
    ).get("value")
    release = (
        (good_release["published_at"][:10], good_release["tag_name"])
        if good_release
        else None
    )
    freshness = metrics_freshness(github, catalog.get("metrics_as_of"))
    history = project.get("history", [])
    pushed_date = github["pushed_at"][:10] if github and github.get("pushed_at") else None
    events = history_view.timeline_events(history)
    grid = plate_grid.render(
        project,
        timeline_html=timeline(created, release, pushed_date, events) if github or events else "",
        history_html=history_view.evidence(history),
        freshness=freshness,
        hn_window=hn_window(catalog, project),
        activity=project.get("_collection_events", ()),
    )
    return specimen_plate(
        project, number, tags, function_detail, grid, (cutouts or {}).get(project["id"]), variants
    )


def project_html(project, categories, catalog, number=0, cutouts=None, position=None, variants=None):
    """A ledger row holding its specimen plate."""
    position = number if position is None else position
    pid = escape(project["id"])
    github = project["github"]
    license_text = (github["license"] if github else None) or ""
    inline_chart = ""
    if project["hn"]:
        attention = project["hn"]
        broad = "broad_total_stories" in attention
        count = attention["broad_total_stories"] if broad else attention["total_stories"]
        label = "possible matches" if broad else "matched stories"
        inline_chart = (f'<img class="name-sparkline" src="{escape(attention["chart_url"])}" width="80" height="16" '
                        f'alt="HN {label} / past 2y" title="HN: {count} {label} / past 2y" loading="lazy">')
    leader_categories = project.get("leader_categories", [])
    interior = plate_html(project, categories, catalog, number, cutouts, variants)
    return f'''<article class="project-card" data-leader="{"true" if leader_categories else "false"}" id="project-{pid}" data-project-id="{pid}">
 <details class="specimen-drawer">
  <summary><span class="folio" title="Position in current results" aria-hidden="true">{position:03d}</span><span class="name-cell"><span class="specimen-name" id="name-{pid}">{split_name(project["name"])}</span>{inline_chart}</span><span class="description">{escape(project["description"])}</span><span class="license-readout">{escape(license_text)}</span><span class="drawer-sign" aria-hidden="true"></span></summary>
{interior}
 </details>
</article>'''


def catalog_script_url(code):
    """Use identical runtime bytes as the cache identity across generated routes."""
    return "catalog.js?v=" + hashlib.sha256(code.encode("utf-8")).hexdigest()


def readme_about(root):
    """About-sheet copy kept in the README: the intro points and the other awesome lists."""
    source = (Path(root) / "README.source.md").read_text(encoding="utf-8")
    intro = source.split("\n---", 1)[1].split("\n## ", 1)[0]
    points = [line[2:].strip() for line in intro.splitlines()
              if line.startswith("- ") and "Visit the catalog homepage" not in line]
    others = []
    section = source.split("\n## Other Awesome", 1)
    for line in (section[1].split("\n## ", 1)[0].splitlines() if len(section) > 1 else []):
        match = re.fullmatch(r"- \[([^\]]+)\]\((https?://[^)\s]+)\)(?: -- (.+))?", line.strip())
        if match:
            name, url, note = match.groups()
            others.append(f'<li><a href="{escape(url)}">{escape(name)}</a>{" · " + escape(note) if note else ""}</li>')
    return points, others


def render_html(catalog, script_url="catalog.js", root=ROOT):
    """The Catalog as one screen: category rail, project list, and one pane for jars, a plate or a sheet."""
    from build_draw_archive import DESCRIPTION as SPOTLIGHT
    from build_observatory import DESCRIPTION as OBSERVATORY
    from build_scoreboard import DESCRIPTION as SCOREBOARD

    count = len(catalog["projects"])
    rail = f'<li><a href="./" data-category=""><span>All</span><span class="n">{count}</span></a></li>' + "".join(
        f'<li><a href="?category={escape(c["id"])}" data-category="{escape(c["id"])}"><span>{escape(c["name"])}</span><span class="n">{c["count"]:02d}</span></a></li>'
        for c in sorted(catalog["categories"], key=lambda c: c["name"].lower())
    )

    def options(pairs):
        return "".join(f'<option value="{escape(value)}">{escape(label)}</option>' for value, label in pairs)

    licenses = sorted({p["github"]["license"] for p in catalog["projects"] if p["github"] and p["github"]["license"]})
    alternatives = sorted({a["name"] for p in catalog["projects"] for a in p["alternatives"]})
    observed = {
        field: sorted({f["value"] for p in catalog["projects"] for f in p.get("deployment", {}).get(field, [])})
        for field in ("run_modes", "install_methods")
    }
    # A select's first option carries its title ("Pushed: any date"); app.js keeps the title on a chosen value.
    selects = (
        f'<select id="f-sort" name="sort" data-title="Sort" aria-label="Sort projects">{options([("match", "Sort: match or stars"), ("name", "Name A–Z"), ("stars", "Most stars"), ("pushed", "Latest push")])}</select>'
        f'<select id="f-window" name="window" data-title="Pushed" aria-label="Repository push window">{options([("all", "Pushed: any date"), ("recent", "Within 90 days of snapshot"), ("older", "More than 2 years before snapshot"), ("unknown", "Push date unknown")])}</select>'
        f'<select id="f-alternative" name="alternative" data-title="Alternative to" aria-label="Reviewed alternative to">{options([("", "Alternative to: any")] + [(v, v) for v in alternatives])}</select>'
        f'<select id="f-license" name="license" data-title="License" aria-label="Detected license">{options([("all", "License: any"), ("known", "Detected license available"), ("unknown", "License unknown")] + [(v, v) for v in licenses])}</select>'
        f'<select id="f-language" name="language" data-title="Repository language" aria-label="Detected repository language">{options([("", "Repository language: any"), ("unknown", "Unknown"), ("empty", "None detected")] + [(v, v) for v in sorted({name for p in catalog["projects"] for name in p.get("languages") or []})])}</select>'
        f'<select id="f-run" name="run_mode" data-title="Runs as" aria-label="Reviewed run mode">{options([("", "Runs as: any"), ("unknown", "Not recorded")] + [(v, deployment.RUN_MODES[v]) for v in observed["run_modes"]])}</select>'
        '<details class="rail-more"><summary><span class="when-closed">More filters</span><span class="when-open">Less filters</span></summary>'
        f'<select id="f-install" name="install_method" data-title="Install" aria-label="Reviewed install method">{options([("", "Install: any"), ("unknown", "Not recorded")] + [(v, deployment.INSTALL_METHODS[v]) for v in observed["install_methods"]])}</select>'
        f'<select id="f-metrics" name="metrics" data-title="Cached metrics" aria-label="Cached repository metrics">{options([("all", "Cached metrics: any"), ("present", "Present"), ("missing", "Missing")])}</select>'
        '<input id="f-stars" name="stars" type="number" min="0" step="1" placeholder="Min. stars: any" aria-label="Minimum GitHub stars">'
        '<label class="rail-date"><span>Pushed since</span><input id="f-pushed" name="pushed" type="date"></label></details>'
    )

    def star_order(project):
        stars = (project.get("github") or {}).get("stars")
        known = type(stars) is int and stars >= 0
        name = "".join(c for c in unicodedata.normalize("NFKD", project["name"])
                       if not "̀" <= c <= "ͯ").lower()
        return (not known, -stars if known else 0, name, project["id"])

    def row(project, position):
        pid = escape(project["id"])
        spark = ""
        if project["hn"]:
            attention = project["hn"]
            broad = "broad_total_stories" in attention
            total = attention["broad_total_stories"] if broad else attention["total_stories"]
            label = "possible matches" if broad else "matched stories"
            spark = (f'<img class="row-spark" src="{escape(attention["chart_url"])}" width="80" height="16" '
                     f'alt="HN {label} / past 2y" title="HN: {total} {label} / past 2y" loading="lazy">')
        leader = "true" if project.get("leader_categories") else "false"
        return (f'<li class="row" data-id="{pid}" data-leader="{leader}"><a href="records/{pid}.html">'
                f'<span class="row-n" aria-hidden="true">{position:03d}</span>'
                f'<span class="row-title"><span class="specimen-name">{split_name(project["name"])}</span>{spark}</span>'
                f'<span class="row-desc">{escape(project["description"])}</span></a></li>')

    rows = "\n".join(row(p, i) for i, p in enumerate(sorted(catalog["projects"], key=star_order), 1))

    # About: everything that is not the catalog — links, the data method, the README's own sections.
    points, others = readme_about(root)
    signal_projects = [p for p in catalog["projects"] if p.get("signals")]
    coverage = ""
    if signal_projects:
        notes = []
        for provider, label in (("release", "Release"), ("scorecard", "Scorecard"), ("languages", "Repository languages")):
            checked = sum(bool((p["signals"].get(provider) or {}).get("checked_at")) for p in signal_projects)
            values = sum(bool((p["signals"].get(provider) or {}).get("last_good")) for p in signal_projects)
            notes.append(f"{label}: {values} cached results / {checked} checked")
        coverage = ('<ul class="coverage-notes">' + "".join(f"<li>{item}</li>" for item in notes)
                    + f"<li>{len(signal_projects)} mapped GitHub repositories.</li>"
                    + f"<li>Collection snapshot {escape(catalog.get('signals_collected_at'))}.</li></ul>"
                    + '<p><a href="data/project_signals.json">Release, Scorecard and language evidence</a></p>')
    star_note = ""
    if any(p.get("star_history") for p in catalog["projects"]):
        star_note = "<li>GitHub stars / past 2y: Stars per month that remained at last successful fetch.</li>"
        coverage += '<p><a id="star-evidence" href="data/star_history.json">GitHub star-history evidence</a></p>'
    sha = catalog.get("source_sha")
    revision = f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else "Local preview (revision not supplied)"
    scoreboard_items = (['<a href="scoreboard/snapshot.json" download>Download snapshot</a>'] if catalog.get("scoreboard_edition") else []) + [
        f'<a href="{REPOSITORY}/blob/main/site/SCOREBOARD.md">Scoreboard method</a>']
    pages = (
        f'<li><a href="#observatory">Observatory</a>: Metrics collection date: <time>{escape(catalog["metrics_as_of"])}</time> UTC</li>'
        f'<li><a href="#scoreboard">Scoreboard</a>: {" · ".join(scoreboard_items)}</li>'
        f'<li><a href="#spotlight">Spotlight</a>: <a href="spotlight/draws.json" download>Download draw records</a> · <a href="{REPOSITORY}/blob/main/site/WEEKLY-DRAWS.md">Draw contract</a></li>'
    )
    backgrounds = [quote(path, safe="/") for path in catalog.get("footer_backgrounds", [])]
    sizes = catalog.get("footer_background_sizes", [])
    size = sizes[0] if sizes else (2048, 682)
    art = (f'<img class="about-art" data-footer-background data-background-sizes="{escape(json.dumps(sizes))}" data-backgrounds="{escape(json.dumps(backgrounds))}" '
           f'src="{escape(backgrounds[0])}" width="{size[0]}" height="{size[1]}" alt="" loading="lazy" decoding="async">') if backgrounds else ""
    about = f'''<div class="about">
 <section class="about-intro"><h2 class="about-title">About</h2>
  <ul class="about-points">{"".join(f"<li>{escape(p)}</li>" for p in points)}</ul>
  <p class="about-actions"><a class="about-primary" href="{escape(source_url(catalog, "CONTRIBUTING.md"))}">Submit a project</a><a href="{REPOSITORY}">GitHub repository</a><a href="https://buymeacoffee.com/jumpermcp.dev">Support the list with a coffee</a></p></section>
 <section class="about-data" id="method" aria-labelledby="method-heading"><h3 class="about-kicker" id="method-heading">About the data</h3><div class="about-colophon"><div><h4>Collection</h4><ul><li>Registry IDs come from canonical URLs</li><li>List numbers show position in current results</li><li>Folio numbers show alphabetical position</li><li>Search results list the strongest matching field first, then by name</li><li>Bold: Top-3 per category (GitHub stars)</li><li>Specimen illustrations are original artwork</li></ul></div><div><h4>Evidence</h4><ul><li>Licenses: GitHub license metadata.</li><li>Repository dates refer to GitHub activity</li><li>HN charts: possible title/URL matches; red foreground: matched stories. Shared cube-root scale / 2 years</li>{star_note}<li>GitHub release: follows publisher</li><li>Scorecard: reports automated security-practice checks (combining aggregate, scored/returned coverage, scan date and reasons)</li><li>Stale: Old scan/cache or a retained result after an unsuccessful check</li></ul>{coverage}<p><a id="hn-evidence" href="data/hn_evidence.json">HN evidence</a> / <a href="data/alternatives.json">Comparison evidence</a> / <a href="data/deployment_evidence.json">Where it runs (data)</a> / <a href="catalog.json">Catalog JSON</a></p></div></div></section>
 <section class="about-pages" aria-labelledby="pages-heading"><h3 class="about-kicker" id="pages-heading">Pages and their data</h3><ul>{pages}</ul></section>
 <section class="about-others" aria-labelledby="others-heading"><h3 class="about-kicker" id="others-heading">Other awesome lists</h3><ul>{"".join(others)}</ul></section>
 <p class="about-baseline"><span>Source revision: {revision} | {count} Projects</span><span>List: <a href="{escape(source_url(catalog, "LICENSE.md"))}">CC0-1.0</a></span></p>
 {art}
</div>'''
    cabinet = (root / "site/cabinet.html").read_text(encoding="utf-8").replace("__SOURCE_SHA__", escape(catalog.get("source_sha") or ""))
    return f'''<!doctype html>
<html lang="en">
<head>
 <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
 <meta name="description" content="A natural-history field guide to software named Open, with searchable project records, repository data, and reviewed comparisons.">
 <meta name="color-scheme" content="light"><title>Awesome Open* Catalog</title>{origin_trial_meta()}
 <link rel="icon" href="brand/favicon.ico" sizes="16x16 32x32 48x48">
 <link rel="icon" type="image/png" href="brand/fruit-16.png" sizes="16x16">
 <link rel="icon" type="image/png" href="brand/fruit-32.png" sizes="32x32">
 <link rel="stylesheet" href="{font_asset_url('vendor/fonts.css', root)}"><link rel="stylesheet" href="{font_asset_url('tokens.css', root)}"><link rel="stylesheet" href="{font_asset_url('styles.css', root)}">
 <link rel="stylesheet" href="{content_url("cabinet.css", root / "site/cabinet.css")}"><link rel="stylesheet" href="{content_url("app.css", root / "site/app.css")}">
 <script src="{content_url("search.js", root / "site/search.js")}" defer></script>
 <script src="{escape(script_url)}" defer></script>
 <script src="{content_url("cabinet.js", root / "site/cabinet.js")}" defer></script>
 <script src="{content_url("app.js", root / "site/app.js")}" defer></script>
 <script src="{content_url("webmcplet/webmcplet.js", root / "webmcplet/webmcplet.js")}" data-webmcplet-src="webmcplet/list.json?v={hashlib.sha256(webmcplet_list(catalog).encode("utf-8")).hexdigest()}" data-webmcplet-title="Awesome Open*" data-webmcplet-assistant="on" data-webmcplet-assistant-tools="cabinet_arrange cabinet_compare cabinet_find cabinet_inspect" defer></script>
</head>
<body class="app">
<a class="skip-link" href="#rows">Skip to the project list</a>
<div class="app-body">
 <nav class="rail" aria-label="Categories and filters">
  <a class="rail-mark" href="./" tabindex="-1" aria-hidden="true"><img src="brand/botanical-128.png" alt="" width="72" height="72"></a>
  <ul class="rail-cats" id="rail-cats">{rail}</ul>
  <form class="rail-filters" id="filters" aria-label="Filter projects" hidden>{selects}<button id="reset" type="button" disabled>Reset filters <span aria-hidden="true">↺</span></button></form>
  <a class="rail-about" id="rail-about" href="#about">About</a>
 </nav>
 <main class="list" id="catalog" tabindex="-1" aria-labelledby="list-brand">
  <header class="list-head">
   <h1 class="list-brand" id="list-brand"><a href="./" aria-label="Awesome Open home"><span>Awesome Open<span aria-hidden="true">*</span></span></a></h1>
   <form class="list-search" id="search-form" role="search" hidden><label class="visually-hidden" for="search">Search projects</label><input id="search" name="q" type="search" autocomplete="off" maxlength="500" aria-describedby="search-help"><button type="submit" aria-label="Search projects" title="Search projects"><img src="brand/search-loupe.png" width="24" height="24" alt=""></button><span id="search-help" class="visually-hidden">Search names, descriptions, and reviewed alternative names. Results update as you type.</span></form>
   <p class="visually-hidden" id="list-count" role="status" aria-live="polite" aria-atomic="true">{count} projects</p>
  </header>
  <p class="list-notice" id="list-notice" role="status" hidden></p>
  <noscript><p class="no-script">All {count} projects are listed below. Each opens its full record. Enable JavaScript for search, filters and the plate view.</p></noscript>
  <ol class="rows" id="rows" tabindex="-1">
{rows}
   <li class="rows-empty" id="empty" hidden></li>
   <li class="rows-end" aria-hidden="true"><img id="end-mark" src="brand/fruit-96.png" data-default="brand/fruit-96.png" alt="" width="96" height="96" loading="lazy"></li>
  </ol>
 </main>
 <section class="pane" id="pane" aria-label="Specimen plate">
  <div class="pane-rest" id="pane-rest"><!-- jar-hall --></div>
  <div class="pane-about" id="pane-about" hidden>
   <div class="pane-head about-head"><nav class="riders" aria-label="Awesome Open pages"><a href="#about" data-sheet="about" aria-current="page">About</a><a href="observatory/" data-sheet="observatory" title="{escape(OBSERVATORY)}">Observatory</a><a href="scoreboard/" data-sheet="scoreboard" title="{escape(SCOREBOARD)}">Scoreboard</a><a href="spotlight/" data-sheet="spotlight" title="{escape(SPOTLIGHT)}">Spotlight</a></nav><button class="about-close" id="about-close" type="button" aria-label="Close About" title="Close (Esc)">×</button></div>
   <div class="pane-scroll about-scroll" id="about-scroll" tabindex="-1">
{about}
   </div>
   <iframe class="pane-frame" id="pane-frame" title="" hidden></iframe>
  </div>
  <div class="pane-plate" id="pane-plate" hidden>
   <div class="pane-head">
    <div class="pane-title"><p class="pane-status" id="plate-status" role="status" aria-live="polite"></p><h2 id="plate-name"></h2></div>
    <div class="pane-tools"><span class="pane-stepper"><button id="plate-prev" type="button" aria-label="Previous project" title="Previous project (←)">‹</button><span id="plate-position"></span><button id="plate-next" type="button" aria-label="Next project" title="Next project (→)">›</button></span><button id="plate-cabinet" class="pane-action" type="button" aria-pressed="false">Compare</button><button id="plate-close" class="pane-close" type="button" aria-label="Close plate" title="Close plate (Esc)">×</button></div>
   </div>
   <div class="pane-scroll" id="pane-scroll" tabindex="-1"></div>
  </div>
 </section>
</div>
{cabinet}
<script id="catalog-data" type="application/json" data-source-sha="{escape(catalog.get("source_sha") or "")}" data-search-text="search-text.json?v={hashlib.sha256(search_text(catalog).encode("utf-8")).hexdigest()}">{json_for_html(search_index(catalog))}</script>
</body></html>
'''


def render_record(project, categories, catalog, number, cutouts=None, script_url="catalog.js", root=ROOT, variants=None):
    """A native no-JS record is also the same-origin fetch-on-open source.

    Keep asset paths identical to the ledger via the explicit base. The loader
    resolves them against this base before adopting only the validated plate.
    """
    pid = escape(project["id"])
    name = escape(project["name"])
    card = project_html(project, categories, catalog, number, cutouts, position=1, variants=variants)
    card = card.replace('<details class="specimen-drawer">', '<details class="specimen-drawer" open>', 1)
    sha = catalog.get("source_sha")
    revision = f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else "Local preview (revision not supplied)"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<base href="../"><meta name="color-scheme" content="light"><title>{name} · Awesome Open*</title>
<meta name="description" content="{escape(project['description'])}">
<link rel="icon" href="brand/favicon.ico"><link rel="stylesheet" href="{font_asset_url('vendor/fonts.css', root)}"><link rel="stylesheet" href="{font_asset_url('tokens.css', root)}">
<link rel="stylesheet" href="{font_asset_url('styles.css', root)}"><link rel="stylesheet" href="{content_url('observatory/observatory.css', root / 'site/observatory.css')}">
<script src="{escape(script_url)}" defer></script></head>
<body class="observatory record-page"><a class="skip-link" href="records/{pid}.html#record">Skip to project record</a>
<div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="./">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Field guide"><a href="#catalog">Ledger</a><a href="#method">About</a><a href="observatory/">Observatory</a><a href="scoreboard/">Scoreboard</a><a href="spotlight/">Weekly draws</a></nav></header></div>
<main class="obs-shell" id="record" tabindex="-1"><section class="obs-hero"><p><span class="obs-label">Project record</span></p><h1>{name}</h1></section>
<aside class="obs-finding"><p>Full catalog record, evidence and sources. <a href="#project-{pid}">Open this project in the Catalog</a>. Use your browser’s Print command to print this record.</p></aside>
{card}
<div class="obs-closing-mark" aria-hidden="true"><img class="obs-logo" src="brand/fruit-96.png" width="96" height="96" alt=""></div></main>
<footer class="obs-footer"><div class="obs-shell"><p>Awesome Open* / Project record</p><ul class="obs-footer-links"><li><a href="./">Return to project ledger</a></li><li><a href="{REPOSITORY}">GitHub</a></li><li>Source revision: {revision}</li></ul></div></footer></body></html>'''


def build(output, source_sha=None, root=ROOT, qr_cache=None, scoreboard_preview=False):
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
        history=project_history.load_optional(root / project_history.PATH),
    )
    display = display_hn_evidence(source, evidence)
    if evidence.get("months"):
        catalog["hn_window"] = {
            "first": evidence["months"][0],
            "last": evidence["months"][-1],
            "monthly_maximum": display["shared_monthly_maximum"],
        }
    footer_assets = discover_footer_art(root)
    catalog["footer_backgrounds"] = list(footer_assets)
    catalog["footer_background_sizes"] = [list(size) for size in footer_assets.values()]
    attach_specimen_art(catalog, root)
    attach_category_art(catalog, root)
    cutouts = attach_specimen_cutouts(catalog, root)
    variants = attach_specimen_variants(root)
    import weekly_draw
    draws = weekly_draw.load(root / weekly_draw.PATH)
    catalog["weekly_draws"] = draws
    import weekly_scoreboard
    scoreboard = weekly_scoreboard.load(root / weekly_scoreboard.PATH)
    if scoreboard_preview:
        weekly_scoreboard.validate_evidence(evidence)
        scoreboard = weekly_scoreboard.snapshot(catalog, evidence, date.fromisoformat(catalog["metrics_as_of"]), source_sha)
    weekly_scoreboard.attach(catalog, scoreboard)
    if scoreboard_preview:
        for project in catalog["projects"]:
            for award in project.get("scoreboard_trophies", []):
                award["preview"] = True
    catalog["scoreboard_edition"] = ({"week": scoreboard["week"], "recorded_on": scoreboard["recorded_on"],
                                     "preview": scoreboard_preview} if scoreboard else None)
    # HTML and its drawer runtime must not share a cache key with older code.
    # Hash content, not snapshots: evidence-only publishes can reuse the script.
    runtime = (root / "site/catalog.js").read_text(encoding="utf-8")
    script_url = catalog_script_url(runtime)
    ledger = render_html(catalog, script_url=script_url, root=root)
    # Validate charts before touching generated files. The renderer is shared with README.
    charts = {}
    for project in display["projects"]:
        if hn.chart_displayable(project):
            slug = project["slug"]
            charts[slug + ".svg"] = hn.svg(project, display)
            charts[slug + "-evidence.html"] = hn.evidence_html(project, display)
            if "broad_story_count" in project:
                charts[slug + "-comparison.svg"] = hn.svg(project, display, comparison=True)
    star_charts = {
        p["star_history"]["chart_url"]: star_history.svg(p)
        for p in catalog["projects"]
        if p.get("star_history", {}).get("chart_url")
    }
    codes = qr_codes(catalog["projects"], qr_cache)
    assets = {
        "styles.css": (root / "site/styles.css").read_text(encoding="utf-8"),
        "catalog.js": runtime,
        "search.js": (root / "site/search.js").read_text(encoding="utf-8"),
        "cabinet.js": (root / "site/cabinet.js").read_text(encoding="utf-8"),
        "cabinet.css": (root / "site/cabinet.css").read_text(encoding="utf-8"),
        "app.css": (root / "site/app.css").read_text(encoding="utf-8"),
        "app.js": (root / "site/app.js").read_text(encoding="utf-8"),
    }
    assets["tokens.css"] = (root / "site/design/tokens.css").read_text(encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "site/vendor/serif-preview", output / "vendor/serif-preview", dirs_exist_ok=True)
    (output / "index.html").write_text(ledger, encoding="utf-8")
    records = output / "records"
    shutil.rmtree(records, ignore_errors=True)
    records.mkdir()
    categories = {c["id"]: c["name"] for c in catalog["categories"]}
    activity_context = collection_log.load(root)
    collection_dir = output / "collection"
    shutil.rmtree(collection_dir, ignore_errors=True)
    collection_dir.mkdir()
    for number, project in enumerate(catalog["projects"], 1):
        events = collection_log.derive(project, activity_context)
        (collection_dir / (project["id"] + ".json")).write_text(
            compact_json(collection_log.payload(project, events, activity_context)), encoding="utf-8")
        project = dict(project, _collection_events=events)
        (records / (project["id"] + ".html")).write_text(
            render_record(project, categories, catalog, number, cutouts, script_url=script_url, root=root, variants=variants), encoding="utf-8"
        )
    (output / "catalog.json").write_text(compact_json(published_catalog(catalog)), encoding="utf-8")
    (output / "data").mkdir(exist_ok=True)
    (output / "data/deployment_evidence.json").write_text(compact_json({
        "schema_version": 1,
        "projects": {p["id"]: p["deployment"] for p in catalog["projects"] if p.get("deployment")},
    }), encoding="utf-8")
    (output / "search-text.json").write_text(search_text(catalog), encoding="utf-8")
    (output / "webmcplet").mkdir(exist_ok=True)
    (output / "webmcplet/list.json").write_text(webmcplet_list(catalog), encoding="utf-8")
    shutil.copyfile(root / "webmcplet/webmcplet.js", output / "webmcplet/webmcplet.js")
    for name, content in assets.items():
        (output / name).write_text(content, encoding="utf-8")
    shutil.rmtree(output / "assets/hn", ignore_errors=True)
    (output / "assets/hn").mkdir(parents=True, exist_ok=True)
    for filename, chart in charts.items():
        (output / "assets/hn" / filename).write_text(chart, encoding="utf-8")
    shutil.rmtree(output / "assets/stars", ignore_errors=True)
    (output / "assets/stars").mkdir(parents=True, exist_ok=True)
    for path, chart in star_charts.items():
        (output / path).write_text(chart, encoding="utf-8")
    shutil.rmtree(output / "assets/qr", ignore_errors=True)
    (output / "assets/qr").mkdir(parents=True, exist_ok=True)
    for path, code in codes.items():
        (output / path).write_text(code, encoding="utf-8")
    (output / "data").mkdir(exist_ok=True)
    evidence_files = ["alternatives.json", "hn_evidence.json"]
    if (root / project_history.PATH).exists():
        evidence_files.append("project_history.json")
    else:
        (output / project_history.PATH).unlink(missing_ok=True)
    if (root / "data/star_history.json").exists():
        evidence_files.append("star_history.json")
    else:
        (output / "data/star_history.json").unlink(missing_ok=True)
    if optional is not None:
        evidence_files.append("project_signals.json")
    else:
        (output / "data/project_signals.json").unlink(missing_ok=True)
    for name in evidence_files:
        document = json.loads((root / "data" / name).read_text(encoding="utf-8"))
        if name == "hn_evidence.json":
            document = published_hn.publish(document)
        (output / "data" / name).write_text(compact_json(document), encoding="utf-8")
    (output / "vendor").mkdir(exist_ok=True)
    for name in ("fonts.css", "FONT-LICENSE.txt", "FONT-PROVENANCE.json", "commit-mono.woff2"):
        shutil.copyfile(root / "site/vendor" / name, output / "vendor" / name)
    for old in (
        "serif-preview.js", "serif-preview.css", "vendor/fraunces.woff2",
        "vendor/serif-preview/instrument.woff2",
        "vendor/serif-preview/instrument-METADATA.pb",
        "vendor/serif-preview/instrument-OFL.txt",
        "motion.js",
        "vendor/gsap.min.js",
        "vendor/ScrollTrigger.min.js",
        "vendor/GSAP-PROVENANCE.txt",
        "standalone.html",
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
    shown = {cutouts[p["id"]]["path"] if p["id"] in cutouts else p["artwork"]["path"]
             for p in catalog["projects"] if "artwork" in p}
    for source in shown & variants.keys():
        for path, _ in variants[source][:-1]:
            (output / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / "site" / path, output / path)
    shutil.rmtree(output / "footer-backgrounds", ignore_errors=True)
    for asset in (*catalog["footer_backgrounds"], FOOTER_PATTERN):
        (output / asset).parent.mkdir(exist_ok=True)
        shutil.copyfile(root / "site" / asset, output / asset)
    (output / "brand").mkdir(exist_ok=True)
    for name in BRAND_ASSETS:
        shutil.copyfile(root / "site/brand" / name, output / "brand" / name)
    copy_category_art(catalog, root, output)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    from build_observatory import build as build_observatory

    build_observatory(catalog, evidence, output, root)
    from build_draw_archive import build as build_draw_archive
    build_draw_archive(catalog, draws, output, root)
    from build_scoreboard import build as build_scoreboard
    build_scoreboard(catalog, scoreboard, output, root, preview=scoreboard_preview)
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
    parser.add_argument(
        "--qr-cache",
        type=Path,
        help="Directory of permalink QR SVGs reused between builds (CI caches it)",
    )
    parser.add_argument("--scoreboard-preview", action="store_true", help="Explicit provisional Scoreboard from cached evidence; never saves a weekly edition")
    args = parser.parse_args()
    if args.production and args.scoreboard_preview:
        parser.error("Provisional Scoreboard is not a production edition")
    catalog = build(args.output, args.source_sha, qr_cache=args.qr_cache, scoreboard_preview=args.scoreboard_preview)
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

