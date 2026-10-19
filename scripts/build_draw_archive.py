"""Static weekly draw archive, rendered only from committed draw records.

The page uses the Observatory route shell (B42): its header, column, section
labels, closing mark and footer come from ../observatory/observatory.css.
"""
from font_assets import font_asset_url
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import shutil

from weekly_draw import visible

REPOSITORY = 'https://github.com/awesomeopen/awesome-open'


def week_label(week):
    year, number, _ = date.fromisoformat(week).isocalendar()
    return f'{year}-W{number:02d}'


def specimen_html(project, status, output, root, categories, current_ids):
    pid = project['id']
    art = project['artwork']
    source = root / 'site' / art['path']
    image = ''
    if source.is_file():
        dest = output / art['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(source, dest)
        image = f'<img src="../{escape(art["path"], quote=True)}" alt="{escape(art["alt"], quote=True)}" width="{art["width"]}" height="{art["height"]}" loading="lazy" decoding="async">'
    link = '../#project-' + pid if pid in current_ids else project['url']
    domains = ', '.join(categories.get(c, c) for c in project['categories'])
    return (
        f'<li class="draw-specimen {"has-art" if image else "no-art"}">{image}'
        f'<h3><a href="{escape(link, quote=True)}">{escape(project["name"])}</a></h3>'
        f'<p class="draw-function">{escape(project["description"])}</p>'
        f'<p class="draw-meta">{escape(domains)}<br>{status}</p></li>'
    )


def edition_html(edition, rows, latest):
    week = week_label(edition['display_week'])
    label = 'This week' if latest else 'Earlier edition'
    return f'''<section id="{week}" class="draw-edition{" is-latest" if latest else ""}" aria-labelledby="{week}-heading">
<p><span class="obs-label">{label}</span></p>
<h2 id="{week}-heading"><a href="#{week}">{week}</a></h2>
<ol class="draw-projects">{''.join(rows)}</ol>
<details class="obs-disclosure draw-record"><summary>Draw record <span class="obs-muted">drawn {edition['recorded_on']} · {edition['eligible_count']} illustrated · {len(edition['candidates'])} after cooldown</span></summary><dl class="draw-record-list"><div><dt>Draw week</dt><dd>{edition['draw_week']}</dd></div><div><dt>Cooldown</dt><dd>{edition['cooldown_weeks']} weeks</dd></div><div><dt>Algorithm</dt><dd>{escape(edition['algorithm'])}</dd></div><div><dt>Seed</dt><dd class="draw-seed">{escape(edition['seed'])}</dd></div></dl></details></section>'''


def metrics_html(editions, total_projects):
    latest = editions[-1] if editions else None
    seen = {p['id'] for e in editions for p in e['projects']}
    items = [
        ('Current edition', week_label(latest['display_week']) if latest else 'None yet'),
        ('Editions shown', f'{len(editions):,}'),
        ('Projects shown so far', f'{len(seen):,} <span class="obs-of">/ {total_projects:,}</span>'),
        ('Eligible at last draw', f'{latest["eligible_count"]:,}' if latest else 'None yet'),
    ]
    return '<dl class="obs-metrics draw-metrics">' + ''.join(
        f'<div class="obs-metric"><dt><span>{label}</span></dt><dd><span data-metric>{value}</span></dd></div>'
        for label, value in items
    ) + '</dl>'


def build(catalog, doc, output, root):
    output, root = Path(output), Path(root)
    target = output / 'spotlight'
    target.mkdir(exist_ok=True)
    categories = {c['id']: c['name'] for c in catalog['categories']}
    current_ids = {p['id'] for p in catalog['projects']}
    editions = visible(doc)
    seen = set()
    # Count appearances chronologically; render newest first.
    rendered = []
    for number, edition in enumerate(editions):
        rows = []
        for project in edition['projects']:
            status = 'Returning' if project['id'] in seen else 'First appearance'
            rows.append(specimen_html(project, status, output, root, categories, current_ids))
            seen.add(project['id'])
        rendered.append(edition_html(edition, rows, number == len(editions) - 1))
    sections = list(reversed(rendered))
    if not sections:
        sections = ['<section class="draw-edition draw-empty"><p><span class="obs-label">This week</span></p><p class="draw-empty-text">The first saved draw appears here when its display week begins. Until then, the original seven stay in the ledger header.</p></section>']
    revision = catalog.get('source_sha')
    stamp = (
        f'<a href="{REPOSITORY}/commit/{revision}">{revision[:12]}</a>'
        if revision else 'Local preview; source revision not supplied'
    )
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Awesome Open* Spotlight</title><meta name="description" content="Seven illustrated Awesome Open projects, drawn each week and shown the following week, with every past edition."><link rel="icon" href="../brand/favicon.ico"><link rel="stylesheet" href="../{font_asset_url('vendor/fonts.css', root)}"><link rel="stylesheet" href="../{font_asset_url('tokens.css', root)}"><link rel="stylesheet" href="../observatory/observatory.css"><link rel="stylesheet" href="draws.css"></head>
<body class="observatory draws"><a class="skip-link" href="#spotlight">Skip to spotlight</a><div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="../">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Field guide"><a href="../#catalog">Catalog</a><a href="../#about">About</a><a href="./" aria-current="page">Spotlight</a></nav></header></div>
<main id="spotlight" tabindex="-1"><div class="obs-shell"><section class="obs-hero"><h1>Spotlight</h1></section>
<nav class="obs-jump draw-jump" aria-label="Sections" hidden><a href="#editions">Editions</a><a href="draws.json" download>Download draw records</a></nav>
{metrics_html(editions, len(catalog['projects']))}
<div id="editions">{''.join(sections)}</div>
</div>
<div class="obs-closing-mark"><img class="obs-logo" src="../brand/botanical-128.png" width="128" height="128" alt="Awesome Open* botanical logo"></div></main>
<footer class="obs-footer"><div class="obs-shell"><p>Awesome Open* / Spotlight</p><ul class="obs-footer-links"><li><a href="draws.json" download>Download draw records</a> · <a href="{REPOSITORY}/blob/main/site/WEEKLY-DRAWS.md">Draw contract</a></li><li><a href="{REPOSITORY}">GitHub</a></li><li>Source revision: {stamp}</li></ul></div></footer></body></html>'''
    (target / 'index.html').write_text(page)
    # Pending draws are retained in the repository but not presented as past displays.
    (target / 'draws.json').write_text(json.dumps({**doc, 'editions': editions}, indent=2, ensure_ascii=False) + '\n')
    shutil.copyfile(root / 'site/draws.css', target / 'draws.css')

