#!/usr/bin/env python3
"""Add preview #1 to an existing offline site bundle. Never called by production."""
import argparse
import json
import shutil
from pathlib import Path
from build_site import catalog_script_url, escape, json_for_html, project_html

ROOT = Path(__file__).resolve().parents[1]
CATEGORY = 'infrastructure--devops'
NOTES = {
    'OpenObserve': ('01', 'Observe', 'Logs, metrics & traces', 'Three signals; one traceable seam.'),
    'OpenResty': ('02', 'Serve', 'Scriptable web platform', 'A passing band, rewritten by its combs.'),
    'OpenTofu': ('03', 'Provision', 'Infrastructure as code', 'A structure grown from an ordered plan.'),
}

def build(output):
    output = Path(output)
    catalog = json.loads((output / 'catalog.json').read_text())
    script_url = catalog_script_url((output / "catalog.js").read_text(encoding="utf-8"))
    category = next(c for c in catalog['categories'] if c['id'] == CATEGORY)
    projects = [{**p, 'leader_categories': [c for c in p.get('leader_categories', []) if c == CATEGORY]} for p in catalog['projects'] if CATEGORY in p['categories']]
    leaders = [p for p in projects if CATEGORY in p.get('leader_categories', [])]
    categories = {c['id']: c['name'] for c in catalog['categories']}
    exhibits = []
    for p in sorted(leaders, key=lambda p: NOTES.get(p['name'], ('99',))[0]):
        if not p.get('artwork'):
            continue
        n,verb,function,note = NOTES.get(p['name'], ('—','Inspect',p['description'],''))
        art=p['artwork'];pid=escape(p['id'])
        exhibits.append(f'''<article class="exhibit exhibit-{n}" aria-labelledby="ex-name-{pid}">
        <div class="plate-head"><span>{n} / {escape(verb)}</span><span>OP-{pid[:8].upper()}</span></div>
        <a class="plate-image" href="#project-{pid}" data-inspect="{pid}" aria-label="Inspect {escape(p['name'])}"><img src="{escape(art['path'])}" alt="{escape(art['alt'])}" width="{art['width']}" height="{art['height']}" decoding="async"><span class="plate-cross" aria-hidden="true">+</span></a>
        <div class="plate-label"><div><p class="plate-function">{escape(function)}</p><h2 id="ex-name-{pid}">{escape(p['name'])}</h2></div><a class="inspect-link" href="#project-{pid}" data-inspect="{pid}">Inspect <span aria-hidden="true">↗</span></a></div>
        <p class="art-note"><span aria-hidden="true">↳</span> {escape(note)}</p></article>''')
    rows='\n'.join(project_html(p,categories,catalog,i+1) for i,p in enumerate(projects))
    # Category links leave this bounded prototype and open the complete directory.
    import re
    rows=re.sub(r'data-category="([^"]+)" href="[^"]+"',r'href="index.html?category=\1"',rows)
    licenses=sorted({p['github']['license'] for p in projects if p.get('github') and p['github'].get('license')})
    options=''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in licenses)
    subset={**catalog,'projects':projects}
    sha=escape(catalog.get('source_sha') or '')
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Infrastructure & DevOps — Awesome Open / Preview 01</title><meta name="robots" content="noindex,nofollow">
    <link rel="icon" href="brand/favicon.ico"><link rel="stylesheet" href="vendor/fonts.css"><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="exhibition.css">
    <script src="{escape(script_url)}" defer></script><script src="exhibition.js" defer></script></head><body class="exhibition-page">
    <a class="skip-link" href="#ex-ledger">Skip to category ledger</a>
    <header class="ex-header"><a class="brand" href="index.html"><img class="brand-mark" src="brand/fruit-96.png" alt="" width="40" height="40"><span>Awesome Open<span class="brand-asterisk">*</span></span></a>
    <form class="ex-search" id="ex-search-form" hidden><label for="ex-search">Search this category</label><input id="ex-search" type="search" placeholder="Name, function, alternative…" autocomplete="off"></form>
    <nav aria-label="Guide"><a href="index.html">All projects ↗</a><span class="preview-stamp">Preview 01</span></nav></header>
    <main class="ex-main"><section class="ex-entrance" aria-labelledby="page-title"><div class="entrance-index"><span>03</span><p>Table of contents</p></div>
    <div class="entrance-title"><p class="eyebrow">Awesome Open / Specimen exhibition</p><h1 id="page-title">Infrastructure<br><span>& DevOps</span></h1></div>
    <div class="entrance-note"><p>Observe systems.<br>Serve requests.<br>Provision infrastructure.</p><span>{len(projects):02d} projects · 03 on display</span></div></section>
    <div class="ex-control-strip"><p><span class="red-mark" aria-hidden="true">●</span> Infrastructure & DevOps</p><div class="view-switch" role="group" aria-label="Browse view" hidden><button data-view="exhibition" aria-pressed="true">Exhibition</button><button data-view="ledger" aria-pressed="false">Ledger</button></div><a href="#ex-ledger">Category ledger ↓</a></div>
    <section class="ex-hall" id="ex-hall" aria-label="Three exhibited specimens">{''.join(exhibits)}</section>
    <p class="hall-caption" id="hall-caption">Three category leaders by cached GitHub stars. Drawings interpret their functions.</p>
    <section class="ex-ledger" id="ex-ledger" aria-labelledby="ledger-title"><div class="ex-ledger-heading"><div><p class="eyebrow">Complete category</p><h2 id="ledger-title">The ledger<span>.</span></h2></div><p id="ex-count" role="status" aria-live="polite">{len(projects)} projects</p></div>
    <form class="ex-filter-form" id="ex-filters" hidden><label>License<select id="ex-license"><option value="all">Any / unknown</option><option value="unknown">Unknown</option>{options}</select></label><label>Order<select id="ex-sort"><option value="name">Name A–Z</option><option value="stars">Most stars</option><option value="pushed">Latest push</option></select></label><button id="ex-reset" type="button">Reset filters ↺</button><p>Snapshot {escape(catalog['metrics_as_of'])} UTC</p></form>
    <noscript><p>All category records are below. Open any row to inspect its evidence.</p></noscript>
    <p class="leader-key">Bold names identify the category’s top three by cached stars.</p><p id="ex-empty" hidden>No matching projects. Broaden the search or reset filters.</p><p id="ex-link-notice" hidden>The linked record is outside the current filters. Reset filters to show it.</p>
    <div class="ledger-columns" aria-hidden="true"><span>Folio</span><span>Specimen</span><span>Observed function</span><span>License</span><span>View</span></div><div id="ex-list">{rows}</div></section>
    </main><footer class="ex-footer"><div><a class="brand" href="index.html">Awesome Open*</a><p>Software named Open. Grouped by what it does.</p></div><div><a href="index.html#method">About the data</a><a href="design/">Style reference</a><a href="#page-title">Back to exhibition ↑</a></div><p>Preview 01 · Infrastructure & DevOps<br>Source revision: <a href="https://github.com/awesomeopen/awesome-open/commit/{sha}">{sha[:12]}</a></p></footer>
    <script type="application/json" id="exhibition-data">{json_for_html(subset)}</script></body></html>'''
    (output/'exhibition.html').write_text(page)
    for filename in ('exhibition.css','exhibition.js'):
        shutil.copyfile(ROOT/'site'/filename,output/filename)
    return {'projects':len(projects),'exhibits':len(exhibits)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(build(parser.parse_args().output))
