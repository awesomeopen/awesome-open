#!/usr/bin/env python3
"""Build the complete, offline static catalog. No network, dependencies or deployment."""

import argparse
import html
import json
from pathlib import Path
import shutil

from build_catalog import build_catalog
import update_hn as hn
import update_stats as stats

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


def project_html(project, categories, catalog):
    pid = escape(project["id"])
    name = escape(project["name"])
    tags = " ".join(
        f'<a class="tag" data-category="{escape(cid)}" '
        f'href="{escape(source_url(catalog, "README.source.md", "#" + cid))}">{escape(categories[cid])}</a>'
        for cid in project["categories"])
    alternatives = ""
    if project["alternatives"]:
        links = ", ".join(f'<a href="{escape(a["source_url"])}">{escape(a["name"])}</a>'
                          for a in project["alternatives"])
        evidence = "".join(
            f'<li><a href="{escape(a["source_url"])}">{escape(a["name"])}</a>'
            f' <span class="evidence-date">· Checked {escape(a["checked_utc_date"])}</span>'
            f'<p>{escape(a["scope"])}</p></li>' for a in project["alternatives"])
        alternatives = (f'<p class="alternatives"><span>Alternative to</span> {links}</p>'
                        f'<details class="evidence"><summary>Reviewed comparison evidence</summary>'
                        f'<ul>{evidence}</ul><p>Relevant use cases; check migration caveats and feature fit.</p></details>')
    github = project["github"]
    if github:
        stars = f'<div class="stars" title="{github["stars"]:,} GitHub stars"><span aria-hidden="true">☆</span> {stats.star_count(github["stars"])} <span class="meta-label">stars</span></div>'
        license_text = github["license"] or "License unknown"
        pushed = github["pushed_at"][:10] if github["pushed_at"] else "Unknown"
        created = github["created_at"][:10]
        dates = (f'<div class="dates"><span>Last push <time>{escape(pushed)}</time></span>'
                 f'<span>Repo created <time>{escape(created)}</time></span></div>')
    else:
        stars = '<div class="stars metadata-missing">No cached GitHub metrics</div>'
        license_text = "License unknown"
        dates = ""
    chart = ""
    if project["hn"]:
        attention = project["hn"]
        chart = (f'<a class="hn-chart" href="{escape(attention["search_url"])}" '
                 f'title="Browse HN discussions; attention is not endorsement">'
                 f'<img src="{escape(attention["chart_url"])}" width="120" height="24" '
                 'alt="HN discussions / 2y" loading="lazy"><span>HN discussions / 2y</span></a>')
    return f'''<article class="project-card" id="project-{pid}" data-project-id="{pid}">
  <div class="project-main">
    <div class="project-heading"><h3><a href="{escape(project['url'])}">{name}<span aria-hidden="true" class="external-arrow"> ↗</span></a></h3><a class="permalink" href="#project-{pid}" aria-label="Permalink to {name}">#</a></div>
    <p class="description">{escape(project['description'])}</p>
    <div class="category-tags">{tags}</div>
    {alternatives}
  </div>
  <div class="project-meta">{stars}<div class="license">{escape(license_text)}</div>{dates}{chart}</div>
</article>'''


def render_html(catalog):
    categories = {c["id"]: c["name"] for c in catalog["categories"]}
    count = len(catalog["projects"])
    nav = ''.join(
        f'<a data-category="{escape(c["id"])}" href="{escape(source_url(catalog, "README.source.md", "#" + c["id"]))}">'
        f'<span>{escape(c["name"])}</span><span class="category-count">{c["count"]}</span></a>'
        for c in catalog["categories"])
    category_options = ''.join(f'<option value="{escape(c["id"])}">{escape(c["name"])}</option>' for c in catalog["categories"])
    licenses = sorted({p["github"]["license"] for p in catalog["projects"] if p["github"] and p["github"]["license"]})
    license_options = ''.join(f'<option value="{escape(value)}">{escape(value)}</option>' for value in licenses)
    projects = '\n'.join(project_html(p, categories, catalog) for p in catalog["projects"])
    sha = catalog.get("source_sha")
    revision = (f'<a href="{REPOSITORY}/commit/{sha}">{sha[:12]}</a>' if sha else 'Local preview (revision not supplied)')
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Explore software whose names begin with Open. Search the curated directory by category, reviewed alternatives, and cached GitHub metadata.">
  <meta name="color-scheme" content="light">
  <title>Awesome Open · A directory of Open*</title>
  <link rel="stylesheet" href="styles.css">
  <script src="catalog.js" defer></script>
</head>
<body>
<a class="skip-link" href="#catalog">Skip to catalog</a>
<div class="page-shell">
<header class="site-header">
  <a class="brand" href="./"><span class="brand-mark" aria-hidden="true">O*</span> Awesome Open</a>
  <nav class="header-links" aria-label="About this directory"><a href="#about">About</a><a href="{escape(source_url(catalog, 'CONTRIBUTING.md'))}">Contribute</a><a href="{REPOSITORY}">GitHub ↗</a></nav>
</header>
<section class="hero" aria-labelledby="page-title">
  <p class="eyebrow">A DIRECTORY OF OPEN*</p>
  <h1 id="page-title">Open by name.<br><span>Yours to explore.</span></h1>
  <p class="hero-copy">Discover software called Open. From everyday tools to the building blocks of your next idea.</p>
  <div class="hero-stats"><span><strong>{count}</strong> projects</span><span><strong>{len(categories)}</strong> categories</span><span>Curated, with sources</span></div>
</section>
<div class="layout">
  <aside class="sidebar" aria-label="Catalog categories">
    <details class="category-panel" open><summary>Browse categories</summary>
      <nav class="category-nav" aria-label="Categories"><a data-category="" href="#catalog" aria-current="true"><span>All projects</span><span class="category-count">{count}</span></a>{nav}</nav>
    </details>
    <p class="sidebar-note">One name. Many possibilities.<br>“Open” is the naming criterion, not a license or quality guarantee.</p>
  </aside>
  <main id="catalog" class="catalog-main" tabindex="-1">
    <form id="filters" class="catalog-toolbar" hidden aria-label="Filter projects">
      <div class="search-field"><label for="search">Find your next tool</label><input id="search" name="q" type="search" placeholder="Search projects, descriptions, alternatives…" autocomplete="off" aria-describedby="search-help"><span id="search-help" class="visually-hidden">Search names, descriptions, and reviewed alternative names. Results update as you type.</span></div>
      <div class="filter-grid">
        <div class="filter-field"><label for="category-filter">Category</label><select id="category-filter" name="category"><option value="">All categories</option>{category_options}</select></div>
        <div class="filter-field"><label for="license-filter">Detected license</label><select id="license-filter" name="license"><option value="all">All licenses</option><option value="known">Known license</option><option value="unknown">Unknown license</option>{license_options}</select></div>
        <div class="filter-field"><label for="min-stars">Minimum stars</label><input id="min-stars" name="stars" type="number" min="0" step="1" placeholder="Any"></div>
        <div class="filter-field"><label for="pushed-since">Last pushed on or after</label><input id="pushed-since" name="pushed" type="date"></div>
      </div>
      <div class="toolbar-bottom"><p class="filter-note">GitHub metadata is a snapshot. Unknown licenses remain unknown.</p><button id="clear-filters" type="button">Clear filters</button></div>
      <button class="visually-hidden" type="submit">Apply filters</button>
    </form>
    <noscript><p class="no-script">All {count} projects are available below. Use your browser’s Find to search. Category links open the curated source sections. Enable JavaScript for filters and sorting.</p></noscript>
    <div class="results-heading"><h2 id="result-count" role="status" aria-live="polite" aria-atomic="true">{count} projects</h2><div class="sort-field"><label for="sort-order">Sort by</label><select id="sort-order" name="sort" disabled><option value="name">Name A–Z</option><option value="stars">Most stars</option><option value="pushed">Latest push</option></select></div></div>
    <p id="empty-state" class="empty-state" hidden>No projects match these filters. Try a broader search or clear the filters.</p>
    <div id="project-list" class="project-list">{projects}</div>
  </main>
</div>
<footer class="site-footer" id="about">
  <div><h2>A name is a starting point.</h2><p>Awesome Open includes open-source and proprietary software, hosted services, libraries, and archived projects. Inclusion is not an endorsement or a claim of production readiness. Check each project’s official sources for its current license and suitability.</p></div>
  <div class="method-notes"><p><strong>Read the signals carefully.</strong> Dates refer to GitHub repository creation and last push in UTC, not project launch or releases. Stars and push dates do not establish quality or maintenance status. “Alternative to” links provide reviewed comparison or migration evidence for a specific use case, not feature parity.</p><p>HN charts show matching story submissions over 24 completed months on a shared square-root scale. Coverage is a researched subset; missing charts do not mean no discussion. Attention includes criticism and controversy.</p><p><a href="{escape(source_url(catalog, 'CONTRIBUTING.md', '#hacker-news-attention-sparklines'))}">Methodology</a> · <a href="data/hn_evidence.json">HN evidence</a> · <a href="data/alternatives.json">Alternative evidence</a> · <a href="catalog.json">Catalog JSON</a></p></div>
  <p class="build-info">GitHub metrics as of {escape(catalog['metrics_as_of'])} · Source revision: {revision}<br>Directory content: <a href="{escape(source_url(catalog, 'LICENSE.md'))}">CC0-1.0</a>. Listed projects keep their own licenses.</p>
</footer>
</div>
<script id="catalog-data" type="application/json">{json_for_html(catalog)}</script>
</body>
</html>
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
    catalog = build_catalog(source, snapshot, alternatives, evidence, source_sha=source_sha)
    page = render_html(catalog)
    # Validate charts before touching generated files. The renderer is shared with README.
    charts = {p['slug']: hn.svg(p, evidence) for p in evidence['projects'] if p['eligible']}
    assets = {name: (root / 'site' / name).read_text(encoding='utf-8') for name in ('styles.css', 'catalog.js')}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, content in assets.items():
        (output / name).write_text(content, encoding='utf-8')
    (output / 'assets/hn').mkdir(parents=True, exist_ok=True)
    for slug, chart in charts.items():
        (output / 'assets/hn' / (slug + '.svg')).write_text(chart, encoding='utf-8')
    (output / 'data').mkdir(exist_ok=True)
    for name in ('alternatives.json', 'hn_evidence.json'):
        shutil.copyfile(root / 'data' / name, output / 'data' / name)
    (output / '.nojekyll').write_text('', encoding='utf-8')
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
