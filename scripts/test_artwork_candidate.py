"""Legacy-original adoption and independently checked art-only Git candidates."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import artwork_candidate as ac
import artwork_checkpoint as cp


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.pid, self.other = '1' * 64, '2' * 64
        self.plan = dict(schema_version=1, batch_id='legacy', source_revision='a' * 40,
                         project_ids=[self.pid, self.other])
        self.history = b'preserved historical index with unresolved work'
        self.selection = ac.reconcile(self.plan, [self.pid], self.history, 'one-image pilot')
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        specs = []
        for role in ('original', 'prompt', 'source', 'provenance'):
            (self.stage / role).write_bytes(b'original prompt\n' if role == 'prompt' else role.encode())
            specs.append(dict(path=role, role=role, project_id=self.pid))
        archive = self.root / 'original.zip'
        cp.create_archive(self.plan, 'generation', self.pid, specs, self.stage, archive)
        restored = self.root / 'restored.zip'
        shutil.copyfile(archive, restored)  # Offline storage fixture only.
        receipt = cp.verify_restore(archive, restored, dict(provider='fixture', destination='fixture',
                                                          object_id='1', version='1'))
        self.archives = self.root / 'archives'
        self.archives.mkdir()
        shutil.copyfile(restored, self.archives / (receipt['archive_sha256'] + '.zip'))
        self.receipts = {self.pid: receipt}
        self.git('init', '-q')
        for path, group in ac.MANIFESTS.items():
            self.write(path, {'schema_version': 1, group: {'existing': {'keep': True}}})
        self.commit()
        self.base = self.git('rev-parse', 'HEAD').decode().strip()
        self.source = f'site/specimens/{self.pid}.webp'
        self.target = f'site/specimens/cutouts/{self.pid}.webp'
        for path in (self.source, self.target):
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(path.encode())  # Real format checks belong to existing artwork tests.
        art = dict(path=self.source[5:], prompt='original prompt')
        cut = dict(path=self.target[5:], source=self.source[5:],
                   source_sha256=cp.digest(self.source.encode()), sha256=cp.digest(self.target.encode()))
        for path, group, additions in (
                ('data/specimen_art.json', 'artworks', {self.pid: art}),
                ('site/specimens/cutouts.json', 'cutouts', {self.pid: cut}),
                ('brand/assets.lock.json', 'files', {p: dict(bytes=len(p), sha256=cp.digest(p.encode()))
                                                    for p in (self.source, self.target)})):
            doc = cp.read_json(self.repo / path)
            doc[group].update(additions)
            self.write(path, doc)
        self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE)

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'Fixture')

    def write(self, path, value):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(cp.encode(value))

    def check(self):
        return ac.candidate(self.selection, self.history, self.receipts,
                            self.archives, self.repo, self.base)

    def test_legacy_adoption_and_independent_git_restore(self):
        before = (self.archives / (self.receipts[self.pid]['archive_sha256'] + '.zip')).read_bytes()
        result = self.check()
        clone = self.root / 'clone'
        subprocess.check_call(['git', 'clone', '-q', '--no-local', str(self.repo), str(clone)])
        recovered = ac.candidate(self.selection, self.history, self.receipts,
                                 self.archives, clone, self.base)
        self.assertEqual(result, recovered)
        self.assertEqual(self.selection['deferred_ids'], [self.other])
        self.assertEqual(self.selection['generation_plan'], self.plan)
        self.assertEqual(before, (self.archives / (self.receipts[self.pid]['archive_sha256'] + '.zip')).read_bytes())

    def test_history_partition_and_selection_are_bound(self):
        for key, value in [('deferred_ids', []), ('schema_version', 1), ('extra', True)]:
            bad = {**self.selection, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                ac.validate_selection(bad, self.history)
        with self.assertRaises(ValueError):
            ac.validate_selection(self.selection, b'changed history')
        for selected in ([], [self.pid, self.pid], ['3' * 64], [self.other, self.pid]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                ac.reconcile(self.plan, selected, self.history, 'pilot')

    def test_missing_conflicting_and_altered_generation_evidence(self):
        original = deepcopy(self.receipts)
        for change in ({'kind': 'quarantine'}, {'plan_sha256': 'a' * 64},
                       {'project_id': self.other}, {'archive_sha256': 'b' * 64}):
            self.receipts = {self.pid: {**original[self.pid], **change}}
            with self.subTest(change=change), self.assertRaises((ValueError, OSError)):
                self.check()
        self.receipts = original
        path = self.archives / (original[self.pid]['archive_sha256'] + '.zip')
        path.write_bytes(b'corrupted')
        with self.assertRaises(Exception):
            self.check()

    def test_accepted_metadata_is_never_overwritten(self):
        path = 'data/specimen_art.json'
        doc = cp.read_json(self.repo / path)
        doc['artworks']['existing']['keep'] = False
        self.write(path, doc)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'Existing records'):
            self.check()

    def test_dirty_unrelated_and_prompt_corrections_fail(self):
        (self.repo / 'unrelated').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.check()
        self.commit()
        with self.assertRaisesRegex(ValueError, 'only selected'):
            self.check()
        self.git('reset', '--hard', 'HEAD~1')
        path = 'data/specimen_art.json'
        doc = cp.read_json(self.repo / path)
        doc['artworks'][self.pid]['prompt'] = 'invented prompt'
        self.write(path, doc)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'prompt differs'):
            self.check()

    def test_final_bytes_and_cutout_binding_are_checked(self):
        (self.repo / self.target).write_bytes(b'changed')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'lock differs'):
            self.check()

    def test_metadata_correction_changes_head_without_new_original_archive(self):
        before = self.check()
        path = 'data/specimen_art.json'
        doc = cp.read_json(self.repo / path)
        doc['artworks'][self.pid]['review_note'] = 'Truthful corrected review'
        self.write(path, doc)
        self.commit()
        after = self.check()
        self.assertNotEqual(before['candidate_revision'], after['candidate_revision'])
        self.assertEqual(before['generation_receipts_sha256'], after['generation_receipts_sha256'])

    def test_cli_output_is_immutable(self):
        plan = self.root / 'plan.json'
        plan.write_bytes(cp.encode(self.plan))
        history = self.root / 'history.json'
        history.write_bytes(self.history)
        output = self.root / 'selection.json'
        args = ['select', '--plan', str(plan), '--history', str(history), '--project-id', self.pid,
                '--reason', 'pilot', '--output', str(output)]
        self.assertEqual(ac.main(args), 0)
        saved = output.read_bytes()
        self.assertEqual(ac.main(args), 1)
        self.assertEqual(output.read_bytes(), saved)
