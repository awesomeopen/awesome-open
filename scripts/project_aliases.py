"""Optional, reviewed project names. Search use never grants HN attribution."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
import unicodedata


PATH = 'data/project_aliases.json'


def load_optional(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def name_key(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value)
                           if not unicodedata.combining(c)).lower().split())


def plain_text(value, label, limit=120):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or len(value) > limit or any(unicodedata.category(c).startswith('C') for c in value)
            or any(c in value for c in '<>')):
        raise ValueError('Invalid alias ' + label)
    return value


def validate(document, canonical_url):
    """Return evidence by canonical URL; validate every supplied record offline."""
    if document is None:
        return {}
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'projects'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or not isinstance(document['projects'], list)):
        raise ValueError('Invalid project aliases schema')
    result = {}
    for entry in document['projects']:
        if not isinstance(entry, dict) or set(entry) != {'project_url', 'aliases', 'checked_at', 'reviewed_by'}:
            raise ValueError('Invalid project alias fields')
        url = canonical_url(entry['project_url'])
        if url in result:
            raise ValueError('Duplicate project alias identity')
        checked = entry['checked_at']
        if not isinstance(checked, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', checked):
            raise ValueError('Alias review needs an ISO date')
        date.fromisoformat(checked)
        plain_text(entry['reviewed_by'], 'reviewer')
        aliases = entry['aliases']
        if not isinstance(aliases, list) or not 1 <= len(aliases) <= 10:
            raise ValueError('Expected one to ten reviewed aliases')
        names = set()
        for alias in aliases:
            if (not isinstance(alias, dict) or not {'name', 'source_url'} <= set(alias)
                    or set(alias) - {'name', 'source_url', 'ambiguous'}):
                raise ValueError('Invalid reviewed alias fields')
            key = name_key(plain_text(alias['name'], 'name'))
            if not any(c.isalnum() for c in key) or key in names:
                raise ValueError('Empty or duplicate normalized alias')
            names.add(key)
            if not canonical_url(alias['source_url']).startswith('https://'):
                raise ValueError('Alias source must use HTTPS')
            if 'ambiguous' in alias and type(alias['ambiguous']) is not bool:
                raise ValueError('Alias ambiguity must be boolean')
        result[url] = deepcopy(entry)
    return result


def attach(projects, document, canonical_url):
    evidence = validate(document, canonical_url)
    unused = evidence.keys() - projects.keys()
    if unused:
        raise ValueError('Reviewed aliases refer to unlisted projects: ' + ', '.join(sorted(unused)))
    for url, entry in evidence.items():
        projects[url]['aliases'] = entry['aliases']
        projects[url]['alias_review'] = {key: entry[key] for key in ('checked_at', 'reviewed_by')}


def hn_rules(project, evidence):
    """Resolve explicitly reviewed references, never all catalog/search aliases.

    Per-alias context is mandatory for short or marked-ambiguous names. Resolved
    rules and their review evidence become part of the HN identity, so matching
    or provenance edits invalidate reuse; unrelated search-only aliases do not.
    """
    references = project.get('catalog_aliases')
    if references is None:
        return []
    if not isinstance(references, list) or not references:
        raise ValueError('Expected nonempty reviewed HN catalog_aliases')
    aliases = {alias['name']: alias for alias in (evidence or {}).get('aliases', [])}
    result, names = [], set()
    for reference in references:
        if (not isinstance(reference, dict) or not {'name'} <= set(reference)
                or set(reference) - {'name', 'context_pattern'}):
            raise ValueError('Invalid reviewed HN alias reference')
        name = reference['name']
        if not isinstance(name, str) or name not in aliases or name in names:
            raise ValueError('HN alias must reference a unique reviewed catalog name')
        names.add(name)
        context = reference.get('context_pattern')
        short = len(re.sub(r'\W', '', name_key(name))) <= 4
        if (short or aliases[name].get('ambiguous')) and not context:
            raise ValueError('Ambiguous HN alias requires reviewed context')
        if context is not None:
            if (not isinstance(context, str) or not context.strip() or len(context) > 500
                    or any(unicodedata.category(c).startswith('C') for c in context)):
                raise ValueError('Invalid HN alias context pattern')
            try:
                pattern = re.compile(context, re.I)
            except re.error as error:
                raise ValueError('Invalid HN alias context pattern') from error
            if pattern.search(''):
                raise ValueError('HN alias context must not match empty text')
        result.append({'name': name, 'context_pattern': context,
                       'source_url': aliases[name]['source_url'],
                       'checked_at': evidence['checked_at'], 'reviewed_by': evidence['reviewed_by']})
    return result
