"""Small, deterministic observatory view of the already-validated catalog.

No collectors, wall clock, inferred founding dates or synthetic history. The same
thin projection drives server-rendered tables and progressive browser filtering.
"""

from collections import Counter
from datetime import date, datetime, timezone
from font_assets import content_url, font_asset_url
import csv
from html import escape
import io
import json
from pathlib import Path
from build_catalog import canonical_url
import re
import shutil

REPOSITORY = "https://github.com/awesomeopen/awesome-open"
RECENCY = [
    ("0–30 days", 30),
    ("31–90 days", 90),
    ("91–365 days", 365),
    ("366–730 days", 730),
    ("Over 730 days", None),
]
AGES = [
    ("0–365 days", 365),
    ("366–1,826 days", 1826),
    ("1,827–3,653 days", 3653),
    ("Over 3,653 days", None),
]
CSV_FIELDS = [
    "id",
    "name",
    "url",
    "description",
    "categories",
    "github",
    "stars",
    "license",
    "created_at",
    "pushed_at",
    "release_at",
    "release_status",
    "release_checked_at",
    "metrics_as_of",
    "source_sha",
    "metrics_status",
    "metrics_last_success_at",
    "metrics_attempt_at",
    "metrics_attempt_status",
    "metrics_attempt_http_status",
    "metrics_attempt_reason",
]


def days_before(value, as_of):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?",
        value,
    ):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        day = parsed.astimezone(timezone.utc).date() if parsed.tzinfo else parsed.date()
        diff = (date.fromisoformat(as_of) - day).days
    except (ValueError, OverflowError):
        return None
    return diff if diff >= 0 else None


def histogram(projects, field, as_of, buckets):
    counts = [0] * (len(buckets) + 1)
    for project in projects:
        days = days_before(project.get(field), as_of)
        index = len(buckets)
        if days is not None:
            index = next(
                i
                for i, (_, limit) in enumerate(buckets)
                if limit is None or days <= limit
            )
        counts[index] += 1
    return [[label, counts[i]] for i, (label, _) in enumerate(buckets)] + [
        ["Unknown", counts[-1]]
    ]


def project_index(catalog):
    """Ship the short description only; no reviewed prose, raw Scorecard checks or complete signal objects."""
    rows = []
    seen = set()
    for project in catalog["projects"]:
        if project["id"] in seen:
            raise ValueError("Duplicate observatory project identity")
        seen.add(project["id"])
        github = project.get("github") or {}
        release = (project.get("signals") or {}).get("release") or {}
        good = release.get("last_good") or {}
        rows.append(
            dict(
                id=project["id"],
                name=project["name"],
                url=project["url"],
                description=project.get("description"),
                categories=list(dict.fromkeys(project["categories"])),
                github=bool(github) and github.get("status") != "unavailable",
                metrics_status=github.get("status", "fresh") if github else "unknown",
                metrics_last_success_at=github.get(
                    "last_success_at", catalog["metrics_as_of"]
                )
                if github
                else None,
                metrics_attempt_at=(github.get("last_attempt") or {}).get("at"),
                metrics_attempt_status=(github.get("last_attempt") or {}).get("status"),
                metrics_attempt_http_status=(github.get("last_attempt") or {}).get(
                    "http_status"
                ),
                metrics_attempt_reason=(github.get("last_attempt") or {}).get("reason"),
                stars=github.get("stars"),
                license=github.get("license"),
                created_at=github.get("created_at"),
                pushed_at=github.get("pushed_at"),
                release_at=good.get("value", {}).get("published_at"),
                release_status=release.get("status", "not checked"),
                release_checked_at=release.get("checked_at"),
            )
        )
    names = shared_names(rows)
    paired = {p["id"] for kind in ("identical", "variants") for g in names[kind] for p in g["projects"]}
    originals = {p["id"]: p for p in catalog["projects"]}
    for row in rows:
        art = originals[row["id"]].get("artwork")
        if row["id"] in paired and art:
            row["specimen"] = {**art, "path": "../" + art["path"]}
    return dict(
        schema_version=1,
        metrics_as_of=catalog["metrics_as_of"],
        source_sha=catalog.get("source_sha"),
        categories=[dict(id=c["id"], name=c["name"]) for c in catalog["categories"]],
        projects=rows,
    )


def reviewed_rhymes(catalog, path):
    """Validate a bounded editorial pronunciation map; never infer from aliases."""
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "language", "checked_at", "reviewed_by", "basis", "projects"}
    if not isinstance(data, dict) or set(data) != required or data["schema_version"] != 1:
        raise ValueError("Invalid name rhyme schema")
    if data["language"] != "en-US" or not isinstance(data["projects"], list):
        raise ValueError("Name rhymes require reviewed en-US readings")
    date.fromisoformat(data["checked_at"])
    for field in ("reviewed_by", "basis"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError("Missing name rhyme review basis")
    projects = {canonical_url(p["url"]): p for p in catalog["projects"]}
    result = {}
    for row in data["projects"]:
        fields = {"project_url", "name", "pronunciation", "key", "onset", "source_url"}
        if not isinstance(row, dict) or set(row) != fields or any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError("Invalid name rhyme record")
        url = canonical_url(row["project_url"])
        project = projects.get(url)
        if not project or project["id"] in result or project["name"] != row["name"]:
            raise ValueError("Unknown, duplicate or renamed rhyme identity")
        if not re.match(r"(?i)^open", row["name"]) or not row["source_url"].startswith("https://"):
            raise ValueError("Rhyme evidence needs an Open display name and HTTPS source")
        # ARPABET onset + last stressed vowel and following sounds. Initial scope
        # deliberately supports single-syllable remainders, with no guessed G2P.
        consonants = r"(?:B|CH|D|DH|F|G|HH|JH|K|L|M|N|NG|P|R|S|SH|T|TH|V|W|Y|Z|ZH)"
        vowels = r"(?:AA|AE|AH|AO|AW|AY|EH|ER|EY|IH|IY|OW|OY|UH|UW)1"
        if not re.fullmatch(consonants + r"(?: " + consonants + r")*", row["onset"]):
            raise ValueError("Invalid rhyme onset")
        if not re.fullmatch(vowels + r"(?: " + consonants + r")*", row["key"]):
            raise ValueError("Invalid stressed rhyme ending")
        if row["pronunciation"] != row["onset"] + " " + row["key"]:
            raise ValueError("Pronunciation does not match rhyme onset and ending")
        result[project["id"]] = {**row, "language": data["language"],
                                 "checked_at": data["checked_at"], "basis": data["basis"],
                                 "reviewed_by": data["reviewed_by"]}
    return result


def rhyming_names(projects):
    """Separate measure: reviewed spoken endings, never identity equivalence."""
    unique = {p["id"]: p for p in projects}
    buckets = {}
    for project in sorted(unique.values(), key=lambda p: (p["name"], p["id"])):
        rhyme = project.get("rhyme")
        if rhyme:
            buckets.setdefault((rhyme["language"], rhyme["key"]), []).append(project)
    groups = []
    for (language, key), rows in sorted(buckets.items()):
        if len({name_key(p["name"]) for p in rows}) < 2 or len({p["rhyme"]["onset"] for p in rows}) < 2:
            continue
        groups.append(dict(key=key, language=language, projects=rows))
    return dict(groups=groups, tool_count=sum(len(g["projects"]) for g in groups),
                reviewed_count=sum(bool(p.get("rhyme")) for p in unique.values()))


def rhyming_names_html(result):
    groups = []
    for group in result["groups"]:
        items = "".join(
            f'<li><a href="../#project-{escape(p["id"], quote=True)}">{escape(p["name"])}</a> '
            f'<span class="obs-muted">({escape(re.sub(r"^https?://(github\.com/)?", "", p["url"]))}) · {escape(p["rhyme"]["pronunciation"])}</span></li>'
            for p in group["projects"]
        )
        groups.append(f'<section class="obs-rhyme-group" data-rhyme-key="{escape(group["key"], quote=True)}"><h3 class="obs-label">{escape(group["key"])} · {len(group["projects"])} tools</h3><ul class="obs-rhyme-projects">{items}</ul></section>')
    body = "".join(groups) or '<p class="obs-muted">No reviewed rhyming names in this selection.</p>'
    return f'''<details id="rhyme-groups" class="obs-disclosure"><summary>Show names that rhyme <span class="obs-muted"><span id="rhyme-count">{result["tool_count"]}</span> tools · <span id="rhyme-group-summary">{len(result["groups"])} groups · {result["reviewed_count"]} reviewed readings</span></span></summary><div id="rhyme-group-list" data-ledger-base="../">{body}</div><p class="obs-muted">Pronunciations use ARPABET; 1 marks primary stress.</p></details>'''


# Unicode White_Space, shared with observatory.js (not Python/JS-specific \s).
NAME_WHITESPACE = re.compile(
    r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]"
)
# Matching-key separators: White_Space, hyphen and underscore. Other punctuation stays.
NAME_SEPARATORS = re.compile(NAME_WHITESPACE.pattern[:-1] + "_-]")
NAME_TAGS = ("Case", "Spacing", "Exact duplicates")


def name_key(name):
    """Lowercase (str.lower, matching JS toLowerCase) and drop separators."""
    return NAME_SEPARATORS.sub("", name.lower())


def name_anatomy(name):
    """Key characters and the separator run before each one (plus a trailing run)."""
    chars, gaps = [], [""]
    for char in name:
        if NAME_SEPARATORS.fullmatch(char):
            gaps[-1] += char
        else:
            chars.append(char)
            gaps.append("")
    return chars, gaps


def name_differences(names):
    parts = [name_anatomy(name) for name in names]
    chars, gaps = parts[0]
    at = lambda values, i: values[i] if i < len(values) else None
    return (
        [any(at(c, i) != chars[i] for c, _ in parts) for i in range(len(chars))],
        [any(at(g, i) != gaps[i] for _, g in parts) for i in range(len(gaps))],
    )


def shared_names(projects):
    """One matching key per displayed name, after canonical-ID deduplication.

    Equal keys form one group, so every project belongs to at most one group and
    groups never chain. Kinds and tags describe a group; they do not assign it.
    """
    unique = {p["id"]: p for p in projects}
    ordered = sorted(unique.values(), key=lambda p: (p["name"], p["id"]))
    buckets = {}
    for project in ordered:
        key = name_key(project["name"])
        if key:
            buckets.setdefault(key, []).append(project)
    identical, variants = [], []
    tags = dict.fromkeys(NAME_TAGS, 0)
    for rows in buckets.values():
        if len(rows) < 2:
            continue
        names = sorted({p["name"] for p in rows})
        group = dict(name=" / ".join(names), names=names, projects=rows, tags=[])
        if len(names) == 1:
            identical.append(group)
            continue
        chars, gaps = name_differences(names)
        group["tags"] = [
            tag
            for tag, present in zip(
                NAME_TAGS,
                [
                    any(chars),
                    any(gaps),
                    any(sum(p["name"] == name for p in rows) > 1 for name in names),
                ],
            )
            if present
        ]
        for tag in group["tags"]:
            tags[tag] += 1
        variants.append(group)
    identical.sort(key=lambda group: group["name"])
    variants.sort(key=lambda group: group["name"])
    identical_count = sum(len(group["projects"]) for group in identical)
    variant_count = sum(len(group["projects"]) for group in variants)
    return dict(
        identical=identical,
        variants=variants,
        tags=tags,
        tool_count=identical_count + variant_count,
        identical_tool_count=identical_count,
        variant_tool_count=variant_count,
    )


def marked_name(name, names):
    """Escape a displayed name, marking case and separator differences in its group."""
    if len(names) < 2:
        return escape(name)
    diff_chars, diff_gaps = name_differences(names)
    chars, gaps = name_anatomy(name)
    out = []
    for i, gap in enumerate(gaps):
        flagged = i < len(diff_gaps) and diff_gaps[i]
        if gap:
            out.append(
                f'<span class="name-diff name-gap">{escape(gap)}</span>'
                if flagged
                else escape(gap)
            )
        elif flagged:
            out.append('<span class="name-diff name-nogap" aria-hidden="true"></span>')
        if i < len(chars):
            char = escape(chars[i])
            out.append(
                f'<span class="name-diff">{char}</span>'
                if i < len(diff_chars) and diff_chars[i]
                else char
            )
    return "".join(out)


def repository_html(url):
    if url.startswith("https://github.com/"):
        owner, _, rest = url[len("https://github.com/") :].partition("/")
        return (
            f'<a class="obs-repo" href="{escape(url, quote=True)}"><span class="obs-repo-path">github.com/</span>'
            f'<span class="obs-repo-owner">{escape(owner)}</span><span class="obs-repo-path">/{escape(rest)}</span></a>'
        )
    return f'<a class="obs-repo" href="{escape(url, quote=True)}"><span class="obs-repo-path">{escape(re.sub(r"^https?://", "", url))}</span></a>'


def category_names(project, categories):
    return (
        ", ".join(categories.get(c, "Unknown") for c in project["categories"])
        or "Unknown"
    )


def metrics_cache_label(project):
    status = project.get("metrics_status", "unknown")
    observed = project.get("metrics_last_success_at")
    return status + (
        " · observed " + observed + " UTC"
        if observed
        else " · no successful observation"
    )


def name_plate_html(group, number, categories):
    names, rows = group["names"], group["projects"]
    plate_id = f"name-group-{number}"
    heading = '<span class="obs-name-sep">/</span>'.join(
        marked_name(name, names) for name in names
    )
    common = []
    category = category_names(rows[0], categories)
    if all(category_names(p, categories) == category for p in rows):
        common.append(category)
    license = rows[0]["license"] or "Unknown"
    if all((p["license"] or "Unknown") == license for p in rows):
        common.append(license)
    meta = f"<strong>{len(rows)} tools</strong>" + "".join(
        f' <span class="obs-tag">{tag}</span>' for tag in group["tags"]
    )
    if common:
        meta += " · In common: " + " · ".join(escape(value) for value in common)
    projects = []
    for p in rows:
        stars = None if p["stars"] is None else f"{p['stars']:,}"
        unknown = lambda value: (
            '<dd class="obs-unknown">Unknown</dd>'
            if value is None
            else f"<dd>{escape(str(value))}</dd>"
        )
        facts = (
            f"<dt>Category</dt><dd>{escape(category_names(p, categories))}</dd><dt>License</dt>{unknown(p['license'])}"
            f"<dt>GitHub stars</dt>{unknown(stars)}"
            f"<dt>Created</dt>{unknown(p['created_at'][:10] if p['created_at'] else None)}"
            f"<dt>Last push</dt>{unknown(p['pushed_at'][:10] if p['pushed_at'] else None)}"
            f"<dt>Metrics cache</dt><dd>{escape(metrics_cache_label(p))}</dd>"
        )
        label = escape(
            f"Catalog record for {p['name']} ({re.sub(r'^https?://(github.com/)?', '', p['url'])})",
            quote=True,
        )
        art = p.get("specimen")
        image = (
            f'<img class="obs-pair-art" src="{escape(art["path"], quote=True)}" '
            f'alt="{escape(art["alt"], quote=True)}" width="{art["width"]}" height="{art["height"]}" loading="lazy" decoding="async">'
            if art else ""
        )
        facts += (
            f'<dt>Catalog</dt><dd><a class="obs-record" href="../#project-{escape(p["id"], quote=True)}" '
            f'aria-label="{label}">OP-{escape(p["id"][:8].upper())}</a></dd>'
        )
        projects.append(
            f'<div class="obs-plate-project" data-project-id="{escape(p["id"], quote=True)}">'
            f'<div class="obs-plate-intro">{image}<div class="obs-plate-copy"><p class="obs-plate-name">{marked_name(p["name"], names)}</p>'
            f'{repository_html(p["url"])}<p class="obs-plate-desc">{escape(p.get("description") or "No short description in the catalog.")}</p></div></div>'
            f'<dl class="obs-plate-facts">{facts}</dl></div>'
        )
    return (
        f'<article class="shared-name-group" id="{plate_id}" data-name="{escape(group["name"], quote=True)}" aria-labelledby="{plate_id}-heading">'
        f'<header class="obs-plate-head"><h4 id="{plate_id}-heading">{heading}</h4><p class="obs-plate-meta">{meta}</p></header>'
        f'<div class="obs-plate-projects" style="--n: {len(rows)}">{"".join(projects)}</div></article>'
    )


NAME_KINDS = (
    ("identical", "Identical names", "Identical name"),
    ("variants", "Spelling variants", "Spelling variants"),
)


def shared_names_html(names, categories, selected, total, rhymes=""):
    clusters, bands, number = [], [], 0
    for key, label, legend in NAME_KINDS:
        groups = names[key]
        if groups and clusters:
            clusters.append('<span class="obs-tally-break"></span>')
        plates = []
        for group in groups:
            number += 1
            project_labels = [
                project["name"] + " (" + re.sub(r"^https?://(github\.com/)?", "", project["url"]) + ")"
                for project in group["projects"]
            ]
            title = "; ".join(project_labels)
            marks = "".join(
                f'<span class="obs-mark obs-mark-{key}" title="{escape(project_label, quote=True)}"></span>'
                for project_label in project_labels
            )
            clusters.append(
                f'<a class="obs-cluster" href="#name-group-{number}" title="{escape(title, quote=True)}" aria-label="{escape(group["name"], quote=True)}, {len(group["projects"])} tools, {legend.lower()}: {escape(title, quote=True)}">{marks}</a>'
            )
            plates.append(name_plate_html(group, number, categories))
        count = names[
            "identical_tool_count" if key == "identical" else "variant_tool_count"
        ]
        body = (
            "".join(plates)
            or f'<p class="obs-empty">No {legend.lower()} in this selection.</p>'
        )
        prefix = "identical" if key == "identical" else "variant"
        bands.append(
            f'<section class="obs-name-band" aria-labelledby="{prefix}-names-heading"><h3 id="{prefix}-names-heading" class="obs-label">{label} · {count} tools</h3><div id="{prefix}-name-groups">{body}</div></section>'
        )
    tally = (
        "".join(clusters)
        or '<p class="obs-muted">No shared names in this selection.</p>'
    )
    legend_items = []
    for (key, _, legend), count_key, count_id in zip(
        NAME_KINDS,
        ["identical_tool_count", "variant_tool_count"],
        ["identical-name-count", "variant-name-count"],
    ):
        zero = "" if names[count_key] else ' class="obs-zero"'
        legend_items.append(
            f'<li{zero}><span class="obs-mark obs-mark-{key}" aria-hidden="true"></span><span>{legend}</span><b id="{count_id}">{names[count_key]}</b></li>'
        )
    legend = "".join(legend_items)
    group_count = len(names["identical"]) + len(names["variants"])
    summary = f"{group_count} group{'' if group_count == 1 else 's'} · {names['tool_count']} tools"
    return f"""<section id="shared-names" class="obs-section obs-names" aria-labelledby="shared-names-heading"><h2 id="shared-names-heading"><span id="shared-name-count">{names["tool_count"]}</span> tools share a name</h2><p class="obs-lede">Each project counts once across these groups. <span id="selection-summary" role="status" aria-live="polite" aria-atomic="true">{selected:,}/{total:,} selected.</span></p><figure class="obs-tally" aria-label="One mark per tool that shares a name"><div id="name-tally" class="obs-tally-marks">{tally}</div><figcaption><ul class="obs-tally-legend">{legend}</ul></figcaption></figure><details id="name-groups" class="obs-disclosure"><summary>Show duplicate names <span id="name-group-summary" class="obs-muted">{summary}</span></summary><div id="name-group-bands">{"".join(bands)}</div><details id="name-method" class="obs-disclosure obs-method"><summary>How groups are formed</summary><ol><li>Projects are deduplicated by canonical project ID. Cross-listed projects count once.</li><li>Each displayed name gets one matching key: lowercased, with whitespace, hyphens and underscores removed.</li><li>Projects with the same key form one group. Each project belongs to at most one group, and a group needs at least two distinct projects.</li><li>Identical name: every project in the group displays the same name. Spelling variants: the displayed names differ.</li></ol><p>Tags name what differs in a variant group: Case, Spacing (whitespace, hyphen or underscore) and Exact duplicates. A group can carry several tags. Other punctuation, spelling and sound-alike names are not matched.</p></details></details>{rhymes}</section>"""


def aggregate(index, projects=None):
    projects = index["projects"] if projects is None else projects
    licenses = Counter(p["license"] for p in projects if p["license"])
    license_rows = sorted(licenses.items(), key=lambda pair: (-pair[1], pair[0]))
    license_rows.append(("Unknown", sum(not p["license"] for p in projects)))
    # Sorted by count; ties keep catalog order. Unknown stays last.
    categories = sorted(
        (
            [c["name"], sum(c["id"] in p["categories"] for p in projects)]
            for c in index["categories"]
        ),
        key=lambda row: -row[1],
    )
    known_ids = {c["id"] for c in index["categories"]}
    unmapped = sum(not (known_ids & set(p["categories"])) for p in projects)
    if unmapped:
        categories.append(["Unknown", unmapped])
    ranked = sorted(
        (p for p in projects if p["github"] and p["stars"] is not None),
        key=lambda p: (-p["stars"], p["name"], p["id"]),
    )
    stars = sum(p["stars"] for p in ranked) if ranked or not projects else None
    leaders = ranked[:10]
    concentration = sum(p["stars"] for p in leaders)
    star_rows = [[p["name"], p["stars"]] for p in leaders]
    if len(ranked) > 10:
        star_rows.append(["Other mapped projects", stars - concentration])
    return dict(
        shared_names=shared_names(projects),
        rhyming_names=rhyming_names(projects),
        total=len(projects),
        mapped=sum(p["github"] for p in projects),
        stars=stars,
        known_license=sum(bool(p["license"]) for p in projects),
        leader_count=len(leaders),
        concentration=round(100 * concentration / stars, 1) if stars else None,
        categories=categories,
        licenses=license_rows,
        star_rows=star_rows,
        ages=histogram(projects, "created_at", index["metrics_as_of"], AGES),
        pushes=histogram(projects, "pushed_at", index["metrics_as_of"], RECENCY),
        releases=histogram(projects, "release_at", index["metrics_as_of"], RECENCY),
    )


def coverage(catalog, hn):
    projects = catalog["projects"]
    urls = {p["url"] for p in projects}
    tracked = [
        p for p in hn.get("projects", []) if canonical_url(p["readme_url"]) in urls
    ]
    ids = set()
    matches = 0
    for project in tracked:
        local = {str(s["id"]) for s in project.get("stories", [])}
        ids.update(local)
        matches += len(local)
    result = dict(
        total=len(projects),
        github=sum(
            bool(p.get("github")) and p["github"].get("status") != "unavailable"
            for p in projects
        ),
        alternatives=sum(bool(p.get("alternatives")) for p in projects),
        summaries=sum(bool(p.get("function_summary")) for p in projects),
        deployment=sum(bool(p.get("deployment")) for p in projects),
        artwork=sum(bool(p.get("artwork")) for p in projects),
        hn_tracked=len(tracked),
        hn_eligible=sum(p.get("eligible") is True for p in tracked),
        hn_unique_stories=len(ids),
        hn_project_matches=matches,
        hn_window_start=hn.get("window_start"),
        hn_window_end_exclusive=hn.get("window_end_exclusive"),
        hn_checked=hn.get("refreshed_utc_date"),
        star_history=sum(
            bool(p.get("star_history", {}).get("last_good")) for p in projects
        ),
        star_charts=sum(
            bool(p.get("star_history", {}).get("chart_url")) for p in projects
        ),
        signals_collected_at=catalog.get("signals_collected_at"),
    )
    for provider in ("release", "scorecard"):
        records = [(p.get("signals") or {}).get(provider) for p in projects]
        result[provider] = dict(
            checked=sum(bool(r and r.get("checked_at")) for r in records),
            cached=sum(bool(r and r.get("last_good")) for r in records),
            states=dict(
                sorted(
                    Counter(
                        r.get("status", "not checked") if r else "not checked"
                        for r in records
                    ).items()
                )
            ),
        )
    return result


def safe_csv(value):
    value = (
        ""
        if value is None
        else str(value).lower()
        if isinstance(value, bool)
        else str(value)
    )
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@"))
        or value.startswith(("\t", "\r", "\n"))
        else value
    )


def csv_text(index):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_FIELDS)
    for project in index["projects"]:
        row = {
            **project,
            "categories": "; ".join(project["categories"]),
            "metrics_as_of": index["metrics_as_of"],
            "source_sha": index["source_sha"],
        }
        writer.writerow([safe_csv(row.get(key)) for key in CSV_FIELDS])
    return output.getvalue()


def json_html(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def bar_width(value, maximum):
    return f"{100 * value / maximum:.4f}%" if maximum else "0.0000%"


def chart(identifier, title, note, rows, unit="Projects", maximum=None, wide=False):
    """Zero-based linear bar list; the folded table is the accessible equivalent."""
    shared = maximum is not None
    maximum = max([value for _, value in rows] or [0]) if maximum is None else maximum
    bars = "".join(
        f'<li class="obs-bar{" obs-bar-unknown" if label == "Unknown" else ""}" data-key="{escape(label, quote=True)}" data-count="{value}">'
        f'<span class="obs-bar-label">{escape(label)}</span><span class="obs-track"><span class="obs-fill" style="width: {bar_width(value, maximum)}"></span></span>'
        f'<span class="obs-bar-count">{value:,}</span></li>'
        for label, value in rows
    )
    empty = (
        "" if rows else '<p class="obs-empty">No observed values in this selection.</p>'
    )
    scale = f"{maximum:,} {unit.lower()}" + (" · shared scale" if shared else "")
    visual = (
        f'<div class="obs-bars" aria-hidden="true"><div class="obs-scale"><span></span><span class="obs-scale-ends"><span>0</span>'
        f'<span class="obs-scale-max">{scale}</span></span><span></span></div><ol class="obs-bar-list">{bars}</ol>{empty}</div>'
    )
    table_rows = "".join(
        f'<tr data-key="{escape(label, quote=True)}" data-count="{value}"><th scope="row">{escape(label)}</th><td>{value:,}</td></tr>'
        for label, value in rows
    )
    if not rows:
        table_rows = (
            '<tr><td colspan="2">No observed values in this selection.</td></tr>'
        )
    table = f'<table class="chart-table"><caption>{escape(title)}</caption><thead><tr><th scope="col">Label</th><th scope="col">{unit}</th></tr></thead><tbody>{table_rows}</tbody></table>'
    return (
        f'<section class="obs-chart{" obs-chart-wide" if wide else ""}" id="{identifier}" aria-labelledby="{identifier}-heading">'
        f'<h3 id="{identifier}-heading">{title}</h3><p class="obs-chart-note">{note}</p>{visual}'
        f'<details class="obs-chart-data"><summary>Chart data</summary>{table}</details></section>'
    )


def finding_html(counts):
    """Whole-collection top-ten share, drawn to scale. Static: filters never change it."""
    if counts["leader_count"] == 10 and counts["concentration"] is not None:
        text = f"The 10 most-starred projects hold {counts['concentration']:.1f}% of stars."
    else:
        text = f"{counts['leader_count']} projects have an observed star count."
    strip = ""
    # star_rows ends with an aggregate tail when more than ten projects are
    # observed. Its editable display label is not a project identifier.
    leaders = counts["star_rows"][:counts["leader_count"]]
    if counts["stars"]:
        top = sum(value for _, value in leaders)
        tail = counts["stars"] - top

        def segment(label, value, kind):
            description = escape(f"{label} · {value:,} stars", quote=True)
            focus = ' tabindex="0"' if value else ''
            return (
                f'<span class="obs-strip-segment {kind}"{focus} role="img" '
                f'aria-label="{description}" title="{description}" '
                f'data-stars="{value}" style="width: {bar_width(value, counts["stars"])}">'
                f'<span class="obs-strip-tooltip" aria-hidden="true">{description}</span></span>'
            )

        segments = "".join(segment(label, value, "obs-strip-leader") for label, value in leaders)
        if tail:
            segments += segment("Other projects", tail, "obs-strip-tail")
        strip = (
            f'<figure class="obs-strip-figure"><div class="obs-strip">{segments}</div><figcaption class="obs-strip-key">'
            f'<span>Top {len(leaders)} · {top:,} stars</span><span class="obs-muted">Other projects · {tail:,}</span></figcaption></figure>'
        )
    return f'<aside class="obs-finding" aria-labelledby="obs-finding-text"><p id="obs-finding-text">{text}</p>{strip}</aside>'


def metrics_html(counts):
    def ratio(key, value, total):
        return (
            f'<span data-metric="{key}">{value:,}</span><span class="obs-of"> / <span data-metric-of>{total:,}</span></span>'
            f'<span class="obs-ratio" aria-hidden="true"><i data-ratio="{key}" style="width: {bar_width(value, total)}"></i></span>'
        )

    items = [
        ("Unique projects", f'<span data-metric="total">{counts["total"]:,}</span>'),
        ("Cached metrics", ratio("mapped", counts["mapped"], counts["total"])),
        (
            "GitHub stars",
            f'<span data-metric="stars">{format(counts["stars"], ",") if counts["stars"] is not None else "Unknown"}</span>',
        ),
        (
            "License detected",
            ratio("known-license", counts["known_license"], counts["total"]),
        ),
    ]
    return (
        '<dl id="metrics" class="obs-metrics">'
        + "".join(
            f'<div class="obs-metric"><dt><span>{label}</span></dt><dd>{value}</dd></div>'
            for label, value in items
        )
        + "</dl>"
    )


def render(index, counts, covered, category_art=None, root=None):
    category_art = category_art or {}
    site = Path(root or Path(__file__).resolve().parents[1]) / "site"
    esc = lambda v: escape(str(v), quote=True)
    revision = index["source_sha"]
    source = f"{REPOSITORY}/blob/{revision or 'main'}"
    stamp = (
        f'<a href="{REPOSITORY}/commit/{revision}">{revision[:12]}</a>'
        if revision
        else "Local preview; source revision not supplied"
    )
    art = '<img class="obs-logo" src="../brand/botanical-128.png" width="128" height="128" alt="Awesome Open* botanical logo">'
    options = "".join(
        f'<option value="{esc(c["id"])}" data-metric-art="{esc(category_art.get(c["id"], ""))}">{esc(c["name"])}</option>'
        for c in index["categories"]
    )
    categories = {c["id"]: c["name"] for c in index["categories"]}
    recency = max(value for _, value in counts["pushes"] + counts["releases"])
    charts = (
        f'<div class="obs-chart-pair">'
        + chart(
            "category-chart",
            "Projects by category",
            "Projects can belong to several categories.",
            counts["categories"],
        )
        + chart(
            "license-chart",
            "Detected licenses",
            "Cached GitHub license identifiers.",
            counts["licenses"],
        )
        + "</div>"
        + chart(
            "star-chart",
            "GitHub stars",
            "Top 10 specimen by GitHub stars.",
            counts["star_rows"],
            "Stars",
            wide=True,
        )
        + chart(
            "age-chart",
            "Repository age",
            "Days since GitHub repository creation.",
            counts["ages"],
            wide=True,
        )
        + '<div class="obs-chart-pair">'
        + chart(
            "push-chart",
            "Last repository push",
            "Days since last repository push.",
            counts["pushes"],
            maximum=recency,
        )
        + chart(
            "release-chart",
            "Latest GitHub release",
            "Days since last GitHub release (cached).",
            counts["releases"],
            maximum=recency,
        )
        + "</div>"
    )
    status = lambda name: "; ".join(
        f"{v:,} {k}" for k, v in covered[name]["states"].items()
    )
    rows = [
        (
            "Cached GitHub metrics",
            covered["github"],
            "Projects with cached GitHub metrics.",
        ),
        (
            "Latest GitHub release",
            covered["release"]["cached"],
            f"{covered['release']['checked']} checked. {status('release')}. Latest full release selected by GitHub.",
        ),
        (
            "OpenSSF Scorecard",
            covered["scorecard"]["cached"],
            f"{covered['scorecard']['checked']} checked. {status('scorecard')}. Cached automated repository checks.",
        ),
        (
            "Reviewed alternatives",
            covered["alternatives"],
            "Reviewed use-case comparisons.",
        ),
        (
            "Reviewed function summaries",
            covered["summaries"],
            "Source-reviewed function descriptions.",
        ),
        (
            "Reviewed setup evidence",
            covered["deployment"],
            "Limited set of source-reviewed setup instructions.",
        ),
        (
            "Approved specimen artwork",
            covered["artwork"],
            "Original specimen illustrations.",
        ),
        (
            "HN identity tracking",
            covered["hn_tracked"],
            f"{covered['hn_eligible']} chart-eligible projects; {covered['hn_unique_stories']} globally distinct story IDs and {covered['hn_project_matches']} project–story matches in the tracked subset. Stories can match several projects.",
        ),
        (
            "Cached star history",
            covered["star_history"],
            f"{covered['star_charts']} aligned charts. Monthly stars retained at fetch. Month boundaries may be approximate.",
        ),
    ]
    coverage_rows = "".join(
        f'<tr><th scope="row">{label}</th><td class="obs-cov-count"><span class="obs-track" aria-hidden="true"><span class="obs-fill" style="width: {bar_width(value, covered["total"])}"></span></span><span>{value:,} / {covered["total"]:,}</span></td><td>{esc(note)}</td></tr>'
        for label, value, note in rows
    )
    evidence_links = f'<a href="{source}/data/github_metrics.json">GitHub metric snapshot</a> · <a href="../data/hn_evidence.json">HN evidence</a>'
    if covered["release"]["checked"] or covered["scorecard"]["checked"]:
        evidence_links += ' · <a href="../data/project_signals.json">Release and Scorecard evidence</a>'
    if covered["star_history"]:
        evidence_links += (
            ' · <a href="../data/star_history.json">Star-history evidence</a>'
        )
    names = shared_names_html(
        counts["shared_names"], categories, counts["total"], len(index["projects"]),
        rhyming_names_html(counts["rhyming_names"])
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Awesome Open* Observatory</title><meta name="description" content="A snapshot of the Awesome Open collection: categories, detected licenses, repository dates, stars and evidence coverage."><link rel="icon" href="../brand/favicon.ico"><link rel="stylesheet" href="../{font_asset_url('vendor/fonts.css', root)}"><link rel="stylesheet" href="../{font_asset_url('tokens.css', root)}"><link rel="stylesheet" href="{content_url('observatory.css', site / 'observatory.css')}"><script src="{content_url('observatory.js', site / 'observatory.js')}" defer></script></head>
<body class="observatory"><a class="skip-link" href="#observatory-main">Skip to observatory</a><div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="../">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Field guide"><a href="../#catalog">Catalog</a><a href="../#about">About</a><a href="./" aria-current="page">Observatory</a></nav></header></div>
<main id="observatory-main" tabindex="-1"><div class="obs-shell"><section class="obs-hero"><div class="obs-hero-copy"><h1>Collection <br />observatory</h1></div></section>
<form id="observatory-filters" class="obs-filters" hidden aria-label="Filter observatory"><div class="obs-filters-row"><select id="category-filter" name="category" aria-label="Category"><option value="">All categories</option>{options}</select><select id="license-filter" name="license" aria-label="Detected license"><option value="all">Any license</option><option value="known">License detected</option><option value="unknown">License unknown</option></select><button id="reset-filters" type="button">Reset filters</button><nav class="obs-jump" aria-label="Sections"><a href="#shared-names">Names</a><a href="#charts">Charts</a><a href="#coverage">Coverage</a><a href="#project-records">Data</a></nav></div></form>
<noscript><p>Filters and filtered CSV export require JavaScript.</p></noscript>{metrics_html(counts)}{finding_html(aggregate(index))}{names}
<section id="charts" class="obs-section" aria-labelledby="charts-heading"><h2 id="charts-heading">Charts</h2>{charts}</section></div>
<section id="coverage" class="obs-coverage" aria-labelledby="coverage-heading"><div class="obs-shell"><h2 id="coverage-heading">Evidence coverage</h2><p><span class="obs-label">Whole collection</span></p><table class="obs-coverage-table"><caption class="visually-hidden">Evidence coverage</caption><thead><tr><th scope="col">Evidence</th><th scope="col">Projects</th><th scope="col">Scope</th></tr></thead><tbody>{coverage_rows}</tbody></table><div class="obs-coverage-notes"><p>Evidence collection: {esc(covered["signals_collected_at"] or "Not available")}. <br />HN checked: {esc(covered["hn_checked"] or "Not available")}; window {esc(covered["hn_window_start"])} to {esc(covered["hn_window_end_exclusive"])}.</p><p>{evidence_links}</p></div></div></section>
<div class="obs-shell"><section id="project-records" class="obs-section obs-ledger" aria-labelledby="project-data-heading"><h2 id="project-data-heading">Project data</h2><p>Dates are UTC. Cached measurements may be stale. The CSV lists the observation dates for each project.</p><p class="obs-downloads"><a id="export-csv" href="projects.csv" download="awesome-open-observatory.csv">Download selection CSV</a><a href="snapshot.json" download>Download complete snapshot JSON</a></p></section></div>
<div class="obs-closing-mark">{art}</div></main><footer class="obs-footer"><div class="obs-shell"><p>Awesome Open* / Observatory</p><ul class="obs-footer-links"><li><a href="{REPOSITORY}">GitHub</a></li><li>Source revision: {stamp}</li><li>Metrics collection date: <time>{index["metrics_as_of"]}</time> UTC</li></ul></div></footer><script id="observatory-data" type="application/json">{json_html(index)}</script></body></html>'''


def build(catalog, hn, output, root):
    output, root = Path(output), Path(root)
    target = output / "observatory"
    target.mkdir(parents=True, exist_ok=True)
    index = project_index(catalog)
    rhymes = reviewed_rhymes(catalog, root / "data/name_rhymes.json")
    for project in index["projects"]:
        if project["id"] in rhymes:
            project["rhyme"] = rhymes[project["id"]]
    counts, covered = aggregate(index), coverage(catalog, hn)
    category_art = {
        c["id"]: "../" + c["artwork"]["variants"]["s"]["path"]
        for c in catalog["categories"] if c.get("artwork")
    }
    page = render(index, counts, covered, category_art, root=root)
    for name in ["observatory.css", "observatory.js"]:
        shutil.copyfile(root / "site" / name, target / name)
    snapshot = {**index, "aggregate": counts, "coverage": covered}
    (target / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (target / "projects.csv").write_text(csv_text(index), encoding="utf-8", newline="")
    (target / "index.html").write_text(page, encoding="utf-8")
    (target / "report.html").unlink(missing_ok=True)
    return snapshot
