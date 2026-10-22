"""Reviewed deployment facts: deterministic validation, no collectors or runtime probes."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import hashlib
import html
import json
import re
import unicodedata

RUN_MODES = {'cli': 'Command line', 'desktop': 'Desktop application', 'local_web': 'Local browser interface',
             'server': 'Self-hosted server', 'library': 'Library / SDK', 'firmware': 'Device firmware'}
INSTALL_METHODS = {'binary': 'Downloadable binary / archive', 'installer': 'Installer',
                   'container': 'Container', 'package_manager': 'Package manager',
                   'source': 'Build from source', 'firmware_image': 'Firmware image'}


def load_optional(path):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 1600 or any(unicodedata.category(c) == 'Cc' for c in value):
        raise ValueError('Invalid deployment ' + label)
    return value


def keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('Invalid deployment fields: ' + str(required))


def attach(projects, document, canonical_url):
    """Attach only approved records. Omitted records/facts remain unknown, never false."""
    if document is None:
        return
    keys(document, ('schema_version', 'projects'))
    if type(document['schema_version']) is not int or document['schema_version'] != 1 or not isinstance(document['projects'], dict):
        raise ValueError('Invalid deployment schema')
    by_id = {p['id']: p for p in projects.values()}
    for pid, entry in document['projects'].items():
        keys(entry, ('project_url', 'review_status', 'checked_at', 'reviewed_by', 'review_note', 'sources'),
             ('run_modes', 'install_methods', 'platforms', 'external_services', 'packages', 'requirements'))
        project = by_id.get(pid)
        url = canonical_url(entry['project_url'])
        if project is None or project['url'] != url or pid != hashlib.sha256(url.encode()).hexdigest():
            raise ValueError('Deployment identity mismatch: ' + pid)
        if not isinstance(entry['review_status'], str) or entry['review_status'] not in {'approved', 'pending', 'rejected'}:
            raise ValueError('Invalid deployment review status')
        checked = entry['checked_at']
        if not isinstance(checked, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', checked):
            raise ValueError('Deployment review date must be ISO YYYY-MM-DD')
        date.fromisoformat(checked)
        text(entry['reviewed_by'], 'reviewer')
        text(entry['review_note'], 'review note')
        sources = entry['sources']
        if not isinstance(sources, dict) or not 1 <= len(sources) <= 20:
            raise ValueError('Deployment needs named primary sources')
        for sid, source in sources.items():
            if not isinstance(sid, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', sid):
                raise ValueError('Invalid deployment source ID')
            keys(source, ('url', 'title', 'kind'), ('revision',))
            if not canonical_url(source['url']).startswith('https://'):
                raise ValueError('Deployment sources must use HTTPS')
            text(source['title'], 'source title')
            if not isinstance(source['kind'], str) or source['kind'] not in {'upstream_docs', 'upstream_repository', 'registry', 'distribution'}:
                raise ValueError('Invalid deployment source kind')
            if 'revision' in source and (not isinstance(source['revision'], str) or not re.fullmatch(r'[0-9a-f]{40}', source['revision'])):
                raise ValueError('Deployment source revision must be a full commit SHA')
        total = 0
        for field in ('run_modes', 'install_methods', 'platforms', 'external_services', 'packages', 'requirements'):
            if field not in entry:
                continue
            facts = entry[field]
            if not isinstance(facts, list) or not 1 <= len(facts) <= 30:
                raise ValueError('Deployment facts must be nonempty lists; omit unknown fields')
            seen = set()
            for fact in facts:
                required = ('scope', 'source_ids')
                if field == 'packages':
                    required += ('ecosystem', 'coordinate', 'channel', 'status', 'upstream_relationship')
                elif field == 'external_services':
                    required += ('name', 'requirement')
                elif field == 'requirements':
                    required += ('kind', 'note')
                else:
                    required += ('value',)
                keys(fact, required)
                for key in required:
                    if key != 'source_ids':
                        text(fact[key], field + ' ' + key)
                refs = fact['source_ids']
                if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or ref not in sources for ref in refs) or len(set(refs)) != len(refs):
                    raise ValueError('Invalid deployment fact provenance')
                if field in ('run_modes', 'install_methods'):
                    choices = RUN_MODES if field == 'run_modes' else INSTALL_METHODS
                    if fact['value'] not in choices or fact['value'] in seen:
                        raise ValueError('Invalid or duplicate deployment mode/method')
                    seen.add(fact['value'])
                if field == 'external_services' and fact['requirement'] not in {'required', 'optional', 'configuration-dependent'}:
                    raise ValueError('Invalid external service requirement')
                if field == 'requirements' and fact['kind'] not in {'minimum', 'recommended', 'default', 'constraint'}:
                    raise ValueError('Invalid deployment requirement kind')
                if field == 'packages':
                    if fact['status'] not in {'documented', 'disabled', 'deprecated', 'discontinued'}:
                        raise ValueError('Invalid package evidence status')
                    if fact['upstream_relationship'] not in {'upstream', 'community', 'distribution', 'third-party', 'unknown'}:
                        raise ValueError('Invalid package upstream relationship')
                    identity = tuple(fact[k] for k in ('ecosystem', 'coordinate', 'channel'))
                    if identity in seen:
                        raise ValueError('Duplicate package coordinate/channel')
                    seen.add(identity)
                total += 1
        if not total:
            raise ValueError('Deployment record needs at least one sourced fact')
        if entry['review_status'] == 'approved':
            project['deployment'] = deepcopy(entry)


def sections(project):
    """Sourced setup facts grouped by kind; the body of every setup disclosure."""
    record = project.get('deployment')
    if not record:
        return ''
    esc = lambda value: html.escape(str(value), quote=True)
    sections = []
    for field, title in (('run_modes', 'Run modes'), ('install_methods', 'Install methods'), ('platforms', 'Documented platforms'),
                         ('external_services', 'External services'), ('packages', 'Package coordinates'), ('requirements', 'Resource and setup notes')):
        items = []
        for fact in record.get(field, []):
            if field in ('run_modes', 'install_methods'):
                label = (RUN_MODES if field == 'run_modes' else INSTALL_METHODS)[fact['value']]
            elif field == 'packages':
                label = ' · '.join(fact[k] for k in ('ecosystem', 'coordinate', 'channel', 'status', 'upstream_relationship'))
            elif field == 'requirements':
                label = fact['kind'].capitalize() + ': ' + fact['note']
            elif field == 'external_services':
                label = fact['name'] + ' · ' + fact['requirement']
            else:
                label = fact['value']
            links = ' / '.join(f'<a href="{esc(record["sources"][sid]["url"])}">{esc(record["sources"][sid]["title"])}</a>' for sid in fact['source_ids'])
            items.append(f'<li><strong>{esc(label)}</strong><p>{esc(fact["scope"])}</p><p class="fine-print">{links}</p></li>')
        if items:
            sections.append(f'<div class="deployment-group"><h5>{title}</h5><ul>{"".join(items)}</ul></div>')
    return ''.join(sections)


def render(project, *, embedded=False, overview=True):
    """Plain factual disclosure; no commands, inferred support badges or ratings."""
    record = project.get('deployment')
    if not record:
        return ''
    esc = lambda value: html.escape(str(value), quote=True)
    summary = []
    for field, label, names in (('run_modes', 'Run', RUN_MODES), ('install_methods', 'Install', INSTALL_METHODS)):
        if overview and record.get(field):
            summary.append('<p><strong>' + label + ':</strong> ' + esc(' / '.join(names[f['value']] for f in record[field])) + '</p>')
    opening = ('<div class="deployment-evidence">' if embedded else
               '<section class="deployment-evidence" aria-labelledby="deployment-' + esc(project['id']) + '"><h4 id="deployment-' + esc(project['id']) + '">Deployment and installation</h4>')
    return (opening +
            '<p class="fine-print">Reviewed ' + esc(record['checked_at']) + ' · ' + esc(record['reviewed_by']) + ' · Approved evidence record</p>'
            + ''.join(summary) + '<details><summary>View setup facts &amp; sources</summary>' + sections(project) +
            '</details>' + ('</div>' if embedded else '</section>'))
