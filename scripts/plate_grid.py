"""Fixed evidence grid below the specimen plate (B-PR158-01).

Every box keeps its place and size whether or not its evidence exists; a box
without evidence reads "Unknown" and its popup says why. Only the reviewed
alternatives row disappears when there is nothing to show.
"""
from html import escape as _escape

import deployment

UNKNOWN = "Unknown"
NO_GITHUB = "No GitHub repository mapped."
NBSP, HAIR = "&nbsp;", "&#8202;"
# Popups opening toward the plate's centre stay on screen at every width.
END = "is-end"


def esc(value):
    return _escape(str(value), quote=True)


def state(text):
    return f'<span class="pg-state">{esc(text)}</span>'


def info(label, body):
    """Bare "i" (control.info) opening the box's details; native fallback."""
    return (f'<details class="pg-info"><summary aria-label="Details: {esc(label)}">i</summary>'
            f'<div class="pg-pop">{body}</div></details>')


def box(title, body, *, cls="", label="", popup="", heading=True, signal=""):
    lab = f'<span class="sheet-label">{label}</span>' if label else ""
    head = f'<h4 class="pg-title">{esc(title)}</h4>' if heading else ""
    data = f' data-signal="{signal}"' if signal else ""
    return (f'<section class="pg-box {cls}" aria-label="{esc(title)}"{data}>{lab}{head}{body}'
            f'{info(title, popup) if popup else ""}</section>')


def value(text, known=True):
    return f'<p class="pg-value{"" if known else " is-unknown"}">{text}</p>'


def reserved(cls=""):
    return f'<div class="pg-reserved {cls}" aria-hidden="true"></div>'


def window(first, last):
    return f'{esc(first)}{HAIR}–{HAIR}{esc(last)}'


def foot(count, first, last):
    """One unbreakable line under a sparkline: count · first – last."""
    span = f"{NBSP}·{NBSP}{window(first, last)}" if first and last else ""
    return f'<p class="pg-foot"><span class="pg-nowrap">{count}{span}</span></p>'


def empty_chart():
    return '<div class="pg-spark-empty" aria-hidden="true"></div><p class="pg-foot is-unknown">Unknown</p>'


def signal_time(value, precision="second"):
    return value[:10] + " (date only)" if precision == "day" else value


def provenance(record, good):
    parts = []
    if record.get("checked_at"):
        parts.append("Checked " + signal_time(record["checked_at"], record.get("check_time_precision", "second")))
    if record.get("last_success_at"):
        parts.append("Last successful fetch " + signal_time(
            record["last_success_at"],
            record.get("success_time_precision", record.get("check_time_precision", "second"))))
    if good:
        parts.append("Value fetched " + signal_time(good["fetched_at"], good.get("fetch_time_precision", "second")))
    if record.get("fetch_status") not in {"ok", "not_modified", "not_checked"}:
        parts.append("Latest attempt: " + record["fetch_status"].replace("_", " "))
    parts.append(f'<a href="{esc(record["source_url"])}">Provider source</a>')
    return '<p class="fine-print">' + " · ".join(parts) + "</p>"


MISSING = {
    "not_checked": "Not checked",
    "not_found": "No result returned",
    "pending": "Provider pending",
    "error": "Unavailable",
    "deferred": "Check deferred",
}


def repository(project, freshness):
    github = project.get("github") or {}
    note = f"<p>{esc(freshness)}</p>" if freshness else ""
    why = f"<p>{NO_GITHUB}</p>" if not github else "<p>Not reported by GitHub.</p>"
    stars = github.get("stars")
    stars = f"{stars:,}" if stars is not None else None
    license_ = github.get("license")
    created = (github.get("created_at") or "")[:10] or None
    pushed = (github.get("pushed_at") or "")[:10] or None

    def fact(title, text, *, label="", extra=""):
        known = bool(text)
        popup = note + ("" if known else why) + extra
        return box(title, value(esc(text) if known else UNKNOWN, known), label=label, popup=popup,
                   cls=END if title in ("Repository created", "Repository push") else "")

    return (fact("GitHub stars", stars, label="II / Repository record")
            + fact("Detected license", license_,
                   extra="" if license_ else "<p>Verify against official terms.</p>")
            + fact("Repository created", created)
            + fact("Repository push", pushed))


def timeline_box(timeline_html, history_html):
    if timeline_html:
        return f'<section class="pg-box pg-timeline" aria-label="Repository timeline">{timeline_html}{history_html}</section>'
    return ('<section class="pg-box pg-timeline is-empty" aria-label="Repository timeline">'
            f'<p class="pg-line">Repository timeline: Unknown</p>{history_html}</section>')


def stars_box(project):
    record = project.get("star_history")
    title, label = "GitHub stars", "III / Observations &amp; evidence"
    if record is None:
        github = project.get("github")
        return box(title, empty_chart(), label=label, signal="star-history",
                   popup=state("Not recorded") + ("" if github else f"<p>{NO_GITHUB}</p>"))
    good = record.get("last_good")
    status = record.get("display_status") or (
        "Cached" if record.get("status") == "ok" else "Stale cached result" if good else "Unavailable")
    trail = f'Latest attempt: {esc(record.get("status", "unknown"))}'
    if record.get("checked_at"):
        trail += " · Checked " + esc(record["checked_at"])
    if good:
        trail += " · Last successful fetch " + esc(good["fetched_at"])
    sources = (f'<p class="fine-print">{trail} · <a href="{esc(record["source_url"])}">Provider source</a></p>')
    if record.get("chart_url"):
        months, counts = good["months"], good["monthly_counts"]
        total = sum(counts)
        body = (f'<a class="pg-spark-link" href="{esc(record["source_url"])}"><img class="pg-spark" src="{esc(record["chart_url"])}" '
                f'width="120" height="24" alt="Monthly stars retained at fetch, {esc(months[0])} to {esc(months[-1])}" loading="lazy"></a>'
                + foot(f"{total:,}", months[0], months[-1]))
        popup = (state(status) + f"<p>{total:,} stars / past 2y: Stars created in each month that remained at the last successful fetch. "
                 f"Independent square-root scale: 0–{max(1, *counts):,} stars/month.</p>" + sources)
    else:
        body = empty_chart()
        withheld = ("Cached history uses a different month window; chart withheld until aligned."
                    if good else "History unavailable; no zero values inferred.")
        popup = state(status) + f"<p>{withheld}</p>" + sources
    return box(title, body, label=label, popup=popup, signal="star-history")


def hn_box(project, hn_window):
    hn = project.get("hn")
    title = "Hacker News stories"
    if not hn:
        return box(title, empty_chart(), popup=state("Not recorded"), signal="hn")
    first, last = (hn_window or {}).get("first"), (hn_window or {}).get("last")
    maximum = (hn_window or {}).get("monthly_maximum")
    alt = "HN stories per month" + (f", {first} to {last}" if first else ", past 2y")
    body = (f'<a class="pg-spark-link" href="{esc(hn["search_url"])}"><img class="pg-spark" src="{esc(hn["chart_url"])}" '
            f'width="120" height="24" alt="{esc(alt)}" loading="lazy"></a>'
            + foot(hn["total_stories"], first, last))
    scale = (f"<p>Square-root scale: 0–{esc(maximum)} stories/month, shared across HN charts.</p>"
             if maximum is not None else "")
    popup = (f'<p>{hn["total_stories"]} {"submission" if hn["total_stories"] == 1 else "submissions"} / past 2y.</p>{scale}'
             f'<p class="fine-print"><a href="{esc(hn["search_url"])}">HN search</a></p>')
    return box(title, body, popup=popup, signal="hn")


def signal_box(project, provider):
    title = {"release": "GitHub release", "scorecard": "OpenSSF Scorecard"}[provider]
    kwargs = {"label": "IV / Release record", "cls": "pg-release"} if provider == "release" else {"cls": END}
    records = project.get("signals") or {}
    record = records.get(provider)
    if record is None:
        why = "" if project.get("github") else f"<p>{NO_GITHUB}</p>"
        return box(title, value(UNKNOWN, False), popup=state("Not checked") + why, signal=provider, **kwargs)
    good = record["last_good"]
    status = state(record["status"].capitalize())
    trail = provenance(record, good)
    if good is None:
        reason = MISSING.get(record["fetch_status"], "Unavailable")
        return box(title, value(UNKNOWN, False), popup=status + f"<p>{esc(reason)}.</p>" + trail,
                   signal=provider, **kwargs)
    found = good["value"]
    if provider == "release":
        body = (value(f'<a href="{esc(found["html_url"])}">{esc(found["tag_name"])}</a>')
                + f'<p class="pg-sub">Published <span class="metric-value">{esc(found["published_at"][:10])}</span></p>')
        return box(title, body, popup=status + trail, signal=provider, **kwargs)
    checks = found["checks"]
    scored = sum(c["score"] is not None for c in checks)
    aggregate = f"{found['score']:g}/10" if found["score"] is not None else "Aggregate inconclusive"
    rows = "".join(
        f"<li><strong>{esc(c['name'])}</strong> · "
        + (f"{c['score']:g}/10" if c["score"] is not None else "Inconclusive")
        + f"<p>{esc(c['reason'])}</p></li>"
        for c in checks)
    commit = good["source_commit"]
    repo = found["repository"].removeprefix("github.com/")
    body = (value(esc(aggregate), True)
            + f'<p class="pg-sub">Scanned <span class="metric-value">{esc(good["observed_at"][:10])}</span> · '
              f"{scored} scored / {len(checks)} returned</p>")
    popup = (status + f'<ul class="pg-checks">{rows}</ul>'
             f'<p class="fine-print">Repository commit <a href="https://github.com/{esc(repo)}/commit/{esc(commit)}">{esc(commit[:12])}</a>'
             f" · Scorecard {esc(good['tool_version'])}</p>" + trail)
    return box(title, body, popup=popup, signal=provider, **kwargs)


RUN_LINES = (
    ("run_modes", "pg-run", "Run", deployment.RUN_MODES),
    ("install_methods", "pg-install", "Install", deployment.INSTALL_METHODS),
    ("platforms", "pg-platform", "Documented platforms", None),
)
KEY = ('<p class="pg-key"><span class="pg-run">Run</span> <span class="pg-install">Install</span> '
       '<span class="pg-platform">Documented platforms</span></p>')


def runs_box(project):
    record = project.get("deployment")
    kwargs = {"label": "V / Where it runs", "heading": False, "cls": f"pg-runs {END}"}
    if not record:
        return box("Where it runs", value(UNKNOWN, False), popup=state("Not reviewed"), **kwargs)
    lines = ""
    for field, cls, label, names in RUN_LINES:
        facts = record.get(field, [])
        if facts:
            chips = "".join(f"<span>{esc(names[f['value']] if names else f['value'])}</span>" for f in facts)
            lines += f'<div><dt class="visually-hidden">{label}</dt><dd class="{cls}">{chips}</dd></div>'
    body = f'<dl class="pg-kit">{lines}</dl>' if lines else value(UNKNOWN, False)
    popup = (KEY + f'<p class="fine-print">Reviewed {esc(record["checked_at"])} · {esc(record["reviewed_by"])} · Approved evidence record</p>'
             + deployment.sections(project))
    return box("Where it runs", body, popup=popup, **kwargs)


def alternatives(project):
    found = project.get("alternatives") or []
    if not found:
        return ""
    cells = "".join(
        box(f"Reviewed alternative: {a['name']}",
            f'<a class="pg-value" href="{esc(a["source_url"])}">{esc(a["name"])}</a>'
            f'<p class="pg-scope">{esc(a["scope"])} Checked{NBSP}<span class="metric-value pg-nowrap">{esc(a["checked_utc_date"])}</span></p>',
            cls="pg-alt", label="VI / Reviewed alternatives" if i == 0 else "", heading=False)
        for i, a in enumerate(found))
    return f'<div class="pg-row pg-alts">{cells}</div>'


def render(project, *, timeline_html="", history_html="", freshness="", hn_window=None):
    """Grid rows; the plate closes the panel with its departure."""
    return (
        f'<div class="pg-row pg-repository">{repository(project, freshness)}</div>'
        f'<div class="pg-row pg-tight">{timeline_box(timeline_html, history_html)}</div>'
        f'<div class="pg-row pg-evidence">{stars_box(project)}{hn_box(project, hn_window)}{reserved()}{signal_box(project, "scorecard")}</div>'
        f'<div class="pg-row pg-release-runs">{signal_box(project, "release")}{reserved("pg-wide")}{runs_box(project)}</div>'
        f"{alternatives(project)}"
    )
