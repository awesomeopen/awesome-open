"""Persisted weekly specimen draw; renderers never draw or consult the wall clock."""
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

PATH = 'data/weekly_draws.json'
SIZE = 7
COOLDOWN = 4
TIMEZONE = 'America/New_York'
ALGORITHM = 'sha256-week-project-v1'


def monday(day):
    return day - timedelta(days=day.weekday())


def empty():
    return {'schema_version': 1, 'as_of': None, 'editions': []}


def validate(doc):
    if doc.get('schema_version') != 1 or not isinstance(doc.get('editions'), list):
        raise ValueError('Invalid weekly draw archive')
    if doc['as_of'] is not None:
        date.fromisoformat(doc['as_of'])
    previous = None
    for item in doc['editions']:
        week = date.fromisoformat(item['draw_week'])
        display = date.fromisoformat(item['display_week'])
        if week != monday(week) or display != week + timedelta(days=7):
            raise ValueError('Invalid weekly draw dates')
        if previous and week <= previous:
            raise ValueError('Weekly draw editions must be unique and chronological')
        previous = week
        ids = [p['id'] for p in item['projects']]
        if len(ids) != SIZE or len(set(ids)) != SIZE or not set(ids) <= set(item['candidates']):
            raise ValueError('Invalid weekly draw selection')
        if item['algorithm'] != ALGORITHM:
            raise ValueError('Unknown weekly draw algorithm')
        order = sorted(item['candidates'], key=lambda pid: score(item['seed'], pid))[:SIZE]
        if ids != order:
            raise ValueError('Weekly draw does not match its recorded seed and candidates')
    return doc


def load(path):
    path = Path(path)
    return validate(json.loads(path.read_text())) if path.exists() else empty()


def score(seed, pid):
    return hashlib.sha256((seed + '\n' + pid).encode()).hexdigest(), pid


def advance(doc, catalog, today, source_sha=None):
    """Record only this actual week. Missed weeks are not invented; reruns are no-ops."""
    validate(doc)
    result = deepcopy(doc)
    if result['as_of'] and today < date.fromisoformat(result['as_of']):
        raise ValueError('Weekly draw clock cannot move backwards')
    result['as_of'] = today.isoformat()
    week = monday(today)
    if any(e['draw_week'] == week.isoformat() for e in result['editions']):
        return result
    eligible = {p['id']: p for p in catalog['projects'] if p.get('artwork')}
    # Four preceding display weeks, even though this draw is made a week ahead.
    display = week + timedelta(days=7)
    recent = [e for e in result['editions']
              if display - timedelta(weeks=COOLDOWN) <= date.fromisoformat(e['display_week']) < display]
    blocked = {p['id'] for e in recent for p in e['projects']}
    candidates = sorted(set(eligible) - blocked)
    # Strict cooldown: never silently relax it or publish a partial group.
    if len(candidates) < SIZE:
        return result
    seed = f'awesome-open/weekly-draw/v1/{week.isoformat()}'
    selected = sorted(candidates, key=lambda pid: score(seed, pid))[:SIZE]
    projects = [{key: deepcopy(eligible[pid][key]) for key in
                 ('id', 'name', 'url', 'description', 'categories', 'artwork')} for pid in selected]
    result['editions'].append({
        'draw_week': week.isoformat(), 'display_week': display.isoformat(),
        'recorded_on': today.isoformat(), 'timezone': TIMEZONE,
        'algorithm': ALGORITHM, 'seed': seed, 'cooldown_weeks': COOLDOWN,
        'eligible_count': len(eligible), 'candidates': candidates,
        'excluded_by_cooldown': sorted(set(eligible) & blocked),
        'source_sha': source_sha, 'projects': projects,
    })
    return validate(result)


def visible(doc):
    if not doc['as_of']:
        return []
    week = monday(date.fromisoformat(doc['as_of'])).isoformat()
    return [e for e in doc['editions'] if e['display_week'] <= week]


def current(doc, catalog):
    available = {p['id'] for p in catalog['projects'] if p.get('artwork')}
    for edition in reversed(visible(doc)):
        if {p['id'] for p in edition['projects']} <= available:
            return edition
    return None


def update(root, source_sha=None, today=None):
    # Use the same validation and illustration eligibility as the site, without
    # building HTML or fetching any additional metrics.
    from build_catalog import build_catalog
    from build_site import attach_specimen_art
    root = Path(root)
    read = lambda path: json.loads((root / path).read_text())
    catalog = build_catalog((root / 'README.source.md').read_text(),
                            read('data/github_metrics.json'), read('data/alternatives.json'),
                            read('data/hn_evidence.json'), source_sha=source_sha)
    attach_specimen_art(catalog, root)
    path = root / PATH
    doc = advance(load(path), catalog, today or datetime.now(ZoneInfo(TIMEZONE)).date(), source_sha)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    return doc


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    update(Path(__file__).resolve().parents[1], args.source_sha)
