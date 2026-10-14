#!/usr/bin/env python3
"""Explicit, staged regeneration of the complete category illustration set."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class ResizeError(RuntimeError):
    pass


class RollbackError(ResizeError):
    """Keep the staging directory if filesystem errors prevent restoration."""


def run_magick(magick, *arguments):
    result = subprocess.run([magick, *map(str, arguments)], capture_output=True, text=True)
    if result.returncode:
        raise ResizeError(f'ImageMagick failed ({result.returncode}): {result.stderr.strip()}')
    return result.stdout


def check_magick():
    magick = shutil.which('magick')
    if not magick:
        raise ResizeError('ImageMagick 7 (magick) is required on PATH, with PNG read and WebP write support.')
    version_output = run_magick(magick, '-version').splitlines()
    version = version_output[0] if version_output else '(empty version output)'
    if not re.match(r'Version: ImageMagick 7\.', version):
        raise ResizeError(f'Expected ImageMagick 7; found {version}')
    formats = run_magick(magick, '-list', 'format')
    modes = dict(re.findall(r'^\s*(PNG|WEBP)\*?\s+\S+\s+([rw+\-]+)\s', formats, re.M))
    if not modes.get('PNG', '').startswith('r') or not modes.get('WEBP', '').startswith('rw'):
        raise ResizeError('ImageMagick must support PNG reading and WebP reading/writing.')
    return magick, version


def load_categories(manifest):
    data = json.loads(manifest.read_text())
    categories = data.get('categories') if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(categories, dict) or not categories:
        raise ResizeError('Expected a schema_version 1 manifest with a nonempty categories object.')
    aliases = {}
    for category, record in categories.items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', category):
            raise ResizeError(f'Unsafe category ID: {category!r}')
        filename = record.get('source_filename') if isinstance(record, dict) else None
        if (not isinstance(filename, str) or not filename.endswith('.png') or
                Path(filename).name != filename or '\\' in filename or
                any(ord(char) < 32 for char in filename)):
            raise ResizeError(f'Expected a plain PNG source_filename for {category}.')
        for alias in {filename, category + '.png'}:
            if alias in aliases and aliases[alias] != category:
                raise ResizeError(f'Ambiguous source filename in manifest: {alias}')
            aliases[alias] = category
    return categories, aliases


def find_sources(source, categories, aliases):
    if not source.is_dir():
        raise ResizeError(f'Source directory is missing: {source}. Supply the archived original PNGs or use --source.')
    found = {}
    for path in sorted(source.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ResizeError(f'Source must be a regular PNG file, not a symlink or directory: {path}')
        category = aliases.get(path.name)
        if category is None:
            raise ResizeError(f'Unknown source filename: {path.name}. Use a manifest source_filename or category-ID.png.')
        if category in found:
            raise ResizeError(f'Duplicate source aliases for {category}: {found[category].name}, {path.name}')
        found[category] = path
    missing = sorted(categories.keys() - found.keys())
    if missing:
        raise ResizeError('Missing source PNGs for: ' + ', '.join(missing))
    return found


def inspect_image(magick, path, expected_format):
    # Unlike ping, this decodes the pixels. Warnings (including CRC errors) fail preflight.
    info = run_magick(magick, '-regard-warnings', path, '-format', '%m %w %h\n', 'info:').splitlines()
    if len(info) != 1:
        raise ResizeError(f'Expected a single-frame {expected_format}: {path}')
    values = info[0].split()
    if (len(values) != 3 or values[0] != expected_format or
            not all(value.isdigit() and int(value) > 0 for value in values[1:])):
        raise ResizeError(f'Invalid {expected_format} image: {path}')
    return tuple(map(int, values[1:]))


def widths(width):
    large = (width * 33 + 50) // 100
    medium = (large + 1) // 2
    small = (medium + 1) // 2
    if not small:
        raise ResizeError(f'Original width {width} is too small for the 33% resize recipe.')
    return (('l', large), ('m', medium), ('s', small))


def validate_targets(output, categories):
    for category in categories:
        for size in ('l', 'm', 's'):
            target = output / f'{category}-{size}.webp'
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ResizeError(f'Output target must be a regular file or absent: {target}')


def publish(generated, output, backup):
    """All encoding has succeeded. Save old bytes before any replacements."""
    files = sorted(generated.iterdir())
    original_hashes = {}
    for path in files:
        target = output / path.name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ResizeError(f'Output target changed during generation: {target}')
        original_hashes[path.name] = hashlib.sha256(target.read_bytes()).digest() if target.exists() else None
        if target.exists():
            shutil.copy2(target, backup / path.name)
    replaced = []
    try:
        for path in files:
            target = output / path.name
            current = hashlib.sha256(target.read_bytes()).digest() if target.exists() else None
            if target.is_symlink() or current != original_hashes[path.name]:
                raise ResizeError(f'Output changed during publication: {target}')
            replaced.append(target)
            os.replace(path, target)
    except BaseException:
        failures = []
        for target in reversed(replaced):
            try:
                saved = backup / target.name
                if saved.exists():
                    os.replace(saved, target)
                else:
                    target.unlink(missing_ok=True)
            except OSError as error:
                failures.append(f'{target}: {error}')
        if failures:
            raise RollbackError('Could not restore all output files; preserve and recover backups in '
                                f'{backup}: ' + '; '.join(failures)) from None
        raise


def generate(source, output, manifest, check_only=False):
    source, output, manifest = (Path(path).resolve() for path in (source, output, manifest))
    categories, aliases = load_categories(manifest)
    sources = find_sources(source, categories, aliases)
    if not output.is_dir():
        raise ResizeError(f'Output directory must already exist: {output}')
    if source == output or source in output.parents or output in source.parents:
        raise ResizeError('Source and output directories must not overlap.')
    validate_targets(output, categories)
    magick, version = check_magick()
    lock = output / '.category-resize.lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ResizeError(f'Resize lock already exists: {lock}. Check for an active process before removing a stale lock.') from None
    stage = None
    retain_stage = False
    try:
        stage = Path(tempfile.mkdtemp(prefix='.category-resize-', dir=output))
        snapshots, generated, backup = (stage / name for name in ('sources', 'generated', 'backup'))
        for directory in (snapshots, generated, backup):
            directory.mkdir()
        jobs = []
        source_hashes = {}
        # Preflight every source before encoding any derivative. Work from immutable copies.
        for category, original in sorted(sources.items()):
            body = original.read_bytes()
            if not body.startswith(PNG_SIGNATURE):
                raise ResizeError(f'Not a PNG: {original}')
            source_hashes[original] = hashlib.sha256(body).digest()
            snapshot = snapshots / f'{category}.png'
            snapshot.write_bytes(body)
            width, _ = inspect_image(magick, snapshot, 'PNG')
            jobs.append((category, snapshot, widths(width)))
        if check_only:
            print(f'Preflight OK: {len(jobs)} originals, {len(jobs) * 3} planned derivatives. {version}')
            return
        for category, snapshot, sizes in jobs:
            for size, width in sizes:
                destination = generated / f'{category}-{size}.webp'
                # Preserve the original recipe: each size reads the full original PNG.
                run_magick(magick, snapshot, '-filter', 'Lanczos', '-distort', 'Resize', width,
                           '-channel', 'RGB', '-unsharp', '0x0.7+0.7+0.015', '+channel',
                           '-define', 'webp:method=6', '-define', 'webp:alpha-quality=100',
                           '-quality', '88', destination)
                actual_width, _ = inspect_image(magick, destination, 'WEBP')
                if actual_width != width:
                    raise ResizeError(f'Unexpected generated width for {destination.name}: {actual_width}, expected {width}')
        for original, digest in source_hashes.items():
            if original.is_symlink() or hashlib.sha256(original.read_bytes()).digest() != digest:
                raise ResizeError(f'Source changed during generation: {original}')
        publish(generated, output, backup)
        print(f'Generated {len(jobs) * 3} WebPs from {len(jobs)} unchanged originals. {version}')
        print('Review the images and update provenance/checksum inventories before committing.')
    except RollbackError:
        retain_stage = True
        raise
    finally:
        if stage is not None and not retain_stage:
            shutil.rmtree(stage)
        if not retain_stage:
            lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'tmp/awesome-open-cat-logos',
                        help='Complete original PNG folder (default: repository tmp/awesome-open-cat-logos).')
    parser.add_argument('--output', type=Path, default=ROOT / 'site/domains',
                        help='Existing derivative directory (default: repository site/domains).')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'site/domains/provenance.json',
                        help='Category/source filename manifest (default: repository site/domains/provenance.json).')
    parser.add_argument('--check', action='store_true', help='Decode and validate originals without generating or replacing WebPs.')
    args = parser.parse_args()
    try:
        generate(args.source, args.output, args.manifest, args.check)
    except (OSError, ValueError, ResizeError) as error:
        print(f'resize.sh: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('resize.sh: interrupted', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    def terminate(signum, frame):
        raise InterruptedError('Interrupted by SIGTERM')
    signal.signal(signal.SIGTERM, terminate)
    sys.exit(main())
