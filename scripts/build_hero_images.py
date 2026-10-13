#!/usr/bin/env python3
"""Regenerate tracked hero-only WebP derivatives (Pillow 12.3.0/libwebp 1.6.0).

Normal site builds copy these files and do not require Pillow. Originals and
expanded/standalone artwork remain untouched. Run explicitly after changing a
hero source, review at display size, then refresh the brand checksum inventory.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (256, 512, 768)


def generate(root=ROOT):
    from PIL import Image, features
    from build_jar_preview import DISPLAY
    jars = json.loads((root / 'site/jars/provenance.json').read_text())
    # Resolve the same seven specimens as the hero without changing their manifest.
    from build_catalog import build_catalog
    from build_site import attach_specimen_art
    catalog = build_catalog((root / 'README.source.md').read_text(),
                            *[json.loads((root / 'data' / name).read_text()) for name in
                              ('github_metrics.json', 'alternatives.json', 'hn_evidence.json')])
    attach_specimen_art(catalog, root)
    names = {item[0] for item in DISPLAY}
    sources = {a['path'] for a in jars if a['id'] in {item[1] for item in DISPLAY}}
    sources.update(p['artwork']['path'] for p in catalog['projects'] if p['name'] in names and p.get('artwork'))
    entries = {}
    for source in sorted(sources):
        path = root / 'site' / source
        original = Image.open(path)
        variants = []
        for width in WIDTHS:
            if width >= original.width:
                continue
            height = round(original.height * width / original.width)
            relative = f'jars/responsive/{Path(source).stem}-{width}.webp'
            target = root / 'site' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            original.resize((width, height), Image.Resampling.LANCZOS).save(
                target, 'WEBP', quality=85, method=4)
            variants.append({'path': relative, 'width': width, 'height': height,
                             'bytes': target.stat().st_size,
                             'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        entries[source] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'width': original.width, 'height': original.height,
                           'variants': variants}
    manifest = {'schema_version': 1, 'purpose': 'Hero display derivatives only; originals retained for full artwork, expanded records and offline/print use.',
                'recipe': {'pillow': Image.__version__, 'libwebp': features.version('webp'),
                           'widths': list(WIDTHS), 'resample': 'LANCZOS', 'quality': 85, 'method': 4},
                'sources': entries}
    (root / 'site/jars/responsive.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(f"Generated derivatives for {len(generate()['sources'])} hero sources")
