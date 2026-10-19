#!/usr/bin/env python3
"""Build the Observatory redesign mock (B31) from a published snapshot.

Usage: python3 site/design/observatory-redesign/build.py SNAPSHOT_JSON OUTPUT_HTML

SNAPSHOT_JSON is a published or locally built observatory/snapshot.json. Short
descriptions come from README.source.md. The output is a single self-contained
page for review; it is not part of the site build.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from font_assets import standalone_font_css
HERE = Path(__file__).resolve().parent
NOTES = 'https://github.com/awesomeopen/awesome-open/blob/main/site/OBSERVATORY-REDESIGN.md'
# Unicode White_Space, shared with build_observatory.py and observatory.js.
WS = '[\\u0009-\\u000d\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000'


def descriptions():
    rows = {}
    pattern = r'^\|\s*\[([^\]]+)\]\((https://github\.com/[^)]+)\)\s*\|\s*(.*?)\s*\|'
    for m in re.finditer(pattern, (ROOT / 'README.source.md').read_text(encoding='utf-8'), re.M):
        rows[m.group(2).lower().rstrip('/')] = (m.group(2).rstrip('/'), re.split(r'<br>', m.group(3))[0].strip())
    return rows


def main(snapshot_path, output_path):
    snap = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    rows = descriptions()
    projects = []
    for p in snap['projects']:
        url, desc = rows.get(p['url'].lower().rstrip('/'), (p['url'], ''))
        projects.append(dict(id=p['id'], n=p['name'], u=url, c=p['categories'], g=p['github'], s=p['stars'],
                             l=p['license'], cr=p['created_at'], p=p['pushed_at'], r=p['release_at'],
                             rs=p['release_status'], rc=p['release_checked_at'], d=desc))
    data = dict(asOf=snap['metrics_as_of'], sha=snap['source_sha'], categories=snap['categories'],
                projects=projects, coverage=snap['coverage'])
    logo = 'data:image/png;base64,' + base64.b64encode((ROOT / 'site/brand/botanical-128.png').read_bytes()).decode()
    sha = snap['source_sha'] or 'unknown'
    page = ((HERE / 'template.html').read_text(encoding='utf-8')
            .replace('/*FONTS*/', standalone_font_css(ROOT, serif='fraunces'))
            .replace('/*WS*/', '/' + WS + ']/g').replace('/*SEP*/', '/' + WS + '_-]/g')
            .replace('/*DATA*/', json.dumps(data, ensure_ascii=True, separators=(',', ':')).replace('</', '<\\/'))
            .replace('{{FULLSHA}}', sha).replace('{{SHA12}}', sha[:12]).replace('{{SHA}}', sha[:7])
            .replace('{{ASOF}}', snap['metrics_as_of']).replace('{{NOTES}}', NOTES).replace('{{LOGO}}', logo))
    Path(output_path).write_text(page, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
