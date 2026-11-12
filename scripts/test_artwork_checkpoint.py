"""Network-free recovery, interruption and generation-budget gates."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import artwork_checkpoint as checkpoint


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.staging = self.root / "staging"
        self.staging.mkdir()
        self.state = self.root / "state"
        self.plan = {"schema_version": 1, "batch_id": "art-20261108", "source_revision": "a" * 40,
                     "project_ids": ["1" * 64, "2" * 64]}
        self.now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        self.storage = {"provider": "test fixture", "destination": "private-folder",
                        "object_id": "object-1", "version": "1"}
        self.counter = 0

    def bundle(self, kind="probe", pid=None):
        self.counter += 1
        specs = []
        for role in sorted(checkpoint.ROLES[kind]):
            ids = [pid]
            for project_id in ids:
                name = f"{self.counter}/{role}-{project_id or 'batch'}.bin"
                target = self.staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if role == "recovery_index":
                    target.write_bytes(checkpoint.encode(self.recovery_index()))
                elif role == "candidate":
                    target.write_bytes(checkpoint.encode({"candidate_revision": "c" * 40}))
                elif role == "reservation":
                    target.write_bytes(checkpoint.encode({"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": pid}))
                elif role == "failure":
                    target.write_bytes(checkpoint.encode(self.quarantine_failure(pid) if kind == "quarantine" else self.failure(pid)))
                else:
                    target.write_bytes(f"Fixture for {role} {project_id}".encode())
                specs.append({"path": name, "role": role, "project_id": project_id})
        output = self.root / f"archive-{self.counter}.zip"
        result = checkpoint.create_archive(self.plan, kind, pid, specs, self.staging, output)
        return output, specs, result

    def receipt(self, kind="probe", pid=None, now=None, storage=None):
        archive, _, _ = self.bundle(kind, pid)
        restored = self.root / f"restored-{self.counter}.zip"
        # A local copy simulates retrieval only in this offline fixture.
        shutil.copyfile(archive, restored)
        receipt = checkpoint.verify_restore(archive, restored, storage or self.storage, now or self.now)
        name = f"probes/{self.counter}.json" if kind == "probe" else f"skips/{pid}.json" if kind == "skip" else f"quarantines/{pid}.json" if kind == "quarantine" else f"{pid}.json"
        checkpoint.write_new(self.state / "receipts" / name, receipt)
        return receipt

    def failure(self, pid):
        return {"schema_version": 1, "plan_sha256": checkpoint.validate_plan(self.plan),
                "project_id": pid, "scope": "project", "outcome": "no_output",
                "operation": "Generate fixture artwork", "reason": "Fixture project input rejected before output",
                "recorded_at": self.now.isoformat(), "retry": "future_batch_review"}

    def quarantine_failure(self, pid):
        return {**self.failure(pid), "outcome": "unknown_output", "retry": "blocked_pending_review",
                "request_state": "terminal_failure", "returned_artifacts": "none",
                "failure_class": "project_rejection"}

    def test_quarantine_retains_marker_and_continues_other_projects(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        marker = self.state / f"started/{pid}.json"
        before = marker.read_bytes()
        self.receipt("quarantine", pid)
        self.assertEqual(checkpoint.begin(self.plan, self.state, self.now), "2" * 64)
        self.assertEqual(marker.read_bytes(), before)
        self.receipt("generation", "2" * 64)
        self.assertIsNone(checkpoint.next_project(self.plan, self.state, self.now))
        self.assertFalse((self.state / f"receipts/{pid}.json").exists())
        self.assertFalse((self.state / f"receipts/skips/{pid}.json").exists())
        plan = self.root / "plan.json"
        plan.write_bytes(checkpoint.encode(self.plan))
        with patch.object(checkpoint, "datetime") as dt, patch("builtins.print") as output:
            dt.now.return_value = self.now
            dt.fromisoformat.side_effect = datetime.fromisoformat
            self.assertEqual(checkpoint.main(["next", "--plan", str(plan), "--state", str(self.state)]), 0)
        report = json.loads(output.call_args.args[0])
        self.assertEqual(report["status"], "generation_processed_with_holds")
        self.assertEqual(report["quarantined_project_ids"], [pid])
        self.assertEqual(report["skipped_project_ids"], [])

    def test_quarantine_requires_terminal_project_rejection_and_no_returned_artifact(self):
        pid = "1" * 64
        _, specs, _ = self.bundle("quarantine", pid)
        failure = next(e for e in specs if e["role"] == "failure")
        original = self.quarantine_failure(pid)
        invalid = ({"scope": "shared"}, {"failure_class": "authentication"},
                   {"failure_class": "storage"}, {"failure_class": "permission"},
                   {"failure_class": "quota"}, {"failure_class": "timeout"},
                   {"request_state": "pending"}, {"request_state": "timeout"},
                   {"returned_artifacts": "image"}, {"returned_artifacts": "output_id"},
                   {"outcome": "no_output"}, {"outcome": "output_produced"},
                   {"retry": "immediate"}, {"retry": "future_batch_review"},
                   {"project_id": "2" * 64}, {"plan_sha256": "f" * 64},
                   {"reason": ""}, {"operation": " "}, {"recorded_at": "2026-11-12"},
                   {"schema_version": True}, {"extra": "field"})
        for change in invalid:
            (self.staging / failure["path"]).write_bytes(checkpoint.encode({**original, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                checkpoint.create_archive(self.plan, "quarantine", pid, specs, self.staging, self.root / "bad.zip")
            self.assertFalse((self.root / "bad.zip").exists())
        (self.staging / failure["path"]).write_bytes(checkpoint.encode(original))
        for role in ("reservation", "failure", "evidence"):
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, "Missing required roles"):
                checkpoint.create_archive(self.plan, "quarantine", pid,
                                          [e for e in specs if e["role"] != role],
                                          self.staging, self.root / "bad.zip")
        reservation = next(e for e in specs if e["role"] == "reservation")
        (self.staging / reservation["path"]).write_bytes(checkpoint.encode({"project_id": pid}))
        with self.assertRaisesRegex(ValueError, "reservation differs"):
            checkpoint.create_archive(self.plan, "quarantine", pid, specs, self.staging, self.root / "bad.zip")

    def test_quarantine_requires_restored_receipt_and_cannot_overwrite(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        source, _, _ = self.bundle("quarantine", pid)
        with self.assertRaisesRegex(ValueError, "Recover outstanding"):
            checkpoint.next_project(self.plan, self.state, self.now)
        with self.assertRaisesRegex(ValueError, "separately retrieved"):
            checkpoint.verify_restore(source, source, self.storage, self.now)
        receipt = self.receipt("quarantine", pid)
        path = self.state / f"receipts/quarantines/{pid}.json"
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            checkpoint.write_new(path, receipt)
        self.assertEqual(path.read_bytes(), before)

    def test_quarantine_preserves_probe_identity_freshness_and_order_checks(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        receipt = self.receipt("quarantine", pid)
        path = self.state / f"receipts/quarantines/{pid}.json"
        with self.assertRaisesRegex(ValueError, "stale"):
            checkpoint.next_project(self.plan, self.state, self.now + timedelta(days=2))
        for change, error in (({"plan_sha256": "b" * 64}, "another plan"),
                              ({"kind": "skip"}, "another plan"),
                              ({"verified_at": (self.now + timedelta(seconds=1)).isoformat()}, "Future-dated"),
                              ({"storage": {**self.storage, "destination": "elsewhere"}}, "destination differ")):
            path.write_bytes(checkpoint.encode({**receipt, **change}))
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, error):
                checkpoint.next_project(self.plan, self.state, self.now)
        path.write_bytes(checkpoint.encode(receipt))
        (self.state / f"started/{pid}.json").unlink()
        with self.assertRaisesRegex(ValueError, "Unreserved"):
            checkpoint.next_project(self.plan, self.state, self.now)
        path.unlink()
        checkpoint.write_new(self.state / ("started/" + "2" * 64 + ".json"),
                             {"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": "2" * 64})
        self.receipt("quarantine", "2" * 64)
        with self.assertRaisesRegex(ValueError, "plan order"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_quarantine_conflicts_with_generated_skipped_or_finalized_state(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        self.receipt("quarantine", pid)
        for kind, path in (("generation", self.state / f"receipts/{pid}.json"),
                           ("skip", self.state / f"receipts/skips/{pid}.json")):
            self.receipt(kind, pid)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "cannot also have"):
                checkpoint.next_project(self.plan, self.state, self.now)
            path.unlink()
        (self.state / f"finalization/{pid}").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "finalization output"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_unknown_quarantine_receipt_is_not_ignored(self):
        self.receipt()
        checkpoint.write_new(self.state / "receipts/quarantines/unknown.json", {})
        with self.assertRaisesRegex(ValueError, "Unknown quarantine"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_quarantine_index_coverage_and_conflicts(self):
        index = self.recovery_index()
        pid = "1" * 64
        del index["images"][pid]
        index["quarantines"] = {pid: self.receipt("quarantine", pid)}
        manifest = {"plan": self.plan, "plan_sha256": checkpoint.validate_plan(self.plan)}
        checkpoint.validate_recovery_index(index, manifest)
        with patch.object(self, "recovery_index", return_value=index):
            self.bundle("publication")
        for field, value in (("images", self.recovery_index()["images"][pid]),
                             ("skips", {"kind": "skip"})):
            bad = deepcopy(index)
            bad.setdefault(field, {})[pid] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "cannot also have"):
                checkpoint.validate_recovery_index(bad, manifest)
        bad = deepcopy(index)
        bad["quarantines"][pid]["kind"] = "skip"
        with self.assertRaisesRegex(ValueError, "another plan"):
            checkpoint.validate_recovery_index(bad, manifest)
        index["quarantines"] = {}
        with self.assertRaisesRegex(ValueError, "every planned"):
            checkpoint.validate_recovery_index(index, manifest)

    def test_candidate_verifies_quarantine_and_forbids_held_artwork(self):
        pid = "1" * 64
        self.plan["project_ids"] = [pid]
        candidate, archives = self.root / "candidate", self.root / "archives"
        archives.mkdir()
        for path, key in (("data/specimen_art.json", "artworks"), ("site/specimens/cutouts.json", "cutouts"),
                          ("brand/assets.lock.json", "files")):
            checkpoint.write_new(candidate / path, {key: {}})
        source, _, _ = self.bundle("quarantine", pid)
        restored = archives / (checkpoint.digest(source.read_bytes()) + ".zip")
        shutil.copyfile(source, restored)
        receipt = checkpoint.verify_restore(source, restored, self.storage, self.now)
        index = {"plan_sha256": checkpoint.validate_plan(self.plan), "candidate_revision": "c" * 40,
                 "images": {}, "quarantines": {pid: receipt}}
        result = checkpoint.verify_candidate(self.plan, index, candidate, archives)
        self.assertEqual((result["project_count"], result["quarantined_count"]), (0, 1))
        for path, key, entry in (("data/specimen_art.json", "artworks", pid),
                                 ("site/specimens/cutouts.json", "cutouts", pid),
                                 ("brand/assets.lock.json", "files", f"site/specimens/{pid}.webp")):
            (candidate / path).write_bytes(checkpoint.encode({key: {entry: {}}}))
            with self.assertRaisesRegex(ValueError, "Quarantined project has candidate artwork"):
                checkpoint.verify_candidate(self.plan, index, candidate, archives)
            (candidate / path).write_bytes(checkpoint.encode({key: {}}))
        checkpoint.write_new_bytes(candidate / f"site/specimens/{pid}.webp", b"unexpected output")
        with self.assertRaisesRegex(ValueError, "Quarantined project has candidate artwork"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)
        (candidate / f"site/specimens/{pid}.webp").unlink()
        restored.write_bytes(restored.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "differs from its receipt"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)
        restored.unlink()
        with self.assertRaises(FileNotFoundError):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)

    def test_skip_preserves_marker_and_advances_in_original_plan(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        marker = self.state / f"started/{pid}.json"
        marker_before = marker.read_bytes()
        self.receipt("skip", pid)
        self.assertEqual(checkpoint.begin(self.plan, self.state, self.now), "2" * 64)
        self.assertEqual(marker.read_bytes(), marker_before)
        self.receipt("generation", "2" * 64)
        self.assertIsNone(checkpoint.next_project(self.plan, self.state, self.now))
        self.assertFalse((self.state / f"receipts/{pid}.json").exists())

    def test_skip_does_not_invalidate_previous_generation_receipt(self):
        self.plan["project_ids"].append("3" * 64)
        self.receipt()
        checkpoint.begin(self.plan, self.state, self.now)
        self.receipt("generation", "1" * 64)
        original = (self.state / ("receipts/" + "1" * 64 + ".json")).read_bytes()
        checkpoint.begin(self.plan, self.state, self.now)
        self.receipt("skip", "2" * 64)
        self.assertEqual(checkpoint.begin(self.plan, self.state, self.now), "3" * 64)
        self.assertEqual((self.state / ("receipts/" + "1" * 64 + ".json")).read_bytes(), original)

    def test_raw_failure_or_unverified_archive_cannot_unblock_generation(self):
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        checkpoint.write_new(self.state / f"failures/{pid}.json", self.failure(pid))
        self.bundle("skip", pid)
        with self.assertRaisesRegex(ValueError, "Recover outstanding"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_unreserved_or_conflicting_skip_receipts_fail_closed(self):
        self.receipt()
        self.receipt("skip", "1" * 64)
        with self.assertRaisesRegex(ValueError, "Unreserved"):
            checkpoint.next_project(self.plan, self.state, self.now)
        checkpoint.write_new(self.state / ("started/" + "1" * 64 + ".json"),
                             {"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": "1" * 64})
        self.receipt("generation", "1" * 64)
        with self.assertRaisesRegex(ValueError, "both a generation and skip"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_skip_retains_probe_identity_freshness_and_order_gates(self):
        self.receipt()
        checkpoint.begin(self.plan, self.state, self.now)
        self.receipt("skip", "1" * 64)
        with self.assertRaisesRegex(ValueError, "stale"):
            checkpoint.next_project(self.plan, self.state, self.now + timedelta(days=2))
        path = self.state / ("receipts/skips/" + "1" * 64 + ".json")
        receipt = checkpoint.read_json(path)
        for change, error in (({"plan_sha256": "b" * 64}, "another plan"),
                              ({"verified_at": (self.now + timedelta(seconds=1)).isoformat()}, "Future-dated"),
                              ({"storage": {**self.storage, "destination": "elsewhere"}}, "destination differ")):
            path.write_bytes(checkpoint.encode({**receipt, **change}))
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, error):
                checkpoint.next_project(self.plan, self.state, self.now)
        path.write_bytes(checkpoint.encode(receipt))
        (self.state / ("started/" + "1" * 64 + ".json")).unlink()
        checkpoint.write_new(self.state / ("started/" + "2" * 64 + ".json"),
                             {"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": "2" * 64})
        with self.assertRaisesRegex(ValueError, "Unreserved"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_unknown_skip_receipt_is_not_ignored(self):
        self.receipt()
        checkpoint.write_new(self.state / "receipts/skips/unknown.json", {})
        with self.assertRaisesRegex(ValueError, "Unknown skip"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_skip_requires_known_no_output_project_scope_and_complete_evidence(self):
        pid = "1" * 64
        _, specs, _ = self.bundle("skip", pid)
        record = next(e for e in specs if e["role"] == "failure")
        for change in ({"scope": "shared"}, {"outcome": "uncertain"}, {"outcome": "output_produced"},
                       {"retry": "immediate"}, {"project_id": "2" * 64}, {"plan_sha256": "f" * 64},
                       {"operation": " "}, {"reason": ""}, {"recorded_at": "2026-11-08"},
                       {"schema_version": True}):
            (self.staging / record["path"]).write_bytes(checkpoint.encode({**self.failure(pid), **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                checkpoint.create_archive(self.plan, "skip", pid, specs, self.staging, self.root / "bad-skip.zip")
            self.assertFalse((self.root / "bad-skip.zip").exists())
        (self.staging / record["path"]).write_bytes(checkpoint.encode(self.failure(pid)))
        for changed in ([e for e in specs if e["role"] != "evidence"],
                        [e for e in specs if e["role"] != "reservation"]):
            with self.assertRaisesRegex(ValueError, "Missing required roles"):
                checkpoint.create_archive(self.plan, "skip", pid, changed, self.staging, self.root / "bad-skip.zip")
        reservation = next(e for e in specs if e["role"] == "reservation")
        (self.staging / reservation["path"]).write_bytes(checkpoint.encode({"project_id": pid}))
        with self.assertRaisesRegex(ValueError, "Skip reservation"):
            checkpoint.create_archive(self.plan, "skip", pid, specs, self.staging, self.root / "bad-skip.zip")

    def test_skip_receipt_requires_separate_unchanged_restore_and_no_overwrite(self):
        source, _, _ = self.bundle("skip", "1" * 64)
        with self.assertRaisesRegex(ValueError, "separately retrieved"):
            checkpoint.verify_restore(source, source, self.storage, self.now)
        receipt = self.receipt("skip", "1" * 64)
        path = self.state / ("receipts/skips/" + "1" * 64 + ".json")
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            checkpoint.write_new(path, receipt)
        self.assertEqual(before, path.read_bytes())

    def test_publication_index_accounts_for_skips_without_artwork_receipts(self):
        index = self.recovery_index()
        pid = "1" * 64
        del index["images"][pid]
        index["skips"] = {pid: self.receipt("skip", pid)}
        manifest = {"plan": self.plan, "plan_sha256": checkpoint.validate_plan(self.plan)}
        checkpoint.validate_recovery_index(index, manifest)
        with patch.object(self, "recovery_index", return_value=index):
            self.bundle("publication")
        duplicate = deepcopy(index)
        duplicate["images"][pid] = self.recovery_index()["images"][pid]
        with self.assertRaisesRegex(ValueError, "both artwork and a skip"):
            checkpoint.validate_recovery_index(duplicate, manifest)
        wrong_kind = deepcopy(index)
        wrong_kind["skips"][pid]["kind"] = "generation"
        with self.assertRaisesRegex(ValueError, "another plan or checkpoint"):
            checkpoint.validate_recovery_index(wrong_kind, manifest)
        index["skips"] = {}
        with self.assertRaisesRegex(ValueError, "every planned"):
            checkpoint.validate_recovery_index(index, manifest)

    def test_candidate_verifies_skip_archive_and_rejects_artwork_on_skipped_id(self):
        pid = "1" * 64
        self.plan["project_ids"] = [pid]
        candidate, archives = self.root / "candidate", self.root / "archives"
        archives.mkdir()
        for path, key in (("data/specimen_art.json", "artworks"), ("site/specimens/cutouts.json", "cutouts"),
                          ("brand/assets.lock.json", "files")):
            checkpoint.write_new(candidate / path, {key: {}})
        source, _, _ = self.bundle("skip", pid)
        restored = archives / (checkpoint.digest(source.read_bytes()) + ".zip")
        shutil.copyfile(source, restored)
        receipt = checkpoint.verify_restore(source, restored, self.storage, self.now)
        index = {"plan_sha256": checkpoint.validate_plan(self.plan), "candidate_revision": "c" * 40,
                 "images": {}, "skips": {pid: receipt}}
        result = checkpoint.verify_candidate(self.plan, index, candidate, archives)
        self.assertEqual((result["project_count"], result["skipped_count"]), (0, 1))
        for path, key, entry in (("data/specimen_art.json", "artworks", pid),
                                 ("site/specimens/cutouts.json", "cutouts", pid),
                                 ("brand/assets.lock.json", "files", f"site/specimens/{pid}.webp")):
            (candidate / path).write_bytes(checkpoint.encode({key: {entry: {}}}))
            with self.assertRaisesRegex(ValueError, "Skipped project has candidate artwork"):
                checkpoint.verify_candidate(self.plan, index, candidate, archives)
            (candidate / path).write_bytes(checkpoint.encode({key: {}}))
        checkpoint.write_new_bytes(candidate / f"site/specimens/{pid}.webp", b"unexpected output")
        with self.assertRaisesRegex(ValueError, "Skipped project has candidate artwork"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)
        (candidate / f"site/specimens/{pid}.webp").unlink()
        restored.unlink()
        with self.assertRaises(FileNotFoundError):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)

    def test_cli_reports_skips_separately_from_generation_completion(self):
        self.receipt()
        for pid in self.plan["project_ids"]:
            checkpoint.begin(self.plan, self.state, self.now)
            self.receipt("skip", pid)
        plan = self.root / "plan.json"
        plan.write_bytes(checkpoint.encode(self.plan))
        with patch.object(checkpoint, "datetime") as dt, patch("builtins.print") as output:
            dt.now.return_value = self.now
            dt.fromisoformat.side_effect = datetime.fromisoformat
            self.assertEqual(checkpoint.main(["next", "--plan", str(plan), "--state", str(self.state)]), 0)
        report = json.loads(output.call_args.args[0])
        self.assertEqual(report["status"], "generation_complete_with_skips")
        self.assertEqual(report["skipped_project_ids"], self.plan["project_ids"])

    def test_deterministic_bytes_and_no_overwrite(self):
        archive, specs, result = self.bundle()
        other = self.root / "deterministic.zip"
        again = checkpoint.create_archive(self.plan, "probe", None, list(reversed(specs)), self.staging, other)
        self.assertEqual(result, again)
        self.assertEqual(archive.read_bytes(), other.read_bytes())
        with self.assertRaisesRegex(ValueError, "already exists"):
            checkpoint.create_archive(self.plan, "probe", None, specs, self.staging, archive)

    def test_probe_required_and_reservation_stops_next_generation(self):
        with self.assertRaisesRegex(ValueError, "probe is required"):
            checkpoint.begin(self.plan, self.state, self.now)
        self.assertFalse((self.state / "started").exists())
        self.receipt()
        pid = checkpoint.begin(self.plan, self.state, self.now)
        self.assertEqual(pid, self.plan["project_ids"][0])
        with self.assertRaisesRegex(ValueError, "Recover outstanding"):
            checkpoint.begin(self.plan, self.state, self.now)
        self.receipt("generation", pid)
        pid2 = checkpoint.begin(self.plan, self.state, self.now)
        self.assertEqual(pid2, self.plan["project_ids"][1])
        self.receipt("generation", pid2)
        self.assertIsNone(checkpoint.next_project(self.plan, self.state, self.now))

    def test_stale_probe_and_renewal(self):
        self.receipt(now=self.now - timedelta(days=2))
        with self.assertRaisesRegex(ValueError, "stale"):
            checkpoint.begin(self.plan, self.state, self.now)
        self.receipt()
        self.assertEqual(checkpoint.next_project(self.plan, self.state, self.now), "1" * 64)
        self.receipt(now=self.now + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "future"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_same_local_file_cannot_count_as_restored(self):
        archive, _, _ = self.bundle()
        with self.assertRaisesRegex(ValueError, "separately retrieved"):
            checkpoint.verify_restore(archive, archive, self.storage, self.now)
        linked = self.root / "linked.zip"
        linked.hardlink_to(archive)
        with self.assertRaises(ValueError):
            checkpoint.verify_restore(archive, linked, self.storage, self.now)

    def test_different_archive_and_corrupt_member_rejected(self):
        archive, _, _ = self.bundle()
        other, _, _ = self.bundle()
        with self.assertRaisesRegex(ValueError, "differs"):
            checkpoint.verify_restore(archive, other, self.storage, self.now)
        damaged = self.root / "damaged.zip"
        with zipfile.ZipFile(archive) as src, zipfile.ZipFile(damaged, "w") as dest:
            for info in src.infolist():
                dest.writestr(info, src.read(info) if info.filename == "checkpoint.json" else b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            checkpoint.inspect_archive(damaged)

    def test_missing_role_wrong_project_duplicate_path(self):
        _, specs, _ = self.bundle("generation", "1" * 64)
        for changed in (specs[:-1], specs + [specs[0]],
                        [{**entry, "project_id": "2" * 64} for entry in specs]):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                checkpoint.create_archive(self.plan, "generation", "1" * 64, changed,
                                          self.staging, self.root / "bad.zip")
        self.assertFalse((self.root / "bad.zip").exists())

    def test_path_traversal_symlink_and_empty_file(self):
        for value in ("../outside", "/tmp/outside", "x/../a", "x//a", "./a", "x\\a", "checkpoint.json"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checkpoint.safe_path(value)
        (self.staging / "link").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            checkpoint.artifact_bytes(self.staging, "link/anything")
        (self.staging / "empty").touch()
        with self.assertRaises(ValueError):
            checkpoint.artifact_bytes(self.staging, "empty")

    def recovery_index(self):
        plan_hash = checkpoint.validate_plan(self.plan)
        return {"plan_sha256": plan_hash, "candidate_revision": "c" * 40, "images": {
            pid: {kind: {"schema_version": 1, "plan_sha256": plan_hash, "kind": kind,
                         "project_id": pid, "archive_sha256": "d" * 64,
                         "verified_at": self.now.isoformat(), "storage": self.storage}
                  for kind in ("generation", "finalization")}
            for pid in self.plan["project_ids"]}}

    def test_publication_index_and_small_per_image_finalization(self):
        archive, _, _ = self.bundle("finalization", "1" * 64)
        self.assertEqual(checkpoint.inspect_archive(archive)["kind"], "finalization")
        archive, _, result = self.bundle("publication")
        self.assertEqual(checkpoint.inspect_archive(archive)["kind"], "publication")
        missing = self.recovery_index()
        del missing["images"]["2" * 64]
        with self.assertRaisesRegex(ValueError, "every planned"):
            checkpoint.validate_recovery_index(missing, result["manifest"])
        wrong = self.recovery_index()
        wrong["images"]["1" * 64]["generation"]["plan_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "another plan"):
            checkpoint.validate_recovery_index(wrong, result["manifest"])

    def test_candidate_revision_mismatch_fails_before_archive_creation(self):
        _, specs, _ = self.bundle("publication")
        candidate = next(e for e in specs if e["role"] == "candidate")
        (self.staging / candidate["path"]).write_bytes(checkpoint.encode({"candidate_revision": "e" * 40}))
        output = self.root / "bad-candidate.zip"
        with self.assertRaisesRegex(ValueError, "Candidate revision differs"):
            checkpoint.create_archive(self.plan, "publication", None, specs, self.staging, output)
        self.assertFalse(output.exists())

    def test_candidate_binding_detects_stale_bytes_records_and_checksums(self):
        pid = "1" * 64
        candidate = self.root / "candidate"
        archives = self.root / "archives"
        archives.mkdir()
        paths = {"final": f"site/specimens/{pid}.webp", "cutout": f"site/specimens/cutouts/{pid}.webp"}
        payloads = {"final": b"final image fixture", "cutout": b"cutout image fixture"}
        lock = {paths[role]: {"bytes": len(data), "sha256": checkpoint.digest(data)} for role, data in payloads.items()}
        art_record = {"path": paths["final"][5:], "alt": "Fixture"}
        cutout_record = {"path": paths["cutout"][5:]}
        for role, path in paths.items():
            checkpoint.write_new_bytes(candidate / path, payloads[role])
        checkpoint.write_new(candidate / "data/specimen_art.json", {"artworks": {pid: art_record}})
        checkpoint.write_new(candidate / "site/specimens/cutouts.json", {"cutouts": {pid: cutout_record}})
        checkpoint.write_new(candidate / "brand/assets.lock.json", {"files": lock})
        payloads.update({"artwork_record": checkpoint.encode(art_record), "cutout_record": checkpoint.encode(cutout_record),
                         "checksums": checkpoint.encode(lock)})
        specs = []
        for role, data in payloads.items():
            name = f"finalization/{role}.bin"
            checkpoint.write_new_bytes(self.staging / name, data)
            specs.append({"path": name, "role": role, "project_id": pid})
        final_archive = self.root / "finalization.zip"
        checkpoint.create_archive(self.plan, "finalization", pid, specs, self.staging, final_archive)
        generation, _, _ = self.bundle("generation", pid)
        receipts = {}
        for kind, source in (("generation", generation), ("finalization", final_archive)):
            restored = archives / (checkpoint.digest(source.read_bytes()) + ".zip")
            shutil.copyfile(source, restored)
            receipts[kind] = checkpoint.verify_restore(source, restored, self.storage, self.now)
        skip, _, _ = self.bundle("skip", "2" * 64)
        restored_skip = archives / (checkpoint.digest(skip.read_bytes()) + ".zip")
        shutil.copyfile(skip, restored_skip)
        skip_receipt = checkpoint.verify_restore(skip, restored_skip, self.storage, self.now)
        index = {"plan_sha256": checkpoint.validate_plan(self.plan), "candidate_revision": "c" * 40,
                 "images": {pid: receipts}, "skips": {"2" * 64: skip_receipt}}
        result = checkpoint.verify_candidate(self.plan, index, candidate, archives)
        self.assertEqual((result["project_count"], result["skipped_count"]), (1, 1))
        target = candidate / paths["final"]
        before = target.read_bytes()
        target.write_bytes(b"changed final")
        with self.assertRaisesRegex(ValueError, "image differs"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)
        target.write_bytes(before)
        manifest = candidate / "data/specimen_art.json"
        before = manifest.read_bytes()
        manifest.write_bytes(checkpoint.encode({"artworks": {pid: {**art_record, "alt": "Changed"}}}))
        with self.assertRaisesRegex(ValueError, "records differ"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)
        manifest.write_bytes(before)
        lock[paths["final"]]["sha256"] = "e" * 64
        (candidate / "brand/assets.lock.json").write_bytes(checkpoint.encode({"files": lock}))
        with self.assertRaisesRegex(ValueError, "checksums differ"):
            checkpoint.verify_candidate(self.plan, index, candidate, archives)

    def test_rejects_stale_plan_unreserved_and_wrong_destination_receipts(self):
        self.receipt()
        changed = {**self.plan, "source_revision": "b" * 40}
        with self.assertRaisesRegex(ValueError, "another plan"):
            checkpoint.begin(changed, self.state, self.now)
        self.receipt("generation", "1" * 64)
        with self.assertRaisesRegex(ValueError, "Unreserved"):
            checkpoint.begin(self.plan, self.state, self.now)
        checkpoint.write_new(self.state / "started" / ("1" * 64 + ".json"),
                             {"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": "1" * 64})
        receipt_path = self.state / "receipts" / ("1" * 64 + ".json")
        receipt = checkpoint.read_json(receipt_path)
        receipt["storage"]["destination"] = "other-folder"
        receipt_path.write_bytes(checkpoint.encode(receipt))
        with self.assertRaisesRegex(ValueError, "destination differ"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_size_limit_and_invalid_plan_fail_closed(self):
        for change in ({"project_ids": []}, {"project_ids": ["1" * 64] * 2},
                       {"project_ids": ["short"]}, {"source_revision": "main"}, {"schema_version": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                checkpoint.validate_plan({**self.plan, **change})
        with patch.object(checkpoint, "MAX_BYTES", 4), self.assertRaisesRegex(ValueError, "32 MiB"):
            self.bundle()

    def test_unknown_out_of_order_and_bad_markers(self):
        self.receipt()
        checkpoint.write_new(self.state / "started" / ("2" * 64 + ".json"),
                             {"plan_sha256": checkpoint.validate_plan(self.plan), "project_id": "2" * 64})
        with self.assertRaisesRegex(ValueError, "plan order"):
            checkpoint.next_project(self.plan, self.state, self.now)
        checkpoint.write_new(self.state / "started/unknown.json", {})
        with self.assertRaisesRegex(ValueError, "Unknown"):
            checkpoint.next_project(self.plan, self.state, self.now)

    def test_duplicate_metadata_special_files_and_zip_overhead(self):
        archive, specs, _ = self.bundle()
        for variant in ("duplicate", "fifo"):
            target = self.root / (variant + ".zip")
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(target, "w") as dest:
                for info in src.infolist():
                    content = src.read(info)
                    if info.filename == "checkpoint.json" and variant == "duplicate":
                        content = content.replace(b'"schema_version": 1', b'"schema_version": 0, "schema_version": 1', 1)
                    elif info.filename != "checkpoint.json" and variant == "fifo":
                        info.external_attr = (stat.S_IFIFO | 0o600) << 16
                    dest.writestr(info, content)
            with self.assertRaises(ValueError):
                checkpoint.inspect_archive(target)
        output = self.root / "too-large.zip"
        with patch.object(checkpoint, "MAX_BYTES", archive.stat().st_size - 1), self.assertRaisesRegex(ValueError, "ZIP headers"):
            checkpoint.create_archive(self.plan, "probe", None, specs, self.staging, output)
        self.assertFalse(output.exists())

    def test_successful_marker_and_receipt_fsync_files_and_directory(self):
        with patch("os.fsync", wraps=checkpoint.os.fsync) as sync:
            checkpoint.write_new(self.root / "durable/receipt.json", {"ok": True})
        self.assertEqual(sync.call_count, 3)

    def test_cli_fails_without_generating_or_network(self):
        plan = self.root / "plan.json"
        plan.write_bytes(checkpoint.encode(self.plan))
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")):
            self.assertEqual(checkpoint.main(["begin", "--plan", str(plan), "--state", str(self.state)]), 1)

    def test_duplicate_json_keys_and_receipt_schema(self):
        path = self.root / "duplicate.json"
        path.write_text('{"schema_version": 1, "schema_version": 2}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            checkpoint.read_json(path)
        receipt = self.receipt()
        for change in ({"verified_at": "2026-11-08T00:00:00"}, {"storage": {}}, {"archive_sha256": "bad"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                checkpoint.validate_receipt({**receipt, **change}, checkpoint.validate_plan(self.plan), "probe", None)


if __name__ == "__main__":
    unittest.main()
