"""Static weekly draw archive, rendered only from committed draw records."""
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import shutil

from weekly_draw import visible


def build(catalog, doc, output, root):
    output, root = Path(output), Path(root)
    target = output / 'draws'
    target.mkdir(exist_ok=True)
    categories = {c['id']: c['name'] for c in catalog['categories']}
    current_ids = {p['id'] for p in catalog['projects']}
    editions = visible(doc)
    sections = []
    seen = set()
    # Count appearances chronologically; render newest first.
    rendered = []
    for edition in editions:
        week = edition['display_week']
        end = (date.fromisoformat(week) + timedelta(days=6)).isoformat()
        rows = []
        for project in edition['projects']:
            pid = project['id']
            art = project['artwork']
            source = root / 'site' / art['path']
            image = ''
            if source.is_file():
                dest = output / art['path']
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copyfile(source, dest)
                image = f'<img src="../{escape(art["path"], quote=True)}" alt="{escape(art["alt"], quote=True)}" width="{art["width"]}" height="{art["height"]}" loading="lazy">'
            link = '../#project-' + pid if pid in current_ids else project['url']
            status = 'Returning' if pid in seen else 'First appearance'
            domains = ', '.join(categories.get(c, c) for c in project['categories'])
            rows.append(f'<li class="{"has-art" if image else "no-art"}">{image}<div><h3><a href="{escape(link, quote=True)}">{escape(project["name"])}</a></h3><p>{escape(project["description"])}</p><p class="draw-meta">{escape(domains)} · {status}</p></div></li>')
            seen.add(pid)
        recorded = edition['recorded_on']
        rendered.append(f'''<section id="week-{week}" class="draw-edition">
<h2><a href="#week-{week}">{week} — {end}</a></h2>
<p class="draw-meta">Drawn {recorded} for the following week · {edition['eligible_count']} illustrated projects · {len(edition['candidates'])} after cooldown</p>
<ol class="draw-projects">{''.join(rows)}</ol>
<details><summary>Draw record</summary><p>Draw week: {edition['draw_week']}. Cooldown: {edition['cooldown_weeks']} weeks. Algorithm: {escape(edition['algorithm'])}.</p><p class="draw-seed">Seed: {escape(edition['seed'])}</p></details></section>''')
    sections = list(reversed(rendered))
    if not sections:
        sections = ['<p>The first saved draw will appear here when its display week begins. Until then, the original seven remain in the header.</p>']
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weekly draws · Awesome Open*</title><link rel="icon" href="../brand/favicon.ico"><link rel="stylesheet" href="../vendor/fonts.css"><link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="../styles.css"><link rel="stylesheet" href="draws.css"></head>
<body><a class="skip-link" href="#draws">Skip to weekly draws</a>
<header class="site-header"><a class="brand" href="../"><img class="brand-mark" src="../brand/botanical-128.png" alt="" width="64" height="64"><span class="brand-name">Awesome Open*</span></a><nav aria-label="Main"><a href="../#catalog">Catalog</a> · <a href="../observatory/">Observatory</a></nav></header>
<main id="draws" class="draw-archive"><h1>Weekly draws</h1>
<p>Seven illustrated projects, drawn at random each week and displayed the following week. Stars do not affect the draw. A project has a four-week repeat cooldown.</p>
<p>Weeks run Monday–Sunday in America/New_York. Jar positions follow illustration fit, not draw order. The latest available group stays in the header if a new draw cannot be made.</p>
<p><a href="draws.json" download>Download draw records</a></p>
{''.join(sections)}</main><footer class="site-footer"><p><a href="../">Awesome Open*</a> · <a href="https://github.com/awesomeopen/awesome-open">GitHub</a></p></footer></body></html>'''
    (target / 'index.html').write_text(page)
    # Pending draws are retained in the repository but not presented as past displays.
    (target / 'draws.json').write_text(json.dumps({**doc, 'editions': editions}, indent=2, ensure_ascii=False) + '\n')
    shutil.copyfile(root / 'site/draws.css', target / 'draws.css')
