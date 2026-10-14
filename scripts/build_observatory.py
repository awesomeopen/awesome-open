"""Small, deterministic observatory view of the already-validated catalog.

No collectors, wall clock, inferred founding dates or synthetic history. The same
thin projection drives server-rendered tables and progressive browser filtering.
"""
from collections import Counter
from datetime import date, datetime, timezone
import base64
import csv
from html import escape
import io
import json
from pathlib import Path
from build_catalog import canonical_url
import re
import shutil

REPOSITORY = 'https://github.com/awesomeopen/awesome-open'
RECENCY = [('0–30 days', 30), ('31–90 days', 90), ('91–365 days', 365), ('366–730 days', 730), ('Over 730 days', None)]
AGES = [('0–365 days', 365), ('366–1,826 days', 1826), ('1,827–3,653 days', 3653), ('Over 3,653 days', None)]
CSV_FIELDS = ['id', 'name', 'url', 'categories', 'github', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_as_of', 'source_sha']


def days_before(value, as_of):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?', value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
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
            index = next(i for i, (_, limit) in enumerate(buckets) if limit is None or days <= limit)
        counts[index] += 1
    return [[label, counts[i]] for i, (label, _) in enumerate(buckets)] + [['Unknown', counts[-1]]]


def project_index(catalog):
    """Do not ship prose, raw Scorecard checks, artwork or complete signal objects."""
    rows = []
    seen = set()
    for project in catalog['projects']:
        if project['id'] in seen:
            raise ValueError('Duplicate observatory project identity')
        seen.add(project['id'])
        github = project.get('github') or {}
        release = (project.get('signals') or {}).get('release') or {}
        good = release.get('last_good') or {}
        rows.append(dict(id=project['id'], name=project['name'], url=project['url'],
                         categories=list(dict.fromkeys(project['categories'])), github=bool(github),
                         stars=github.get('stars'), license=github.get('license'),
                         created_at=github.get('created_at'), pushed_at=github.get('pushed_at'),
                         release_at=good.get('value', {}).get('published_at'),
                         release_status=release.get('status', 'not checked'),
                         release_checked_at=release.get('checked_at')))
    return dict(schema_version=1, metrics_as_of=catalog['metrics_as_of'], source_sha=catalog.get('source_sha'),
                categories=[dict(id=c['id'], name=c['name']) for c in catalog['categories']], projects=rows)


def aggregate(index, projects=None):
    projects = index['projects'] if projects is None else projects
    licenses = Counter(p['license'] for p in projects if p['license'])
    license_rows = sorted(licenses.items(), key=lambda pair: (-pair[1], pair[0]))
    license_rows.append(('Unknown', sum(not p['license'] for p in projects)))
    categories = [[c['name'], sum(c['id'] in p['categories'] for p in projects)] for c in index['categories']]
    known_ids = {c['id'] for c in index['categories']}
    unmapped = sum(not (known_ids & set(p['categories'])) for p in projects)
    if unmapped:
        categories.append(['Unknown', unmapped])
    ranked = sorted((p for p in projects if p['github'] and p['stars'] is not None), key=lambda p: (-p['stars'], p['name'], p['id']))
    stars = sum(p['stars'] for p in ranked)
    leaders = ranked[:10]
    concentration = sum(p['stars'] for p in leaders)
    star_rows = [[p['name'], p['stars']] for p in leaders]
    if len(ranked) > 10:
        star_rows.append(['Other mapped projects', stars - concentration])
    return dict(total=len(projects), mapped=sum(p['github'] for p in projects), stars=stars,
                known_license=sum(bool(p['license']) for p in projects), leader_count=len(leaders),
                concentration=round(100 * concentration / stars, 1) if stars else None,
                categories=categories, licenses=license_rows, star_rows=star_rows,
                ages=histogram(projects, 'created_at', index['metrics_as_of'], AGES),
                pushes=histogram(projects, 'pushed_at', index['metrics_as_of'], RECENCY),
                releases=histogram(projects, 'release_at', index['metrics_as_of'], RECENCY))


def coverage(catalog, hn):
    projects = catalog['projects']
    urls = {p['url'] for p in projects}
    tracked = [p for p in hn.get('projects', []) if canonical_url(p['readme_url']) in urls]
    ids = set()
    matches = 0
    for project in tracked:
        local = {str(s['id']) for s in project.get('stories', [])}
        ids.update(local)
        matches += len(local)
    result = dict(total=len(projects), github=sum(bool(p.get('github')) for p in projects),
                  alternatives=sum(bool(p.get('alternatives')) for p in projects),
                  summaries=sum(bool(p.get('function_summary')) for p in projects),
                  deployment=sum(bool(p.get('deployment')) for p in projects),
                  artwork=sum(bool(p.get('artwork')) for p in projects),
                  hn_tracked=len(tracked), hn_eligible=sum(p.get('eligible') is True for p in tracked),
                  hn_unique_stories=len(ids), hn_project_matches=matches,
                  hn_window_start=hn.get('window_start'), hn_window_end_exclusive=hn.get('window_end_exclusive'),
                  hn_checked=hn.get('refreshed_utc_date'),
                  star_history=sum(bool(p.get('star_history', {}).get('last_good')) for p in projects),
                  star_charts=sum(bool(p.get('star_history', {}).get('chart_url')) for p in projects),
                  signals_collected_at=catalog.get('signals_collected_at'))
    for provider in ('release', 'scorecard'):
        records = [(p.get('signals') or {}).get(provider) for p in projects]
        result[provider] = dict(checked=sum(bool(r and r.get('checked_at')) for r in records),
                               cached=sum(bool(r and r.get('last_good')) for r in records),
                               states=dict(sorted(Counter(r.get('status', 'not checked') if r else 'not checked' for r in records).items())))
    return result


def safe_csv(value):
    value = '' if value is None else str(value).lower() if isinstance(value, bool) else str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value


def csv_text(index):
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(CSV_FIELDS)
    for project in index['projects']:
        row = {**project, 'categories': '; '.join(project['categories']), 'metrics_as_of': index['metrics_as_of'], 'source_sha': index['source_sha']}
        writer.writerow([safe_csv(row.get(key)) for key in CSV_FIELDS])
    return output.getvalue()


def json_html(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def chart(identifier, number, title, note, rows, unit='Projects'):
    maximum = max([value for _, value in rows] or [0])
    height = max(80, len(rows) * 32 + 44)
    marks = []
    for i, (label, value) in enumerate(rows):
        y = 36 + i * 32
        width = 330 * value / maximum if maximum else 0
        short_label = label[:28] + '…' if len(label) > 29 else label
        bar_class = 'chart-bar chart-bar-unknown' if label == 'Unknown' else 'chart-bar'
        marks.append(f'<text class="chart-label" x="0" y="{y + 11}">{escape(short_label)}</text><rect class="{bar_class}" data-key="{escape(label, quote=True)}" data-count="{value}" x="240" y="{y}" width="{width:.6f}" height="15"/><text class="chart-count" x="640" y="{y + 11}" text-anchor="end">{value:,}</text>')
    guides = ''.join(f'<line class="{"chart-zero" if tick == 0 else "chart-gridline"}" x1="{240 + 330 * tick / 4}" x2="{240 + 330 * tick / 4}" y1="24" y2="{height - 10}"/>' for tick in range(5))
    empty = '<text class="chart-label" x="0" y="53">No observed values in this selection.</text>' if not rows else ''
    visual = f'<div class="chart-visual" tabindex="0" role="region" aria-label="{escape(title, quote=True)} visual; scroll horizontally if needed"><svg aria-hidden="true" focusable="false" viewBox="0 0 640 {height}"><text class="chart-scale" x="240" y="14">0</text><text class="chart-scale" x="570" y="14" text-anchor="end">{maximum:,} {unit.lower()}</text>{guides}{"".join(marks)}{empty}</svg></div>'
    table_rows = ''.join(f'<tr data-key="{escape(label, quote=True)}" data-count="{value}"><th scope="row">{escape(label)}</th><td>{value:,}</td></tr>' for label, value in rows)
    if not rows:
        table_rows = '<tr><td colspan="2">No observed values in this selection.</td></tr>'
    table = '<table class="chart-table"><caption>' + escape(title) + '</caption><thead><tr><th scope="col">Label</th><th scope="col">' + unit + '</th></tr></thead><tbody>' + table_rows + '</tbody></table>'
    return f'<section class="obs-chart" id="{identifier}"><div class="obs-chart-head"><p class="obs-kicker">{number} / {unit.lower()}</p><h2>{title}</h2><p>{note}</p><p class="chart-scale">Linear scale from zero.</p></div>{visual}<details><summary>Chart data</summary>{table}</details></section>'


def render(index, counts, covered):
    esc = lambda v: escape(str(v), quote=True)
    revision = index['source_sha']
    source = f'{REPOSITORY}/blob/{revision or "main"}'
    stamp = f'<a href="{REPOSITORY}/commit/{revision}">{revision[:12]}</a>' if revision else 'Local preview; source revision not supplied'
    art = '<img class="obs-logo" src="../brand/botanical-128.png" width="128" height="128" alt="Awesome Open* botanical logo">'
    options = ''.join(f'<option value="{esc(c["id"])}">{esc(c["name"])}</option>' for c in index['categories'])
    metrics = ''.join(f'<div class="obs-metric"><dt>{label}</dt><dd data-metric="{key}">{value:,}</dd></div>' for key, label, value in [('total','Unique projects',counts['total']),('mapped','Cached GitHub metrics',counts['mapped']),('stars','Observed GitHub stars',counts['stars']),('known-license','Detected license available',counts['known_license'])])
    concentration = (f'The 10 most-starred projects hold {counts["concentration"]:.1f}% of observed stars.' if counts['leader_count'] == 10 and counts['concentration'] is not None else f'{counts["leader_count"]} projects have an observed star count.')
    charts = ''.join([
        chart('category-chart','01','Projects by category','Projects can belong to several categories.',counts['categories']),
        chart('license-chart','02','Detected licenses','Cached GitHub license identifiers. Missing or unrecognized identifiers are Unknown.',counts['licenses']),
        chart('star-chart','03','GitHub stars','Top 10 (by GitHub stars).',counts['star_rows'],'Stars'),
        chart('age-chart','04','Repository age','Days since GitHub repository creation.',counts['ages']),
        chart('push-chart','05','Last repository push','Days since last repository push.',counts['pushes']),
        chart('release-chart','06','Latest GitHub release','Days since the cached latest full GitHub release. Excludes prereleases. Cache status appears in the data table and CSV.',counts['releases'])])
    project_rows = []
    for p in index['projects']:
        project_rows.append(f'<tr data-id="{p["id"]}"><th scope="row"><a href="../#project-{p["id"]}">{esc(p["name"])}</a></th><td>{esc(p["license"] or "Unknown")}</td><td>{p["stars"] if p["stars"] is not None else "Unknown"}</td>' + ''.join(f'<td>{esc(p[k][:10] if p[k] else "Unknown")}</td>' for k in ['created_at','pushed_at','release_at']) + f'<td>{esc(p["release_status"])}<br>{esc(p["release_checked_at"] or "Not checked")}</td><td><a href="{esc(p["url"])}">Official source</a></td></tr>')
    status = lambda name: '; '.join(f'{v:,} {k}' for k,v in covered[name]['states'].items())
    rows = [
        ('Cached GitHub metrics', covered['github'], 'Projects with cached GitHub metrics.'),
        ('Latest GitHub release',covered['release']['cached'],f'{covered["release"]["checked"]} checked. {status("release")}. Latest full release selected by GitHub.'),
        ('OpenSSF Scorecard',covered['scorecard']['cached'],f'{covered["scorecard"]["checked"]} checked. {status("scorecard")}. Cached automated repository checks.'),
        ('Reviewed alternatives',covered['alternatives'],'Reviewed use-case comparisons.'),
        ('Reviewed function summaries',covered['summaries'],'Source-reviewed function descriptions.'),
        ('Reviewed setup evidence',covered['deployment'],'Limited set of source-reviewed setup instructions.'),
        ('Approved specimen artwork',covered['artwork'],'Original specimen illustrations.'),
        ('HN identity tracking',covered['hn_tracked'],f'{covered["hn_eligible"]} chart-eligible projects; {covered["hn_unique_stories"]} globally distinct story IDs and {covered["hn_project_matches"]} project–story matches in the tracked subset. Stories can match several projects.'),
        ('Cached star history',covered['star_history'],f'{covered["star_charts"]} aligned charts. Monthly stars retained at fetch. Month boundaries may be approximate.')]
    coverage_rows = ''.join(f'<tr><th scope="row">{label}</th><td>{value:,} / {covered["total"]:,}</td><td>{esc(note)}</td></tr>' for label,value,note in rows)
    evidence_links = f'<a href="{source}/data/github_metrics.json">GitHub metric snapshot</a> · <a href="../data/hn_evidence.json">HN evidence</a>'
    if covered['release']['checked'] or covered['scorecard']['checked']:
        evidence_links += ' · <a href="../data/project_signals.json">Release and Scorecard evidence</a>'
    if covered['star_history']:
        evidence_links += ' · <a href="../data/star_history.json">Star-history evidence</a>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Observatory · Awesome Open*</title><meta name="description" content="A snapshot of the Awesome Open collection: categories, detected licenses, repository dates, stars and evidence coverage."><link rel="icon" href="../brand/favicon.ico"><link rel="stylesheet" href="../vendor/fonts.css"><link rel="stylesheet" href="../tokens.css"><link rel="stylesheet" href="observatory.css"><script src="observatory.js" defer></script></head>
<body class="observatory"><a class="skip-link" href="#observatory-main">Skip to observatory</a><div class="obs-shell"><header class="obs-header"><a class="obs-brand" href="../">Awesome Open<span aria-hidden="true">*</span></a><nav class="obs-nav" aria-label="Observatory"><a href="../">Project ledger</a><a href="#coverage">Coverage</a><a href="#project-records">Data</a></nav></header>
<main id="observatory-main" tabindex="-1"><section class="obs-hero"><div class="obs-hero-copy"><p class="obs-kicker">Awesome Open* / snapshot</p><h1>Collection<br>observatory</h1><p class="obs-provenance">Metrics snapshot: <time>{index['metrics_as_of']}</time> UTC<br>Source revision: {stamp}</p></div>{art}</section>
<aside class="obs-finding"><p class="obs-kicker">Whole collection</p><p>{concentration}</p></aside>
<form id="observatory-filters" class="obs-filters" hidden aria-label="Filter observatory"><label for="category-filter">Category<select id="category-filter" name="category"><option value="">All categories</option>{options}</select></label><label for="license-filter">Detected license<select id="license-filter" name="license"><option value="all">Any / unknown</option><option value="known">Detected license available</option><option value="unknown">License unknown</option></select></label><button id="reset-filters" type="button">Reset filters</button></form>
<noscript><p>Filters and filtered CSV export require JavaScript.</p></noscript><p id="selection-summary" role="status" aria-live="polite" aria-atomic="true">{counts['total']} projects selected.</p><dl id="metrics" class="obs-metrics">{metrics}</dl><div class="obs-charts">{charts}</div>
<section id="coverage" class="obs-notes"><p class="obs-kicker">07 / projects</p><h2>Evidence coverage</h2><p>Whole collection; unaffected by filters. Counts are out of {covered['total']} unique projects.</p><div class="obs-table-scroll" tabindex="0" role="region" aria-label="Evidence coverage table"><table><caption>Evidence coverage</caption><thead><tr><th scope="col">Evidence</th><th scope="col">Projects</th><th scope="col">Scope</th></tr></thead><tbody>{coverage_rows}</tbody></table></div><p>Evidence collection: {esc(covered['signals_collected_at'] or 'Not available')}. HN checked: {esc(covered['hn_checked'] or 'Not available')}; window {esc(covered['hn_window_start'])} to {esc(covered['hn_window_end_exclusive'])} (end exclusive). Provider checks can be older than the build.</p><p>{evidence_links}</p></section>
<section id="project-records" class="obs-ledger"><p class="obs-kicker">08 / downloads</p><h2>Project data</h2><p>Dates are UTC.</p><p class="obs-downloads"><a id="export-csv" href="projects.csv" download="awesome-open-observatory.csv">Download selection CSV</a> · <a href="snapshot.json" download>Download complete snapshot JSON</a> · <a href="report.html" download>Download standalone report</a></p><details id="project-data"><summary>Data table</summary><div class="obs-table-scroll" tabindex="0" role="region" aria-label="Project data table"><table id="project-table"><caption>Project records</caption><thead><tr><th scope="col">Project</th><th scope="col">Detected license</th><th scope="col">GitHub stars</th><th scope="col">Repository created</th><th scope="col">Last push</th><th scope="col">Latest full release</th><th scope="col">Release cache / checked UTC</th><th scope="col">Source</th></tr></thead><tbody>{''.join(project_rows)}</tbody></table></div></details></section>
</main><footer class="obs-footer"><p>Awesome Open* / Observatory</p><p><a href="../">Return to project ledger</a> · <a href="{REPOSITORY}">GitHub</a><br>Source revision: {stamp}</p></footer></div><script id="observatory-data" type="application/json">{json_html(index)}</script></body></html>'''


def build(catalog, hn, output, root):
    output, root = Path(output), Path(root)
    target = output / 'observatory'
    target.mkdir(parents=True, exist_ok=True)
    index = project_index(catalog)
    counts, covered = aggregate(index), coverage(catalog, hn)
    page = render(index, counts, covered)
    for name in ['observatory.css','observatory.js']:
        shutil.copyfile(root / 'site' / name, target / name)
    snapshot = {**index, 'aggregate': counts, 'coverage': covered}
    (target / 'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))+'\n',encoding='utf-8')
    (target / 'projects.csv').write_text(csv_text(index),encoding='utf-8',newline='')
    (target / 'index.html').write_text(page,encoding='utf-8')
    report = page
    for href, path in [('../vendor/fonts.css',root/'site/vendor/fonts.css'),('../tokens.css',root/'site/design/tokens.css'),('observatory.css',root/'site/observatory.css')]:
        report = report.replace(f'<link rel="stylesheet" href="{href}">','<style>'+path.read_text(encoding='utf-8')+'</style>')
    encoded = base64.b64encode((root/'site/observatory.js').read_bytes()).decode('ascii')
    report = report.replace('src="observatory.js"',f'src="data:text/javascript;base64,{encoded}"')
    for name,mime in [('snapshot.json','application/json'),('projects.csv','text/csv')]:
        encoded = base64.b64encode((target/name).read_bytes()).decode('ascii')
        report = report.replace(f'href="{name}"',f'href="data:{mime};base64,{encoded}"')
    encoded = base64.b64encode((root/'site/brand/botanical-128.png').read_bytes()).decode('ascii')
    report = report.replace('src="../brand/botanical-128.png"', f'src="data:image/png;base64,{encoded}"')
    icon = base64.b64encode((root/'site/brand/favicon.ico').read_bytes()).decode('ascii')
    report = report.replace('href="../brand/favicon.ico"',f'href="data:image/x-icon;base64,{icon}"')
    report = report.replace(' · <a href="report.html" download>Download standalone report</a>','')
    # Offline report keeps provenance on a pinned source revision. Runtime
    # dependencies and downloads are embedded; optional source links are online.
    for name in ['project_signals.json','hn_evidence.json','star_history.json']:
        report = report.replace(f'href="../data/{name}"',f'href="{REPOSITORY}/blob/{index["source_sha"] or "main"}/data/{name}"')
    report = report.replace('href="../#project-', 'href="https://awesomeopen.github.io/awesome-open/#project-')
    report = report.replace('href="../"','href="https://awesomeopen.github.io/awesome-open/"')
    (target/'report.html').write_text(report,encoding='utf-8')
    return snapshot
