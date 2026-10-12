#!/usr/bin/env python3
"""Build preview #2 from the complete ledger; production stays unchanged."""
import argparse
import json
import shutil
from pathlib import Path
from html import escape
ROOT = Path(__file__).resolve().parents[1]

# Native SVG glass: front and back share a rigid vessel coordinate system.
SHAPES = {
 'stoppered': ('M91 53 L91 76 Q64 84 64 110 L64 248 Q65 264 120 265 Q175 264 176 248 L176 110 Q176 84 149 76 L149 53 Z', '<path d="M92 51 L89 30 Q120 23 151 30 L148 51Z"/><ellipse cx="120" cy="30" rx="31" ry="6"/><ellipse cx="120" cy="55" rx="30" ry="7"/>'),
 'kitchen': ('M56 125 Q48 133 48 151 L48 245 Q48 264 120 265 Q192 264 192 245 L192 151 Q192 133 184 125 L184 104 L56 104 Z', '<path d="M54 108 L52 94 Q120 80 188 94 L186 108Z"/><ellipse cx="120" cy="95" rx="68" ry="10"/><path d="M62 98v9m10-10v9m10-9v9m10-9v9m10-8v8m10-8v8m10-8v8m10-8v8m10-9v9m10-9v9m10-10v9m10-10v9"/>'),
 'open': ('M73 86 L73 111 Q59 127 59 145 L59 247 Q59 264 120 265 Q181 264 181 247 L181 145 Q181 127 167 111 L167 86 Z', '<ellipse cx="120" cy="87" rx="47" ry="9"/><ellipse cx="120" cy="88" rx="42" ry="6"/><g transform="translate(174 252) rotate(-24)"><ellipse rx="35" ry="10"/><path d="M-35 0v7 Q0 23 35 7V0"/></g>')
}

def glass(kind,front):
    body,cap=SHAPES[kind]
    if not front:
        return f'<svg class="jar-glass jar-back" viewBox="0 0 240 290" aria-hidden="true"><defs><linearGradient id="wash-{kind}"><stop stop-color="#83acb8" stop-opacity=".22"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/><stop offset=".8" stop-color="#d9eef8" stop-opacity=".1"/><stop offset="1" stop-color="#6696a0" stop-opacity=".2"/></linearGradient></defs><path d="{body}" fill="url(#wash-{kind})" stroke="#0b2546" stroke-opacity=".35"/></svg>'
    fluid='' if kind=='open' else f'<path d="M{65 if kind=="stoppered" else 49} 177 Q120 186 {175 if kind=="stoppered" else 191} 177" stroke="#4a7c72" opacity=".4"/><ellipse cx="120" cy="178" rx="{55 if kind=="stoppered" else 71}" ry="6" fill="#4a7c72" opacity=".06"/>'
    return f'<svg class="jar-glass jar-front" viewBox="0 0 240 290" aria-hidden="true"><g fill="none" stroke="#0b2546" stroke-width="1.1" stroke-linecap="round"><path d="{body}"/>{cap}{fluid}<path d="M{72 if kind=="stoppered" else 65} 148v84" stroke="white" stroke-width="5" opacity=".85"/><path d="M{79 if kind=="stoppered" else 71} 144v77" opacity=".2"/><path d="M{168 if kind=="stoppered" else 173} 160v67" stroke="white" stroke-width="3"/><path d="M80 252 Q120 264 161 252" opacity=".35"/></g></svg>'

def build(output):
    output=Path(output)
    catalog=json.loads((output/'catalog.json').read_text())
    exhibits=[]
    for number,(name,kind,verb) in enumerate([('OpenObserve','stoppered','Observe'),('OpenResty','kitchen','Serve'),('OpenTofu','open','Provision')],1):
        p=next(p for p in catalog['projects'] if p['name']==name)
        if not p.get('artwork'): continue
        art=p['artwork']; github=p.get('github') or {}; pid=p['id']
        stars=github.get('stars'); stars=f'{stars:,} stars' if isinstance(stars,int) else 'Stars unavailable'
        exhibits.append(f'''<article class="jar-exhibit jar-{kind}">
          <a class="jar-link" href="#project-{pid}" data-jar-inspect="{pid}" aria-label="Inspect {name}">
           <span class="jar-shadow" aria-hidden="true"></span><span class="vessel">{glass(kind,False)}<span class="jar-specimen"><img src="{escape(art['path'])}" alt="{escape(art['alt'])}" width="{art['width']}" height="{art['height']}"></span>{glass(kind,True)}</span>
           <svg class="jar-leader" viewBox="0 0 360 300" aria-hidden="true"><path d="M185 184h30l22-22h96"/><circle cx="185" cy="184" r="2"/></svg>
           <span class="jar-label"><span class="jar-number">0{number} / {verb}</span><strong>{name}</strong><span class="jar-metrics">{stars}<br>{escape(github.get('license') or 'License unrecorded')}<br><span class="jar-inspect">Inspect record</span></span></span>
          </a></article>''')
    hero=f'''<section class="jar-hall" aria-label="Three illustrated software specimens"><div class="jar-stage">{''.join(exhibits)}</div><div class="jar-review"><span>Preview 02 · specimen study</span><div role="group" aria-label="Ground treatment"><button type="button" data-ground="shadows" aria-pressed="true">Shadows</button><button type="button" data-ground="baseline" aria-pressed="false">Baseline</button></div></div></section>'''
    page=(output/'index.html').read_text().replace('<body>','<body class="jar-page">').replace('</head>','<meta name="robots" content="noindex,nofollow"><link rel="stylesheet" href="jars.css"><script src="jars.js" defer></script></head>').replace('<div class="layout">',hero+'<div class="layout">',1)
    page=page.replace('<title>','<title>Preview 02 / ',1)
    (output/'jars.html').write_text(page)
    for filename in ('jars.css','jars.js'): shutil.copyfile(ROOT/'site'/filename,output/filename)
    return {'exhibits':len(exhibits)}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(build(parser.parse_args().output))
