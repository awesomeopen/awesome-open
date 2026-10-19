"""Reviewed name-change evidence; observation dates never become event dates."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re

from project_aliases import plain_text

PATH = 'data/project_history.json'
KINDS = {'software_rename': 'Project renamed', 'repository_rename': 'Repository renamed',
         'owner_transfer': 'Repository transferred'}
BASES = {'announcement': 'announced', 'implementation': 'implemented', 'effective': 'effective',
         'release': 'released'}


def load_optional(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def checked_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Expected an ISO history date')
    return date.fromisoformat(value)


def attach(projects, document, canonical_url):
    if document is None:
        return
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'events'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or not isinstance(document['events'], list)):
        raise ValueError('Invalid project history schema')
    seen, facts = set(), set()
    for event in document['events']:
        required = {'id', 'project_url', 'kind', 'old_name', 'new_name', 'occurred',
                    'sources', 'checked_at', 'reviewed_by', 'note'}
        if (not isinstance(event, dict) or not required <= set(event)
                or set(event) - required - {'first_observed_at'}):
            raise ValueError('Invalid history event fields')
        eid = event['id']
        if not isinstance(eid, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', eid) or eid in seen:
            raise ValueError('Invalid or duplicate history event ID')
        seen.add(eid)
        url = canonical_url(event['project_url'])
        if url not in projects or event['kind'] not in KINDS:
            raise ValueError('Unknown history project or event kind')
        for field in ('old_name', 'new_name', 'reviewed_by'):
            plain_text(event[field], field)
        if event['old_name'] == event['new_name']:
            raise ValueError('History needs a changed name or path')
        plain_text(event['note'], 'note', limit=1000)
        checked = checked_date(event['checked_at'])
        if 'first_observed_at' in event and checked_date(event['first_observed_at']) > checked:
            raise ValueError('First observation is later than review')
        sources = event['sources']
        if not isinstance(sources, list) or not 1 <= len(sources) <= 5:
            raise ValueError('History needs official sources')
        source_urls = set()
        for source in sources:
            if not isinstance(source, dict) or set(source) != {'url', 'title', 'role', 'date'}:
                raise ValueError('Invalid history source')
            src = canonical_url(source['url'])
            if not src.startswith('https://') or src in source_urls or source['role'] not in {*BASES, 'identity'}:
                raise ValueError('Invalid history source URL or role')
            source_urls.add(src)
            plain_text(source['title'], 'source title', limit=200)
            if source['date'] is not None and checked_date(source['date']) > checked:
                raise ValueError('History source is later than review')
        occurred = event['occurred']
        if occurred is not None:
            if (not isinstance(occurred, dict) or set(occurred) != {'value', 'precision', 'basis', 'source_url'}
                    or occurred['precision'] not in {'day', 'month', 'year'} or occurred['basis'] not in BASES):
                raise ValueError('Invalid history occurrence date')
            value, precision = occurred['value'], occurred['precision']
            patterns = {'day': r'\d{4}-\d{2}-\d{2}', 'month': r'\d{4}-\d{2}', 'year': r'\d{4}'}
            if not isinstance(value, str) or not re.fullmatch(patterns[precision], value):
                raise ValueError('Occurrence date must preserve its precision')
            earliest = checked_date(value + {'day': '', 'month': '-01', 'year': '-01-01'}[precision])
            if earliest > checked:
                raise ValueError('Occurrence is later than review')
            source_url = canonical_url(occurred['source_url'])
            supporting = next((s for s in sources if canonical_url(s['url']) == source_url), None)
            if supporting is None or supporting['role'] != occurred['basis']:
                raise ValueError('Occurrence needs a source with the same date meaning')
        fact = (url, event['kind'], event['old_name'], event['new_name'],
                json.dumps(occurred, sort_keys=True))
        if fact in facts:
            raise ValueError('Duplicate history event')
        facts.add(fact)
        projects[url].setdefault('history', []).append(deepcopy(event))
    for project in projects.values():
        if 'history' in project:
            project['history'].sort(key=lambda e: ((e['occurred'] or {}).get('value', '9999'), e['id']))


def exact_events(events):
    """Only reviewed day-precision occurrences; never fall back to first observation."""
    return [e for e in events if e['occurred'] is not None and e['occurred']['precision'] == 'day']
