#!/usr/bin/env python3
"""Build review-only before records with the PR base renderer and unchanged data/art.

The base must already be fetched. Output is test-only, never a production route.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def build(base, site):
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', base + '^{commit}'], text=True).strip()
    site = Path(site)
    output = site / 'bounds-before'
    output.mkdir(exist_ok=True)
    def source(path):
        return subprocess.check_output(['git', 'show', f'{revision}:{path}'], text=True)
    with tempfile.TemporaryDirectory() as temporary:
        module_path = Path(temporary) / 'base_build_site.py'
        module_path.write_text(source('scripts/build_site.py'))
        spec = importlib.util.spec_from_file_location('base_build_site', module_path)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        catalog = json.loads((site / 'catalog.json').read_text())
        catalog['source_sha'] = revision
        root = Path(__file__).resolve().parents[1]
        cutouts = renderer.attach_specimen_cutouts(catalog, root)
        categories = {c['id']: c['name'] for c in catalog['categories']}
        names = {'openspec', 'openbb', 'openpilot', 'openrocket'}
        for number, project in enumerate(catalog['projects'], 1):
            if project['name'].lower() not in names or not project.get('artwork'):
                continue
            html = renderer.render_record(project, categories, catalog, number, cutouts)
            html = html.replace('href="styles.css?', 'href="bounds-before/styles.css?')
            html = html.replace('src="catalog.js"', 'src="bounds-before/catalog.js"')
            (output / f"{project['id']}.html").write_text(html)
        for path in ('styles.css', 'catalog.js'):
            (output / path).write_text(source('site/' + path))
        (output / 'source.json').write_text(json.dumps({'base_sha': revision,
            'comparison': 'Base renderer/CSS/JS, same current cached catalog and unchanged artwork.'}) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--site', default='tmp/site')
    args = parser.parse_args()
    build(args.base, args.site)
