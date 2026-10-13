#!/usr/bin/env python3
"""Build the complete, offline static catalog. No network, dependencies or deployment."""

import argparse
import base64
import html
import json
import warnings
from pathlib import Path
import shutil

from build_catalog import build_catalog, load_function_summaries
import update_hn as hn
import update_stats as stats
import signals

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/awesomeopen/awesome-open"
BRAND_ASSETS = {
    "botanical-128.png": "image/png",
    "search-loupe.png": "image/png",
    'favicon.ico': 'image/x-icon',
    'fruit-16.png': 'image/png',
    'fruit-32.png': 'image/png',
    'fruit-96.png': 'image/png',
    'awesome-open-logo.png': 'image/png',
}


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


def signal_time(value, precision='second'):
    return value[:10] + ' (date only)' if precision == 'day' else value


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
            content = (f'<p><a class="note-value" href="{escape(value["html_url"])}">{escape(value["tag_name"])}</a>'
                       f'Published <span class="metric-value">{escape(value["published_at"][:10])}</span></p>')
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
            content = (f'<p><span class="note-value">{aggregate}</span>Scanned <span class="metric-value">{escape(good["observed_at"][:10])}</span> · '
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
        pieces.append(f'<section class="optional-signal evidence-note" data-signal="{provider}"><h4>{title} <span class="signal-status">{state}</span></h4>{content}<details class="note-provenance"><summary>Source &amp; retrieval history</summary><p class="fine-print">' + ' · '.join(provenance) + '</p></details></section>')
    return '<div class="optional-signals">' + ''.join(pieces) + '</div>'


def attach_specimen_art(catalog, root):
    manifest = root / 'data/specimen_art.json'
    if not manifest.exists():
        return
    document = json.loads(manifest.read_text(encoding='utf-8'))
    if document.get('schema_version') != 1 or not isinstance(document.get('artworks'), dict):
        raise ValueError('Invalid specimen art manifest')
    projects = {p['id']: p for p in catalog['projects']}
    for pid, entry in document['artworks'].items():
        if pid not in projects:
            warnings.warn('Specimen art has no current catalog record: ' + pid)
            continue
        if entry.get('review_status') != 'approved':
            continue
        expected = f'specimens/{pid}.webp'
        if entry.get('path') != expected or entry.get('project_url') != projects[pid]['url']:
            raise ValueError('Specimen identity/path mismatch: ' + pid)
        if not isinstance(entry.get('alt'), str) or not entry['alt'].strip():
            raise ValueError('Specimen artwork needs descriptive alt text: ' + pid)
        asset = root / 'site' / expected
        if not asset.is_file():
            warnings.warn('Skipping missing specimen artwork: ' + expected)
            continue
        if asset.is_symlink():
            raise ValueError('Specimen assets must be regular repository files')
        data = asset.read_bytes()
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            raise ValueError('Expected a WebP specimen asset: ' + expected)
        width, height = entry.get('width'), entry.get('height')
        if any(type(v) is not int or not 1 <= v <= 8192 for v in (width, height)):
            raise ValueError('Invalid specimen image dimensions: ' + pid)
        projects[pid]['artwork'] = {k: entry[k] for k in ('path', 'alt', 'width', 'height')}


def project_html(project, categories, catalog, number=0):
    pid = escape(project['id'])
    name = escape(project['name'])
    github = project['github']
    license_text = (github['license'] if github else None) or ''
    pushed = github['pushed_at'][:10] if github and github['pushed_at'] else 'Unknown'
    created = github['created_at'][:10] if github else 'Unknown'
    stars = f'{github["stars"]:,}' if github else 'Unknown'
    tags = ' / '.join(f'<a class="tag" data-category="{escape(cid)}" href="{escape(source_url(catalog, "README.source.md", "#" + cid))}">{escape(categories[cid])}</a>' for cid in project['categories'])
    evidence = ''.join(f'<li><a href="{escape(a["source_url"])}">{escape(a["name"])}</a><span class="evidence-date">Checked {escape(a["checked_utc_date"])}</span><p>{escape(a["scope"])}</p></li>' for a in project['alternatives'])
    alternatives = f'<div class="comparison evidence-note"><h4>Reviewed alternatives</h4><ul>{evidence}</ul></div>' if evidence else ''
    chart = ''
    inline_chart = ''
    if project['hn']:
        attention = project['hn']
        inline_chart = f'<img class="name-sparkline" src="{escape(attention["chart_url"])}" width="80" height="16" alt="HN discussions / 2y" title="HN discussions / 2y: {attention["total_stories"]} matched stories" loading="lazy">'
        chart = f'<div class="signal evidence-note"><h4>HN discussions</h4><a class="hn-chart" href="{escape(attention["search_url"])}" title="HN discussions"><img src="{escape(attention["chart_url"])}" width="120" height="24" alt="HN discussions / 2y" loading="lazy"><span>{attention["total_stories"]} submissions / past 24 months</span></a></div>'
    summary = project.get('function_summary')
    function_detail = ''
    if summary:
        sources = ' / '.join(f'<a href="{escape(item["url"])}">{escape(item["title"])}</a>' for item in summary['sources'])
        function_detail = f'<div class="function-detail"><p>{escape(summary["text"])}</p><p class="function-provenance">{sources} · Reviewed <span class="metric-value">{escape(summary["checked_at"])}</span></p></div>'
    art = project.get('artwork')
    artwork = (f'<figure class="specimen-art"><img src="{escape(art["path"])}" alt="{escape(art["alt"])}" width="{art["width"]}" height="{art["height"]}" loading="lazy" decoding="async"></figure>' if art else '')
    leader_categories = project.get('leader_categories', [])
    leader_label = ' / '.join(categories[c] for c in leader_categories) if leader_categories else ''
    return f'''<article class="project-card" data-leader="{'true' if leader_categories else 'false'}" id="project-{pid}" data-project-id="{pid}">
 <details class="specimen-drawer">
  <summary><span class="folio" aria-hidden="true">{number:03d}</span><span class="name-cell"><span class="specimen-name" id="name-{pid}">{split_name(project['name'])}</span>{inline_chart}<span class="leader-label"{'' if leader_categories else ' hidden'}>{escape(leader_label)}</span></span><span class="description">{escape(project['description'])}</span><span class="license-readout">{escape(license_text)}</span><span class="drawer-sign" aria-hidden="true"></span></summary>
  <div class="specimen-interior{"" if art else " without-art"}" aria-labelledby="name-{pid}">
   <div class="specimen-caption">{artwork}<div class="specimen-identity"><span class="registry">OP-{pid[:8].upper()}</span><span class="sheet-folio">Folio {number:03d}</span><p>{tags}</p><nav class="specimen-links" aria-label="Sources for {name}"><a class="source-link" href="{escape(project['url'])}">Official source</a><a class="permalink" href="#project-{pid}" aria-label="Permalink to {name}">Specimen permalink</a></nav></div></div>
   <div class="diagnostics"><span class="sheet-label">Function</span><p class="record-description">{escape(project["description"])}</p>{function_detail}<dl class="vitals"><div><dt>Detected license</dt><dd>{escape(license_text)}</dd></div><div><dt>GitHub stars</dt><dd>{stars}</dd></div><div><dt>Last repository push</dt><dd>{escape(pushed)}</dd></div><div><dt>Repository created</dt><dd>{escape(created)}</dd></div></dl><div class="evidence-notes">{optional_signal_html(project)}{alternatives}{chart}</div></div>
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
    footer_backgrounds = catalog.get('footer_backgrounds', [])
    footer_art = (f'<img class="footer-art" data-footer-background data-backgrounds="{escape(json.dumps(footer_backgrounds))}" src="{escape(footer_backgrounds[0])}" width="2048" height="682" alt="" loading="lazy" decoding="async">' if footer_backgrounds else '')
    projects = '\n'.join(project_html(p, categories, catalog, i+1) for i, p in enumerate(catalog['projects']))
    signal_projects = [p for p in catalog['projects'] if p.get('signals')]
    signal_coverage = []
    for provider, label in (('release', 'Release'), ('scorecard', 'Scorecard')):
        checked = sum(bool(p['signals'][provider]['checked_at']) for p in signal_projects)
        values = sum(bool(p['signals'][provider]['last_good']) for p in signal_projects)
        signal_coverage.append(f'{label}: {values} cached results / {checked} checked')
    optional_notes = ('<ul class="coverage-notes">' + ''.join(f'<li>{item}</li>' for item in signal_coverage)
                      + f'<li>{len(signal_projects)} mapped GitHub repositories.</li>'
                      + f'<li>Collection snapshot {escape(catalog.get("signals_collected_at"))}.</li></ul>'
                      + '<p><a href="data/project_signals.json">Release and Scorecard evidence</a></p>') if signal_projects else ''
    sha = catalog.get('source_sha')
    revision = f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else 'Local preview (revision not supplied)'
    return f'''<!doctype html>
<html lang="en">
<head>
 <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
 <meta name="description" content="A natural-history field guide to software named Open, with searchable project records, repository data, and reviewed comparisons.">
 <meta name="color-scheme" content="light"><title>Awesome Open — Project ledger</title>
 <link rel="icon" href="brand/favicon.ico" sizes="16x16 32x32 48x48">
 <link rel="icon" type="image/png" href="brand/fruit-16.png" sizes="16x16">
 <link rel="icon" type="image/png" href="brand/fruit-32.png" sizes="32x32">
 <link rel="stylesheet" href="vendor/fonts.css"><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="styles.css?v={escape(sha or 'preview')}">
 <script src="catalog.js" defer></script>
</head>
<body>
<a class="skip-link" href="#catalog">Skip to specimen ledger</a>
<div class="page-shell">
<header class="site-header"><a class="brand" href="./" aria-label="Awesome Open home"><img class="brand-mark" src="brand/botanical-128.png" alt="" width="64" height="64"><span class="brand-name">Awesome Open<span class="brand-asterisk" aria-hidden="true">*</span></span></a><div class="search-field header-search" id="header-search" hidden><label for="search" class="visually-hidden">Search projects</label><div class="search-input"><input id="search" name="q" form="filters" type="search" autocomplete="off" aria-describedby="search-help"><button class="search-submit" type="submit" form="filters" aria-label="Search projects" title="Search projects"><img class="search-icon" src="brand/search-loupe.png" width="32" height="32" alt=""></button></div><span id="search-help" class="visually-hidden">Search names, descriptions, and reviewed alternative names. Results update as you type.</span></div><nav class="header-links" aria-label="Field guide"><a href="#catalog">Ledger</a><a href="#method">About</a><a href="{REPOSITORY}">GitHub</a></nav></header>
<div class="layout">

 <main id="catalog" class="catalog-main" tabindex="-1">
  <h1 id="page-title" class="visually-hidden">Projects</h1>
  <div class="control-row">
 <aside class="sidebar" aria-label="Catalog categories"><details class="category-panel" name="catalog-controls"><summary>Index by function <span aria-hidden="true">+</span></summary><nav class="category-nav" aria-label="Categories"><a data-category="" href="#catalog" aria-current="true"><span>All specimens</span><span class="category-count">{count}</span></a>{nav}</nav></details></aside>
  <form id="filters" class="catalog-toolbar" hidden aria-label="Filter projects">

   <details class="filter-options" name="catalog-controls"><summary>Filters <span aria-hidden="true">+</span></summary><div class="filter-body"><div class="diagnostic-filters"><div class="filter-field"><label for="push-window">Repository push window</label><select id="push-window" name="window"><option value="all">Any observed date</option><option value="recent">Within 90 days of snapshot</option><option value="older">More than 2 years before snapshot</option><option value="unknown">Push date unknown</option></select></div><div class="filter-field"><label for="alternative-filter">Reviewed alternative to</label><select id="alternative-filter" name="alternative"><option value="">Any / not recorded</option>{alternative_options}</select></div><div class="filter-field"><label for="license-filter">Detected license</label><select id="license-filter" name="license"><option value="all">Any / unknown</option><option value="known">Detected license available</option><option value="unknown">License unknown</option>{license_options}</select></div></div>
   <details class="more-filters"><summary>More filters <span aria-hidden="true">+</span></summary><div class="filter-grid"><div class="filter-field"><label for="category-filter">Function</label><select id="category-filter" name="category"><option value="">All categories</option>{category_options}</select></div><div class="filter-field"><label for="metrics-filter">Cached repository metrics</label><select id="metrics-filter" name="metrics"><option value="all">Present or missing</option><option value="present">Present</option><option value="missing">Missing</option></select></div><div class="filter-field"><label for="min-stars">Minimum GitHub stars</label><input id="min-stars" name="stars" type="number" min="0" step="1" placeholder="Any"></div><div class="filter-field"><label for="pushed-since">Last pushed on or after</label><input id="pushed-since" name="pushed" type="date"></div></div></details>
   <div class="toolbar-bottom"><p class="filter-note">Date filters use the {escape(catalog["metrics_as_of"])} UTC snapshot.</p></div></div></details><button class="visually-hidden" type="submit" tabindex="-1">Apply filters</button>
  </form></div>
  <noscript><p class="no-script">All {count} projects are available below. Use your browser’s Find to search and open any specimen drawer. Category links open the curated source sections. Enable JavaScript for filters and sorting.</p></noscript>
  <div class="results-heading"><h2 id="result-count" class="visually-hidden" role="status" aria-live="polite" aria-atomic="true">{count} projects</h2><div class="result-actions"><button id="clear-filters" type="button" disabled>Reset filters <span aria-hidden="true">↺</span></button><div class="sort-field"><label for="sort-order" class="visually-hidden">Sort projects</label><select id="sort-order" name="sort" disabled><option value="name">Name A–Z</option><option value="stars">Most stars</option><option value="pushed">Latest push</option></select></div></div></div>
  <p id="project-link-notice" class="link-notice" role="status" hidden></p><p id="empty-state" class="empty-state" hidden>No projects match these filters. Try a broader search or reset filters.</p>
  <div id="project-list" class="project-list">{projects}</div>
 </main>
</div>
</div>
<div class="page-end" aria-hidden="true"><img src="brand/fruit-96.png" alt="" width="96" height="96" loading="lazy"></div>
<footer class="site-footer{' has-art' if footer_backgrounds else ''}" id="about">{footer_art}<div class="footer-actions"><a href="{escape(source_url(catalog, 'CONTRIBUTING.md'))}">Submit a project</a><a href="standalone.html" download>Download</a><a href="#catalog">Top</a></div><details class="data-notes" id="method" open><summary>About the data <span aria-hidden="true">+</span></summary><div class="colophon"><div><h2>Collection</h2><ul><li>Registry IDs come from canonical URLs</li><li>Folio numbers show alphabetical position</li><li>Bold: Top-3 per category (GitHub stars)</li><li>Specimen illustrations are original artwork, not official logos</li></ul></div><div><h2>Evidence</h2><ul><li>Detected licenses: verify against current official terms</li><li>Repository dates refer to GitHub activity</li><li>HN charts: matched stories / 2 years, shared square-root scale</li><li>Latest GitHub release: follows publisher</li><li>Scorecard: reports automated security-practice checks (combining: aggregate, scored/returned coverage, scan date and check reasons)</li><li>Stale: Old scan/cache or a retained result after an unsuccessful check</li></ul>{optional_notes}<p><a id="hn-evidence" href="data/hn_evidence.json">HN evidence</a> / <a href="data/alternatives.json">Comparison evidence</a> / <a href="catalog.json">Catalog JSON</a></p></div></div></details><div class="footer-baseline"><span>Source revision: {revision} | {count} Projects</span><span>List: <a href="{escape(source_url(catalog, 'LICENSE.md'))}">CC0-1.0</a></span></div></footer>
<script id="catalog-data" type="application/json">{json_for_html(catalog)}</script>
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
    catalog = build_catalog(source, snapshot, alternatives, evidence, source_sha=source_sha, optional_signals=optional,
                            function_summaries=load_function_summaries(root / "data/function_summaries.json"))
    catalog['footer_backgrounds'] = ['footer-backgrounds/' + p.name for p in sorted((root / 'site/footer-backgrounds').glob('*')) if p.is_file() and p.suffix.lower() in {'.webp', '.png'} and not p.is_symlink()]
    attach_specimen_art(catalog, root)
    page = render_html(catalog)
    # Validate charts before touching generated files. The renderer is shared with README.
    charts = {p['slug']: hn.svg(p, evidence) for p in evidence['projects'] if p['eligible']}
    assets = {name: (root / 'site' / name).read_text(encoding='utf-8') for name in ('styles.css', 'catalog.js')}
    assets['tokens.css'] = (root / 'site/design/tokens.css').read_text(encoding='utf-8')
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
    (output / 'vendor').mkdir(exist_ok=True)
    for name in ('fonts.css', 'FONT-LICENSE.txt', 'FONT-PROVENANCE.json'):
        shutil.copyfile(root / 'site/vendor' / name, output / 'vendor' / name)
    for old in ('motion.js', 'vendor/gsap.min.js', 'vendor/ScrollTrigger.min.js', 'vendor/GSAP-PROVENANCE.txt'):
        (output / old).unlink(missing_ok=True)
    shutil.rmtree(output / 'specimens', ignore_errors=True)
    for project in catalog['projects']:
        if 'artwork' in project:
            asset = project['artwork']['path']
            (output / asset).parent.mkdir(exist_ok=True)
            shutil.copyfile(root / 'site' / asset, output / asset)
    shutil.rmtree(output / 'footer-backgrounds', ignore_errors=True)
    for asset in catalog['footer_backgrounds']:
        (output / asset).parent.mkdir(exist_ok=True)
        shutil.copyfile(root / 'site' / asset, output / asset)
    (output / 'brand').mkdir(exist_ok=True)
    for name in BRAND_ASSETS:
        shutil.copyfile(root / 'site/brand' / name, output / 'brand' / name)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    # A phone/download-friendly edition: every runtime asset and evidence download
    # is embedded, so opening one HTML file never depends on adjacent files.
    standalone = page.replace('href="data/hn_evidence.json">View evidence', 'href="#hn-evidence">View evidence')
    for asset in catalog['footer_backgrounds']:
        mime_type = 'image/png' if asset.lower().endswith('.png') else 'image/webp'
        encoded = base64.b64encode((output / asset).read_bytes()).decode('ascii')
        standalone = standalone.replace(f'src="{asset}"', f'src="data:{mime_type};base64,{encoded}"')
        standalone = standalone.replace(f'&quot;{asset}&quot;', f'&quot;data:{mime_type};base64,{encoded}&quot;')
    for name, mime_type in BRAND_ASSETS.items():
        encoded = base64.b64encode((output / 'brand' / name).read_bytes()).decode('ascii')
        for attribute in ('src', 'href'):
            standalone = standalone.replace(f'{attribute}="brand/{name}"',
                                            f'{attribute}="data:{mime_type};base64,{encoded}"')
    for name in ('vendor/fonts.css', 'tokens.css', 'styles.css'):
        href = f'{name}?v={source_sha or "preview"}' if name == 'styles.css' else name
        standalone = standalone.replace(f'<link rel="stylesheet" href="{href}">',
                                        '<style>' + (output / name).read_text(encoding='utf-8') + '</style>')
    for name in ('catalog.js',):
        # Keep parser ordering identical to deferred scripts: initialize after DOM.
        code = (output / name).read_text(encoding='utf-8')
        encoded = base64.b64encode(code.encode('utf-8')).decode('ascii')
        standalone = standalone.replace(f'src="{name}"', f'src="data:text/javascript;base64,{encoded}"')
    for project in catalog['projects']:
        if 'artwork' in project:
            asset = project['artwork']['path']
            encoded = base64.b64encode((output / asset).read_bytes()).decode('ascii')
            standalone = standalone.replace(f'src="{asset}"', f'src="data:image/webp;base64,{encoded}"')
    standalone = standalone.replace('<a href="standalone.html" download>Download</a>', '')
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
