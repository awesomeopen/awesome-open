#!/usr/bin/env python3
"""Build the complete, offline static catalog. No network, dependencies or deployment."""

import argparse
import base64
import html
import json
from pathlib import Path
import shutil

from build_catalog import build_catalog
import update_hn as hn
import update_stats as stats
import signals

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/awesomeopen/awesome-open"


def escape(value):
    return html.escape(str(value), quote=True)


def source_url(catalog, path, anchor=""):
    ref = catalog.get("source_sha") or "main"
    return f"{REPOSITORY}/blob/{ref}/{path}{anchor}"


def json_for_html(value):
    """A JSON script is still parsed as raw HTML text; never allow a closing tag."""
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def split_name(name):
    """The prefix treatment never changes the canonical name or identity."""
    if name[:4].lower() == 'open':
        return f'<span class="name-prefix">{escape(name[:4])}</span><span class="name-stem">{escape(name[4:])}</span>'
    return f'<span class="name-stem">{escape(name)}</span>'


def specimen_art():
    """An original vector prefix study, deliberately not a phylogenetic diagram."""
    import math
    paths = []
    for angle in range(0, 360, 30):
        a = math.radians(angle)
        x, y = 200 + 151 * math.cos(a), 200 + 151 * math.sin(a)
        paths.append(f'<path d="M200 200 Q{200 + 45 * math.cos(a+.32):.2f} {200 + 45 * math.sin(a+.32):.2f} {x:.2f} {y:.2f}"/>')
        for distance in (54, 82, 111, 137):
            cx, cy = 200 + distance * math.cos(a), 200 + distance * math.sin(a)
            for direction in (-1, 1):
                tipx = 200 + (distance + 22) * math.cos(a) + direction * 17 * math.sin(a)
                tipy = 200 + (distance + 22) * math.sin(a) - direction * 17 * math.cos(a)
                controlx = cx + direction * 35 * math.sin(a)
                controly = cy - direction * 35 * math.cos(a)
                paths.append(f'<path d="M{cx:.2f} {cy:.2f} Q{controlx:.2f} {controly:.2f} {tipx:.2f} {tipy:.2f} Q{cx+15*math.cos(a):.2f} {cy+15*math.sin(a):.2f} {cx:.2f} {cy:.2f}"/>')
    return '<svg class="prefix-flora" viewBox="0 0 400 400" aria-hidden="true" fill="none" stroke="currentColor" stroke-width=".85">'+''.join(paths)+'<circle cx="200" cy="200" r="9"/><circle cx="200" cy="200" r="181" stroke-dasharray="1 8"/></svg>'


def signal_time(value, precision='second'):
    return value[:10] + ' UTC (date only)' if precision == 'day' else value


def optional_signal_html(project):
    """Evidence stays in native drawers; unknown values never become zeroes."""
    records = project.get('signals')
    if not records:
        return ''
    pieces = []
    for provider, title in (('release', 'Latest GitHub release'), ('scorecard', 'OpenSSF Scorecard')):
        record = records[provider]
        good = record['last_good']
        state = record['status'].capitalize()
        if good is None:
            label = {'not_checked': 'Not checked', 'not_found': 'No result returned',
                     'pending': 'Provider pending', 'error': 'Unavailable', 'deferred': 'Check deferred'}.get(record['fetch_status'], 'Unavailable')
            content = f'<p>{escape(label)}</p>'
        elif provider == 'release':
            value = good['value']
            content = (f'<p><a href="{escape(value["html_url"])}">{escape(value["tag_name"])}</a>'
                       f' · Published {escape(value["published_at"][:10])} UTC</p>')
        else:
            value = good['value']
            scored = sum(check['score'] is not None for check in value['checks'])
            total = len(value['checks'])
            aggregate = f'{value["score"]:g}/10' if value['score'] is not None else 'Aggregate inconclusive'
            checks = ''.join(f'<li><strong>{escape(c["name"])}</strong> · '
                             + (f'{c["score"]:g}/10' if c['score'] is not None else 'Inconclusive')
                             + f'<p>{escape(c["reason"])}</p></li>' for c in value['checks'])
            commit = good['source_commit']
            repo = value['repository'].removeprefix('github.com/')
            content = (f'<p>{aggregate} · Scanned {escape(good["observed_at"][:10])} · '
                       f'{scored} scored / {total} returned checks</p>'
                       f'<details class="signal-checks"><summary>Check results and scan provenance</summary><ul>{checks}</ul>'
                       f'<p class="fine-print">Repository commit <a href="https://github.com/{escape(repo)}/commit/{commit}">{commit[:12]}</a>'
                       f' · Scorecard {escape(good["tool_version"])}</p></details>')
        provenance = []
        if record['checked_at']:
            provenance.append('Checked ' + signal_time(record['checked_at'], record.get('check_time_precision', 'second')))
        if record['last_success_at']:
            provenance.append('Last successful fetch ' + signal_time(record['last_success_at'], record.get('success_time_precision', record.get('check_time_precision', 'second'))))
        if good:
            provenance.append('Value fetched ' + signal_time(good['fetched_at'], good.get('fetch_time_precision', 'second')))
        if record['fetch_status'] not in {'ok', 'not_modified', 'not_checked'}:
            provenance.append('Latest attempt: ' + record['fetch_status'].replace('_', ' '))
        provenance.append(f'<a href="{escape(record["source_url"])}">Provider source</a>')
        pieces.append(f'<section class="optional-signal" data-signal="{provider}"><h4>{title} <span class="signal-status">{state}</span></h4>{content}<p class="fine-print">' + ' · '.join(provenance) + '</p></section>')
    return '<div class="optional-signals">' + ''.join(pieces) + '</div>'


def project_html(project, categories, catalog, number=0):
    pid = escape(project['id'])
    name = escape(project['name'])
    github = project['github']
    license_text = (github['license'] if github else None) or 'License unknown'
    pushed = github['pushed_at'][:10] if github and github['pushed_at'] else 'Unknown'
    created = github['created_at'][:10] if github else 'Unknown'
    stars = f'{github["stars"]:,}' if github else 'Unknown'
    tags = ' / '.join(f'<a class="tag" data-category="{escape(cid)}" href="{escape(source_url(catalog, "README.source.md", "#" + cid))}">{escape(categories[cid])}</a>' for cid in project['categories'])
    evidence = ''.join(f'<li><a href="{escape(a["source_url"])}">{escape(a["name"])}</a><span class="evidence-date">Checked {escape(a["checked_utc_date"])}</span><p>{escape(a["scope"])}</p></li>' for a in project['alternatives'])
    alternatives = f'<div class="comparison"><h4>Reviewed alternatives</h4><ul>{evidence}</ul><p class="fine-print">Source-backed use cases; feature parity is not established.</p></div>' if evidence else ''
    chart = ''
    if project['hn']:
        attention = project['hn']
        chart = f'<div class="signal"><h4>HN seismograph</h4><a class="hn-chart" href="{escape(attention["search_url"])}" title="HN discussions"><img src="{escape(attention["chart_url"])}" width="120" height="24" alt="HN discussions / 2y" loading="lazy"><span>{attention["total_stories"]} matched story submissions / 24 completed months</span></a><p class="fine-print">Shared square-root scale. <a href="data/hn_evidence.json">View evidence</a></p></div>'
    return f'''<article class="project-card" id="project-{pid}" data-project-id="{pid}">
 <details class="specimen-drawer">
  <summary><span class="folio" aria-hidden="true">{number:03d}</span><span class="specimen-name">{split_name(project['name'])}</span><span class="description">{escape(project['description'])}</span><span class="license-readout">{escape(license_text)}</span><span class="drawer-sign" aria-hidden="true">+</span></summary>
  <div class="specimen-interior">
   <div class="specimen-caption"><span class="registry">OP-{pid[:8].upper()}</span><h3>{name}</h3><p>{tags}</p><a class="source-link" href="{escape(project['url'])}">Official source <span aria-hidden="true">↗</span></a><a class="permalink" href="#project-{pid}" aria-label="Permalink to {name}">Specimen permalink</a></div>
   <div class="diagnostics"><dl class="vitals"><div><dt>Detected license</dt><dd>{escape(license_text)}</dd></div><div><dt>GitHub stars</dt><dd>{stars}</dd></div><div><dt>Last repository push · UTC</dt><dd>{escape(pushed)}</dd></div><div><dt>Repository created · UTC</dt><dd>{escape(created)}</dd></div></dl><p class="fine-print">{'Cached GitHub metrics' if github else 'No cached GitHub metrics'} · Snapshot {escape(catalog['metrics_as_of'])}. Unknown values indicate missing cached data.</p>{optional_signal_html(project)}{alternatives}{chart}</div>
  </div>
 </details>
</article>'''


def render_html(catalog):
    categories = {c['id']: c['name'] for c in catalog['categories']}
    count = len(catalog['projects'])
    nav = ''.join(f'<a data-category="{escape(c["id"])}" href="{escape(source_url(catalog, "README.source.md", "#" + c["id"]))}"><span>{escape(c["name"])}</span><span class="category-count">{c["count"]:02d}</span></a>' for c in catalog['categories'])
    category_options = ''.join(f'<option value="{escape(c["id"])}">{escape(c["name"])}</option>' for c in catalog['categories'])
    licenses = sorted({p['github']['license'] for p in catalog['projects'] if p['github'] and p['github']['license']})
    license_options = ''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in licenses)
    alternative_names = sorted({a['name'] for p in catalog['projects'] for a in p['alternatives']})
    alternative_options = ''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in alternative_names)
    projects = '\n'.join(project_html(p, categories, catalog, i+1) for i, p in enumerate(catalog['projects']))
    known_licenses = sum(bool(p['github'] and p['github']['license']) for p in catalog['projects'])
    comparisons = sum(bool(p['alternatives']) for p in catalog['projects'])
    charts = sum(bool(p['hn']) for p in catalog['projects'])
    signal_projects = [p for p in catalog['projects'] if p.get('signals')]
    signal_coverage = []
    for provider, label in (('release', 'Release'), ('scorecard', 'Scorecard')):
        checked = sum(bool(p['signals'][provider]['checked_at']) for p in signal_projects)
        values = sum(bool(p['signals'][provider]['last_good']) for p in signal_projects)
        signal_coverage.append(f'{label}: {values} cached results / {checked} checked')
    optional_notes = ('<p>' + ' · '.join(signal_coverage) + f" · {len(signal_projects)} mapped GitHub repositories. Optional collection snapshot {escape(catalog.get('signals_collected_at'))}.</p>"
                      '<p>Latest GitHub release follows the publisher’s latest designation; its date is publication time. Scorecard reports automated security-practice checks. Its aggregate, scored/returned coverage, scan date and check reasons belong together. Inconclusive and omitted checks remain unknown. These observations do not establish security, compliance, or production suitability. Stale marks an old scan/cache or a retained result after an unsuccessful check.</p>'
                      '<p><a href="data/project_signals.json">Release and Scorecard evidence</a></p>') if signal_projects else ''
    sha = catalog.get('source_sha')
    revision = f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else 'Local preview (revision not supplied)'
    sample = next((p for p in catalog['projects'] if p['name'] == 'OpenBao'), catalog['projects'][0])
    return f'''<!doctype html>
<html lang="en">
<head>
 <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
 <meta name="description" content="A natural-history field guide to software named Open, with searchable project records, repository data, and reviewed comparisons.">
 <meta name="color-scheme" content="light"><title>Genus Open* — The Awesome Open field guide</title>
 <link rel="stylesheet" href="vendor/fonts.css"><link rel="stylesheet" href="styles.css">
 <script src="catalog.js" defer></script><script src="vendor/gsap.min.js" defer></script><script src="vendor/ScrollTrigger.min.js" defer></script><script src="motion.js" defer></script>
</head>
<body>
<a class="skip-link" href="#catalog">Skip to specimen ledger</a>
<div class="page-shell">
<header class="site-header"><a class="brand" href="./" aria-label="Awesome Open home">Awesome Open<span class="brand-asterisk" aria-hidden="true">*</span></a><span class="header-caption">A lexicographical collection<br>Software / Natural history</span><nav class="header-links" aria-label="Field guide"><a href="#catalog">The ledger <span aria-hidden="true">↓</span></a><a href="#method">Reading the evidence</a><a href="{REPOSITORY}">GitHub <span aria-hidden="true">↗</span></a></nav></header>
<section class="hero" aria-labelledby="page-title">
 <div class="cover-line"><span>A field guide to the genus</span><span>THE NAME IS THE CRITERION.</span></div>
 <h1 id="page-title" aria-label="Genus Open star">Open<span class="wildcard" aria-hidden="true">*</span></h1>
 <div class="hero-baseline"><div class="hero-copy" aria-hidden="true"></div><p class="dictionary"><span>Open-</span> <i>prefix</i><br>A source model. A fresh start.<br>A name.</p><a class="enter-ledger" href="#catalog">Inspect the specimens <span aria-hidden="true">↘</span></a></div>
 <div class="botanical-plate">{specimen_art()}<span class="plate-note">Fig. O*<br>Prefix study<br><span>Schematic</span></span><span class="plate-crosshair" aria-hidden="true">+</span></div>
 <div class="cover-bottom"><span>cat /dev/software | grep '^Open'</span><span>Names, functions, sources.</span></div>
</section>
<section class="reading-room" id="method" aria-labelledby="method-title">
 <div class="reading-intro"><span class="mono-label">Notes from the collection</span><h2 id="method-title">Same prefix.<br><em>Different species.</em></h2><p>Opening a specimen brings its source links and available evidence into view.</p><a class="text-link" href="#catalog">Go straight to the ledger <span aria-hidden="true">↘</span></a></div>
 <div class="observation-sheets">
  <article class="observation-sheet"><div class="sheet-heading"><span class="mono-label">A name under glass</span><span class="sheet-sign" aria-hidden="true">⌕</span></div><h3>{split_name(sample['name'])}</h3><p>{escape(sample['description'])}</p><div class="sheet-bottom"><span>OP-{sample['id'][:8].upper()} / URL-derived registry ID</span><a href="#project-{sample['id']}">Inspect specimen ↗</a></div></article>
  <article class="observation-sheet"><div class="sheet-heading"><span class="mono-label">The label &amp; the substance</span><span class="sheet-sign" aria-hidden="true">≠</span></div><h3>Open ≠<br>one license.</h3><p><strong>{known_licenses} of {count}</strong> records have a detected license in this snapshot. Selecting a license narrows the ledger to matching records.</p><div class="sheet-bottom"><span>Licenses recorded by GitHub.</span><a href="#catalog">Read the actual terms ↘</a></div></article>
  <article class="observation-sheet"><div class="sheet-heading"><span class="mono-label">Repository &amp; HN records</span><span class="sheet-sign" aria-hidden="true">∿</span></div><h3>Activity<br>&amp; attention.</h3><p>Push dates measure repository pushes. HN charts count matched story submissions across 24 completed months.</p><div class="sheet-bottom"><span>{charts} HN records / {comparisons} reviewed comparisons</span><a href="{escape(source_url(catalog, 'CONTRIBUTING.md'))}">Methods &amp; sources ↗</a></div></article>
 </div>
</section>
<div class="collection-band"><span>THE SPECIMEN LEDGER</span><span>{count} distinct projects</span><span>{catalog['category_memberships']} category memberships</span><span>{len(categories)} functional categories</span></div>
<div class="layout">
 <aside class="sidebar" aria-label="Catalog categories"><details class="category-panel" open><summary>Index by function <span aria-hidden="true">+</span></summary><nav class="category-nav" aria-label="Categories"><a data-category="" href="#catalog" aria-current="true"><span>All specimens</span><span class="category-count">{count}</span></a>{nav}</nav></details><p class="sidebar-note">Grouped by what the software does.</p></aside>
 <main id="catalog" class="catalog-main" tabindex="-1">
  <div class="ledger-heading"><div><span class="mono-label">Project records &amp; source evidence.</span><h2>The register<span aria-hidden="true">.</span></h2></div><span class="snapshot-label">Snapshot<br>{escape(catalog['metrics_as_of'])} UTC</span></div>
  <form id="filters" class="catalog-toolbar" hidden aria-label="Filter projects">
   <div class="search-field"><label for="search">Find a specimen</label><div class="search-input"><span aria-hidden="true">⌕</span><input id="search" name="q" type="search" placeholder="A name, a function, an alternative…" autocomplete="off" aria-describedby="search-help"></div><span id="search-help" class="visually-hidden">Search names, descriptions, and reviewed alternative names. Results update as you type.</span></div>
   <div class="diagnostic-filters"><div class="filter-field"><label for="push-window">Repository push window</label><select id="push-window" name="window"><option value="all">Any observed date</option><option value="recent">Within 90 days of snapshot</option><option value="older">More than 2 years before snapshot</option><option value="unknown">Push date unknown</option></select></div><div class="filter-field"><label for="alternative-filter">Reviewed alternative to</label><select id="alternative-filter" name="alternative"><option value="">Any / not recorded</option>{alternative_options}</select></div><div class="filter-field"><label for="license-filter">Detected license</label><select id="license-filter" name="license"><option value="all">Any / unknown</option><option value="known">Detected license available</option><option value="unknown">License unknown</option>{license_options}</select></div></div>
   <details class="more-filters"><summary>More diagnostic filters <span aria-hidden="true">+</span></summary><div class="filter-grid"><div class="filter-field"><label for="category-filter">Function</label><select id="category-filter" name="category"><option value="">All categories</option>{category_options}</select></div><div class="filter-field"><label for="metrics-filter">Cached repository metrics</label><select id="metrics-filter" name="metrics"><option value="all">Present or missing</option><option value="present">Present</option><option value="missing">Missing</option></select></div><div class="filter-field"><label for="min-stars">Minimum GitHub stars</label><input id="min-stars" name="stars" type="number" min="0" step="1" placeholder="Any"></div><div class="filter-field"><label for="pushed-since">Last pushed on or after · UTC</label><input id="pushed-since" name="pushed" type="date"></div></div></details>
   <div class="toolbar-bottom"><p class="filter-note">Date filters use the snapshot shown above.</p><button id="clear-filters" type="button">Reset the lens <span aria-hidden="true">↺</span></button></div><button class="visually-hidden" type="submit" tabindex="-1">Apply filters</button>
  </form>
  <noscript><p class="no-script">All {count} projects are available below. Use your browser’s Find to search and open any specimen drawer. Category links open the curated source sections. Enable JavaScript for filters and sorting.</p></noscript>
  <div class="results-heading"><h3 id="result-count" role="status" aria-live="polite" aria-atomic="true">{count} projects</h3><div class="sort-field"><label for="sort-order">Order</label><select id="sort-order" name="sort" disabled><option value="name">Name A–Z</option><option value="stars">Most stars</option><option value="pushed">Latest push</option></select></div></div>
  <p id="project-link-notice" class="link-notice" role="status" hidden></p><p id="empty-state" class="empty-state" hidden>No specimens in this view. Try a broader search or reset the lens.</p>
  <div class="ledger-columns" aria-hidden="true"><span>Folio</span><span>Specimen</span><span>Observed function</span><span>License</span><span>View</span></div><div id="project-list" class="project-list">{projects}</div>
 </main>
</div>
<footer class="site-footer" id="about"><span class="mono-label">The collection is never finished.</span><h2>Another Open<br><em>in the wild?</em></h2><a class="contribute-link" href="{escape(source_url(catalog, 'CONTRIBUTING.md'))}">Bring it to the collection <span aria-hidden="true">↗</span></a><div class="colophon"><div><h3>Collection notes.</h3><p>Awesome Open includes open-source and proprietary software, services, libraries, and archived projects. The prefix is the inclusion criterion.</p><p>Registry IDs derive from canonical URLs. Folio numbers show this edition’s alphabetical position. The botanical illustration is a typographic study.</p></div><div><h3>Evidence methods.</h3><p>GitHub metadata is cached. Detected licenses require verification against current official terms; missing license data remains unknown. Repository dates describe GitHub activity, not project age or maintenance health.</p><p>HN charts count matched stories over 24 completed months on a shared square-root scale. Stars and HN counts measure attention, not quality or sentiment. Coverage is a researched subset; missing charts do not establish an absence of discussion.</p>{optional_notes}<p><a id="hn-evidence" href="data/hn_evidence.json">HN evidence</a> / <a href="data/alternatives.json">Comparison evidence</a> / <a href="catalog.json">Catalog JSON</a></p></div></div><div class="footer-baseline"><span>Awesome Open / Genus Open*</span><span>Source revision: {revision}</span><span>List: <a href="{escape(source_url(catalog, 'LICENSE.md'))}">CC0-1.0</a> / Projects retain their licenses</span><a href="#page-title">Back to the cover ↑</a></div></footer>
</div><script id="catalog-data" type="application/json">{json_for_html(catalog)}</script>
</body></html>
'''

def build(output, source_sha=None, root=ROOT):
    root = Path(root)
    output = Path(output).resolve()
    # Protect source directories from accidental --output . or --output site.
    for protected in (root, root / 'site', root / 'scripts', root / 'data', root / 'assets', root / '.github'):
        if (output == protected.resolve() or output in protected.resolve().parents
                or (protected != root and protected.resolve() in output.parents)):
            raise ValueError('Use a separate generated output directory (default: tmp/site)')
    source = (root / 'README.source.md').read_text(encoding='utf-8')
    snapshot = json.loads((root / 'data/github_metrics.json').read_text(encoding='utf-8'))
    alternatives = json.loads((root / 'data/alternatives.json').read_text(encoding='utf-8'))
    evidence = json.loads((root / 'data/hn_evidence.json').read_text(encoding='utf-8'))
    optional = signals.load_optional(root / 'data/project_signals.json')
    catalog = build_catalog(source, snapshot, alternatives, evidence, source_sha=source_sha, optional_signals=optional)
    page = render_html(catalog)
    # Validate charts before touching generated files. The renderer is shared with README.
    charts = {p['slug']: hn.svg(p, evidence) for p in evidence['projects'] if p['eligible']}
    assets = {name: (root / 'site' / name).read_text(encoding='utf-8') for name in ('styles.css', 'catalog.js', 'motion.js')}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, content in assets.items():
        (output / name).write_text(content, encoding='utf-8')
    (output / 'assets/hn').mkdir(parents=True, exist_ok=True)
    for slug, chart in charts.items():
        (output / 'assets/hn' / (slug + '.svg')).write_text(chart, encoding='utf-8')
    (output / 'data').mkdir(exist_ok=True)
    evidence_files = ['alternatives.json', 'hn_evidence.json']
    if optional is not None:
        evidence_files.append('project_signals.json')
    else:
        (output / 'data/project_signals.json').unlink(missing_ok=True)
    for name in evidence_files:
        shutil.copyfile(root / 'data' / name, output / 'data' / name)
    shutil.copytree(root / 'site/vendor', output / 'vendor', dirs_exist_ok=True)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    # A phone/download-friendly edition: every runtime asset and evidence download
    # is embedded, so opening one HTML file never depends on adjacent files.
    standalone = page.replace('href="data/hn_evidence.json">View evidence', 'href="#hn-evidence">View evidence')
    for name in ('vendor/fonts.css', 'styles.css'):
        standalone = standalone.replace(f'<link rel="stylesheet" href="{name}">',
                                        '<style>' + (output / name).read_text(encoding='utf-8') + '</style>')
    for name in ('catalog.js', 'vendor/gsap.min.js', 'vendor/ScrollTrigger.min.js', 'motion.js'):
        # Keep parser ordering identical to deferred scripts: initialize after DOM.
        code = (output / name).read_text(encoding='utf-8')
        encoded = base64.b64encode(code.encode('utf-8')).decode('ascii')
        standalone = standalone.replace(f'src="{name}"', f'src="data:text/javascript;base64,{encoded}"')
    for slug, chart in charts.items():
        encoded = base64.b64encode(chart.encode('utf-8')).decode('ascii')
        standalone = standalone.replace(f'src="assets/hn/{slug}.svg"', f'src="data:image/svg+xml;base64,{encoded}"')
    for name in ['catalog.json', *('data/' + item for item in evidence_files)]:
        encoded = base64.b64encode((output / name).read_bytes()).decode('ascii')
        standalone = standalone.replace(f'href="{name}"',
                                        f'download="{Path(name).name}" href="data:application/json;base64,{encoded}"')
    standalone = standalone.replace('href="./"', 'href="#page-title"')
    (output / 'standalone.html').write_text(standalone, encoding='utf-8')
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'tmp/site')
    parser.add_argument('--source-sha', help='Explicit full source commit SHA, supplied by the caller; never inferred')
    args = parser.parse_args()
    catalog = build(args.output, args.source_sha)
    print(f"Built {len(catalog['projects'])} projects / {catalog['category_memberships']} category memberships in {args.output}")
    print(f"Cached GitHub metrics as of {catalog['metrics_as_of']}; no data fetched or deployed.")


if __name__ == '__main__':
    main()
