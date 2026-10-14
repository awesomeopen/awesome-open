"""Synthetic-only resize tests; never regenerate the repository's artwork."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import zlib

import resize_category_images as resize


def png(path, width=131, height=87):
    """A small RGBA PNG with varying color and alpha, using only the standard library."""
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    pixels = b''.join(b'\x00' + bytes(value for x in range(width)
                                     for value in (x % 256, y % 256, (x + y) % 256, x * 255 // width))
                      for y in range(height))
    path.write_bytes(resize.PNG_SIGNATURE +
                     chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


def contents(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


class ResizeFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='category resize tests ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'original PNGs'
        self.output = self.root / 'WebP output'
        self.source.mkdir()
        self.output.mkdir()
        self.manifest = self.root / 'provenance.json'
        self.categories = {
            'alpha--example': {'source_filename': 'An original image (1).png'},
            'beta': {'source_filename': 'Second original drawing.png'},
        }
        self.write_manifest()
        png(self.source / self.categories['alpha--example']['source_filename'])
        png(self.source / 'beta.png', 109, 121)
        for category in self.categories:
            for size in ('s', 'm', 'l'):
                (self.output / f'{category}-{size}.webp').write_bytes(f'old {category} {size}'.encode())
        (self.output / 'provenance.json').write_text('Preserve unrelated metadata.\n')
        (self.output / 'README.md').write_text('Preserve unrelated documentation.\n')
        self.originals = contents(self.source)
        self.previous_output = contents(self.output)

    def write_manifest(self):
        self.manifest.write_text(json.dumps({'schema_version': 1, 'categories': self.categories}))

    def generate(self, **kwargs):
        return resize.generate(self.source, self.output, self.manifest, **kwargs)

    def assert_unchanged(self):
        self.assertEqual(contents(self.output), self.previous_output)
        self.assertEqual(contents(self.source), self.originals)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()),
                         sorted(self.previous_output))


class ResizeContractTests(ResizeFixture, unittest.TestCase):
    def test_missing_source_directory(self):
        with self.assertRaisesRegex(resize.ResizeError, 'Source directory is missing'):
            resize.generate(self.root / 'absent', self.output, self.manifest)
        self.assert_unchanged()

    def test_missing_source_category(self):
        (self.source / 'beta.png').unlink()
        self.originals = contents(self.source)
        with self.assertRaisesRegex(resize.ResizeError, 'Missing source PNGs for: beta'):
            self.generate()
        self.assert_unchanged()

    def test_unknown_and_duplicate_aliases(self):
        for filename, message in [('unknown.png', 'Unknown source filename'),
                                  ('alpha--example.png', 'Duplicate source aliases')]:
            with self.subTest(filename=filename):
                png(self.source / filename)
                with self.assertRaisesRegex(resize.ResizeError, message):
                    self.generate()
                (self.source / filename).unlink()
                self.assert_unchanged()

    def test_unsafe_manifest_ids_and_source_names(self):
        for categories in ({'../escape': {'source_filename': 'alpha.png'}},
                           {'alpha': {'source_filename': '../source.png'}},
                           {'alpha': {'source_filename': 'same.png'}, 'beta': {'source_filename': 'same.png'}},
                           {'alpha': {'source_filename': 'beta.png'}, 'beta': {'source_filename': 'Second.png'}}):
            with self.subTest(categories=categories):
                self.categories = categories
                self.write_manifest()
                with self.assertRaises(resize.ResizeError):
                    self.generate()
                self.assert_unchanged()

    def test_malformed_or_empty_manifest(self):
        for data in ([], None, {}, {'schema_version': 1, 'categories': {}},
                     {'schema_version': 2, 'categories': self.categories}):
            with self.subTest(data=data):
                self.manifest.write_text(json.dumps(data))
                with self.assertRaisesRegex(resize.ResizeError, 'schema_version 1'):
                    self.generate()
                self.assert_unchanged()

    def test_symlink_source_and_target_refused(self):
        original = self.source / 'beta.png'
        saved = self.root / 'original.png'
        original.rename(saved)
        original.symlink_to(saved)
        with self.assertRaisesRegex(resize.ResizeError, 'symlink'):
            self.generate()
        original.unlink()
        saved.rename(original)
        target = self.output / 'beta-m.webp'
        body = target.read_bytes()
        target.unlink()
        target.symlink_to(original)
        with self.assertRaisesRegex(resize.ResizeError, 'Output target'):
            self.generate()
        target.unlink()
        target.write_bytes(body)
        self.assert_unchanged()

    def test_missing_output_and_overlap_refused(self):
        with self.assertRaisesRegex(resize.ResizeError, 'Output directory must already exist'):
            resize.generate(self.source, self.root / 'absent', self.manifest)
        with self.assertRaisesRegex(resize.ResizeError, 'must not overlap'):
            resize.generate(self.source, self.source, self.manifest)
        self.assert_unchanged()

    def test_dependency_errors_are_actionable(self):
        with mock.patch.object(resize.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(resize.ResizeError, 'ImageMagick 7'):
                self.generate()
        with mock.patch.object(resize.shutil, 'which', return_value='/fake/magick'):
            with mock.patch.object(resize, 'run_magick', return_value='Version: ImageMagick 6.9.0'):
                with self.assertRaisesRegex(resize.ResizeError, 'Expected ImageMagick 7'):
                    self.generate()
            with mock.patch.object(resize, 'run_magick', side_effect=[
                    'Version: ImageMagick 7.1.1-43', ' PNG* PNG rw- Portable Network Graphics\n']):
                with self.assertRaisesRegex(resize.ResizeError, 'PNG reading and WebP reading/writing'):
                    self.generate()
        self.assert_unchanged()

    def test_rounding_keeps_original_recipe(self):
        self.assertEqual(resize.widths(131), (('l', 43), ('m', 22), ('s', 11)))
        self.assertEqual(resize.widths(109), (('l', 36), ('m', 18), ('s', 9)))
        with self.assertRaises(resize.ResizeError):
            resize.widths(1)


@unittest.skipUnless(shutil.which('magick'), 'Optional ImageMagick 7 integration tests require magick on PATH')
class ResizeImageMagickTests(ResizeFixture, unittest.TestCase):
    def test_success_preserves_originals_metadata_and_exact_recipe(self):
        self.generate()
        first = contents(self.output)
        self.assertEqual(contents(self.source), self.originals)
        for name in ('provenance.json', 'README.md'):
            self.assertEqual(first[name], self.previous_output[name])
        magick, _ = resize.check_magick()
        # Compare to the old direct command, independently of the implementation's job planning.
        reference = self.root / 'reference.webp'
        original = self.source / 'An original image (1).png'
        for size, width in [('l', 43), ('m', 22), ('s', 11)]:
            subprocess.run([magick, str(original), '-filter', 'Lanczos', '-distort', 'Resize', str(width),
                            '-channel', 'RGB', '-unsharp', '0x0.7+0.7+0.015', '+channel',
                            '-define', 'webp:method=6', '-define', 'webp:alpha-quality=100', '-quality', '88',
                            str(reference)], check=True, capture_output=True)
            self.assertEqual(first[f'alpha--example-{size}.webp'], reference.read_bytes())
            self.assertEqual(resize.inspect_image(magick, reference, 'WEBP')[0], width)
        self.generate()
        self.assertEqual(contents(self.output), first, 'Repeated runs must be byte-identical with one toolchain')
        self.assertEqual(contents(self.source), self.originals)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), sorted(first))

    def test_default_paths_resolve_from_script_not_working_directory(self):
        scripts = self.root / 'repo with spaces/scripts'
        scripts.mkdir(parents=True)
        for name in ('resize.sh', 'resize_category_images.py'):
            shutil.copy2(Path(resize.__file__).parent / name, scripts / name)
        source = scripts.parent / 'tmp/awesome-open-cat-logos'
        output = scripts.parent / 'site/domains'
        shutil.copytree(self.source, source)
        shutil.copytree(self.output, output)
        shutil.copy2(self.manifest, output / 'provenance.json')
        result = subprocess.run(['bash', str(scripts / 'resize.sh')], cwd=self.root,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Generated 6 WebPs', result.stdout)
        self.assertEqual(contents(source), self.originals)
        self.assertEqual((output / 'provenance.json').read_bytes(), self.manifest.read_bytes())
        self.assert_unchanged()

    def test_explicit_relative_paths_and_preflight_only(self):
        result = subprocess.run(['bash', str(Path(resize.__file__).with_name('resize.sh')),
                                 '--source', self.source.name, '--output', self.output.name,
                                 '--manifest', self.manifest.name, '--check'],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Preflight OK', result.stdout)
        self.assert_unchanged()

    def test_late_corrupt_input_fails_before_any_generation(self):
        (self.source / 'beta.png').write_bytes(resize.PNG_SIGNATURE + b'corrupt')
        self.originals = contents(self.source)
        with mock.patch.object(resize, 'run_magick', wraps=resize.run_magick) as magick:
            with self.assertRaises(resize.ResizeError):
                self.generate()
        self.assertFalse(any('-distort' in call.args for call in magick.call_args_list))
        self.assert_unchanged()

    def test_late_generation_failure_preserves_entire_existing_batch(self):
        original_run = resize.run_magick
        calls = []
        def fail_later(magick, *args):
            if '-distort' in args:
                calls.append(Path(args[-1]).name)
                if calls[-1] == 'beta-m.webp':
                    raise resize.ResizeError('Injected late encoding failure')
            return original_run(magick, *args)
        with mock.patch.object(resize, 'run_magick', side_effect=fail_later):
            with self.assertRaisesRegex(resize.ResizeError, 'late encoding failure'):
                self.generate()
        self.assertEqual(len(calls), 5, 'Failure must occur after multiple successful encodes')
        self.assert_unchanged()

    def test_invalid_generated_output_preserves_entire_existing_batch(self):
        original_run = resize.run_magick
        def corrupt_later(magick, *args):
            if '-distort' in args and Path(args[-1]).name == 'beta-m.webp':
                Path(args[-1]).write_bytes(b'not a WebP')
                return ''
            return original_run(magick, *args)
        with mock.patch.object(resize, 'run_magick', side_effect=corrupt_later):
            with self.assertRaises(resize.ResizeError):
                self.generate()
        self.assert_unchanged()

    def test_publication_failure_restores_existing_and_removes_new_outputs(self):
        (self.output / 'alpha--example-m.webp').unlink()
        self.previous_output = contents(self.output)
        replace = os.replace
        def fail_later(source, target):
            if source.parent.name == 'generated' and target.name == 'beta-l.webp':
                raise OSError('Injected publication failure')
            return replace(source, target)
        with mock.patch.object(resize.os, 'replace', side_effect=fail_later):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                self.generate()
        self.assert_unchanged()

    def test_existing_lock_is_not_removed(self):
        lock = self.output / '.category-resize.lock'
        lock.mkdir()
        with self.assertRaisesRegex(resize.ResizeError, 'lock already exists'):
            self.generate()
        self.assertTrue(lock.is_dir())
        lock.rmdir()
        self.assert_unchanged()

    def test_recovery_files_retained_if_filesystem_prevents_rollback(self):
        replace = os.replace
        def fail_twice(source, target):
            if source.parent.name == 'generated' and target.name == 'beta-l.webp':
                raise OSError('Injected publication failure')
            if source.parent.name == 'backup':
                raise OSError('Injected rollback failure')
            return replace(source, target)
        with mock.patch.object(resize.os, 'replace', side_effect=fail_twice):
            with self.assertRaisesRegex(resize.RollbackError, 'preserve and recover backups'):
                self.generate()
        stages = [path for path in self.output.glob('.category-resize-*') if path.is_dir()]
        self.assertEqual(len(stages), 1)
        self.assertTrue((self.output / '.category-resize.lock').is_dir())
        self.assertEqual(contents(stages[0] / 'backup'),
                         {name: body for name, body in self.previous_output.items() if name.endswith('.webp')})
        self.assertEqual(contents(self.source), self.originals)


if __name__ == '__main__':
    unittest.main()
