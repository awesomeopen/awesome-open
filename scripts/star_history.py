"""Offline, site-only presentation of privacy-safe GitHub star history."""
from copy import deepcopy
from datetime import datetime
import html
import json
import math
import re

import plate_detail
from update_star_history import accepted_history_sources, validate_cache

REPO = re.compile(r'[a-z0-9_.-]+/[a-z0-9_.-]+')
BOUNDARIES = 'GitHub day boundaries are not guaranteed UTC; month-edge counts may differ from UTC months.'
MEANING = 'Stars created in each month that remained at the last successful fetch. Not historical totals, active users, sentiment, or evidence of causation.'


def load_optional(path):
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or not isinstance(value.get('repositories'), dict):
        raise ValueError('Invalid star-history cache')
    return validate_cache(value)


def attach(projects, snapshot, evidence):
    """Attach only exact GitHub identities; unknown data never becomes zero."""
    if snapshot is None:
        return
    if snapshot.get('schema_version') != 1 or not isinstance(snapshot.get('repositories'), dict):
        raise ValueError('Invalid star-history cache')
    validate_cache(snapshot)
    for project in projects.values():
        url = project['url']
        if not url.startswith('https://github.com/'):
            continue
        repo = url.removeprefix('https://github.com/')
        if not REPO.fullmatch(repo):
            continue
        record = snapshot['repositories'].get(repo)
        if record is None:
            continue
        if record.get('repo') != repo or record.get('readme_url') != url:
            raise ValueError('Star-history identity mismatch: ' + repo)
        if record.get('source_url') not in accepted_history_sources(repo):
            raise ValueError('Invalid star-history provider URL')
        selected = deepcopy(record)
        good = selected.get('last_good')
        selected['chart_url'] = None
        selected['hn_monthly_maximum'] = evidence.get('shared_monthly_maximum')
        if good is not None:
            counts, months = good.get('monthly_counts'), good.get('months')
            if (not isinstance(counts, list) or len(counts) != 24 or
                    any(type(n) is not int or n < 0 for n in counts) or
                    not isinstance(months, list) or len(months) != 24 or
                    any(not isinstance(m, str) or not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", m) for m in months)):
                raise ValueError('Invalid star-history monthly counts')
            for key in ('fetched_at', 'window_start', 'window_end_exclusive'):
                datetime.fromisoformat(good[key].replace('Z', '+00:00'))
            if (months == evidence['months'] and good['window_start'] == evidence['window_start']
                    and good['window_end_exclusive'] == evidence['window_end_exclusive']):
                selected['chart_url'] = 'assets/stars/' + project['id'] + '.svg'
            else:
                selected['display_status'] = 'Window mismatch; awaiting refresh'
        project['star_history'] = selected


def svg(project):
    record = project['star_history']
    good = record['last_good']
    counts = good['monthly_counts']
    maximum = max(1, *counts)
    title = html.escape(project['name'] + ': monthly stars retained at fetch / 2y')
    desc = html.escape(f"{good['months'][0]} through {good['months'][-1]}, oldest at left. Independent square-root scale: 0–{maximum} stars/month. Counts: " + ', '.join(map(str, counts)) + '. ' + MEANING + ' ' + BOUNDARIES)
    bars = []
    for i, count in enumerate(counts):
        height = math.sqrt(count / maximum) * 20
        bars.append(f'<rect x="{i*5}" y="{22-height:.3f}" width="4" height="{height:.3f}" fill="#64748b"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="24" viewBox="0 0 120 24" role="img" aria-labelledby="title desc"><title id="title">{title}</title><desc id="desc">{desc}</desc>' + ''.join(bars) + '</svg>\n'


def render(project):
    record = project.get('star_history')
    if record is None:
        return ''
    esc = lambda value: html.escape(str(value), quote=True)
    good = record.get('last_good')
    status = record.get('display_status') or ('Cached' if record.get('status') == 'ok' else 'Stale cached result' if good else 'Unavailable')
    body, window = '<p>History unavailable; no zero values inferred.</p>', ''
    if record.get('chart_url'):
        months = good['months']
        maximum = max(1, *good['monthly_counts'])
        body = (f'<a class="hn-chart star-chart" href="{esc(record["source_url"])}"><img src="{esc(record["chart_url"])}" width="120" height="24" alt="Monthly stars retained at fetch / 2y" loading="lazy">'
                f'<span>{sum(good["monthly_counts"]):,} stars / past 2y</span></a>')
        window = f'<p class="fine-print star-window">{esc(months[0])}&nbsp;–&nbsp;{esc(months[-1])}<br>Independent square-root scale: 0–{maximum:,} stars/month</p>'
    elif good:
        body = '<p>Cached history uses a different month window; chart withheld until aligned.</p>'
    provenance = f'Latest attempt: {esc(record.get("status", "unknown"))}'
    if record.get('checked_at'):
        provenance += ' · Checked ' + esc(record['checked_at'])
    if good:
        provenance += ' · Last successful fetch ' + esc(good['fetched_at'])
    glyph = 'state.current' if record.get('status') == 'ok' else 'state.aged' if good else 'state.failed'
    trigger, panel = plate_detail.detail(
        plate_detail.uid(project['id'], 'stars'), glyph, f'<span class="signal-status">{esc(status)}</span>',
        'GitHub stars: scale, source and retrieval history',
        f'{window}<p class="fine-print">{MEANING} {BOUNDARIES} HN stories and GitHub stars are independent measurements with separate scales. {provenance}</p>',
        [plate_detail.link(record['source_url'], 'Star-history source'),
         plate_detail.link('data/star_history.json', 'GitHub star-history evidence', 'data')])
    return (f'<section class="signal evidence-note star-history" data-signal="star-history"><h4>GitHub stars {trigger}</h4>{body}{panel}</section>')
