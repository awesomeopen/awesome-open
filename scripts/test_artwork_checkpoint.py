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
        name = f"probes/{self.counter}.json" if kind == "probe" else f"{pid}.json"
        checkpoint.write_new(self.state / "receipts" / name, receipt)
        return receipt

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
