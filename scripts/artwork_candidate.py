"""Offline batch candidates using immutable generation archives and Git final files.

External transfers and independent reviews remain operator responsibilities.
Legacy checkpoints are read without rewriting their plans or receipts.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import zipfile

import artwork_checkpoint as cp

MANIFESTS = {'data/specimen_art.json': 'artworks',
             'site/specimens/cutouts.json': 'cutouts', 'brand/assets.lock.json': 'files'}


def reconcile(plan, selected, history, reason):
    cp.validate_plan(plan)
    if (not isinstance(selected, list) or not selected or
            len(set(selected)) != len(selected) or
            any(pid not in plan['project_ids'] for pid in selected)):
        raise ValueError('Select unique IDs from the preserved plan')
    if selected != [pid for pid in plan['project_ids'] if pid in selected]:
        raise ValueError('Preserve plan order')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Record the scope-change reason')
    if not isinstance(history, bytes) or not history:
        raise ValueError('Preserve the prior durable index bytes')
    return {'schema_version': 2, 'generation_plan': plan,
            'selected_ids': selected,
            'deferred_ids': [pid for pid in plan['project_ids'] if pid not in selected],
            'prior_index_sha256': cp.digest(history), 'reason': reason}


def validate_selection(selection, history):
    expected = reconcile(selection['generation_plan'], selection['selected_ids'],
                         history, selection['reason'])
    if selection != expected:
        raise ValueError('Selection or preserved history differs')
    return cp.validate_plan(selection['generation_plan'])


def originals(selection, history, receipts, archives):
    plan_hash = validate_selection(selection, history)
    if not isinstance(receipts, dict) or set(receipts) != set(selection['selected_ids']):
        raise ValueError('One generation receipt per selected ID is required')
    result = {}
    for pid in selection['selected_ids']:
        receipt = receipts[pid]
        cp.validate_receipt(receipt, plan_hash, 'generation', pid)
        path = Path(archives) / (receipt['archive_sha256'] + '.zip')
        data = cp.artifact_bytes(archives, path.name)
        manifest = cp.inspect_archive_bytes(data)
        if cp.digest(data) != receipt['archive_sha256'] or (
                manifest['plan_sha256'], manifest['kind'], manifest['project_id']) != (
                plan_hash, 'generation', pid):
            raise ValueError('Original archive differs from generation receipt')
        with zipfile.ZipFile(path) as archive:
            roles = {}
            for entry in manifest['artifacts']:
                roles.setdefault(entry['role'], []).append(archive.read(entry['path']))
            if any(len(roles[r]) != 1 for r in ('original', 'prompt', 'provenance')):
                raise ValueError('Generation requires one original, prompt and provenance')
            result[pid] = roles
    return result


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def candidate(selection, history, receipts, archives, root, base):
    """Read a clean committed art-only candidate; never grant review or publication."""
    recovered = originals(selection, history, receipts, archives)
    if not isinstance(base, str) or not cp.HEX40.fullmatch(base):
        raise ValueError('Use the full base commit')
    if git(root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('Candidate checkout must be clean')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'merge-base', '--is-ancestor', base, head)
    ids = selection['selected_ids']
    assets = {f'site/specimens/{pid}.webp' for pid in ids} | {
        f'site/specimens/cutouts/{pid}.webp' for pid in ids}
    expected = assets | set(MANIFESTS)
    changed = set(git(root, 'diff', '--name-only', '-z', base, head).decode().strip('\0').split('\0'))
    if changed != expected:
        raise ValueError('Candidate must contain only selected new art and three manifests')
    docs = {}
    for path, group in MANIFESTS.items():
        before = cp.decode_json(git(root, 'show', f'{base}:{path}'))
        after = cp.read_json(Path(root) / path)
        additions = assets if group == 'files' else set(ids)
        if set(after[group]) != set(before[group]) | additions or set(before[group]) & additions:
            raise ValueError('Selected art must be new; preserve all existing records')
        stripped = {**after, group: {k: v for k, v in after[group].items() if k not in additions}}
        if stripped != before:
            raise ValueError('Existing records or manifest metadata changed')
        docs[group] = after[group]
    for path in assets:
        if git(root, 'ls-tree', base, '--', path).strip():
            raise ValueError('An accepted asset would be overwritten')
        mode = git(root, 'ls-tree', head, '--', path).decode().split()[0]
        if mode != '100644':
            raise ValueError('Assets must be ordinary non-executable files')
    for pid, roles in recovered.items():
        art, cut = docs['artworks'][pid], docs['cutouts'][pid]
        source, target = f'site/specimens/{pid}.webp', f'site/specimens/cutouts/{pid}.webp'
        if art['path'] != source[5:] or cut['path'] != target[5:] or cut['source'] != art['path']:
            raise ValueError('Asset paths differ from selected identity')
        if art['prompt'] != roles['prompt'][0].decode().rstrip('\n'):
            raise ValueError('Candidate prompt differs from original generation')
        for path in (source, target):
            data = cp.artifact_bytes(root, path)
            if docs['files'][path] != {'bytes': len(data), 'sha256': cp.digest(data)}:
                raise ValueError('Asset lock differs from candidate bytes')
        if (cut['source_sha256'] != docs['files'][source]['sha256'] or
                cut['sha256'] != docs['files'][target]['sha256']):
            raise ValueError('Cutout hashes differ from candidate bytes')
    return {'schema_version': 2, 'base_revision': base, 'candidate_revision': head,
            'selection_sha256': cp.digest(cp.encode(selection)),
            'generation_receipts_sha256': cp.digest(cp.encode(receipts)),
            'files': {p: cp.digest(cp.artifact_bytes(root, p)) for p in sorted(expected)}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    select = sub.add_parser('select')
    for name in ('plan', 'history', 'reason', 'output'):
        select.add_argument('--' + name, required=True)
    select.add_argument('--project-id', action='append', required=True)
    check = sub.add_parser('candidate')
    for name in ('selection', 'history', 'receipts', 'archives', 'root', 'base', 'output'):
        check.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        history = Path(args.history).read_bytes()
        if args.command == 'select':
            result = reconcile(cp.read_json(args.plan), args.project_id, history, args.reason)
        else:
            result = candidate(cp.read_json(args.selection), history, cp.read_json(args.receipts),
                               args.archives, args.root, args.base)
        cp.write_new(args.output, result)
        print(json.dumps({'status': 'recorded', 'output': args.output}))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f'Artwork candidate blocked: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
