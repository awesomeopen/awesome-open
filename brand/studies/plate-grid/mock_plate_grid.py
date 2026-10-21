"""Mock-up: fixed evidence grid below the specimen plate (B-PR158-01 study, not shipped).

Reads generated records from a built site (default tmp/site), keeps everything
above the first plate band, and replaces the bands with a stable 8-column box
grid. Boxes say "Unknown" for anything not known; the reason lives in the popup.
Writes records/mock-grid-<name>.html next to the generated records.

    python3 scripts/build_site.py --output tmp/site
    python3 brand/studies/plate-grid/mock_plate_grid.py [tmp/site]
"""
import json, re, sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import deployment  # noqa: E402

SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "tmp/site"
catalog = json.loads((SITE / "catalog.json").read_text())
by_name = {p["name"]: p for p in catalog["projects"]}
U = "Unknown"
NB, HAIR = "&nbsp;", "&#8202;"

CSS = """
<style>
/* upper half: long short-descriptions step down so the study stays near one screen */
.record-description.is-long {font-size:clamp(24px,2vw,30px);line-height:1.18;}
.plate-band, .pg {margin-top:48px;}
.pg {position:relative;--pg-gap:12px;--pg-lane:30px;background:var(--rs-mist);padding:2px 32px 32px;border-radius:var(--rs-radius);}
.specimen-plate .pg .pg-box > .sheet-label {background:var(--rs-muted);color:var(--rs-mist);}
.tool-name {background:var(--rs-scarlet) !important;color:white;}
.pg-row {display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:var(--pg-gap);padding-top:var(--pg-lane);align-items:stretch;}
.pg-row.is-tight {padding-top:0;margin-top:var(--pg-gap);}
.pg-box {position:relative;grid-column:span 2;background:var(--rs-paper);border:1px solid var(--rs-blueprint);border-radius:var(--rs-radius);padding:10px 14px 10px;min-width:0;display:flex;flex-direction:column;}
.pg-box.span-3 {grid-column:span 3;}
.pg-box.span-8 {grid-column:1 / -1;}
.pg-box > .sheet-label {position:absolute;left:-1px;top:calc(-1 * var(--pg-lane) + 6px);margin:0 !important;white-space:nowrap;}
.pg-title {font:12px/1.4 var(--mono);color:var(--muted);margin:0 0 4px;}
.pg-value {font:var(--rs-display-weight,400) 33px/1.1 var(--rs-display);color:var(--rs-blueprint);font-variant-numeric:tabular-nums;margin:0;overflow-wrap:anywhere;}
.pg-value.is-unknown {color:var(--muted);font-size:28px;}
.pg-value a {color:inherit;text-decoration-thickness:1px;text-underline-offset:4px;}
.pg-sub {font:12px/1.5 var(--mono);color:var(--ink);margin:6px 0 0;}
.pg-sub .metric-value {color:var(--accent);}
.nw {white-space:nowrap;}
/* sparkline boxes: the foot line anchors the chart from below */
.pg-spark-link {display:block;margin-top:auto;}
.pg-spark-link .pg-spark {margin:0;}
.pg-spark {display:block;width:100%;height:44px;margin:auto 0 0;object-fit:fill;}
.pg-spark-empty {height:44px;margin:auto 0 0;border-bottom:1px solid var(--rule);background:repeating-linear-gradient(90deg,transparent 0 calc(100%/24 - 1px),#e3e9ee calc(100%/24 - 1px) calc(100%/24));}
.pg-foot {font:12px/1.5 var(--mono);margin:6px 0 0;padding-right:28px;color:var(--ink);}
.pg-foot.is-unknown {color:var(--muted);}
/* reserved: an empty case on the shelf */
.pg-reserved {grid-column:span 2;background:var(--rs-verdigris-art);border-radius:var(--rs-radius);}
.pg-reserved.span-3 {grid-column:span 3;}
/* info: bare "i" (control.info, planned) opening a popover; native details fallback */
.pg-info {position:absolute;right:2px;bottom:2px;}
.pg-info > summary {list-style:none;display:grid;place-items:center;width:32px;height:32px;cursor:pointer;font:700 15px/1 var(--rs-display);color:var(--rs-blueprint);}
.pg-info > summary::-webkit-details-marker {display:none;}
.pg-info > summary:focus-visible {outline:2px solid var(--rs-blueprint);outline-offset:-2px;}
.pg-info[open] > summary {background:var(--rs-blueprint);color:var(--rs-paper);}
.pg-pop {position:absolute;right:0;bottom:36px;width:min(420px,80vw);max-height:420px;overflow:auto;z-index:20;background:var(--rs-paper);border:1px solid var(--rs-blueprint);box-shadow:var(--rs-shadow);padding:12px 14px;font:12px/1.55 var(--mono);}
.pg-pop p {margin:0 0 8px;} .pg-pop p:last-child{margin:0;} .pg-pop ul {margin:0;padding:0;list-style:none;} .pg-pop li {margin-bottom:8px;}
.pg-pop .pg-state {display:inline-block;padding:0 5px;border:1px dashed var(--rule);color:var(--muted);}
.pg-pop .deployment-group h5 {font:700 12px/1.5 var(--mono);margin:0 0 4px;} .pg-pop .deployment-group p{margin:0}
/* where it runs: one line per kind, kinds told apart by fill (names stay readable) */
.pg-kit {margin:0;display:grid;gap:5px;padding-right:24px;}
.pg-kit dd {margin:0;display:flex;flex-wrap:wrap;gap:4px 5px;}
.pg-kit dd span {padding:0 6px;font:12px/1.6 var(--mono);color:var(--rs-ink);border:1px solid transparent;border-radius:var(--rs-radius);}
.pg-kit .k-run span {background:var(--rs-amber);}
.pg-kit .k-install span {background:var(--rs-trace);border-color:#a9c8da;}
.pg-kit .k-platform span {background:var(--rs-emerald-art);}
.pg-row.alts {grid-template-columns:repeat(3,minmax(0,1fr));}
.pg-alt {grid-column:span 1;}
.pg-release .pg-value:not(.is-unknown) {text-align:center;margin:10px 0;}
.pg-alt a.pg-value {font-size:24px;align-self:flex-start;}
.pg-alt p {font:12px/1.55 var(--mono);margin:6px 0 0;}
.pg-alt .metric-value {color:var(--accent);}
/* timeline: full height only when there is something to draw */
.pg-timeline {padding:0 20px 40px;}
.pg-timeline .timeline {margin-top:64px !important;margin-bottom:0;}
.pg-timeline .timeline-label.up.is-rename {bottom:76px !important;}
.pg-timeline.is-empty {padding:6px 14px;}
.pg-timeline.is-empty p {margin:0;font:12px/1.5 var(--mono);color:var(--muted);}
.pg-row.r2 .pg-box {min-height:84px;}
.pg-row.r3 > * {min-height:132px;}
.pg-row.r4 > * {min-height:132px;}
.pg-row.is-depart {padding-top:0;margin-top:40px;}
.pg-depart {grid-column:1 / -1;}
.pg-depart .plate-departure {margin:0;padding:36px 32px 32px;border-radius:var(--rs-radius);}
.pg-depart .plate-departure .sheet-label {margin-bottom:12px;}
.mock-bar {background:var(--rs-amber);color:var(--rs-ink);font:12px/1.5 var(--mono);padding:8px 16px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;}
.mock-bar a {color:inherit;}
.mock-aside {margin:56px 0 0;padding:16px;border:1px dashed var(--rs-blueprint);font:12px/1.55 var(--mono);}
.mock-aside h3 {font:700 12px/1.5 var(--mono);text-transform:uppercase;letter-spacing:.06em;margin:0 0 12px;}
.mock-aside .pg-row {padding-top:0;}
@media (max-width:1100px){
 .pg {padding:2px 24px 24px;}
 .pg-row {grid-template-columns:repeat(4,minmax(0,1fr));}
 .pg-box.span-3,.pg-reserved.span-3 {grid-column:span 2;}
 .pg-row.alts {grid-template-columns:repeat(2,minmax(0,1fr));}
 .pg-box > .sheet-label {position:static;align-self:flex-start;margin:-10px 0 8px -14px !important;transform:translateY(-100%);}
}
@media (max-width:720px){
 .pg {padding:4px 16px 16px;}
 .pg-row,.pg-row.alts {grid-template-columns:minmax(0,1fr);padding-top:12px;}
 .pg-box,.pg-box.span-3,.pg-alt {grid-column:1 / -1;}
 .pg-reserved {display:none;}
 .pg-row > * {min-height:0 !important;}
 .pg-box > .sheet-label {transform:none;margin:0 0 8px !important;}
 .pg-spark,.pg-spark-empty {margin-top:4px;}
}
</style>"""

BAR = """<div class="mock-bar" role="note"><strong>MOCK-UP · plate grid v2</strong><span>{who}</span>
<a href="{other}">{other_name} →</a><a href="{orig}">Current plate</a></div>"""


def info(label, body):
    return (f'<details class="pg-info"><summary aria-label="Details: {escape(label)}" title="{escape(label)}">i</summary>'
            f'<div class="pg-pop">{body}</div></details>')


def state(text):
    return f'<span class="pg-state">{text}</span>'


def box(title, body, *, span="", label="", info_html="", show_title=True):
    lab = f'<span class="sheet-label">{label}</span>' if label else ""
    head = f'<h4 class="pg-title">{escape(title)}</h4>' if show_title else ""
    return f'<section class="pg-box {span}" aria-label="{escape(title)}">{lab}{head}{body}{info_html}</section>'


def value(text, unknown=False):
    return f'<p class="pg-value{" is-unknown" if unknown else ""}">{text}</p>'


def reserved(span=""):
    return f'<div class="pg-reserved {span}" aria-hidden="true"></div>'


def grab(html, start_pat, end_pat):
    i = html.find(start_pat)
    if i < 0:
        return ""
    j = html.find(end_pat, i)
    return html[i:j + len(end_pat)]


def provenance(fragment):
    m = re.search(r'<details class="note-provenance"><summary>.*?</summary>(.*?)</details>', fragment, re.S)
    return m.group(1) if m else ""


def status_of(fragment):
    m = re.search(r'signal-status">([^<]+)', fragment)
    return m.group(1) if m else ""


def window(months):
    return f'{months[0]}{HAIR}–{HAIR}{months[-1]}'


def foot(count, months):
    return f'<p class="pg-foot"><span class="nw">{count}{NB}·{NB}{window(months)}</span></p>'


def build(p, html):
    gh = p.get("github") or {}
    sig = p.get("signals") or {}
    no_gh = "<p>No GitHub repository mapped.</p>" if not gh else ""

    # II / Repository record (stars, license, created, push) + timeline
    stars = f'{gh["stars"]:,}' if gh.get("stars") is not None else None
    created = (gh.get("created_at") or "")[:10] or None
    pushed = (gh.get("pushed_at") or "")[:10] or None
    lic = gh.get("license")
    why = lambda t, known: "" if known else info(t, no_gh or "<p>Not reported by GitHub.</p>")
    row2 = (box("GitHub stars", value(stars or U, not stars), label="II / Repository record", info_html=why("GitHub stars", stars))
            + box("Detected license", value(escape(lic or U), not lic),
                  info_html=info("Detected license", (no_gh or "<p>No license detected by GitHub.</p>") + "<p>Verify against official terms.</p>") if not lic else "")
            + box("Repository created", value(created or U, not created), info_html=why("Repository created", created))
            + box("Repository push", value(pushed or U, not pushed), info_html=why("Repository push", pushed)))
    tl = re.search(r'<div class="timeline".*?</div>(?=</section>)', html, re.S)
    if tl:
        t = tl.group(0)
        # rename popup: sources only, no reviewer
        t = re.sub(r'(<div class="timeline-info-panel">).*?(<p>Sources:.*?</p>).*?(</div>)', r"\1\2\3", t, flags=re.S)
        timeline = f'<section class="pg-box span-8 pg-timeline" aria-label="Repository timeline">{t}</section>'
    else:
        timeline = '<section class="pg-box span-8 pg-timeline is-empty" aria-label="Repository timeline"><p>Repository timeline: Unknown</p></section>'

    # III / Observations & evidence
    good = (p.get("star_history") or {}).get("last_good")
    sh_html = grab(html, 'data-signal="star-history"', "</section>")
    if good:
        total = sum(good["monthly_counts"])
        svg = re.search(r'src="(assets/stars/[^"]+)"', sh_html).group(1)
        scale = re.search(r"Independent square-root scale: [^<]+", sh_html).group(0)
        gh_spark = box("GitHub stars",
                       f'<img class="pg-spark" src="{svg}" alt="Monthly stars retained at fetch, {good["months"][0]} to {good["months"][-1]}" width="240" height="44">'
                       + foot(f"{total:,}", good["months"]),
                       label="III / Observations &amp; evidence",
                       info_html=info("GitHub stars", f'<p>{state(status_of(sh_html))}</p><p>{total:,} stars / past 2y, per month retained at fetch.</p><p>{scale}.</p>{provenance(sh_html)}'))
    else:
        gh_spark = box("GitHub stars", '<div class="pg-spark-empty"></div><p class="pg-foot is-unknown">Unknown</p>',
                       label="III / Observations &amp; evidence",
                       info_html=info("GitHub stars", f"<p>{state('Not recorded')}</p>{no_gh}"))
    hn = p.get("hn")
    if hn:
        hn_html = grab(html, '<div class="signal evidence-note"><h4>Hacker News', "</div>")
        win = re.search(r'<p class="fine-print star-window">(.*?)</p>', hn_html, re.S)
        months = re.findall(r"\d{4}-\d{2}", win.group(1))[:2] if win else ["", ""]
        scale = win.group(1).split("<br>")[1] if win else ""
        hn_box = box("Hacker News stories",
                     f'<a class="pg-spark-link" href="{escape(hn["search_url"])}"><img class="pg-spark" src="{hn["chart_url"]}" alt="HN stories per month, {months[0]} to {months[1]}" width="240" height="44"></a>'
                     + foot(hn["total_stories"], months),
                     info_html=info("Hacker News stories", f'<p>{hn["total_stories"]} submissions / past 2y.</p><p>{scale}</p><p><a href="{escape(hn["search_url"])}">HN search</a> · <a href="data/hn_evidence.json">HN evidence</a></p>'))
    else:
        hn_box = box("Hacker News stories", '<div class="pg-spark-empty"></div><p class="pg-foot is-unknown">Unknown</p>',
                     info_html=info("Hacker News stories", f"<p>{state('Not recorded')}</p>"))
    sc = sig.get("scorecard")
    sc_html = grab(html, 'data-signal="scorecard"', "</section>")
    sc_box = scorecard_box(sc, sc_html, no_gh)
    row3 = gh_spark + hn_box + reserved() + sc_box

    # IV / Release record, reserved, V / Where it runs
    rel = sig.get("release")
    rel_html = grab(html, 'data-signal="release"', "</section>")
    if rel and rel.get("last_good"):
        rv = rel["last_good"]["value"]
        rel_box = box("GitHub release", value(f'<a href="{escape(rv["html_url"])}">{escape(rv["tag_name"])}</a>')
                      + f'<p class="pg-sub">Published <span class="metric-value">{rv["published_at"][:10]}</span></p>',
                      span="pg-release", label="IV / Release record", info_html=info("GitHub release", f"<p>{state(status_of(rel_html))}</p><p>{provenance(rel_html)}</p>"))
    else:
        why_rel = f"<p>{state(status_of(rel_html) or 'Not checked')}</p><p>No release returned.</p><p>{provenance(rel_html)}</p>" if rel else f"<p>{state('Not checked')}</p>{no_gh}"
        rel_box = box("GitHub release", value(U, True), label="IV / Release record", info_html=info("GitHub release", why_rel))
    dep = p.get("deployment")
    if dep:
        lines = ""
        for field, cls, label, names in (("run_modes", "k-run", "Run", deployment.RUN_MODES),
                                         ("install_methods", "k-install", "Install", deployment.INSTALL_METHODS),
                                         ("platforms", "k-platform", "Documented platforms", None)):
            facts = dep.get(field, [])
            if facts:
                chips = "".join(f"<span>{escape(names[f['value']] if names else f['value'])}</span>" for f in facts)
                lines += f'<div><dt class="visually-hidden">{label}</dt><dd class="{cls}">{chips}</dd></div>'
        setup = re.search(r'<details><summary>View setup facts &amp; sources</summary>(.*?)</details></div></section>', html, re.S)
        reviewed = re.search(r'<p class="fine-print">(Reviewed [^<]+)</p>', html)
        key = ('<p><span style="background:var(--rs-amber);padding:0 4px">Run</span> '
               '<span style="background:var(--rs-trace);padding:0 4px">Install</span> '
               '<span style="background:var(--rs-emerald-art);padding:0 4px">Documented platforms</span></p>')
        runs = box("Where it runs", f'<dl class="pg-kit">{lines}</dl>', span="span-3", label="V / Where it runs", show_title=False,
                   info_html=info("Setup facts &amp; sources", key + (f"<p>{reviewed.group(1)}</p>" if reviewed else "") + (setup.group(1) if setup else "")))
    else:
        runs = box("Where it runs", value(U, True), span="span-3", label="V / Where it runs", show_title=False,
                   info_html=info("Where it runs", f"<p>{state('Not reviewed')}</p>"))
    row4 = rel_box + reserved("span-3") + runs

    # VI / Reviewed alternatives: the only row that may disappear
    row6 = ""
    if p["alternatives"]:
        cells = "".join(
            box(f'Reviewed alternative: {a["name"]}',
                f'<a class="pg-value" href="{escape(a["source_url"])}">{escape(a["name"])}</a>'
                f'<p>{escape(a["scope"])} Checked{NB}<span class="metric-value nw">{escape(a["checked_utc_date"])}</span></p>',
                span="pg-alt", label="VI / Reviewed alternatives" if i == 0 else "", show_title=False)
            for i, a in enumerate(p["alternatives"]))
        row6 = f'<div class="pg-row alts">{cells}</div>'

    depart = grab(html, '<nav class="plate-departure"', "</nav>")
    return (f'<div class="pg">'
            f'<div class="pg-row r2">{row2}</div><div class="pg-row is-tight">{timeline}</div>'
            f'<div class="pg-row r3">{row3}</div><div class="pg-row r4">{row4}</div>{row6}'
            f'<div class="pg-row is-depart"><div class="pg-depart">{depart}</div></div></div>')


def scorecard_box(sc, sc_html, no_gh):
    if sc and sc.get("last_good"):
        m = re.search(r'<p><span class="note-value">(.*?)</span>(.*?)</p>', sc_html, re.S)
        checks = grab(sc_html, '<details class="signal-checks">', "</details>")
        checks = re.sub(r"^<details[^>]*><summary>.*?</summary>|</details>$", "", checks, flags=re.S)
        return box("OpenSSF Scorecard", value(m.group(1)) + f'<p class="pg-sub">{m.group(2)}</p>',
                   info_html=info("OpenSSF Scorecard", f"<p>{state(status_of(sc_html))}</p>{checks}<p>{provenance(sc_html)}</p>"))
    if sc:
        return box("OpenSSF Scorecard", value(U, True),
                   info_html=info("OpenSSF Scorecard", f"<p>{state(status_of(sc_html))}</p><p>No result returned.</p><p>{provenance(sc_html)}</p>"))
    return box("OpenSSF Scorecard", value(U, True), info_html=info("OpenSSF Scorecard", f"<p>{state('Not checked')}</p>{no_gh}"))


def page(name, other, who, extra=""):
    p = by_name[name]
    src = (SITE / "records" / f'{p["id"]}.html').read_text()
    i = src.find('<section class="plate-band')
    j = src.find("</nav>", src.find('<nav class="plate-departure')) + len("</nav>")
    out = src[:i] + build(p, src) + extra + src[j:]
    if len(p["description"]) > 90:
        out = out.replace('<p class="record-description">', '<p class="record-description is-long">', 1)
    out = out.replace("</head>", CSS + "</head>", 1)
    slug = lambda n: "mock-grid-" + n.lower().replace(" ", "-") + ".html"
    out = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BAR.format(who=who, other="records/" + slug(other), other_name=other, orig=f'records/{p["id"]}.html'), out, count=1)
    (SITE / "records" / slug(name)).write_text(out)
    print(SITE / "records" / slug(name))


# Inset for OpenTofu: what the Scorecard box looks like with a returned result.
scad = by_name["OpenSCAD"]
scad_html = (SITE / "records" / f'{scad["id"]}.html').read_text()
inset = ('<aside class="mock-aside"><h3>Mock note · Scorecard box with a returned result</h3>'
         '<p>No catalog record has every evidence type. OpenTofu has all but a Scorecard result (checked, not found). '
         'The box below shows the filled state with OpenSCAD’s real values.</p>'
         '<div class="pg-row r3" style="grid-template-columns:repeat(8,minmax(0,1fr))">'
         + scorecard_box(scad["signals"]["scorecard"], grab(scad_html, 'data-signal="scorecard"', "</section>"), "")
         + "</div></aside>")

page("OpenTofu", "OpenGeoSys", "Fullest record: OpenTofu (real data)", inset)
page("OpenGeoSys", "OpenTofu", "Sparse record: OpenGeoSys (real data, not on GitHub)")
page("openstatus", "OpenTofu", "Three alternatives: openstatus (real data)")
