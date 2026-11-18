#!/usr/bin/env python3
"""Offline alias-only planning and report checkpoints; stdout never advances state."""
import argparse
from bisect import bisect_right
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from build_catalog import canonical_url
import project_aliases

MAX_BATCH = 10
OUTCOMES = {'reviewed', 'unresolved', 'unsupported', 'overlap', 'proposed'}


def full_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Expected full canonical project ID')
    return value


def plan_batch(catalog, aliases, *, day, slot, after=None, excluded=(), revisit=None,
               limit=MAX_BATCH):
    """Plan distinct IDs, reserving capacity for explicitly evidenced revisits.

    Exclusions are fresh full IDs from open PRs/active work. Revisit maps IDs to
    new official evidence URLs; the operator must review their contents.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError('Limit must be 1..10')
    if type(slot) is not int or slot not in (0, 1, 2):
        raise ValueError('UTC eight-hour slot must be 0, 1 or 2')
    day_number = (date.fromisoformat(day) - date(1970, 1, 1)).days
    if after is not None:
        full_id(after)
    projects = {}
    for p in catalog['projects']:
        pid, url = full_id(p['id']), canonical_url(p['url'])
        if hashlib.sha256(url.encode()).hexdigest() != pid:
            raise ValueError('Catalog ID does not match canonical URL')
        if pid in projects and projects[pid]['url'] != url:
            raise ValueError('Conflicting canonical ID')
        projects[pid] = {'id': pid, 'url': url, 'name': p['name']}
    existing_urls = project_aliases.validate(aliases, canonical_url)
    excluded = set(map(full_id, excluded))
    existing = {pid for pid, p in projects.items() if p['url'] in existing_urls}
    ids = sorted(projects)
    eligible = set(ids) - existing - excluded
    revisit = revisit or {}
    for pid, source in revisit.items():
        full_id(pid)
        if pid not in projects:
            raise ValueError('Revisit identity absent from catalog')
        if not canonical_url(source).startswith('https://'):
            raise ValueError('Revisit needs new official HTTPS evidence')
    targeted = sorted(set(revisit) & eligible)
    if len(targeted) > limit:
        raise ValueError('Revisits exceed considered cap')
    offset = (bisect_right(ids, after) if after is not None else
              ((3 * day_number + slot) * MAX_BATCH) % len(ids) if ids else 0)
    rotated = [(pid, False) for pid in ids[offset:]] + [(pid, True) for pid in ids[:offset]]
    entries = [dict(projects[pid], targeted=True, evidence_url=revisit[pid], wrapped=False)
               for pid in targeted]
    for pid, wrapped in rotated:
        if pid in eligible and pid not in targeted and len(entries) < limit:
            entries.append(dict(projects[pid], targeted=False, wrapped=wrapped))
    return {'kind': 'alias-plan', 'after': after, 'date': day, 'slot': slot,
            'offset': offset, 'catalog_count': len(ids), 'eligible_count': len(eligible),
            'existing_ids': sorted(existing), 'excluded_ids': sorted(excluded & set(ids)),
            'entries': entries, 'cursor': after,
            'note': 'Planning does not establish consideration or sweep completion.'}


def checkpoint(plan, outcomes):
    """Checkpoint only a completed prefix, preserving prepared evidence verbatim.

    Each outcome needs id, outcome and reason; source logs/prepared records may
    be retained in additional fields. A targeted revisit never moves the cursor.
    """
    entries = plan['entries']
    if len(outcomes) > len(entries):
        raise ValueError('More outcomes than planned projects')
    cursor = plan['after']
    considered, boundaries = [], []
    crossed = False
    for entry, outcome in zip(entries, outcomes):
        if (outcome['id'] != entry['id'] or outcome['outcome'] not in OUTCOMES
                or not isinstance(outcome.get('reason'), str) or not outcome['reason'].strip()):
            raise ValueError('Outcomes must be a completed plan prefix with reasons')
        if not entry['targeted']:
            cursor = entry['id']
            if entry['wrapped'] and not crossed:
                boundaries.append({'before_id': cursor, 'kind': 'sorted-end-crossed'})
                crossed = True
        considered.append(dict(outcome, targeted=entry['targeted']))
    return {'kind': 'alias-run-report', 'date': plan['date'], 'slot': plan['slot'],
            'previous_cursor': plan['after'], 'cursor': cursor, 'considered': considered,
            'unresearched_ids': [p['id'] for p in entries[len(outcomes):]],
            'excluded_ids': plan['excluded_ids'], 'existing_ids': plan['existing_ids'],
            'sweep_boundaries': boundaries, 'complete_sweep': False,
            'coverage_note': 'Combine retained reports and their catalog denominators to assess a sweep.',
            'catalog_count': plan['catalog_count'], 'eligible_count': plan['eligible_count']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan', help='Read-only dry run; JSON to stdout')
    p.add_argument('--catalog', type=Path, required=True)
    p.add_argument('--aliases', type=Path, default=Path('data/project_aliases.json'))
    p.add_argument('--date', required=True, help='UTC YYYY-MM-DD')
    p.add_argument('--slot', type=int, required=True)
    p.add_argument('--after')
    p.add_argument('--exclude-ids', type=Path, required=True, help='Fresh JSON full-ID list; [] if none')
    p.add_argument('--revisit', type=Path, help='JSON ID to new official evidence URL mapping')
    p.add_argument('--limit', type=int, default=MAX_BATCH)
    p = sub.add_parser('checkpoint', help='Completed prefix to stdout; retain alongside the plan')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--outcomes', type=Path, required=True)
    args = parser.parse_args(argv)
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    try:
        if args.command == 'plan':
            result = plan_batch(read(args.catalog), project_aliases.load_optional(args.aliases),
                                day=args.date, slot=args.slot, after=args.after,
                                excluded=read(args.exclude_ids),
                                revisit=read(args.revisit) if args.revisit else None, limit=args.limit)
        else:
            result = checkpoint(read(args.plan), read(args.outcomes))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
