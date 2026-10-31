"""Evidence-led Scoreboard history panels; static HTML, SVG and native disclosures."""
from calendar import monthrange
from datetime import date
from html import escape

from weekly_scoreboard import history_view, utc_day

REPOSITORY = 'https://github.com/awesomeopen/awesome-open'


def month_keys(end, count=12):
    year, month = end.year, end.month
    result = []
    for offset in range(count - 1, -1, -1):
        n = year * 12 + month - 1 - offset
        result.append(f'{n // 12:04d}-{n % 12 + 1:02d}')
    return result


def monthly_series(view, metric, project_id, end):
    """Keep the latest actual capture in each month, including missing values."""
    months = month_keys(end)
    chosen = {}
    for observation in view['observations']:
        key = observation['recorded_on'][:7]
        if key in months and observation['recorded_on'] <= end.isoformat():
            if key not in chosen or observation['recorded_on'] > chosen[key]['recorded_on']:
                chosen[key] = observation
    result = []
    for month in months:
        observation = chosen.get(month)
        point = None
        if observation:
            point = next((p for p in observation['metrics'][metric]['points'] if p[0] == project_id), None)
        result.append((month, observation, point))
    return result


def link(url, label):
    if isinstance(url, str) and url.startswith('https://'):
        return f'<a href="{escape(url, quote=True)}">{escape(str(label))}</a>'
    return escape(str(label))


def svg_chart(title, months, values, unit, releases=(), captured_dates=None, step=False):
    """Draw sampled points; only adjacent retained months receive a connector."""
    width, left, right, top, bottom = 360, 72, 344, 20, 115
    maximum = max([v for v in values if v is not None] or [1]) or 1
    first = date.fromisoformat(months[0] + '-01')
    final_month = date.fromisoformat(months[-1] + '-01')
    last = final_month.replace(day=monthrange(final_month.year, final_month.month)[1])
    span = max(1, (last - first).days)
    x_date = lambda day: left + (day - first).days / span * (right - left)
    x = lambda i: x_date(date.fromisoformat((captured_dates[i] if captured_dates else None) or months[i] + '-01'))
    y = lambda value: bottom - value / maximum * (bottom - top)
    out = [f'<svg class="score-chart" viewBox="0 0 {width} 150" role="img" aria-label="{escape(title, quote=True)}">',
           f'<title>{escape(title)}</title><desc>Observed cached measurements, not an interpolated activity history. Missing values leave gaps. Exact dates and sources follow.</desc>',
           f'<path class="score-axis" d="M{left} {top} V{bottom} H{right}"/>',
           f'<text x="{left - 5}" y="{top + 4}" text-anchor="end">{maximum:,}</text>',
           f'<text x="{left - 5}" y="{bottom + 4}" text-anchor="end">0</text>']
    prior = None
    for index, (month, value) in enumerate(zip(months, values)):
        if index in {0, 2, 4, 6, 8, len(months) - 1}:
            tick_x = x_date(date.fromisoformat(month + '-01'))
            out.append(f'<text x="{tick_x:.2f}" y="135" text-anchor="middle">{escape(month[5:])}</text>')
        if value is None:
            prior = None
            continue
        if prior is not None:
            segment = f'H{x(index):.2f} V{y(value):.2f}' if step else f'L{x(index):.2f} {y(value):.2f}'
            out.append(f'<path class="score-series" d="M{x(prior):.2f} {y(values[prior]):.2f} {segment}"/>')
        out.append(f'<circle class="score-point" data-captured="{escape(str(captured_dates[index] if captured_dates else month))}" cx="{x(index):.2f}" cy="{y(value):.2f}" r="3"><title>{escape(month)}: {value:,} {escape(unit)}</title></circle>')
        prior = index
    for published, label in releases:
        month = published[:7]
        if month in months:
            i = months.index(month)
            out.append(f'<path class="score-release" d="M{x_date(utc_day(published)):.2f} {top} V{bottom}"><title>{escape(label)} · {escape(published)}</title></path>')
    out.append('</svg>')
    return ''.join(out)


def history_table(series, metric, unit):
    rows = []
    for month, observation, point in series:
        if observation is None:
            continue
        captured = observation['recorded_on']
        source = link(f'{REPOSITORY}/commit/{observation["source_sha"]}', 'Source snapshot') if observation.get('source_sha') else 'Local preview'
        coverage = observation['metrics'][metric]['eligible_count']
        coverage_text = f'{coverage:,} qualifying · {observation["coverage"]}'
        if point is None:
            value = 'No retained value'
            detail = ''
        else:
            value = f'{point[1]:,} {unit}'
            details = point[2]
            observed = details.get('metrics_observed_at') or details.get('collected_at')
            detail = (' · source dated ' + escape(observed)) if observed else ' · source date unavailable'
            if metric == 'release-push-gap':
                detail += '<br>' + link(details.get('release_url'), 'Release ' + str(details.get('tag') or ''))
                detail += ': ' + escape(str(details.get('published_at') or 'unknown'))
                detail += '<br>Last push: ' + escape(str(details.get('pushed_at') or 'unknown'))
            if details.get('metrics_status') == 'stale' or details.get('release_status') == 'stale':
                detail += ' · retained cache'
        rows.append(f'<tr><th scope="row">{captured}</th><td>{value}</td><td>{source}{detail}<br>{escape(coverage_text)}</td></tr>')
    if not rows:
        return '<p>No captured measurements in this view.</p>'
    return '<details class="score-values"><summary>Values and sources</summary><table><caption>Latest retained capture in each month</caption><thead><tr><th scope="col">Captured</th><th scope="col">Value</th><th scope="col">Evidence</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></details>'


def series_html(view, metric, row, end):
    series = monthly_series(view, metric['id'], row['id'], end)
    months = [entry[0] for entry in series]
    values = [entry[2][1] if entry[2] else None for entry in series]
    count = sum(v is not None for v in values)
    releases = []
    if metric['id'] == 'release-push-gap':
        releases = sorted({(p[2]['published_at'], 'Release ' + str(p[2].get('tag') or ''))
                           for _, _, p in series if p and p[2].get('published_at')})
    title = row['name'] + ': ' + metric['title']
    note = f'{count} monthly capture' + ('' if count == 1 else 's') + '.'
    if count == 1:
        note += ' One point is available; later publications will add observations.'
    chart = svg_chart(title, months, values, metric['unit'], releases,
                      [observation['recorded_on'] if observation else None for _, observation, _ in series],
                      step=metric['id'] == 'release-push-gap')
    release_text = ''
    if metric['id'] == 'release-push-gap':
        d = row['details']
        release_text = f'<p>{link(d.get("release_url"), "Latest full release " + str(d.get("tag") or ""))}: {escape(d["published_at"])}<br>Last push: {escape(d["pushed_at"])}</p>'
        if any(p[:7] in months for p, _ in releases):
            release_text += '<p>Dashed markers show evidenced release publication dates.</p>'
    return f'<p class="score-history-scope">{months[0]} – {months[-1]} · observed monthly captures</p>{chart}<p>{note}</p>{release_text}{history_table(series, metric["id"], metric["unit"])}'


def creation_html(rows):
    """Compare actual creation dates, never plot inevitable age growth."""
    dated = [(row, utc_day(row['details']['created_at'])) for row in rows]
    earliest = min(day for _, day in dated)
    latest = max(day for _, day in dated)
    span = max(1, (latest - earliest).days)
    parts = ['<p>Repository creation dates</p><svg class="score-chart score-creation" viewBox="0 0 360 140" role="img" aria-label="Repository creation date comparison"><title>Repository creation date comparison</title>']
    for index, (row, day) in enumerate(dated):
        y = 24 + index * 32
        x = 30 + (day - earliest).days / span * 300
        parts.append(f'<path class="score-axis" d="M30 {y} H330"/><circle class="score-point" cx="{x:.2f}" cy="{y}" r="4"><title>{escape(row["name"])}: {day.isoformat()}</title></circle>')
    parts += [f'<text x="30" y="130">{earliest.year}</text><text x="330" y="130" text-anchor="end">{latest.year}</text></svg>', '<ol class="score-event-list">']
    for row, day in dated:
        parts.append(f'<li><time datetime="{day.isoformat()}">{day.isoformat()}</time><strong>{escape(row["name"])}</strong></li>')
    return ''.join(parts) + '</ol>'


def rename_html(row):
    events = row['details'].get('events', [])
    parts = ['<ol class="score-event-list">']
    for event in events:
        occurred = event.get('occurred') or {}
        value = occurred.get('value')
        occurrence = escape(str(value)) if value else 'Occurrence date unrecorded'
        precision = occurred.get('precision')
        if precision and precision != 'day':
            occurrence += ' (' + escape(precision) + ')'
        facts = []
        if event.get('first_observed_at'):
            facts.append('First recorded: ' + escape(event['first_observed_at']))
        if event.get('checked_at'):
            facts.append('Evidence reviewed: ' + escape(event['checked_at']))
        if not facts:
            facts.append('Discovery and review dates were not retained in this snapshot.')
        sources = ' · '.join(link(s['url'], s.get('title') or s['url']) for s in event['sources'])
        parts.append(f'<li><span>{occurrence}</span><strong>{escape(event["old_name"])} → {escape(event["new_name"])}</strong><p>{"<br>".join(facts)}</p><p>{sources}</p></li>')
    return ''.join(parts) + '</ol>'


def streak_html(row, doc):
    d = row['details']
    text = f'{d["first_day"]} – {d["last_day"]} UTC · {row["value"]:,} consecutive story days'
    single = d['first_day'] == d['last_day']
    marks = ('<circle class="score-point" cx="180" cy="24" r="4"/>' if single else
             '<path class="score-series" d="M20 24 H340"/><circle class="score-point" cx="20" cy="24" r="4"/><circle class="score-point" cx="340" cy="24" r="4"/>')
    labels = (f'<text x="180" y="52" text-anchor="middle">{escape(d["first_day"])}</text>' if single else
              f'<text x="20" y="52">{escape(d["first_day"])}</text><text x="340" y="52" text-anchor="end">{escape(d["last_day"])}</text>')
    chart = f'<svg class="score-chart score-streak" viewBox="0 0 360 70" role="img" aria-label="{escape(text, quote=True)}"><title>{escape(text)}</title>{marks}{labels}</svg>'
    return chart + f'<p>{row["value"]:,} consecutive UTC story days.</p><p>Search window: {doc["hn_window"]["start"]} to {doc["hn_window"]["end_exclusive"]} (end exclusive).</p>'


def hn_scope(doc):
    window = doc.get('hn_window')
    if not window:
        return ''
    return f'<p>Search window: {escape(window["start"])} to {escape(window["end_exclusive"])} (end exclusive). Counts describe this matching scope, not all HN mentions.</p>'


def monthly_stories_html(row, doc):
    d = row['details']
    bins = d.get('monthly_stories')
    if not bins:
        return '<p>Monthly story counts were not retained in this snapshot. The current table retains the evidenced window total.</p>' + hn_scope(doc)
    bins = bins[-12:]
    maximum = max([b['value'] for b in bins] or [1]) or 1
    parts = ['<p>Matched stories · last 12 retained months</p><svg class="score-chart" viewBox="0 0 360 150" role="img" aria-label="Monthly matched HN stories"><title>Monthly matched HN stories</title>', f'<text x="20" y="18" text-anchor="end">{maximum:,}</text><text x="20" y="114" text-anchor="end">0</text>']
    for index, entry in enumerate(bins):
        x, height = 24 + index * 27, entry['value'] / maximum * 90
        parts.append(f'<rect class="score-bar" x="{x}" y="{110-height:.2f}" width="18" height="{height:.2f}"><title>{entry["month"]}: {entry["value"]} stories</title></rect>')
        if index % 2 == 0 or index == len(bins) - 1:
            parts.append(f'<text x="{x+9}" y="132" text-anchor="middle">{entry["month"][5:]}</text>')
    parts += ['</svg>', f'<p>{bins[0]["month"]} – {bins[-1]["month"]}. Collected {escape(str(d.get("collected_at") or "at an unrecorded legacy date"))}; {escape(d.get("coverage", "unknown matching scope"))}.</p>',
              '<details class="score-values"><summary>Monthly values</summary><table><thead><tr><th scope="col">Month</th><th scope="col">Stories</th></tr></thead><tbody>']
    for entry in bins:
        parts.append(f'<tr><th scope="row">{entry["month"]}</th><td>{entry["value"]:,}</td></tr>')
    return ''.join(parts) + '</tbody></table></details>' + hn_scope(doc) + '<p>' + link(d.get('search_url'), 'HN search') + '</p>'


def over_time(metric, doc, view=None):
    rows = metric['rows'][:3]
    if not rows:
        return ''
    key = metric['id']
    if key == 'oldest-repository':
        content = creation_html(rows)
    else:
        if key in ('release-push-gap', 'github-stars') and view is None:
            view = history_view(doc)
        end = date.fromisoformat(doc['recorded_on'])
        panels = []
        for index, row in enumerate(rows):
            if key in ('release-push-gap', 'github-stars'):
                body = series_html(view, metric, row, end)
            elif key == 'software-renames':
                body = rename_html(row)
            elif key == 'hn-streak':
                body = streak_html(row, doc)
            else:
                body = monthly_stories_html(row, doc)
            panels.append(f'<details class="score-project-history"{" open" if index == 0 else ""}><summary>{escape(row["name"])}</summary>{body}</details>')
        content = f'<p>{len(rows)} projects from the current table. Open a name to inspect its evidence.</p>' + ''.join(panels)
    return f'<details class="obs-disclosure score-history"><summary>Over time</summary><div class="score-history-body">{content}</div></details>'
