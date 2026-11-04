"""Conservative browser impact from a verified Git base and the current worktree."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ID = r'[a-f0-9]{64}'
ART = re.compile(rf'(?:site/)?specimens/(?:cutouts/|responsive/)?({ID})(?:-cutout)?(?:-(?:512|768))?\.webp')
MAPS = {'data/specimen_art.json': 'artworks', 'data/function_summaries.json': 'summaries',
        'site/specimens/cutouts.json': 'cutouts', 'site/specimens/responsive.json': 'sources',
        'brand/assets.lock.json': 'files'}


def documentation(path):
    # Explicit authored guidance only. New paths and rendered site documentation
    # require review before joining this allowlist.
    return path in {'AGENTS.md', 'CONTRIBUTING.md'} or (
        path.endswith('.md') and path.startswith(('automation/', 'brand/decisions/', 'brand/studies/')))


def classify(paths, before, after):
    """Readers return parsed JSON. Any ambiguous input fails back to full."""
    full = dict(mode='full', reason='Shared, unknown or invalid input', changedIds=[])
    if not paths or len(paths) != len(set(paths)):
        return full
    changed = set()
    try:
        for path in paths:
            if documentation(path):
                continue
            match = ART.fullmatch(path)
            if match:
                changed.add(match[1])
                continue
            if path not in MAPS:
                return full
            key = MAPS[path]
            old, new = before(path), after(path)
            if not isinstance(old, dict) or not isinstance(new, dict):
                return full
            if {k: v for k, v in old.items() if k != key} != {k: v for k, v in new.items() if k != key}:
                return full
            a, b = old[key], new[key]
            if not isinstance(a, dict) or not isinstance(b, dict):
                return full
            for item in a.keys() | b.keys():
                if a.get(item) == b.get(item):
                    continue
                if any(item in mapping and not isinstance(mapping[item], dict) for mapping in (a, b)):
                    return full
                if re.fullmatch(ID, item) and key in {'artworks', 'summaries', 'cutouts'}:
                    changed.add(item)
                elif key in {'sources', 'files'} and (match := ART.fullmatch(item)):
                    changed.add(match[1])
                else:
                    return full
        if not changed and not all(documentation(p) for p in paths):
            return full
        return dict(mode='selective' if changed else 'docs',
                    reason='Verified per-project inputs' if changed else 'Allowlisted guidance only',
                    changedIds=sorted(changed))
    except (ValueError, KeyError, TypeError, OSError):
        return full


def impact(base, root=ROOT):
    fallback = dict(mode='full', reason='Missing or unverifiable Git comparison', changedIds=[])
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode()
    try:
        if not base or not re.fullmatch(r'[a-f0-9]{40}', base) or base == '0' * 40:
            return fallback
        git('cat-file', '-e', base + '^{commit}')
        head = git('rev-parse', 'HEAD').strip()
        # Diff includes committed and local tracked edits; untracked inputs are
        # uncertain. --no-renames includes both old and new paths.
        if git('ls-files', '--others', '--exclude-standard').strip():
            return fallback
        paths = git('diff', '--name-only', '--no-renames', '-z', base, '--').rstrip('\0').split('\0')
        # Deletions/symlinks are deliberately uncertain, including docs deletion.
        if any(not (root / p).is_file() or (root / p).is_symlink() for p in paths):
            return fallback
        result = classify(paths, lambda p: json.loads(git('show', f'{base}:{p}')),
                          lambda p: json.loads((root / p).read_text()))
        return dict(result, baseSha=base, headSha=head, paths=paths)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        return fallback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=os.environ.get('BROWSER_BASE_SHA'))
    args = parser.parse_args()
    result = impact(args.base)
    print(json.dumps(result, indent=2))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('browser=' + str(result['mode'] != 'docs').lower() + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
