"""Immutable, offline archive of completed HN and aggregate-star observations.

The display caches remain rolling 24-month views. This archive never synthesizes
historical totals, merges counts from different fetches, or drives chart output.
Raw stories and weekly bins are content-addressed so unchanged evidence is stored
once, including across fetches, windows and reviewed identity revisions.
"""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile

ARCHIVE = 'data/chart_observations.json'
HASH = re.compile(r'[a-f0-9]{64}')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def empty():
    return {'schema_version': 1, 'objects': {}, 'observations': {}, 'recoveries': {}}


def intern(archive, kind, value):
    item = {'kind': kind, 'value': deepcopy(value)}
    key = digest(item)
    archive['objects'][key] = item
    return key


def resolve(archive, key, kind):
    if not isinstance(key, str) or not HASH.fullmatch(key):
        raise ValueError('Invalid observation evidence reference')
    item = archive['objects'].get(key)
    if not isinstance(item, dict) or item.get('kind') != kind:
        raise ValueError('Missing or mismatched observation evidence')
    return deepcopy(item['value'])


def stamp(value, field, precision='timestamp'):
    if value is None:
        return None
    if precision == 'day':
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Invalid observation day')
    elif precision == 'timestamp':
        if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('Observation timestamp needs a timezone')
    else:
        raise ValueError('Invalid observation date precision')
    return {'value': value, 'precision': precision, 'field': field}


def append(archive, kind, identity, evidence, metadata, observed_at):
    observation = {'kind': kind, 'identity': identity,
                   'evidence': intern(archive, kind + '_evidence', evidence),
                   'metadata': metadata, 'observed_at': observed_at}
    key = digest(observation)
    archive['observations'][key] = observation
    return key


def add_stars(archive, cache):
    from update_star_history import validate_cache
    validate_cache(cache)
    for repo, record in cache['repositories'].items():
        if not record.get('last_good'):
            continue
        good = deepcopy(record['last_good'])
        metadata = {key: good.pop(key) for key in ('fetched_at', 'source_sha') if key in good}
        good['week_refs'] = [intern(archive, 'star_week', row) for row in good.pop('weeks')]
        evidence = {'readme_url': record['readme_url'], 'source_url': record['source_url'], 'last_good': good}
        append(archive, 'stars', repo, evidence, metadata, stamp(metadata['fetched_at'], 'last_good.fetched_at'))
    return archive


def add_hn(archive, document):
    import update_hn as hn
    hn.validate_queue(document)
    queue = document.get('queue', {})
    if queue:
        items = [(key, deepcopy(record['last_good']), None) for key, record in queue.items() if record.get('last_good')]
    else:
        # A legacy snapshot records only a retrieval day. Never substitute a
        # commit date, current date or later attempt for its original precision.
        observed = stamp(document.get('refreshed_utc_date'), 'snapshot.refreshed_utc_date', 'day')
        items = [(hn.canonical_url(project['readme_url']),
                  {'months': document['months'], 'project': deepcopy(project)}, observed)
                 for project in document['projects']]
    for key, good, observed in items:
        metadata = {name: good.pop(name) for name in ('collected_at',) if name in good}
        if 'collected_at' in metadata:
            observed = stamp(metadata['collected_at'], 'last_good.collected_at')
        project = good['project']
        for name in ('stories', 'excluded_candidates'):
            if name in project:
                project[name + '_refs'] = [intern(archive, 'hn_story', row) for row in project.pop(name)]
        append(archive, 'hn', key, good, metadata, observed)
    return archive


def materialize(archive, observation):
    """Recover the original completed payload, including its original dates."""
    kind = observation['kind']
    evidence = resolve(archive, observation['evidence'], kind + '_evidence')
    if kind == 'stars':
        good = evidence['last_good']
        good['weeks'] = [resolve(archive, ref, 'star_week') for ref in good.pop('week_refs')]
        good.update(deepcopy(observation['metadata']))
        return {'repo': observation['identity'], 'status': 'ok', **evidence}
    good = evidence
    project = good['project']
    for name in ('stories', 'excluded_candidates'):
        if name + '_refs' in project:
            project[name] = [resolve(archive, ref, 'hn_story') for ref in project.pop(name + '_refs')]
    good.update(deepcopy(observation['metadata']))
    return good


def validate(archive):
    import update_hn as hn
    import update_star_history as stars
    if (not isinstance(archive, dict) or set(archive) != {'schema_version', 'objects', 'observations', 'recoveries'}
            or archive['schema_version'] != 1):
        raise ValueError('Invalid chart-observation archive schema')
    for section in ('objects', 'observations', 'recoveries'):
        if not isinstance(archive[section], dict):
            raise ValueError('Invalid chart-observation archive section')
        for key, value in archive[section].items():
            if not isinstance(key, str) or digest(value) != key:
                raise ValueError('Chart-observation content hash mismatch')
    for obj in archive['objects'].values():
        if (not isinstance(obj, dict) or set(obj) != {'kind', 'value'}
                or obj['kind'] not in {'hn_story', 'star_week', 'hn_evidence', 'stars_evidence'}
                or not isinstance(obj['value'], dict)):
            raise ValueError('Invalid chart-observation evidence object')
    for observation in archive['observations'].values():
        if (not isinstance(observation, dict)
                or set(observation) != {'kind', 'identity', 'evidence', 'metadata', 'observed_at'}
                or observation['kind'] not in {'hn', 'stars'} or not isinstance(observation['metadata'], dict)):
            raise ValueError('Invalid chart observation')
        observed = observation['observed_at']
        if observed is not None:
            if not isinstance(observed, dict) or set(observed) != {'value', 'precision', 'field'}:
                raise ValueError('Invalid observation date')
            stamp(observed['value'], observed['field'], observed['precision'])
        record = materialize(archive, observation)
        if observation['kind'] == 'stars':
            stars.validate_cache({'schema_version': 1, 'repositories': {observation['identity']: record}})
            if observed != stamp(record['last_good']['fetched_at'], 'last_good.fetched_at'):
                raise ValueError('Star observation date differs from its source')
        else:
            project, months = record['project'], record['months']
            hn.validate_collection(project, months)
            if hn.canonical_url(project['readme_url']) != observation['identity']:
                raise ValueError('Archived HN identity mismatch')
            # Validate consecutive complete-month positions, independent of the
            # current window. This derives boundaries, never extra data points.
            end_year, end_month = map(int, months[-1].split('-'))
            end_month += 1
            if end_month == 13:
                end_year, end_month = end_year + 1, 1
            if hn.window(datetime(end_year, end_month, 1))[2] != months:
                raise ValueError('Invalid archived HN month sequence')
            identity = {k: v for k, v in project.items() if k not in hn.COLLECTED_KEYS}
            if 'identity_key' in record and record['identity_key'] != hn.identity_key(identity):
                raise ValueError('Archived HN identity fingerprint mismatch')
            if 'collected_at' in record:
                if observed != stamp(record['collected_at'], 'last_good.collected_at'):
                    raise ValueError('HN observation date differs from its source')
            elif observed is not None and (observed['precision'] != 'day' or observed['field'] != 'snapshot.refreshed_utc_date'):
                raise ValueError('Undated HN evidence cannot acquire an exact collection timestamp')
    for recovery in archive['recoveries'].values():
        if (not isinstance(recovery, dict) or recovery.get('method') != 'git-first-parent'
                or not isinstance(recovery.get('base_sha'), str)
                or not re.fullmatch('[a-f0-9]{40}', recovery['base_sha'])
                or not isinstance(recovery.get('sources'), list)):
            raise ValueError('Invalid observation recovery manifest')
        for source in recovery['sources']:
            if (source.get('path') not in {'data/hn_evidence.json', 'data/star_history.json'}
                    or not re.fullmatch('[a-f0-9]{40}', source.get('commit', ''))
                    or not re.fullmatch('[a-f0-9]{40}', source.get('blob', ''))
                    or any(ref not in archive['observations'] for ref in source.get('observations', []))):
                raise ValueError('Invalid observation recovery source')
    return archive


def merge(*archives):
    result = empty()
    for archive in archives:
        validate(archive)
        for section in ('objects', 'observations', 'recoveries'):
            result[section].update(deepcopy(archive[section]))
    return validate(result)


def load(path):
    path = Path(path)
    return validate(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else empty()


def save(path, archive):
    validate(archive)
    path = Path(path)
    # One line per object/observation keeps the archive compact and Git diffs
    # reviewable. Repeated no-op collection does not create a new observation.
    lines = ['{', '  "schema_version": 1,']
    for index, section in enumerate(('objects', 'observations', 'recoveries')):
        lines.append('  ' + json.dumps(section) + ': {')
        items = sorted(archive[section].items())
        lines.extend('    ' + json.dumps(key) + ': ' + canonical(value) + (',' if i + 1 < len(items) else '')
                     for i, (key, value) in enumerate(items))
        lines.append('  }' + (',' if index < 2 else ''))
    content = '\n'.join(lines + ['}', ''])
    if path.exists() and path.read_text(encoding='utf-8') == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def coverage(archive):
    result = {}
    for kind in ('hn', 'stars'):
        observations = [o for o in archive['observations'].values() if o['kind'] == kind]
        months = set()
        for observation in observations:
            record = materialize(archive, observation)
            months.update((record['last_good'] if kind == 'stars' else record)['months'])
        result[kind] = {'identities': len({o['identity'] for o in observations}), 'observations': len(observations),
                        'months': sorted(months), 'undated_observations': sum(o['observed_at'] is None for o in observations),
                        'retrieval_days': sorted({o['observed_at']['value'][:10] for o in observations if o['observed_at']})}
    return result
