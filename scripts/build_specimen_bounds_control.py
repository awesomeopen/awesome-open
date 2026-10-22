#!/usr/bin/env python3
"""Build review-only before records with the PR base renderer and unchanged data/art.

The base must already be fetched. Output is test-only, never a production route.
"""
import argparse
import importlib.util
import inspect
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile

from build_jar_preview import jar_stylesheet_href
import build_jar_preview as current_jars
from font_assets import font_asset_url


JAR_STYLESHEET = r'jars\.css(?:\?[^"<>]*)?'


def strip_jar_stylesheet(head):
    return re.sub(r'<link\b[^>]*href="' + JAR_STYLESHEET + r'"[^>]*>', '', head)


def comparison_stylesheet(html, css):
    # Hash the actual base bytes, not the current ROOT used by its renderer.
    href = 'jars-before/' + jar_stylesheet_href(css)
    return re.sub(r'href="' + JAR_STYLESHEET + '"', f'href="{href}"', html)


def comparison_font_asset_url(path, root=None):
    # The comparison keeps current shared typography. Pre-retirement renderers
    # still ask for this script while assembling HTML; it is stripped below,
    # never copied or executed, and no longer exists in the current checkout.
    if path == 'serif-preview.js':
        return path
    return font_asset_url(path, root)


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
        renderer.font_asset_url = comparison_font_asset_url
        # Plate helpers render with the base renderer's own versions, so a PR
        # that changes or removes a helper still builds its before records.
        for name in ('star_history', 'deployment', 'history_view'):
            if not hasattr(renderer, name):
                continue
            helper_path = Path(temporary) / f'base_{name}.py'
            helper_path.write_text(source(f'scripts/{name}.py'))
            helper_spec = importlib.util.spec_from_file_location(f'base_{name}', helper_path)
            helper = importlib.util.module_from_spec(helper_spec)
            helper_spec.loader.exec_module(helper)
            setattr(renderer, name, helper)
        catalog = json.loads((site / 'catalog.json').read_text())
        catalog['source_sha'] = revision
        root = Path(__file__).resolve().parents[1]
        cutouts = renderer.attach_specimen_cutouts(catalog, root)
        categories = {c['id']: c['name'] for c in catalog['categories']}
        names = {'openspec', 'openbb', 'openpilot', 'openrocket'}
        for number, project in enumerate(catalog['projects'], 1):
            if project['name'].lower() not in names or not project.get('artwork'):
                continue
            # Newer base renderers hash fonts using an explicit root; older
            # revisions have no such argument. Never resolve assets in /tmp.
            options = {'root': root} if 'root' in inspect.signature(renderer.render_record).parameters else {}
            html = renderer.render_record(project, categories, catalog, number, cutouts, **options)
            html = re.sub(r'<script\b[^>]*src=["\'][^"\']*serif-preview\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', '', html)
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
        # Review-only stress set: two tallest and two widest approved subjects,
        # plus intermediate shapes. Never changes publisher-owned draw data.
        measured = []
        for project in catalog['projects']:
            if not project.get('artwork'):
                continue
            box = current_jars.subject_box(project, cutouts)
            art = project['artwork']
            ratio = art['width'] * (box[2]-box[0]) / (art['height'] * (box[3]-box[1]))
            measured.append((ratio, project['id'], project))
        measured.sort(key=lambda item: item[:2])
        if len(measured) >= 7:
            indices = (0, 1, len(measured)//3, len(measured)//2,
                       2*len(measured)//3, len(measured)-2, len(measured)-1)
            selected = [measured[i][2] for i in indices]
            review = dict(catalog)
            review['weekly_draws'] = {'as_of': '2000-01-03', 'editions': [{
                'display_week': '2000-01-03', 'projects': [{'id': p['id']} for p in selected]}]}
            stress = site / 'jars-outliers'
            stress.mkdir(exist_ok=True)
            (stress / 'catalog.json').write_text(json.dumps(review))
            (stress / 'index.html').write_text(
                '<!doctype html><html><head><base href="../">' + head +
                '</head><body><div class="layout"></div></body></html>')
            current_jars.build(stress, production=True)
            (stress / 'source.json').write_text(json.dumps({
                'purpose': 'Review-only shape outliers; not a saved Spotlight draw.',
                'projects': [{'id': p['id'], 'name': p['name']} for p in selected]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--site', default='tmp/site')
    args = parser.parse_args()
    build(args.base, args.site)
