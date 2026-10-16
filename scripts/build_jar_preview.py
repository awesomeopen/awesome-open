#!/usr/bin/env python3
"""Compose the specimen hero for the production guide or an isolated preview."""
import argparse
import json
import math
from itertools import permutations

import weekly_draw
from build_site import attach_specimen_cutouts
import shutil
from pathlib import Path
from html import escape
ROOT = Path(__file__).resolve().parents[1]
# Ordered by vessel height, not by project rank. Calibrated to the source photographs.
DISPLAY = [
 ('OpenSCAD','low-open','Model',225,32,24,38,53,43,125),
 ('OpenSSL','square-cork','Encrypt',242,15,23,39,54,44,110),
 ('OpenRefine','shouldered','Refine',283,15,30,45,40,39,150),
 ('OpenObserve','central','Observe',330,17,37,29,26,55,300),
 ('OpenSearch','bail','Search',286,18,29,39,42,44,120),
 ('OpenResty','ribbed','Serve',254,24,24,46,52,36,140),
 ('OpenTofu','low-lid','Provision',215,23,20,40,49,39,130),
]


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

def assign_to_jars(projects, assets, cutouts):
    """Try all 7! assignments; maximize subject area without cropping any subject.

    Positions and window geometry belong to the jars. Subject boxes belong to
    validated cut-outs; an unmeasured image conservatively uses its whole canvas.
    """
    def ratio(project):
        art = project['artwork']
        box = cutouts.get(project['id'], {}).get('bbox', [0, 0, 1, 1])
        return art['width'] * (box[2]-box[0]) / (art['height'] * (box[3]-box[1]))
    windows = [assets[row[1]]['width'] / assets[row[1]]['height'] * row[7] / row[8]
               for row in DISPLAY]
    ratios = {p['id']: ratio(p) for p in projects}
    def occupancy(order):
        return sum(min(ratios[p['id']] / window, window / ratios[p['id']])
                   for p, window in zip(order, windows))
    return max(permutations(sorted(projects, key=lambda p: p['id'])), key=occupancy)


def fitted_image(project, slot, asset, cutouts):
    art = project['artwork']
    box = cutouts.get(project['id'], {}).get('bbox', [0, 0, 1, 1])
    window_ratio = asset['width'] / asset['height'] * slot[7] / slot[8]
    canvas_ratio = art['width'] / art['height']
    # Reserve 12% breathing room for idle motion/displacement; center the subject,
    # rather than the source canvas's possibly asymmetric white margins.
    scale = .88 * min(1 / (box[2]-box[0]), canvas_ratio / (window_ratio * (box[3]-box[1])))
    cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
    return (f'width:{scale*100:.4f}%;left:50%;top:50%;'
            f'transform:translate({-cx*100:.4f}%,{-cy*100:.4f}%);')


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
    for number,(name,kind,verb,height,foot,x,y,w,h,zoom) in enumerate(DISPLAY,1):
        p=selected[number-1] if selected else next(p for p in catalog['projects'] if p['name']==name)
        name=p['name']
        verb='Function' if selected else verb
        if not p.get('artwork'): continue
        art=dict(p['artwork'])
        image_style = ''
        if selected:
            image_style = fitted_image(p, DISPLAY[number-1], asset=assets[kind], cutouts=cutouts)
            if p['id'] in cutouts:
                art['path'] = cutouts[p['id']]['path']
        github=p.get('github') or {}; pid=p['id'];asset=assets[kind]
        glass_width=max(height*1.1,300)*asset['width']/asset['height']
        glass_attrs,mask=responsive_image(asset['path'],glass_width,manifest)
        image_scale = float(image_style.split('%')[0].split(':')[1]) if selected else zoom
        art_attrs,_=responsive_image(art['path'],glass_width*w/100*image_scale/100,manifest,art['width'])
        stars=github.get('stars'); stars=f'{stars:,} stars' if isinstance(stars,int) else 'Stars unavailable'
        license=github.get('license'); license_line=f'<span>{escape(license)}</span>' if license else ''
        styles=f'--height:{height}px;--foot:{foot}px;--ratio:{asset["width"]}/{asset["height"]};--sx:{x}%;--sy:{y}%;--sw:{w}%;--sh:{h}%;--zoom:{zoom}%'
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
        exhibits.append(f'''<article class="jar-exhibit jar-{kind}{" has-lid" if cut else ""}" style="{styles}" data-project="{pid}">
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
    label = (f"Weekly draw · week of {edition['display_week']}" if edition else 'Weekly draws · original display')
    hero=f'''<section class="jar-hall" aria-label="Seven illustrated software specimens">
      <button class="jar-motion-toggle" type="button" aria-pressed="false" aria-label="Pause motion" title="Pause motion" hidden>[II]</button>
      <svg width="0" height="0" class="jar-filter-defs" aria-hidden="true"><defs><filter id="glass-displacement"><feTurbulence type="fractalNoise" baseFrequency=".017 .08" numOctaves="1" seed="6" result="glass"/><feDisplacementMap in="SourceGraphic" in2="glass" scale="1.3" xChannelSelector="R" yChannelSelector="G"/></filter></defs></svg>
      <div class="jar-scroll" role="region" aria-label="Specimen display; scroll horizontally on smaller screens" tabindex="0"><div class="jar-stage">{''.join(exhibits)}</div></div>
      <p class="jar-draw-link"><a href="draws/{"#week-" + edition["display_week"] if edition else ""}">{label}</a></p>
    </section>'''
    # Mark JS startup before the first body paint. Deferred scripts settle before
    # DOMContentLoaded, which restores the readable fallback if jars.js fails.
    startup = '<script>document.documentElement.classList.add("jars-pending");document.addEventListener("DOMContentLoaded",()=>document.documentElement.classList.remove("jars-pending"),{once:true});</script>'
    page=(output/'index.html').read_text()
    if 'class="jar-page"' not in page:
        page=page.replace('<body>','<body class="jar-page">').replace('</head>',startup+'<link rel="stylesheet" href="jars.css"><script src="jars.js" defer></script></head>').replace('<div class="layout">',hero+'<div class="layout">',1)
    if not production:
        page=page.replace('</head>','<meta name="robots" content="noindex,nofollow"></head>').replace('<title>','<title>Preview / ',1)
    (output/('index.html' if production else 'jars.html')).write_text(page)
    for filename in ('jars.css','jars.js'): shutil.copyfile(ROOT/'site'/filename,output/filename)
    shutil.copytree(ROOT/'site/jars',output/'jars',dirs_exist_ok=True)
    return {'exhibits':len(exhibits), 'display_week': edition['display_week'] if edition else None}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(build(parser.parse_args().output))
