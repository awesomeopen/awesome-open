"""Freeze one weekly ranking of validated cached evidence; no network requests."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

from build_catalog import build_catalog, canonical_url
import project_history
import signals
import update_hn

PATH = 'data/weekly_scoreboard.json'
TIMEZONE = 'America/New_York'
ALGORITHM = 'cached-competition-ranks-v1'
INPUTS = ('README.source.md', 'data/github_metrics.json', 'data/alternatives.json',
          'data/hn_evidence.json', 'data/project_signals.json', 'data/project_history.json')
METRICS = (
    ('oldest-repository', 'Oldest repository', 'days', 'desc'),
    ('release-push-gap', 'Longest release-to-push gap', 'days', 'desc'),
    ('software-renames', 'Most recorded software renames', 'renames', 'desc'),
    ('hn-streak', 'Longest matched HN story-day streak', 'days', 'desc'),
    ('hn-stories', 'Most matched HN stories', 'stories', 'desc'),
    ('github-stars', 'Most cached GitHub stars', 'stars', 'desc'),
)


def monday(day):
    return day - timedelta(days=day.weekday())


def utc_day(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).date() if parsed.tzinfo else date.fromisoformat(value)
    except (ValueError, OverflowError):
        return None


def longest_streak(stories, start, end):
    """One day per UTC date; repeated stories/dates never lengthen a run."""
    days = sorted({day for s in stories if (day := utc_day(s.get('created_at')))
                   and start <= day < end})
    best, run, previous, run_start = (0, None, None), 0, None, None
    for day in days:
        if previous is not None and day == previous + timedelta(days=1):
            run += 1
        else:
            run, run_start = 1, day
        # Equal longest runs retain the earliest start.
        if run > best[0]:
            best = (run, run_start.isoformat(), day.isoformat())
        previous = day
    return best


def ranked(rows):
    ordered = sorted(rows, key=lambda r: (-r['value'], r['id']))
    result, rank, previous = [], 0, None
    for position, row in enumerate(ordered, 1):
        if row['value'] != previous:
            rank = position
        if rank > 10:
            break
        result.append({**row, 'rank': rank})
        previous = row['value']
    return result


def snapshot(catalog, evidence, today, source_sha=None, input_hashes=None):
    as_of = date.fromisoformat(catalog['metrics_as_of'])
    start = utc_day(evidence['window_start'])
    end = utc_day(evidence['window_end_exclusive'])
    hn_by_url = {canonical_url(p['readme_url']): p for p in evidence['projects']}
    queue = {canonical_url(url): item for url, item in evidence.get('queue', {}).items()}
    rows = {m[0]: [] for m in METRICS}
    hn_covered = 0
    url_only = 0
    def add(metric, project, value, details):
        rows[metric].append({k: project[k] for k in ('id', 'name', 'url')} |
                            {'value': value, 'details': details})
    for p in catalog['projects']:
        g = p.get('github') or {}
        meta = {'metrics_status': g.get('status', 'fresh'),
                'metrics_observed_at': g.get('last_success_at', catalog['metrics_as_of'])}
        created = utc_day(g.get('created_at'))
        if created and created <= as_of and g.get('status') != 'unavailable':
            add('oldest-repository', p, (as_of - created).days,
                {**meta, 'created_at': g['created_at']})
        stars = g.get('stars')
        if type(stars) is int and stars >= 0 and g.get('status') != 'unavailable':
            add('github-stars', p, stars, meta)
        release = (p.get('signals') or {}).get('release') or {}
        good = release.get('last_good') or {}
        release_value = good.get('value') or {}
        published, pushed = utc_day(release_value.get('published_at')), utc_day(g.get('pushed_at'))
        if (published and pushed and pushed <= as_of and published < pushed
                and g.get('status') != 'unavailable'):
            add('release-push-gap', p, (pushed - published).days,
                {**meta, 'published_at': release_value['published_at'], 'pushed_at': g['pushed_at'],
                 'release_status': release.get('status', 'unknown'),
                 'release_observed_at': good.get('fetched_at'),
                 'release_url': release_value.get('html_url'), 'tag': release_value.get('tag_name')})
        events = list({e['id']: e for e in p.get('history', []) if e['kind'] == 'software_rename'}.values())
        if events:
            add('software-renames', p, len({e['id'] for e in events}),
                {'events': [{k: e[k] for k in ('id', 'old_name', 'new_name', 'sources', 'occurred')}
                            for e in events]})
        hn = hn_by_url.get(canonical_url(p['url']))
        if hn is not None:
            hn_covered += 1
            url_only += hn.get('coverage') == 'catalog-url-only'
            q = queue.get(canonical_url(p['url']), {})
            provenance = {'coverage': hn.get('coverage', 'reviewed'), 'search_url': hn['search_url'],
                          'collected_at': (q.get('last_good') or {}).get('collected_at'),
                          'attempt_status': q.get('status', 'unknown'), 'checked_at': q.get('checked_at')}
            # The validated current-window projects view contains complete matching
            # observations; incomplete queue pages and historical eligibility are irrelevant.
            stories = {str(s['id']): s for s in hn['stories']}
            if stories:
                add('hn-stories', p, len(stories), provenance)
                days, first, last = longest_streak(stories.values(), start, end)
                if days:
                    add('hn-streak', p, days, {**provenance, 'first_day': first, 'last_day': last})
    result = {'schema_version': 1, 'algorithm': ALGORITHM, 'timezone': TIMEZONE,
              'week': monday(today).isoformat(), 'recorded_on': today.isoformat(),
              'metrics_as_of': catalog['metrics_as_of'], 'source_sha': source_sha,
              'input_hashes': input_hashes or {}, 'catalog_count': len(catalog['projects']),
              'hn_window': {'start': start.isoformat(), 'end_exclusive': end.isoformat(),
                            'covered_count': hn_covered, 'url_only_count': url_only},
              'metrics': [{'id': key, 'title': title, 'unit': unit,
                           'eligible_count': len(rows[key]), 'rows': ranked(rows[key])}
                          for key, title, unit, _ in METRICS]}
    return validate(result)


def validate(doc):
    if doc is None:
        return None
    if (not isinstance(doc, dict) or doc.get('schema_version') != 1
            or doc.get('algorithm') != ALGORITHM or doc.get('timezone') != TIMEZONE):
        raise ValueError('Invalid weekly scoreboard schema')
    week, recorded = date.fromisoformat(doc['week']), date.fromisoformat(doc['recorded_on'])
    if week != monday(recorded):
        raise ValueError('Scoreboard week must contain its recording date')
    date.fromisoformat(doc['metrics_as_of'])
    if doc['source_sha'] is not None and not re.fullmatch(r'[a-f0-9]{40}', doc['source_sha']):
        raise ValueError('Invalid scoreboard source revision')
    if any(k not in INPUTS or not re.fullmatch(r'[a-f0-9]{64}', v) for k, v in doc['input_hashes'].items()):
        raise ValueError('Invalid scoreboard input fingerprint')
    if type(doc['catalog_count']) is not int or doc['catalog_count'] < 0:
        raise ValueError('Invalid scoreboard catalog count')
    window = doc['hn_window']
    if date.fromisoformat(window['start']) >= date.fromisoformat(window['end_exclusive']):
        raise ValueError('Invalid scoreboard HN window')
    if not 0 <= window['url_only_count'] <= window['covered_count'] <= doc['catalog_count']:
        raise ValueError('Invalid scoreboard HN coverage')
    if [m['id'] for m in doc['metrics']] != [m[0] for m in METRICS]:
        raise ValueError('Invalid scoreboard metric set')
    for metric, (_, title, unit, _) in zip(doc['metrics'], METRICS):
        rows = metric['rows']
        if metric['title'] != title or metric['unit'] != unit:
            raise ValueError('Invalid scoreboard metric definition')
        if (type(metric['eligible_count']) is not int
                or not min(10, metric['eligible_count']) <= len(rows) <= metric['eligible_count'] <= doc['catalog_count']):
            raise ValueError('Invalid scoreboard eligible count')
        seen = set()
        for row in rows:
            if (not re.fullmatch(r'[a-f0-9]{64}', row['id']) or row['id'] in seen
                    or hashlib.sha256(canonical_url(row['url']).encode()).hexdigest() != row['id']
                    or not isinstance(row['name'], str) or not row['name'].strip()
                    or type(row['value']) is not int or row['value'] < 0
                    or type(row['rank']) is not int or not 1 <= row['rank'] <= 10
                    or not isinstance(row['details'], dict)):
                raise ValueError('Invalid scoreboard row')
            validate_value(metric['id'], row, doc)
            seen.add(row['id'])
        if rows != ranked([{k: v for k, v in row.items() if k != 'rank'} for row in rows]):
            raise ValueError('Invalid scoreboard competition ranks or ordering')
    return doc


def validate_value(metric, row, doc):
    d, value = row['details'], row['value']
    if metric == 'oldest-repository':
        created = utc_day(d.get('created_at'))
        if not created or (date.fromisoformat(doc['metrics_as_of']) - created).days != value:
            raise ValueError('Scoreboard repository age disagrees with evidence')
    elif metric == 'release-push-gap':
        published, pushed = utc_day(d.get('published_at')), utc_day(d.get('pushed_at'))
        if (not published or not pushed or value <= 0 or (pushed - published).days != value
                or pushed > date.fromisoformat(doc['metrics_as_of'])):
            raise ValueError('Scoreboard release gap disagrees with evidence')
    elif metric == 'software-renames':
        events = d.get('events')
        if (not isinstance(events, list) or not events or len({e['id'] for e in events}) != len(events)
                or value != len(events)):
            raise ValueError('Scoreboard rename count disagrees with evidence')
        for event in events:
            if not event.get('old_name') or not event.get('new_name') or not event.get('sources'):
                raise ValueError('Scoreboard rename evidence is incomplete')
    elif metric == 'hn-streak':
        first, last = utc_day(d.get('first_day')), utc_day(d.get('last_day'))
        if (not first or not last or value <= 0 or (last - first).days + 1 != value
                or not date.fromisoformat(doc['hn_window']['start']) <= first <= last
                < date.fromisoformat(doc['hn_window']['end_exclusive'])):
            raise ValueError('Scoreboard HN streak disagrees with evidence')
    elif metric == 'hn-stories' and value <= 0:
        raise ValueError('Scoreboard HN counts must be positive')


def load(path):
    path = Path(path)
    return validate(json.loads(path.read_text())) if path.exists() else None


def advance(doc, catalog, evidence, today, source_sha=None, input_hashes=None):
    validate(doc)
    if doc is not None:
        if today < date.fromisoformat(doc['recorded_on']):
            raise ValueError('Scoreboard clock cannot move backwards')
        if doc['week'] == monday(today).isoformat():
            return deepcopy(doc)
    return snapshot(catalog, evidence, today, source_sha, input_hashes)


def attach(catalog, doc):
    """Current canonical records share the frozen edition's top-three places."""
    validate(doc)
    for p in catalog['projects']:
        p.pop('scoreboard_trophies', None)
    if doc is None:
        return
    by_id = {p['id']: p for p in catalog['projects']}
    for metric in doc['metrics']:
        for row in metric['rows']:
            if row['rank'] <= 3 and row['id'] in by_id:
                by_id[row['id']].setdefault('scoreboard_trophies', []).append({
                    'metric': metric['id'], 'title': metric['title'], 'rank': row['rank'],
                    'week': doc['week'], 'value': row['value'], 'unit': metric['unit']})


def validate_evidence(evidence):
    update_hn.validate_queue(evidence)
    start, end = utc_day(evidence['window_start']), utc_day(evidence['window_end_exclusive'])
    if not start or not end or start.day != 1 or end.day != 1:
        raise ValueError('Invalid scoreboard HN boundary')
    months, month = [], start
    while month < end and len(months) <= 24:
        months.append(month.strftime('%Y-%m'))
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    if len(months) != 24 or months != evidence['months'] or month != end:
        raise ValueError('Scoreboard HN window does not match its months')
    urls = [canonical_url(p['readme_url']) for p in evidence['projects']]
    if len(set(urls)) != len(urls):
        raise ValueError('Duplicate scoreboard HN identity')


def update(root, source_sha=None, today=None):
    root = Path(root)
    observed = {path: ((root / path).read_bytes() if (root / path).exists() else None) for path in INPUTS}
    content = {path: data for path, data in observed.items() if data is not None}
    target = root / PATH
    previous = target.read_bytes() if target.exists() else None
    read = lambda path: json.loads(content[path]) if path in content else None
    evidence = read('data/hn_evidence.json')
    validate_evidence(evidence)
    catalog = build_catalog(content['README.source.md'].decode(), read('data/github_metrics.json'),
                            read('data/alternatives.json'), evidence, source_sha=source_sha,
                            optional_signals=read('data/project_signals.json'),
                            history=read('data/project_history.json'))
    doc = advance(load(target), catalog, evidence,
                  today or datetime.now(ZoneInfo(TIMEZONE)).date(), source_sha,
                  {path: hashlib.sha256(data).hexdigest() for path, data in content.items()})
    # Existing publisher owns its detached attempt and commits only after validation.
    # Avoid replacing even the local snapshot if an input changed during computation.
    if (any(((root / path).read_bytes() if (root / path).exists() else None) != data
            for path, data in observed.items())
            or (target.read_bytes() if target.exists() else None) != previous):
        raise ValueError('Scoreboard inputs changed during computation')
    encoded = json.dumps(doc, ensure_ascii=False, indent=2) + '\n'
    if not target.exists() or target.read_text() != encoded:
        with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, prefix='.scoreboard-', delete=False) as f:
            temporary = Path(f.name)
            f.write(encoded)
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return doc


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    update(Path(__file__).resolve().parents[1], args.source_sha)
