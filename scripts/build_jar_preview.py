#!/usr/bin/env python3
"""Compose the specimen hero for the production guide or an isolated preview."""
import argparse
import hashlib
import json
import math
import re
from itertools import permutations

import weekly_draw
from build_site import attach_specimen_cutouts
import shutil
from pathlib import Path
from html import escape
ROOT = Path(__file__).resolve().parents[1]
def jar_stylesheet_href(css):
    """Keep generated geometry paired with its CSS across cached page visits."""
    return 'jars.css?v=' + hashlib.sha256(css).hexdigest()


# Calibrated vessel slots; retain these indices for specimen assignment.
DISPLAY = [
 ('OpenSCAD','low-open','Model',225,32,24,38,53,43,125),
 ('OpenSSL','square-cork','Encrypt',242,15,23,39,54,44,110),
 ('OpenRefine','shouldered','Refine',283,15,30,45,40,39,150),
 ('OpenObserve','central','Observe',330,17,37,29,26,55,300),
 ('OpenSearch','bail','Search',286,18,29,39,42,44,120),
 ('OpenResty','ribbed','Serve',254,24,24,46,52,36,140),
 ('OpenTofu','low-lid','Provision',215,23,20,40,49,39,130),
]
# Move the original fifth vessel between the second and third, with its contents.
DISPLAY_ORDER = (0, 1, 4, 2, 3, 5, 6)


# Specimen interiors calibrated against the original photographs: x/y/w/h in
# percent of the full source canvas, including its transparent margins. Keep
# these separate from DISPLAY's glass feather, crack and lighting coordinates.
# The low-lid right edge avoids the detached lid; the central cylinder's actual
# inner walls are narrower than its historical compositing window.
SPECIMEN_INTERIORS = {
    'low-open': (9.2, 39, 83.6, 43.7),
    'square-cork': (16.3, 37, 68.3, 51.5),
    'shouldered': (23.7, 33, 52.9, 55),
    'central': (40.1, 22, 20.6, 63.7),
    'bail': (20.3, 28, 60.5, 61.4),
    'ribbed': (20, 34, 60, 53.9),
    'low-lid': (9.5, 40, 63, 46),
}

# Photo-traced inner wall/floor contours in full source-canvas percentages.
# These masks stay fixed to the glass while specimen depth and idle layers move.
# The low-lid trace follows the leaning lid instead of a floating vertical cut.
SPECIMEN_INTERIOR_CONTOURS = {
    'low-open': (
        (17, 28.5), (85, 28.5), (86, 32), (90, 35),
        (92.8, 39), (92.8, 75), (91, 78.5), (85, 80.8),
        (75, 82), (50, 82.7), (25, 82), (15, 80.8),
        (10, 78.5), (9.2, 75), (9.2, 42), (10.5, 38),
        (15, 34), (17, 31),
    ),
    'square-cork': (
        (34.5, 23.7), (67, 23.7), (67.5, 28.5), (74, 31.5),
        (81, 35.5), (84.6, 40), (84.6, 84.5), (83, 87.4),
        (77, 88.5), (24, 88.5), (18, 87.4), (16.3, 84.5),
        (16.3, 42), (19, 37), (26, 32.5), (33.5, 29),
    ),
    'shouldered': (
        (34, 27.8), (67, 27.8), (73, 30), (76, 33),
        (76.6, 38), (76.6, 84.5), (74.8, 86.5), (67, 87.7),
        (50, 88), (33, 87.7), (25.3, 86.5), (23.7, 84.5),
        (23.7, 38), (24.5, 33), (28, 30),
    ),
    'central': (
        (41, 21.8), (59.8, 21.8), (60.7, 23), (60.7, 82.8),
        (60.5, 84.3), (58, 85.2), (53, 85.7), (47, 85.7),
        (42.5, 85.2), (40.4, 84.3), (40.1, 82.8), (40.1, 25),
        (39.8, 23),
    ),
    'bail': (
        (28.5, 18.5), (73.5, 18.5), (73.5, 22.3), (77.5, 25.7),
        (80.3, 29.3), (80.8, 34), (80.8, 84.1), (79, 86.3),
        (73, 88), (63, 89), (50, 89.4), (36, 89),
        (26, 88), (21.7, 86.3), (20.3, 84.1), (20.3, 34),
        (20.8, 29.3), (24, 25.7), (28.5, 22.3),
    ),
    'ribbed': (
        (29, 22.4), (71, 22.4), (72, 25.8), (78, 30),
        (80, 34), (80, 82.3), (78, 85.2), (71, 87.1),
        (59, 87.9), (41, 87.9), (29, 87.1), (22, 85.2),
        (20, 82.3), (20, 35), (21, 31.5), (27, 27),
        (29, 24.7),
    ),
    'low-lid': (
        (20, 29.2), (71, 29.2), (72, 33.5), (78, 36.8),
        (81.3, 40), (82, 45), (82, 50.5), (80, 49.1),
        (76.2, 48.9), (71.9, 50.4), (68.6, 53.9), (66.6, 59.2),
        (66.8, 66.4), (69, 74), (72.2, 80.4), (75.6, 84.8),
        (65, 85.8), (45, 86), (25, 85), (15, 83),
        (10.1, 79.4), (8.8, 75), (8.8, 46), (10, 41),
        (14.5, 37), (19, 34),
    ),
}


def interior_clip(kind):
    """Express the full-glass contour relative to the independent fit box."""
    x, y, w, h = SPECIMEN_INTERIORS[kind]
    points = SPECIMEN_INTERIOR_CONTOURS[kind]
    return "polygon(" + ",".join(
        f"{(px-x)/w*100:.4f}% {(py-y)/h*100:.4f}%" for px, py in points) + ")"


# Reviewed horizontal body span, not a destructive crop. Full-height bounds
# remain authoritative; ribbons and foot tips may meet the fixed glass mask.
# Bind the composition to its approved original so replacement art falls back.
SPECIMEN_BODY_SPANS = {
    '8d1401d46c9088a90e896b86ab0a6d1afcda86cedcc9dbf1fbcd8f1b06759d20': {
        'x': (.415, .68),
        'source_sha256': 'e4e24a73382c5e8da45cea057877c1557795a8282774c76244af12868dc88199',
    },
}


def responsive_image(source, width, manifest, source_width=None):
    """Share the same responsive resource for glass, reflection, lid and mask.

    The hero has fixed CSS heights at all breakpoints. Reserve 110% of its
    untransformed width for hover/focus zoom and the 300px-high no-JS fallback;
    the browser handles DPR selection.
    Full sources remain the final candidate for extreme DPR and print.
    """
    if source not in manifest['sources']:
        # New occupants use the committed source until responsive derivatives
        # are deliberately generated; never require an image library at build time.
        return f'src="{escape(source)}" srcset="{escape(source)} {source_width or math.ceil(width)}w" sizes="{math.ceil(width)}px"', ''
    entry = manifest['sources'][source]
    candidates = [(v['path'], v['width']) for v in entry['variants']]
    candidates.append((source, entry['width']))
    sizes = math.ceil(width)
    srcset = ', '.join(f'{path} {pixels}w' for path, pixels in candidates)
    attrs = f'src="{candidates[0][0]}" srcset="{srcset}" sizes="{sizes}px"'
    mask = 'image-set(' + ', '.join(
        f"url('{path}') {pixels / sizes:.6f}x" for path, pixels in candidates) + ')'
    return attrs, mask

def subject_box(project, cutouts):
    """Unmeasured or invalid bounds conservatively retain the entire canvas."""
    box = cutouts.get(project['id'], {}).get('bbox')
    if (isinstance(box, (list, tuple)) and len(box) == 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for v in box)
            and 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
        return box
    return [0, 0, 1, 1]


def composition_box(project, cutouts):
    """Use only source-matched, reviewed body spans; otherwise keep all parts."""
    box = subject_box(project, cutouts)
    entry = SPECIMEN_BODY_SPANS.get(project['id'])
    if entry and project['id'] in cutouts and box != [0, 0, 1, 1]:
        source = ROOT / 'site/specimens' / (project['id'] + '.webp')
        if (project['artwork']['path'] == 'specimens/' + project['id'] + '.webp'
                and source.is_file()
                and hashlib.sha256(source.read_bytes()).hexdigest() == entry['source_sha256']
                and box[0] <= entry['x'][0] < entry['x'][1] <= box[2]):
            return [entry['x'][0], box[1], entry['x'][1], box[3]]
    return box


def assign_to_jars(projects, assets, cutouts):
    """Try all 7! assignments; protect the worst fit, then maximize total fill.

    Positions and window geometry belong to the jars. Reviewed body spans may
    exclude protrusions; an unmeasured image conservatively uses its whole canvas.
    """
    def ratio(project):
        art = project['artwork']
        box = composition_box(project, cutouts)
        return art['width'] * (box[2]-box[0]) / (art['height'] * (box[3]-box[1]))
    windows = [assets[row[1]]['width'] / assets[row[1]]['height'] * SPECIMEN_INTERIORS[row[1]][2] / SPECIMEN_INTERIORS[row[1]][3]
               for row in DISPLAY]
    ratios = {p['id']: ratio(p) for p in projects}
    def occupancy(order):
        fills = [min(ratios[p['id']] / window, window / ratios[p['id']])
                 for p, window in zip(order, windows)]
        return min(fills), sum(fills)
    return max(permutations(sorted(projects, key=lambda p: p['id'])), key=occupancy)


def fitted_image(project, slot, asset, cutouts):
    art = project['artwork']
    box = composition_box(project, cutouts)
    canvas_ratio = art['width'] / art['height']
    _, _, width, height = SPECIMEN_INTERIORS[slot[1]]
    # Fit the visible body wall-to-wall. The stationary, photo-traced glass
    # mask contains horizontal motion and approved protrusions, not an inset
    # rectangle. Retain vertical idle clearance without shrinking width again.
    display_height = round(slot[3] * (.94 if slot[1] == 'central' else .82))
    display_width = round(display_height * asset['width'] / asset['height'])
    window_width = display_width * width / 100
    window_height = display_height * height / 100
    usable_width, usable_height = window_width, window_height - 4.5
    scale = min(usable_width / (window_width * (box[2]-box[0])),
                usable_height * canvas_ratio / (window_width * (box[3]-box[1])))
    subject_height = window_width * scale / canvas_ratio * (box[3]-box[1])
    # Seat the specimen at the glass floor rather than sharing slack below it.
    top = (window_height - 2.25 - subject_height) / window_height
    cx = (box[0]+box[2])/2
    return (f'width:{scale*100:.4f}%;left:50%;top:{top*100:.4f}%;'
            f'transform:translate({-cx*100:.4f}%,{-box[1]*100:.4f}%);')


def build(output, production=False):
    output=Path(output)
    catalog=json.loads((output/'catalog.json').read_text())
    assets={a['id']:a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
    manifest=json.loads((ROOT/'site/jars/responsive.json').read_text())
    draw_doc = catalog.get('weekly_draws', weekly_draw.empty())
    edition = weekly_draw.current(draw_doc, catalog)
    cutouts = attach_specimen_cutouts(catalog, ROOT)
    selected = None
    if edition:
        by_id = {p['id']: p for p in catalog['projects']}
        selected = assign_to_jars([by_id[p['id']] for p in edition['projects']], assets, cutouts)
    exhibits=[]
    for index in DISPLAY_ORDER:
        number = index + 1
        name,kind,verb,height,foot,x,y,w,h,zoom = DISPLAY[index]
        p=selected[number-1] if selected else next(p for p in catalog['projects'] if p['name']==name)
        name=p['name']
        verb='Function' if selected else verb
        if not p.get('artwork'): continue
        art=dict(p['artwork'])
        image_style = ''
        fit_bounds = ''
        if selected:
            image_style = fitted_image(p, DISPLAY[number-1], asset=assets[kind], cutouts=cutouts)
            fit_bounds = ' data-fit-bounds="' + ','.join(map(str, composition_box(p, cutouts))) + '"'
            if p['id'] in cutouts:
                art['path'] = cutouts[p['id']]['path']
        github=p.get('github') or {}; pid=p['id'];asset=assets[kind]
        glass_width=max(height*1.1,300)*asset['width']/asset['height']
        glass_attrs,mask=responsive_image(asset['path'],glass_width,manifest)
        image_scale = float(image_style.split('%')[0].split(':')[1]) if selected else zoom
        art_attrs,_=responsive_image(art['path'],glass_width*(SPECIMEN_INTERIORS[kind][2] if selected else w)/100*image_scale/100,manifest,art['width'])
        stars=github.get('stars'); stars=f'{stars:,} stars' if isinstance(stars,int) else 'Stars unavailable'
        license=github.get('license'); license_line=f'<span>{escape(license)}</span>' if license else ''
        styles=f'--height:{height}px;--foot:{foot}px;--ratio:{asset["width"]}/{asset["height"]};--sx:{x}%;--sy:{y}%;--sw:{w}%;--sh:{h}%;--zoom:{zoom}%'
        if selected:
            ix, iy, iw, ih = SPECIMEN_INTERIORS[kind]
            styles += f';--specimen-x:{ix}%;--specimen-y:{iy}%;--specimen-w:{iw}%;--specimen-h:{ih}%;--specimen-clip:{interior_clip(kind)};--specimen-overflow:visible'
        rest = .94 if kind == 'central' else .82
        display_height = round(height * rest)
        display_width = round(display_height * asset['width'] / asset['height'])
        styles += f';--display-height:{display_height}px;--display-width:{display_width}px;--display-foot:{round(foot * rest)}px'
        cut={'central':12.5,'shouldered':15.5,'ribbed':17.5}.get(kind)
        mouth={'low-open':25,'low-lid':26,'square-cork':26,'bail':17}.get(kind,cut or 20)
        styles+=f";--glass-mask:{mask};--mouth:{mouth}%;--idle-delay:{number*1.7}s;--idle-period:{18+number*1.3}s"
        cork = (f'<picture><source media="print" srcset="{asset["path"]}"><img class="jar-cork" {glass_attrs} alt="" width="{asset["width"]}" height="{asset["height"]}"></picture>'
                if kind == 'square-cork' else '')
        # Recover the original paper labels above the clear-glass treatment.
        sticker = (f'<picture><source media="print" srcset="{asset["path"]}"><img class="jar-sticker" {glass_attrs} alt="" width="{asset["width"]}" height="{asset["height"]}"></picture>'
                   if kind in ('square-cork', 'ribbed') else '')
        lid=''
        if cut:
            styles+=f';--lid-cut:{cut}%'
            lid=f'<picture><source media="print" srcset="{asset["path"]}"><img class="jar-lid" {glass_attrs} alt="" width="{asset["width"]}" height="{asset["height"]}"></picture>'
        steam='<svg class="jar-steam" viewBox="0 0 60 64" aria-hidden="true"><text class="steam-strand" x="4" y="54">∰</text><text class="steam-strand" x="23" y="34">⋈</text><text class="steam-strand" x="40" y="17">⌘</text></svg>' if cut or kind in ('low-open','low-lid') else ''
        exhibits.append(f'''<article class="jar-exhibit jar-{kind}{" has-lid" if cut else ""}" style="{styles}" data-project="{pid}"{fit_bounds}>
          <button class="jar-select" type="button" aria-expanded="false" aria-controls="jar-info-{pid}" aria-label="Crack glass — {escape(name, quote=True)}" hidden></button>
          <div class="jar-shadow" aria-hidden="true"></div><span class="jar-light-source" aria-hidden="true"></span><div class="vessel" aria-hidden="true">
           <picture><source media="print" srcset="{asset['path']}"><img class="jar-photo" {glass_attrs} alt="" width="{asset['width']}" height="{asset['height']}" fetchpriority="high"></picture>
           <div class="specimen-window"><div class="specimen-depth"><div class="specimen-idle"><picture><source media="print" srcset="{art['path']}"><img class="specimen-print" style="{image_style}" {art_attrs} alt="" width="{art['width']}" height="{art['height']}"></picture></div></div></div>
           <picture><source media="print" srcset="{asset['path']}"><img class="jar-reflection" {glass_attrs} alt="" width="{asset['width']}" height="{asset['height']}"></picture>
           {sticker}{cork}<svg class="jar-cracks" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <g class="crack-first"><path pathLength="1" d="M48 49 39 38 42 27 31 14 M39 38 24 36 16 27 M48 49 63 44 70 31 79 25 M48 49 44 63 53 75 48 91 M44 63 30 70"/></g>
           </svg><span class="jar-uplight"></span><span class="jar-led"></span>{lid}{steam}
          </div>
          <span class="jar-caption" title="{escape(name, quote=True)}"><span>0{number}</span> {escape(name)}</span>
          <div class="jar-annotation" id="jar-info-{pid}">
           <svg class="jar-leaders" aria-hidden="true"><g><path pathLength="1"/><circle r="3"/></g><g><path pathLength="1"/><circle r="3"/></g><g><path pathLength="1"/><circle r="3"/></g></svg>
           <div class="jar-callout callout-function"><span class="callout-kicker">{verb}</span><p><span class="label-ink">{escape(p['description'])}</span></p></div>
           <div class="jar-callout callout-metrics"><div class="jar-metrics"><span>{stars}</span>{license_line}</div></div>
           <div class="jar-callout callout-inspect"><a href="#project-{pid}" data-jar-inspect="{pid}">Inspect record</a></div>
          </div>
        </article>''')
    hero=f'''<section class="jar-hall" aria-label="Seven illustrated software specimens">
      <button class="jar-motion-toggle" type="button" aria-pressed="false" aria-label="Pause motion" title="Pause motion" hidden>[II]</button>
      <div class="jar-scroll" role="region" aria-label="Specimen display; scroll horizontally on smaller screens" tabindex="0"><div class="jar-stage">{''.join(exhibits)}</div></div>
    </section>'''
    # Mark JS startup before the first body paint. Deferred scripts settle before
    # DOMContentLoaded, which restores the readable fallback if jars.js fails.
    startup = '<script>document.documentElement.classList.add("jars-pending");document.addEventListener("DOMContentLoaded",()=>document.documentElement.classList.remove("jars-pending"),{once:true});</script>'
    page=(output/'index.html').read_text()
    css = (ROOT / 'site/jars.css').read_bytes()
    stylesheet = jar_stylesheet_href(css)
    if 'class="jar-page"' not in page:
        page=page.replace('<body>','<body class="jar-page">').replace('</head>',startup+f'<link rel="stylesheet" href="{stylesheet}"><script src="jars.js" defer></script></head>').replace('<div class="layout">',hero+'<div class="layout">',1)
    # Recomposition must not retain a previous token while copying newer CSS.
    page = re.sub(r'href="jars\.css(?:\?[^"<>]*)?"', f'href="{stylesheet}"', page)
    if not production:
        page=page.replace('</head>','<meta name="robots" content="noindex,nofollow"></head>').replace('<title>','<title>Preview / ',1)
    (output/('index.html' if production else 'jars.html')).write_text(page)
    (output / 'jars.css').write_bytes(css)
    shutil.copyfile(ROOT / 'site/jars.js', output / 'jars.js')
    shutil.copytree(ROOT/'site/jars',output/'jars',dirs_exist_ok=True)
    return {'exhibits':len(exhibits), 'display_week': edition['display_week'] if edition else None}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(build(parser.parse_args().output))
