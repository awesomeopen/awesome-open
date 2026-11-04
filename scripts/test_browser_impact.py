"""Impact fails open to exhaustive testing, never to skipped coverage."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from browser_impact import classify, impact
from run_browser_checks import make_plan, REPRESENTATIVE_IDS

A, B = 'a' * 64, 'b' * 64


class ImpactTests(unittest.TestCase):
    def test_guidance_allowlist_and_rendered_unknown_inputs(self):
        for paths, mode in [(['CONTRIBUTING.md'], 'docs'), (['automation/backfill.md'], 'docs'),
                            (['README.source.md'], 'full'), (['site/guide.md'], 'full'),
                            (['scripts/build_site.py'], 'full'), (['site/styles.css'], 'full'),
                            (['data/schema.json'], 'full'), ([], 'full')]:
            self.assertEqual(classify(paths, None, None)['mode'], mode)

    def test_all_changed_manifest_records_and_bytes_are_captured(self):
        old = {'schema_version': 1, 'artworks': {A: {'alt': 'old'}}}
        new = {'schema_version': 1, 'artworks': {A: {'alt': 'new'}, B: {'alt': 'added'}}}
        result = classify(['data/specimen_art.json', f'site/specimens/{A}.webp'], lambda _: old, lambda _: new)
        self.assertEqual(result['changedIds'], [A, B])
        data = dict(source_sha='sha', projects=[dict(id=i, name='sample', artwork=True) for i in [A, B]])
        plan = make_plan(data, result)
        self.assertEqual(plan['captureIds'], [A, B])
        self.assertEqual(plan['artworkIds'], [A, B])

    def test_representatives_keep_identity_after_display_name_changes(self):
        sample = sorted(REPRESENTATIVE_IDS)[0]
        data = dict(source_sha='sha', projects=[dict(id=sample, name='Renamed', artwork=True),
                                             dict(id=A, name='Changed', artwork=True)])
        plan = make_plan(data, dict(mode='selective', changedIds=[A]))
        self.assertEqual(plan['captureIds'], sorted([sample, A]))

    def test_invalid_manifest_schema_or_lock_scope_uses_full(self):
        for old, new in [({}, {}), ({'artworks': []}, {'artworks': {}}),
                         ({'schema_version': 1, 'artworks': {}}, {'schema_version': 2, 'artworks': {}}),
                         ({'artworks': {}}, {'artworks': {'bad-id': 1}})]:
            self.assertEqual(classify(['data/specimen_art.json'], lambda _: old, lambda _: new)['mode'], 'full')
        self.assertEqual(classify(['brand/assets.lock.json'], lambda _: {'files': {}},
                                 lambda _: {'files': {'site/footer.webp': 'new'}})['mode'], 'full')

    def test_missing_changed_rendered_id_uses_full(self):
        plan = make_plan(dict(source_sha='sha', projects=[dict(id=A, artwork=True)]),
                         dict(mode='selective', changedIds=[B]))
        self.assertEqual(plan['mode'], 'full')
        self.assertEqual(plan['captureIds'], [A])

    def test_git_deleted_missing_untracked_and_invalid_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid')
            guide = root / 'CONTRIBUTING.md'; guide.write_text('old')
            git('add', '.'); git('commit', '-m', 'base'); base = git('rev-parse', 'HEAD')
            guide.write_text('new')
            self.assertEqual(impact(base, root)['mode'], 'docs')
            (root / 'unknown').write_text('new')
            self.assertEqual(impact(base, root)['mode'], 'full')
            (root / 'unknown').unlink(); guide.unlink()
            self.assertEqual(impact(base, root)['mode'], 'full')
            for invalid in (None, 'main', '0' * 40, 'f' * 40):
                self.assertEqual(impact(invalid, root)['mode'], 'full')


if __name__ == '__main__':
    unittest.main()
