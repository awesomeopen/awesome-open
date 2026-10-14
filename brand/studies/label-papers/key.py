"""Recipe used for the label paper studies: chroma-key green-backdrop PNGs to RGBA WebP, despill, crop.

Expects the generated PNGs in ./green/ (see provenance.json for their hashes). Not part of the site build."""
import glob, json, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'keyed')
os.makedirs(OUT, exist_ok=True)
meta = {}
sheet = []
for path in sorted(glob.glob(os.path.join(HERE, 'green', '*.png'))):
    name = os.path.splitext(os.path.basename(path))[0]
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dom = g - np.maximum(r, b)                      # green dominance: ~150+ on backdrop, ~0 on paper
    alpha = np.clip((120 - dom) / 90, 0, 1)
    g2 = np.minimum(g, np.maximum(r, b) + 4)         # despill
    rgba = np.dstack([r, g2, b, alpha * 255]).clip(0, 255).astype(np.uint8)
    ys, xs = np.where(alpha > .5)
    pad = 6
    y0, y1, x0, x1 = max(ys.min() - pad, 0), ys.max() + pad, max(xs.min() - pad, 0), xs.max() + pad
    im = Image.fromarray(rgba[y0:y1 + 1, x0:x1 + 1], 'RGBA')
    w = 1200
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(OUT, f'{name}.webp'), 'WEBP', quality=86, method=6)
    meta[name] = {'width': im.width, 'height': im.height, 'bytes': os.path.getsize(os.path.join(OUT, f'{name}.webp'))}
    sheet.append(im)
json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
# Preview on page white
H = sum(i.height for i in sheet) + 40 * len(sheet) + 40
prev = Image.new('RGB', (1280, H), 'white')
y = 40
for i in sheet:
    prev.paste(i, (40, y), i); y += i.height + 40
prev.thumbnail((900, 4000)); prev.save(os.path.join(OUT, 'preview.png'))
print(json.dumps(meta, indent=1))
