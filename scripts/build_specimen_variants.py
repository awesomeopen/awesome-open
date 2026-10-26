#!/usr/bin/env python3
"""Regenerate the plate's responsive specimen variants (Pillow 12.3.0/libwebp 1.6.0).

Each plate shows one source: the project's cut-out while it matches its original,
otherwise the original. This writes 512 and 768 px wide WebP copies of that source
to site/specimens/responsive/ and records them in site/specimens/responsive.json.
Normal builds read the manifest and copy the committed files; they need no Pillow.

Entries whose source and variant hashes still match are kept as they are, so
adding a specimen writes only its own files. --force regenerates every entry.
Inspect the new files at display size, then refresh brand/assets.lock.json.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'site/specimens/responsive.json'
OUTPUT = 'specimens/responsive'
WIDTHS = (512, 768)
RECIPE = {'widths': list(WIDTHS), 'resample': 'LANCZOS', 'quality': 85, 'method': 4}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plate_sources(root):
    """The image each plate shows, resolved exactly as the site build does."""
    from build_catalog import build_catalog
    from build_site import attach_specimen_art, attach_specimen_cutouts
    catalog = build_catalog((root / 'README.source.md').read_text(encoding='utf-8'),
                            *[json.loads((root / 'data' / name).read_text(encoding='utf-8')) for name in
                              ('github_metrics.json', 'alternatives.json', 'hn_evidence.json')])
    attach_specimen_art(catalog, root)
    cutouts = attach_specimen_cutouts(catalog, root)
    return sorted(cutouts[p['id']]['path'] if p['id'] in cutouts else p['artwork']['path']
                  for p in catalog['projects'] if p.get('artwork'))


def current(entry, root, source):
    return (entry.get('sha256') == sha256(root / 'site' / source)
            and entry.get('recipe') == RECIPE
            and all((root / 'site' / v['path']).is_file()
                    and sha256(root / 'site' / v['path']) == v['sha256'] for v in entry['variants']))


def generate(root=ROOT, force=False):
    from PIL import Image, features
    path = root / MANIFEST
    previous = json.loads(path.read_text(encoding='utf-8'))['sources'] if path.exists() else {}
    entries = {}
    for source in plate_sources(root):
        if not force and source in previous and current(previous[source], root, source):
            entries[source] = previous[source]
            continue
        original = Image.open(root / 'site' / source)
        suffix = '-cutout' if '/cutouts/' in source else ''
        variants = []
        for width in WIDTHS:
            if width >= original.width:
                continue
            height = round(original.height * width / original.width)
            relative = f'{OUTPUT}/{Path(source).stem}{suffix}-{width}.webp'
            target = root / 'site' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            original.resize((width, height), Image.Resampling.LANCZOS).save(
                target, 'WEBP', quality=RECIPE['quality'], method=RECIPE['method'])
            variants.append({'path': relative, 'width': width, 'height': height,
                             'bytes': target.stat().st_size, 'sha256': sha256(target)})
        entries[source] = {'sha256': sha256(root / 'site' / source),
                           'width': original.width, 'height': original.height, 'recipe': RECIPE,
                           'tools': {'pillow': Image.__version__, 'libwebp': features.version('webp')},
                           'variants': variants}
    kept = {v['path'] for entry in entries.values() for v in entry['variants']}
    for stale in (root / 'site' / OUTPUT).glob('*.webp'):
        if f'{OUTPUT}/{stale.name}' not in kept:
            stale.unlink()
    manifest = {'schema_version': 1,
                'purpose': 'Plate display variants of the shown specimen source; the source stays '
                           'the widest srcset candidate and the loupe image.',
                'sources': entries}
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--force', action='store_true', help='Regenerate every entry')
    args = parser.parse_args()
    print(f"Recorded variants for {len(generate(force=args.force)['sources'])} plate sources in {MANIFEST}")
