#!/usr/bin/env python3
"""Write Awesome Open*'s catalog as a WebMCPlet list document.

Reads a built site's catalog.json. Field meanings follow the evidence contract in
brand/foundation.md; unrecorded values are omitted, so WebMCPlet reports them as
Unknown. Items keep the Catalog's no-query order: GitHub stars descending, unknown
last, then name and registry ID. A search ties on name, then this order; the
Catalog ties on name, then registry ID, so the two differ only between projects
that share a name.
"""

import argparse
import json
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

from deployment import RUN_MODES

UNKNOWN_LICENSES = {'NOASSERTION', 'OTHER', 'UNKNOWN'}


def normalize_url(url):
    """Mirror of normalizeUrl in webmcplet/webmcplet.js."""
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https'):
        raise ValueError(f'Not a web URL: {url}')
    host = parts.netloc[4:] if parts.netloc.lower().startswith('www.') else parts.netloc
    path = parts.path.rstrip('/')
    if path.lower().endswith('.git'):
        path = path[:-4]
    path = path.rstrip('/')
    query = f'?{parts.query}' if parts.query else ''
    return (host + path + query).lower()


def fold(value):
    """Mirror of fold in site/search.js, for the name tie-break."""
    decomposed = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def stars_of(project):
    stars = (project.get('github') or {}).get('stars')
    return stars if isinstance(stars, int) and not isinstance(stars, bool) and stars >= 0 else None


def license_of(project):
    value = (project.get('github') or {}).get('license')
    value = value.strip() if isinstance(value, str) else ''
    return value if value and value.upper() not in UNKNOWN_LICENSES else None


def fields(catalog):
    observed = catalog.get('metrics_as_of')
    github = {'source': 'GitHub REST API, cached by the Awesome Open* publisher'}
    if observed:
        github['observed_at'] = observed
    return {
        'github_stars': {'label': 'GitHub stars', 'type': 'number',
                         'meaning': 'Stargazer count of the GitHub repository.', **github},
        'license': {'label': 'Detected license', 'type': 'string', 'filter': True,
                    'meaning': 'SPDX license identifier from GitHub license metadata. '
                               'Unknown means no SPDX license was detected, including NOASSERTION and OTHER.',
                    **github},
        'pushed_at': {'label': 'Last push', 'type': 'date',
                      'meaning': 'UTC timestamp of the latest push to the GitHub repository.', **github},
        'run_modes': {'label': 'run mode', 'type': 'list', 'filter': True, 'values': RUN_MODES,
                      'meaning': 'Ways the project runs, from a reviewed deployment record with sources.',
                      'source': 'Awesome Open* deployment evidence'},
        'alternatives': {'label': 'Reviewed alternatives', 'type': 'list', 'search': True,
                         'meaning': 'Products this project is a reviewed use-case comparison for.',
                         'source': 'Awesome Open* reviewed alternatives'},
        'function_summary': {'label': 'Function summary', 'type': 'text', 'search': True,
                             'meaning': 'Reviewed prose describing what the project does, from its sources.',
                             'source': 'Awesome Open* function summaries'},
        'feature_notes': {'label': 'Feature notes', 'type': 'text', 'search': True,
                          'meaning': 'Reviewed notes on individual features, each a title and text.',
                          'source': 'Awesome Open* function summaries'},
    }


def item(project, page_url):
    github = project.get('github') or {}
    values = {
        'github_stars': stars_of(project),
        'license': license_of(project),
        'pushed_at': github.get('pushed_at') or None,
        'run_modes': [mode['value'] for mode in (project.get('deployment') or {}).get('run_modes', [])] or None,
        'alternatives': [alt['name'] for alt in project.get('alternatives') or []] or None,
    }
    summary = project.get('function_summary')
    if summary:
        values['function_summary'] = summary['text']
        values['feature_notes'] = [f'{f["title"]} {f["text"]}' for f in summary.get('features', [])] or None
    out = {'id': normalize_url(project['url']), 'name': project['name'], 'url': project['url'],
           'description': project['description'], 'sections': list(project['categories']),
           'link': f'{page_url}records/{project["id"]}.html',
           'fields': {name: value for name, value in values.items() if value is not None}}
    aliases = [alias['name'] for alias in project.get('aliases') or []]
    if aliases:
        out['aliases'] = aliases
    return out


def build(catalog, page_url):
    listing = {'title': 'Awesome Open*', 'page_url': page_url,
               'description': 'A catalog of software whose name begins with Open.',
               'source_url': 'https://github.com/awesomeopen/awesome-open', 'license': 'CC0-1.0'}
    if catalog.get('source_sha'):
        listing['source_revision'] = catalog['source_sha']
    projects = sorted(catalog['projects'], key=lambda p: (
        stars_of(p) is None, -(stars_of(p) or 0), fold(p['name']), p['id']))
    return {
        'webmcplet': 1,
        'list': listing,
        'sections': [{'id': c['id'], 'title': c['name']} for c in catalog['categories']],
        'fields': fields(catalog),
        'items': [item(project, page_url) for project in projects],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('catalog', type=Path, help='catalog.json from a built site')
    parser.add_argument('--page-url', default='https://awesomeopen.github.io/awesome-open/')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    document = build(json.loads(args.catalog.read_text(encoding='utf-8')), args.page_url)
    args.output.write_text(json.dumps(document, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(document["items"])} items in {len(document["sections"])} sections to {args.output}')


if __name__ == '__main__':
    main()
