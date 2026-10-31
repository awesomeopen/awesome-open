"""Static Scoreboard and metric-specific specimen trophy links."""
from datetime import date
from html import escape
import json
from pathlib import Path
import shutil

from build_icons import render as render_icon
from build_draw_archive import week_label
from font_assets import content_url, font_asset_url
from weekly_scoreboard import validate

REPOSITORY = 'https://github.com/awesomeopen/awesome-open'
SHORT = {'oldest-repository': 'Repo age', 'release-push-gap': 'Release → push',
         'software-renames': 'Renames', 'hn-streak': 'HN streak',
         'hn-stories': 'HN stories', 'github-stars': 'Stars'}
METHOD = {
    'oldest-repository': 'Days from GitHub repository creation to the frozen metrics date. Equal UTC creation dates share a place.',
    'release-push-gap': 'UTC calendar days from the latest published, full GitHub release to the last repository push. Only positive gaps with both dates enter this board.',
    'software-renames': 'Distinct reviewed software-name changes in the project history ledger. Repository path changes and owner transfers have separate meanings. Coverage is limited to recorded events.',
    'hn-streak': 'Longest run of consecutive UTC dates with at least one matched HN story. Several stories on one day count as one day. Equal longest runs retain the earliest start.',
    'hn-stories': 'Distinct matched HN story IDs in the stated window. Only completed current-window collections enter; a story can match more than one project.',
    'github-stars': 'Cached GitHub star totals at the recorded observation time. Unknown counts are excluded; observed zero remains zero.',
}


def trophy(rank):
    return f'<span class="score-trophy">{render_icon("rank.trophy", "m")}<span>{rank}</span></span>'


def trophy_links(project):
    awards = project.get('scoreboard_trophies', [])
    if not awards:
        return ''
    week = week_label(awards[0]['week'])
    links = []
    preview = any(a.get('preview') for a in awards)
    for award in awards:
        label = f'{"Preview: " if preview else ""}{award["title"]}, place {award["rank"]}, {week}'
        links.append(f'<a href="scoreboard/#{escape(award["metric"])}" title="{escape(label, quote=True)}" aria-label="{escape(label, quote=True)}">{trophy(award["rank"])}<span>{SHORT[award["metric"]]}</span></a>')
    return f'<div class="scoreboard-plate"><span class="scoreboard-edition">{"Preview · " if preview else ""}Scoreboard · {week}</span><nav class="scoreboard-trophies" aria-label="Scoreboard places">{"".join(links)}</nav></div>'


def safe_link(url, label):
    if isinstance(url, str) and url.startswith(('https://', 'http://')):
        return f'<a href="{escape(url, quote=True)}">{escape(str(label))}</a>'
    return escape(str(label))


def evidence_html(metric, row):
    d = row['details']
    pieces = []
    if metric == 'oldest-repository':
        pieces.append('Repository created ' + escape(d['created_at']))
    elif metric == 'release-push-gap':
        pieces += [safe_link(d.get('release_url'), 'Release ' + str(d.get('tag') or '')) + ': ' + escape(d['published_at']),
                   'Last push: ' + escape(d['pushed_at']),
                   'Release cache: ' + escape(str(d.get('release_status', 'unknown'))) +
                   '; observed ' + escape(str(d.get('release_observed_at') or 'unknown'))]
    elif metric == 'software-renames':
        for event in d['events']:
            sources = ' · '.join(safe_link(s['url'], s['title']) for s in event['sources'])
            pieces.append(escape(event['old_name']) + ' → ' + escape(event['new_name']) + ': ' + sources)
    elif metric.startswith('hn-'):
        if metric == 'hn-streak':
            pieces.append(escape(d['first_day']) + ' – ' + escape(d['last_day']) + ' UTC')
        pieces += [safe_link(d.get('search_url'), 'HN search') + ' · ' + escape(d.get('coverage', 'unknown')),
                   'Collected: ' + escape(str(d.get('collected_at') or 'not recorded in legacy cache')),
                   'Latest attempt: ' + escape(str(d.get('checked_at') or 'unknown')) + ' · ' + escape(d.get('attempt_status', 'unknown'))]
    if 'metrics_status' in d:
        pieces.append('GitHub cache: ' + escape(d['metrics_status']) + '; observed ' + escape(str(d.get('metrics_observed_at') or 'unknown')))
    return '<br>'.join(pieces)


def metric_html(metric, current_ids):
    key = metric['id']
    rows = []
    for row in metric['rows']:
        link = '../#project-' + row['id'] if row['id'] in current_ids else row['url']
        rank = trophy(row['rank']) if row['rank'] <= 3 else str(row['rank'])
        cached = row['details'].get('metrics_status') == 'stale' or row['details'].get('release_status') == 'stale'
        stale = '<span class="score-retained">Retained cache</span>' if cached else ''
        rows.append(f'<tr data-project-id="{row["id"]}" data-rank="{row["rank"]}"><td class="score-place">{rank}</td><th scope="row"><a href="{escape(link, quote=True)}">{escape(row["name"])}</a>{stale}<details class="score-evidence"><summary>Evidence</summary><p>{evidence_html(key, row)}</p></details></th><td class="score-value">{row["value"]:,}<span>{metric["unit"]}</span></td></tr>')
    if not rows:
        rows.append('<tr><td colspan="3" class="obs-empty">No qualifying cached observations.</td></tr>')
    extra = ' · includes cutoff ties' if len(metric['rows']) > 10 else ''
    return f'''<section class="score-board" id="{key}" aria-labelledby="{key}-heading"><p><span class="obs-label">Top 10{extra}</span></p><h2 id="{key}-heading">{escape(metric['title'])}</h2><p class="score-coverage">{metric['eligible_count']:,} qualifying projects</p><table><thead><tr><th scope="col">Place</th><th scope="col">Project</th><th scope="col">{metric['unit'].capitalize()}</th></tr></thead><tbody>{''.join(rows)}</tbody></table><details class="obs-disclosure score-method"><summary>How this is measured</summary><p>{METHOD[key]}</p></details></section>'''


def build(catalog, doc, output, root, preview=False):
    validate(doc)
    output, root = Path(output), Path(root)
    target = output / 'scoreboard'
    target.mkdir(exist_ok=True)
    revision = catalog.get('source_sha')
    stamp = safe_link(f'{REPOSITORY}/commit/{revision}', revision[:12]) if revision else 'Local preview; source revision not supplied'
    if doc:
        week = week_label(doc['week'])
        end = date.fromisoformat(doc['hn_window']['end_exclusive'])
        window = f'{doc["hn_window"]["start"]} ≤ UTC date < {end.isoformat()}'
        lead = ('<strong>Provisional preview.</strong> Computed from this checkout’s cached evidence; no weekly edition has been published.' if preview else
                f'Frozen {doc["recorded_on"]} · metrics dated {doc["metrics_as_of"]}.')
        edition = f'<div class="score-scope"><p class="score-week">{week}</p><p>{lead}</p><p>{doc["catalog_count"]:,} catalog projects · six measurements</p></div>'
        jumps = '<nav class="obs-jump score-jump" aria-label="Rankings">' + ''.join(f'<a href="#{m["id"]}">{SHORT[m["id"]]}</a>' for m in doc['metrics']) + '</nav>'
        boards = '<div class="score-boards">' + ''.join(metric_html(m, {p['id'] for p in catalog['projects']}) for m in doc['metrics']) + '</div>'
        details = f'''<section class="obs-section score-notes" id="method"><h2>Edition and coverage</h2><p>Ranks compare the cached facts frozen for this edition. The first successful normal publication each Monday–Sunday week in America/New_York freezes the next snapshot. A delayed publication retains the displayed edition and its original dates.</p><p>Equal values share a place: 1, 1, 3. Canonical Registry ID orders tied rows. Every project tied at the tenth position is shown, so a board may contain more than ten projects. Shared places 1–3 carry the same trophy on their specimen plates.</p><p>HN window: {window}. Completed matching collections: {doc['hn_window']['covered_count']:,}; catalog-URL-only scopes: {doc['hn_window']['url_only_count']:,}. Matching scope varies by project and Algolia coverage is best-effort. Only projects with matched stories enter the HN boards. Retained successful observations keep their collection date and latest attempt status in Evidence.</p><p>Repository age refers to repository creation. Rename counts cover recorded software renames; missing history is unreviewed. Each table states its qualifying coverage. Collection dates and retained-cache states remain in each row’s evidence.</p><details class="obs-disclosure"><summary>Snapshot provenance</summary><p>Captured from {safe_link(f'{REPOSITORY}/commit/{doc["source_sha"]}', doc['source_sha']) if doc['source_sha'] else 'a local preview'} · algorithm {escape(doc['algorithm'])}. Input fingerprints and frozen values are in the snapshot download.</p></details></section>'''
    else:
        edition = '<div class="score-scope"><p>The first weekly edition will appear after the next successful normal publication.</p></div>'
        jumps = boards = details = ''
    download = '<li><a href="snapshot.json" download>Download snapshot</a></li>' if doc else ''
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Awesome Open* Scoreboard</title><meta name="description" content="Weekly Top 10 rankings from Awesome Open’s cached repository facts, reviewed renames and matched HN stories."><link rel="icon" href="../brand/favicon.ico"><link rel="stylesheet" href="../{font_asset_url('vendor/fonts.css', root)}"><link rel="stylesheet" href="../{font_asset_url('tokens.css', root)}"><link rel="stylesheet" href="../{content_url('observatory/observatory.css', root / 'site/observatory.css')}"><link rel="stylesheet" href="{content_url('scoreboard.css', root / 'site/scoreboard.css')}"></head><body class="observatory scoreboard"><a class="skip-link" href="#scoreboard">Skip to scoreboard</a><div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="../">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Field guide"><a href="../#catalog">Catalog</a><a href="../observatory/">Observatory</a><a href="./" aria-current="page">Scoreboard</a><a href="../spotlight/">Spotlight</a></nav></header></div><main id="scoreboard" tabindex="-1"><div class="obs-shell"><section class="obs-hero"><h1>Scoreboard</h1></section>{edition}{jumps}{boards}{details}</div><div class="obs-closing-mark"><img class="obs-logo" src="../brand/botanical-128.png" width="128" height="128" alt="Awesome Open* botanical logo"></div></main><footer class="obs-footer"><div class="obs-shell"><p>Awesome Open* / Scoreboard</p><ul class="obs-footer-links">{download}<li><a href="{REPOSITORY}/blob/main/site/SCOREBOARD.md">Scoreboard method</a></li><li><a href="../#catalog">Return to Catalog</a></li><li><a href="{REPOSITORY}">GitHub</a></li><li>Source revision: {stamp}</li></ul></div></footer></body></html>'''
    (target / 'index.html').write_text(page)
    if doc:
        (target / 'snapshot.json').write_text(json.dumps({**doc, 'preview': preview}, ensure_ascii=False, separators=(',', ':')) + '\n')
    else:
        (target / 'snapshot.json').unlink(missing_ok=True)
    shutil.copyfile(root / 'site/scoreboard.css', target / 'scoreboard.css')
