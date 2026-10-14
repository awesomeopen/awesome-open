#!/usr/bin/env python3
"""Regenerate transparent display cut-outs of approved specimen art.

Only white ground connected to the image border becomes transparent, so pale
areas inside a drawing stay opaque. Run deliberately after adding or changing
specimen art (requires Pillow, NumPy and SciPy); normal builds copy the committed
derivatives and need no extra dependency. Originals are never modified.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, features
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'specimens/cutouts'
RECIPE = ('Border-connected ground: luminance > 0.90, connected to an image edge. Edge band: ground dilated 2px, '
          'alpha = clip((0.985 - L) / 0.085), Gaussian sigma 0.6, colour un-premultiplied from white. WebP q88, method 6.')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cutout(source):
    rgb = np.asarray(Image.open(source).convert('RGB')).astype(np.float32) / 255
    lum = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    labels, _ = ndimage.label(lum > .9)
    edge = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    ground = np.isin(labels, edge[edge > 0])
    band = ndimage.binary_dilation(ground, iterations=2)
    alpha = np.ones_like(lum)
    alpha[band] = np.clip((.985 - lum) / .085, 0, 1)[band]
    alpha = ndimage.gaussian_filter(alpha, .6)
    alpha[~band] = 1
    a = np.maximum(alpha[..., None], 1e-3)
    colour = np.clip((rgb - (1 - a)) / a, 0, 1)
    colour[alpha < .02] = 0
    ys, xs = np.nonzero(alpha > .5)
    h, w = lum.shape
    bbox = [round(xs.min() / w, 4), round(ys.min() / h, 4), round((xs.max() + 1) / w, 4), round((ys.max() + 1) / h, 4)]
    image = Image.fromarray(np.dstack([colour * 255, alpha * 255]).astype(np.uint8), 'RGBA')
    return image, bbox


def main():
    manifest = json.loads((ROOT / 'data/specimen_art.json').read_text(encoding='utf-8'))
    out_dir = ROOT / 'site' / OUTPUT
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = {}
    for pid, entry in sorted(manifest['artworks'].items()):
        source = ROOT / 'site' / entry['path']
        if entry.get('review_status') != 'approved' or not source.is_file():
            continue
        image, bbox = cutout(source)
        target = out_dir / f'{pid}.webp'
        image.save(target, 'WEBP', quality=88, method=6)
        entries[pid] = {'source': entry['path'], 'source_sha256': sha256(source), 'path': f'{OUTPUT}/{pid}.webp',
                        'sha256': sha256(target), 'width': image.width, 'height': image.height, 'subject_bbox': bbox}
    for stale in out_dir.glob('*.webp'):
        if stale.stem not in entries:
            stale.unlink()
    document = {'schema_version': 1, 'recipe': RECIPE,
                'tools': {'pillow': Image.__version__, 'numpy': np.__version__, 'webp': features.version('webp')},
                'cutouts': entries}
    (ROOT / 'site/specimens/cutouts.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(entries)} specimen cut-outs to site/{OUTPUT}')


if __name__ == '__main__':
    main()
