"""Fixture-cache contracts use tiny fake builds, never an extra full site build."""
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

import site_test_fixtures as fixtures


class SiteFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / 'source'
        self.root.mkdir()
        self.enterContext(patch.object(fixtures, '_fixtures', {}))
        self.addCleanup(fixtures._cleanup)
        self.enterContext(patch.object(fixtures.build_site, 'ROOT', self.root))

    @staticmethod
    def fake_build(output, source_sha=None, root=None):
        (output / 'assets').mkdir(parents=True)
        (output / 'index.html').write_text('Baseline page')
        (output / 'assets/chart.svg').write_text('Baseline chart')
        return {'source_sha': source_sha, 'root': str(root),
                'projects': [{'name': 'OpenFixture', 'categories': ['one']}]}

    def test_identical_root_and_revision_build_once(self):
        with patch.object(fixtures.build_site, 'build', side_effect=self.fake_build) as build:
            first, catalog = fixtures.baseline_site(source_sha='a' * 40)
            second, again = fixtures.baseline_site(source_sha='a' * 40)
        self.assertEqual(first, second)
        self.assertEqual(catalog, again)
        build.assert_called_once_with(first, source_sha='a' * 40, root=self.root.resolve())

    def test_different_root_or_exact_revision_never_share(self):
        with patch.object(fixtures.build_site, 'build', side_effect=self.fake_build) as build:
            local, _ = fixtures.baseline_site()
            stamped, _ = fixtures.baseline_site(source_sha='a' * 40)
            other_revision, _ = fixtures.baseline_site(source_sha='b' * 40)
            other_root = self.directory / 'other-source'
            other_root.mkdir()
            with patch.object(fixtures.build_site, 'ROOT', other_root):
                other, catalog = fixtures.baseline_site(source_sha='a' * 40)
            again, _ = fixtures.baseline_site(source_sha='a' * 40)
        self.assertEqual(len({local, stamped, other_revision, other}), 4)
        self.assertEqual(build.call_count, 4)
        self.assertEqual(catalog['root'], str(other_root.resolve()))
        self.assertEqual(again, stamped)

    def test_every_catalog_is_a_deep_copy_including_first_return(self):
        with patch.object(fixtures.build_site, 'build', side_effect=self.fake_build) as build:
            _, first = fixtures.baseline_site()
            first['projects'][0]['name'] = 'Changed'
            first['projects'][0]['categories'].append('two')
            _, second = fixtures.baseline_site()
            self.assertEqual(second['projects'], [{'name': 'OpenFixture', 'categories': ['one']}])
            second['projects'].clear()
            _, third = fixtures.baseline_site()
            self.assertEqual(third['projects'], [{'name': 'OpenFixture', 'categories': ['one']}])
        self.assertEqual(build.call_count, 1)

    def test_baseline_tree_is_read_only_and_private_copy_can_change(self):
        with patch.object(fixtures.build_site, 'build', side_effect=self.fake_build):
            baseline, _ = fixtures.baseline_site()
        before = {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
        for path in [baseline, *baseline.rglob('*')]:
            self.assertEqual(path.stat().st_mode & 0o222, 0, path)
        copied = fixtures.copy_site_fixture(baseline, self.directory / 'private')
        self.assertEqual(before, {p.relative_to(copied): p.read_bytes() for p in copied.rglob('*') if p.is_file()})
        for path in [copied, *copied.rglob('*')]:
            self.assertTrue(path.stat().st_mode & stat.S_IWUSR, path)
        (copied / 'index.html').write_text('Rebuilt page')
        (copied / 'assets/chart.svg').unlink()
        (copied / 'assets/new.svg').write_text('New chart')
        self.assertEqual(before, {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()})

    def test_failed_partial_build_is_removed_and_retried(self):
        attempts = []

        def build(output, **kwargs):
            attempts.append(output)
            catalog = self.fake_build(output, **kwargs)
            if len(attempts) == 1:
                raise ValueError('Incomplete build')
            return catalog

        with patch.object(fixtures.build_site, 'build', side_effect=build):
            with self.assertRaisesRegex(ValueError, 'Incomplete build'):
                fixtures.baseline_site()
            self.assertEqual(fixtures._fixtures, {})
            self.assertFalse(attempts[0].parent.exists())
            output, catalog = fixtures.baseline_site()
        self.assertEqual(len(attempts), 2)
        self.assertNotEqual(attempts[0], output)
        self.assertEqual(catalog['projects'][0]['name'], 'OpenFixture')

    def test_actual_build_rejects_urlopen(self):
        def build(*args, **kwargs):
            urllib.request.urlopen('https://example.invalid/')

        with patch.object(fixtures.build_site, 'build', side_effect=build):
            with self.assertRaisesRegex(AssertionError, 'Offline build attempted network'):
                fixtures.baseline_site()
        self.assertEqual(fixtures._fixtures, {})

    def test_actual_build_rejects_socket_connection(self):
        def build(*args, **kwargs):
            socket.create_connection(('example.invalid', 443))

        with patch.object(fixtures.build_site, 'build', side_effect=build):
            with self.assertRaisesRegex(AssertionError, 'Offline build attempted network'):
                fixtures.baseline_site()
        self.assertEqual(fixtures._fixtures, {})

    def test_cleanup_removes_all_outputs_and_next_request_builds_again(self):
        with patch.object(fixtures.build_site, 'build', side_effect=self.fake_build) as build:
            first, _ = fixtures.baseline_site()
            second, _ = fixtures.baseline_site(source_sha='a' * 40)
            fixtures._cleanup()
            self.assertFalse(first.parent.exists())
            self.assertFalse(second.parent.exists())
            self.assertEqual(fixtures._fixtures, {})
            fresh, _ = fixtures.baseline_site()
        self.assertEqual(build.call_count, 3)
        self.assertNotEqual(first, fresh)


if __name__ == '__main__':
    unittest.main()
