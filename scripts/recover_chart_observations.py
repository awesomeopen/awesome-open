#!/usr/bin/env python3
"""Seed the archive from bounded, local first-parent Git history; no API calls.

Only complete snapshots accepted by today's evidence validators are imported.
A source commit/blob identifies recovery provenance, never a collection date.
"""
import argparse
import json
from pathlib import Path
import subprocess

import chart_observations as observations
from update_star_history import HistoryError

ROOT = Path(__file__).resolve().parents[1]
PATHS = ('data/hn_evidence.json', 'data/star_history.json')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def recover(root, base, limit=200, archive=None):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Recovery must be bounded to 1–1000 snapshot commits')
    previous = observations.merge(archive or observations.empty())
    archive = observations.empty()
    base = git(root, 'rev-parse', '--verify', base + '^{commit}')
    revisions = git(root, 'log', '--first-parent', '--format=%H', '-n', str(limit + 1), base, '--', *PATHS).splitlines()
    truncated = len(revisions) > limit
    revisions = list(reversed(revisions[:limit]))
    seen = set()
    sources, skipped = [], []
    for commit in revisions:
        entries = git(root, 'ls-tree', commit, '--', *PATHS).splitlines()
        for entry in entries:
            metadata, path = entry.split('\t', 1)
            blob = metadata.split()[2]
            if (path, blob) in seen:
                continue
            seen.add((path, blob))
            before = set(archive['observations'])
            add = observations.add_hn if path == PATHS[0] else observations.add_stars
            try:
                document = json.loads(git(root, 'cat-file', 'blob', blob))
                candidate = observations.empty()
                add(candidate, document)
                observations.validate(candidate)
            except (ValueError, KeyError, TypeError, HistoryError) as error:
                # Unsupported/invalid historical payloads are disclosed, never
                # relabeled as successful current-schema evidence.
                skipped.append({'commit': commit, 'blob': blob, 'path': path,
                                'reason': str(error)[:250]})
                continue
            # Import the whole verified blob or nothing. A late corrupt record
            # must not leave partially imported, unattributed observations.
            for section in ('objects', 'observations'):
                archive[section].update(candidate[section])
            sources.append({'commit': commit, 'blob': blob, 'path': path,
                            'observations': sorted(set(archive['observations']) - before)})
    manifest = {'method': 'git-first-parent', 'base_sha': base, 'max_snapshot_commits': limit,
                'snapshot_commits_scanned': len(revisions), 'history_truncated': truncated,
                'sources': sources, 'skipped': skipped}
    archive['recoveries'][observations.digest(manifest)] = manifest
    observations.validate(archive)
    return observations.merge(previous, archive), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='origin/main')
    parser.add_argument('--max-commits', type=int, default=200)
    parser.add_argument('--archive', type=Path, default=ROOT / observations.ARCHIVE)
    args = parser.parse_args()
    archive, manifest = recover(ROOT, args.ref, args.max_commits, observations.load(args.archive))
    observations.save(args.archive, archive)
    print(json.dumps({'recovery': {k: v for k, v in manifest.items() if k != 'sources'},
                      'unique_snapshot_blobs': len(manifest['sources']),
                      'coverage': observations.coverage(archive)}, indent=2))


if __name__ == '__main__':
    main()
