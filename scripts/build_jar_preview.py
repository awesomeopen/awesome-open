#!/usr/bin/env python3
"""Compose the specimen hero for the production guide or an isolated preview."""
import argparse
import json
import math
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


def responsive_image(source, width, manifest):
    """Share the same responsive resource for glass, reflection, lid and mask.

    The hero has fixed CSS heights at all breakpoints. Reserve 110% of its
    untransformed width for hover/focus zoom and the 300px-high no-JS fallback;
    the browser handles DPR selection.
    Full sources remain the final candidate for extreme DPR and print.
    """
    entry = manifest['sources'][source]
    candidates = [(v['path'], v['width']) for v in entry['variants']]
    candidates.append((source, entry['width']))
    sizes = math.ceil(width)
    srcset = ', '.join(f'{path} {pixels}w' for path, pixels in candidates)
    attrs = f'src="{candidates[0][0]}" srcset="{srcset}" sizes="{sizes}px"'
    mask = 'image-set(' + ', '.join(
        f"url('{path}') {pixels / sizes:.6f}x" for path, pixels in candidates) + ')'
    return attrs, mask

def build(output, production=False):
    output=Path(output)
    catalog=json.loads((output/'catalog.json').read_text())
    assets={a['id']:a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
    manifest=json.loads((ROOT/'site/jars/responsive.json').read_text())
    exhibits=[]
    for number,(name,kind,verb,height,foot,x,y,w,h,zoom) in enumerate(DISPLAY,1):
        p=next(p for p in catalog['projects'] if p['name']==name)
        if not p.get('artwork'): continue
        art=p['artwork']; github=p.get('github') or {}; pid=p['id'];asset=assets[kind]
        glass_width=max(height*1.1,300)*asset['width']/asset['height']
        glass_attrs,mask=responsive_image(asset['path'],glass_width,manifest)
        art_attrs,_=responsive_image(art['path'],glass_width*w/100*zoom/100,manifest)
        stars=github.get('stars'); stars=f'{stars:,} stars' if isinstance(stars,int) else 'Stars unavailable'
        license=github.get('license'); license_line=f'<span>{escape(license)}</span>' if license else ''
        styles=f'--height:{height}px;--foot:{foot}px;--ratio:{asset["width"]}/{asset["height"]};--sx:{x}%;--sy:{y}%;--sw:{w}%;--sh:{h}%;--zoom:{zoom}%'
        cut={'central':12.5,'shouldered':15.5,'ribbed':17.5}.get(kind)
        mouth={'low-open':25,'low-lid':26,'square-cork':26,'bail':17}.get(kind,cut or 20)
        styles+=f";--glass-mask:{mask};--mouth:{mouth}%;--idle-delay:{number*1.7}s;--idle-period:{18+number*1.3}s"
        lid=''
        if cut:
            styles+=f';--lid-cut:{cut}%'
            lid=f'<picture><source media="print" srcset="{asset["path"]}"><img class="jar-lid" {glass_attrs} alt="" width="{asset["width"]}" height="{asset["height"]}"></picture>'
        steam='<svg class="jar-steam" viewBox="0 0 60 64" aria-hidden="true"><text class="steam-strand" x="4" y="54">∰</text><text class="steam-strand" x="23" y="34">⋈</text><text class="steam-strand" x="40" y="17">⌘</text></svg>' if cut or kind in ('low-open','low-lid') else ''
        exhibits.append(f'''<article class="jar-exhibit jar-{kind}{" has-lid" if cut else ""}" style="{styles}" data-project="{pid}">
          <button class="jar-select" type="button" aria-expanded="false" aria-controls="jar-info-{pid}" aria-label="Crack glass — {name}" hidden></button>
          <div class="jar-shadow" aria-hidden="true"></div><span class="jar-light-source" aria-hidden="true"></span><div class="vessel" aria-hidden="true">
           <picture><source media="print" srcset="{asset['path']}"><img class="jar-photo" {glass_attrs} alt="" width="{asset['width']}" height="{asset['height']}" fetchpriority="high"></picture>
           <div class="specimen-window"><div class="specimen-depth"><div class="specimen-idle"><picture><source media="print" srcset="{art['path']}"><img class="specimen-print" {art_attrs} alt="" width="{art['width']}" height="{art['height']}"></picture></div></div></div>
           <picture><source media="print" srcset="{asset['path']}"><img class="jar-reflection" {glass_attrs} alt="" width="{asset['width']}" height="{asset['height']}"></picture>
           <svg class="jar-cracks" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <g class="crack-first"><path pathLength="1" d="M48 49 39 38 42 27 31 14 M39 38 24 36 16 27 M48 49 63 44 70 31 79 25 M48 49 44 63 53 75 48 91 M44 63 30 70"/></g>
           </svg><span class="jar-uplight"></span><span class="jar-led"></span>{lid}{steam}
          </div>
          <span class="jar-caption"><span>0{number}</span> {name}</span>
          <div class="jar-annotation" id="jar-info-{pid}">
           <svg class="jar-leaders" aria-hidden="true"><g><path pathLength="1"/><circle r="3"/></g><g><path pathLength="1"/><circle r="3"/></g><g><path pathLength="1"/><circle r="3"/></g></svg>
           <div class="jar-callout callout-function"><span class="callout-kicker">{verb}</span><p><span class="label-ink">{escape(p['description'])}</span></p></div>
           <div class="jar-callout callout-metrics"><div class="jar-metrics"><span>{stars}</span>{license_line}</div></div>
           <div class="jar-callout callout-inspect"><a href="#project-{pid}" data-jar-inspect="{pid}">Inspect record</a></div>
          </div>
        </article>''')
    hero=f'''<section class="jar-hall" aria-label="Seven illustrated software specimens">
      <button class="jar-motion-toggle" type="button" aria-pressed="false" aria-label="Pause motion" title="Pause motion" hidden>[II]</button>
      <svg width="0" height="0" class="jar-filter-defs" aria-hidden="true"><defs><filter id="glass-displacement"><feTurbulence type="fractalNoise" baseFrequency=".017 .08" numOctaves="1" seed="6" result="glass"/><feDisplacementMap in="SourceGraphic" in2="glass" scale="1.3" xChannelSelector="R" yChannelSelector="G"/></filter></defs></svg>
      <div class="jar-scroll" role="region" aria-label="Specimen display; scroll horizontally on smaller screens" tabindex="0"><div class="jar-stage">{''.join(exhibits)}</div></div>
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
    return {'exhibits':len(exhibits)}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(build(parser.parse_args().output))
