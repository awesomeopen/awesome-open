#!/usr/bin/env python3
"""Measure a built field guide against its size budget.

Prints a Markdown table, appends it to $GITHUB_STEP_SUMMARY when set and exits
non-zero when a limit is exceeded (unless --warn-only). Limits sit just above the
measured sizes; a PR that intentionally grows or shrinks an output changes its
limit here, with the reason. See PRD/2026-10-22_Performance-tuning.md (W3).
"""

import argparse
import gzip
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
KIB, MIB = 1024, 1024 * 1024
IMAGES = {'.webp', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.avif'}

# (label, measure, limit, reason). Measures are defined in measure().
BUDGET = [
    ('Site total', 'total_bytes', 512 * MIB,
     'GitHub Pages publishes at most 1 GB; baseline 128 MiB, about 270 MiB with artwork for every project'),
    ('Site without specimen artwork', 'other_bytes', 64 * MIB,
     'Everything outside specimens/; baseline 57 MiB'),
    ('Specimen artwork per illustrated project', 'specimen_average', 512 * KIB,
     'Original plus cutout, averaged over projects with artwork; baseline 408 KiB'),
    ('Files', 'files', 4000, 'Pages artifact upload time; baseline 2,055'),
    ('index.html', 'index_bytes', 1536 * KIB,
     'Initial ledger HTML parsed on every visit; baseline 932 KiB'),
    ('index.html (gzip)', 'index_gzip', 256 * KIB,
     'Initial ledger transfer; baseline 133 KiB'),
    ('catalog.json', 'catalog_bytes', 16 * MIB, 'Download size; baseline 12.2 MiB'),
    ('Largest other file', 'largest_other', 12 * MIB,
     'Any single file outside the rows above; baseline 9.5 MiB (data/star_history.json)'),
    ('Largest image', 'largest_image', 2560 * KIB,
     'Footer panoramas and pattern; baseline 2.0 MiB'),
    ('Largest specimen artwork', 'largest_specimen', 640 * KIB,
     'One specimen or cutout WebP; baseline 441 KiB'),
]


def measure(site):
    files = [path for path in site.rglob('*') if path.is_file()]
    sizes = {path.relative_to(site).as_posix(): path.stat().st_size for path in files}
    named = {'index.html', 'catalog.json'}
    index = site / 'index.html'
    specimen_bytes = sum(size for name, size in sizes.items() if name.startswith('specimens/'))
    # Each illustrated project has one original at the top of specimens/.
    illustrated = sum(1 for name in sizes if name.startswith('specimens/') and name.count('/') == 1)
    values = {
        'total_bytes': sum(sizes.values()),
        'other_bytes': sum(sizes.values()) - specimen_bytes,
        'specimen_average': specimen_bytes // illustrated if illustrated else 0,
        'files': len(sizes),
        'index_bytes': sizes.get('index.html', 0),
        'index_gzip': len(gzip.compress(index.read_bytes(), 6)) if index.is_file() else 0,
        'catalog_bytes': sizes.get('catalog.json', 0),
        'largest_other': max((size for name, size in sizes.items() if name not in named), default=0),
        'largest_image': max((size for name, size in sizes.items()
                              if Path(name).suffix.lower() in IMAGES), default=0),
        'largest_specimen': max((size for name, size in sizes.items()
                                 if name.startswith('specimens/')), default=0),
    }
    return values, sorted(sizes.items(), key=lambda item: -item[1])


def human(value, measure):
    if measure == 'files':
        return f'{value:,}'
    for unit, size in (('MiB', MIB), ('KiB', KIB)):
        if value >= size:
            return f'{value / size:.1f} {unit}'
    return f'{value} B'


def report(site):
    values, largest = measure(site)
    failures = []
    lines = ['## Site size budget', '',
             '| Measure | Value | Limit | Status | Reason |', '| --- | ---: | ---: | --- | --- |']
    for label, key, limit, reason in BUDGET:
        over = values[key] > limit
        if over:
            failures.append(label)
        status = 'Over' if over else 'OK'
        lines.append(f'| {label} | {human(values[key], key)} | {human(limit, key)} | {status} | {reason} |')
    lines += ['', 'Largest files:', '']
    lines += [f'- `{name}`: {human(size, "bytes")}' for name, size in largest[:5]]
    return '\n'.join(lines) + '\n', failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('site', nargs='?', type=Path, default=ROOT / 'tmp/site')
    parser.add_argument('--warn-only', action='store_true',
                        help='Report limits that are exceeded without failing')
    args = parser.parse_args(argv)
    if not (args.site / 'index.html').is_file():
        raise SystemExit(f'No built site at {args.site}; run scripts/build_site.py first')
    text, failures = report(args.site)
    print(text)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as output:
            output.write(text)
    if failures:
        message = 'Size budget exceeded: ' + ', '.join(failures)
        if args.warn_only:
            print(f'::warning::{message}')
        else:
            print(f'::error::{message}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
