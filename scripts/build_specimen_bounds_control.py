#!/usr/bin/env python3
"""Build review-only before records with the PR base renderer and unchanged data/art.

The base must already be fetched. Output is test-only, never a production route.
"""
import argparse
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile

from build_jar_preview import jar_stylesheet_href


JAR_STYLESHEET = r'jars\.css(?:\?[^"<>]*)?'


def strip_jar_stylesheet(head):
    return re.sub(r'<link\b[^>]*href="' + JAR_STYLESHEET + r'"[^>]*>', '', head)


def comparison_stylesheet(html, css):
    # Hash the actual base bytes, not the current ROOT used by its renderer.
    href = 'jars-before/' + jar_stylesheet_href(css)
    return re.sub(r'href="' + JAR_STYLESHEET + '"', f'href="{href}"', html)


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
        # Jar comparison uses the actual base generator, CSS and JS with the
        # same edition and unchanged artwork. It is a CI-only review route.
        jar_output = site / 'jars-before'
        jar_output.mkdir(exist_ok=True)
        jar_module = Path(temporary) / 'base_build_jars.py'
        jar_module.write_text(source('scripts/build_jar_preview.py'))
        jar_spec = importlib.util.spec_from_file_location('base_build_jars', jar_module)
        jars = importlib.util.module_from_spec(jar_spec)
        jar_spec.loader.exec_module(jars)
        jars.ROOT = root
        (jar_output / 'catalog.json').write_text(json.dumps(catalog))
        # Reuse the shared typography/tokens head from the same generated page.
        # Remove scripts and jar CSS: build() adds only the base jar enhancement.
        # A styles.css-only shell would silently compare fallback serif labels.
        head = (site / 'index.html').read_text().split('<head>', 1)[1].split('</head>', 1)[0]
        head = re.sub(r'<script\b[^>]*>.*?</script>', '', head, flags=re.S)
        head = strip_jar_stylesheet(head)
        (jar_output / 'index.html').write_text(
            '<!doctype html><html><head><base href="../">' + head +
            '</head><body><div class="layout"></div></body></html>')
        jars.build(jar_output, production=True)
        html = (jar_output / 'index.html').read_text()
        base_css = source('site/jars.css')
        html = comparison_stylesheet(html, base_css.encode('utf-8'))
        html = html.replace('src="jars.js"', 'src="jars-before/jars.js"')
        (jar_output / 'index.html').write_text(html)
        for name in ('jars.css', 'jars.js'):
            (jar_output / name).write_text(source('site/' + name))
        (output / 'source.json').write_text(json.dumps({'base_sha': revision,
            'comparison': 'Base renderer/CSS/JS, same current cached catalog and unchanged artwork.'}) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--site', default='tmp/site')
    args = parser.parse_args()
    build(args.base, args.site)
