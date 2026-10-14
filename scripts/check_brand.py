#!/usr/bin/env python3
"""Offline brand inventory integrity and optional PR documentation advisory.

No network, Git mutations, approval changes or upstream skill updates. --refresh
records intentional local bytes only; provenance and approval remain reviewed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    'AGENTS.md', 'brand/README.md', 'brand/foundation.md',
    'brand/visual-system.md', 'brand/illustration.md', 'brand/assets.md',
    'brand/decisions.md', 'brand/skills.md', 'brand/maintenance.md',
    'brand/sources.md', '.agents/skills/awesome-open-brand/SKILL.md',
    '.agents/skills/awesome-open-brand/agents/openai.yaml',
)
ASSET_DIRS = ('site/brand', 'site/footer-backgrounds', 'site/specimens', 'site/jars', 'brand/studies')
ASSET_SUFFIXES = {'.png', '.webp', '.ico', '.svg', '.jpg', '.jpeg'}
FONT_FILES = ('site/vendor/fonts.css', 'site/vendor/FONT-LICENSE.txt',
              'site/vendor/FONT-PROVENANCE.json')


def record(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def safe_path(relative):
    path = ROOT / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError(f'Unsafe inventory path: {relative}')
    if not path.resolve().is_relative_to(ROOT.resolve()) or path.is_symlink():
        raise ValueError(f'Inventory path escapes root or is a symlink: {relative}')
    return path


def asset_inventory():
    paths = []
    for directory in ASSET_DIRS:
        paths.extend(p for p in (ROOT / directory).rglob('*')
                     if p.is_file() and p.suffix.lower() in ASSET_SUFFIXES)
    paths.extend(ROOT / p for p in FONT_FILES)
    return {str(p.relative_to(ROOT)): record(safe_path(str(p.relative_to(ROOT))))
            for p in sorted(paths)}


def skill_inventory(entry):
    directory = safe_path(entry['path'])
    if entry['path'] != '.agents/skills/' + entry['name']:
        raise ValueError(f'Skill name/path mismatch: {entry["name"]}')
    if not (directory / 'SKILL.md').is_file():
        raise ValueError(f'Missing skill: {entry["name"]}')
    return {str(p.relative_to(ROOT)): record(safe_path(str(p.relative_to(ROOT))))
            for p in sorted(directory.rglob('*')) if p.is_file()}


def compare(label, expected, actual):
    errors = []
    for path in sorted(expected.keys() | actual.keys()):
        safe_path(path)
        if path not in actual:
            errors.append(f'{label}: missing {path}')
        elif path not in expected:
            errors.append(f'{label}: unrecorded {path}')
        elif expected[path] != actual[path]:
            errors.append(f'{label}: changed {path}')
    return errors


def advisory(base):
    # Resolve the supplied base as a commit, then pass only verified SHAs to diff.
    sha = subprocess.check_output(
        ['git', 'rev-parse', '--verify', '--end-of-options', base + '^{commit}'],
        cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(
        ['git', 'diff', '--name-only', sha + '...HEAD', '--'],
        cwd=ROOT, text=True).splitlines()
    design = any(p.startswith(('site/', '.agents/skills/')) or p in (
        'scripts/build_site.py', 'scripts/build_jar_preview.py',
        'scripts/build_exhibition_preview.py', 'scripts/star_history.py') for p in paths)
    docs = any(p.startswith('brand/') and p.endswith('.md') or
               p.startswith('site/') and p.endswith('.md') for p in paths)
    if design and not docs:
        print('::warning::Design sources changed without brand documentation. '
              'Update affected rules/decisions or explain Brand impact: none in the PR.')
    elif design:
        print('Design and documentation paths changed; semantic review is still required.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--base', help='Optional PR base commit/ref for advisory')
    args = parser.parse_args()
    errors = [f'Missing required file: {p}' for p in REQUIRED if not safe_path(p).is_file()]
    assets_path = ROOT / 'brand/assets.lock.json'
    skills_path = ROOT / 'brand/skills.lock.json'
    skills = json.loads(skills_path.read_text())
    if skills.get('schema_version') != 1 or len(skills.get('skills', [])) != 2:
        raise ValueError('Expected the two documented pinned reusable skills (schema 1)')
    if {s['name'] for s in skills['skills']} != {'retro-scraperism', 'speculative-fossoligy'}:
        raise ValueError('Unexpected or duplicate pinned skill names')
    actual_assets = asset_inventory()
    actual_skills = [skill_inventory(entry) for entry in skills['skills']]
    for entry in skills['skills']:
        if not entry.get('source_revision') or not entry.get('authority'):
            errors.append(f'Missing skill provenance: {entry["name"]}')
    # Historical documents are fixed source captures, not refreshed with current rules.
    for entry in json.loads((ROOT / 'brand/archive/source-records.json').read_text()):
        body = safe_path(entry['path']).read_text().split(
            '<!-- Original source body begins below. -->\n', 1)[1]
        if hashlib.sha256(body.encode()).hexdigest() != entry['body_sha256']:
            errors.append(f'Historical source body changed: {entry["path"]}')
    if args.refresh and not errors:
        assets_path.write_text(json.dumps({'schema_version': 1, 'files': actual_assets}, indent=2) + '\n')
        for entry, actual in zip(skills['skills'], actual_skills):
            entry['files'] = actual
        skills_path.write_text(json.dumps(skills, indent=2) + '\n')
        print('Refreshed byte inventories. Review provenance and approval separately.')
    else:
        assets = json.loads(assets_path.read_text())
        if assets.get('schema_version') != 1:
            errors.append('Unsupported asset inventory schema')
        errors.extend(compare('Asset', assets['files'], actual_assets))
        for entry, actual in zip(skills['skills'], actual_skills):
            errors.extend(compare('Skill', entry['files'], actual))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    if args.base:
        advisory(args.base)
    print(f'Brand integrity OK: {len(actual_assets)} assets; {len(actual_skills)} pinned skills.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        print(f'Brand check failed: {exc}', file=sys.stderr)
        sys.exit(1)
