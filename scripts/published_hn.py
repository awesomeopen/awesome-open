"""Lossless site-only HN schema 3; collector schemas 1/2 remain unchanged."""
from copy import deepcopy
import json

from update_hn import canonical_url

PUBLISHED_SCHEMA = 3
SOURCE_SCHEMAS = (1, 2)


def _shape(document):
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int:
        raise ValueError('HN evidence requires an integer schema_version')
    if not isinstance(document.get('projects'), list):
        raise ValueError('HN projects must be a list')
    indices = {}
    for index, project in enumerate(document['projects']):
        if not isinstance(project, dict) or not isinstance(project.get('readme_url'), str):
            raise ValueError('HN project requires readme_url')
        key = canonical_url(project['readme_url'])
        if key in indices:
            raise ValueError('Duplicate HN project identity')
        indices[key] = index
    if not isinstance(document.get('queue', {}), dict):
        raise ValueError('HN queue must be an object')
    for entry in document.get('queue', {}).values():
        if not isinstance(entry, dict):
            raise ValueError('HN queue entry must be an object')
        good = entry.get('last_good')
        if good is not None and not isinstance(good, dict):
            raise ValueError('HN last_good must be an object or null')
    return indices


def _same(left, right):
    # JSON comparison preserves scalar types as well as every nested field.
    return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False)


def publish(document):
    """Copy a collector snapshot, replacing only identical last_good projects."""
    indices = _shape(document)
    if document['schema_version'] not in SOURCE_SCHEMAS or 'source_schema_version' in document:
        raise ValueError('Expected collector HN schema 1 or 2')
    result = deepcopy(document)
    result['source_schema_version'] = result['schema_version']
    result['schema_version'] = PUBLISHED_SCHEMA
    for key, entry in result.get('queue', {}).items():
        good = entry.get('last_good')
        if good is None:
            continue
        if not isinstance(good.get('project'), dict):
            raise ValueError('Collector last_good requires a project object')
        if 'project_ref' in good:
            raise ValueError('Collector last_good must not contain project_ref')
        index = indices.get(key)
        if index is not None and 'project' in good and _same(good['project'], result['projects'][index]):
            del good['project']
            good['project_ref'] = index
    return result


def materialize(document):
    """Reconstruct independent collector objects; also accept legacy downloads."""
    indices = _shape(document)
    version = document['schema_version']
    if version in SOURCE_SCHEMAS:
        # Reject reserved fields rather than silently returning unresolved data.
        publish(document)
        return deepcopy(document)
    if version != PUBLISHED_SCHEMA:
        raise ValueError('Unsupported published HN schema')
    source = document.get('source_schema_version')
    if type(source) is not int or source not in SOURCE_SCHEMAS:
        raise ValueError('Unsupported source HN schema')
    result = deepcopy(document)
    for key, entry in result.get('queue', {}).items():
        good = entry.get('last_good')
        if good is None:
            continue
        if 'project_ref' not in good:
            if not isinstance(good.get('project'), dict):
                raise ValueError('HN last_good requires project or project_ref')
            continue
        index = good['project_ref']
        if ('project' in good or type(index) is not int or index < 0
                or index >= len(result['projects']) or indices.get(key) != index):
            raise ValueError('Invalid HN project_ref')
        good['project'] = deepcopy(result['projects'][index])
        del good['project_ref']
    result['schema_version'] = result.pop('source_schema_version')
    return result
