"""Offline, immutable artwork checkpoints and a one-unbacked-image gate.

Storage operations belong to the authorized host. A receipt is created only after
comparing a separately restored archive with the original. This module validates
bytes and recorded identity; it cannot authenticate a remote storage service.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

MAX_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 256
PROBE_AGE = timedelta(hours=24)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
ROLES = {
    "probe": {"probe"},
    "generation": {"original", "prompt", "source", "provenance"},
    "finalization": {"final", "cutout", "artwork_record", "cutout_record", "checksums"},
    "publication": {"artwork_manifest", "cutout_manifest", "checksums",
                    "candidate", "recovery_index"},
}


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def read_json(path):
    return decode_json(Path(path).read_text())


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != {
        "schema_version", "batch_id", "source_revision", "project_ids"
    } or type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise ValueError("Invalid plan schema")
    if not isinstance(plan["batch_id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", plan["batch_id"]):
        raise ValueError("Invalid batch ID")
    if not isinstance(plan["source_revision"], str) or not HEX40.fullmatch(plan["source_revision"]):
        raise ValueError("Use the full source revision")
    ids = plan["project_ids"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 40 or any(
        not isinstance(pid, str) or not HEX64.fullmatch(pid) for pid in ids
    ) or len(ids) != len(set(ids)):
        raise ValueError("Plan requires 1–40 unique full project IDs")
    return digest(encode(plan))


def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Invalid artifact path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..") for part in value.split("/")) or str(path) != value:
        raise ValueError("Use a normalized relative artifact path")
    if value == "checkpoint.json":
        raise ValueError("checkpoint.json is reserved")
    return path


def artifact_bytes(root, path):
    path = safe_path(path)
    root = Path(root).resolve(strict=True)
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("Symlinks are not checkpoint artifacts")
    if not target.is_file() or not target.resolve().is_relative_to(root):
        raise ValueError(f"Missing regular artifact: {path}")
    if not 0 < target.stat().st_size <= MAX_BYTES:
        raise ValueError("Artifact must contain 1–32 MiB of bytes")
    return target.read_bytes()


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "plan", "plan_sha256", "kind", "project_id", "artifacts"
    } or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("Invalid checkpoint schema")
    if manifest["plan_sha256"] != validate_plan(manifest["plan"]):
        raise ValueError("Plan hash mismatch")
    kind, pid = manifest["kind"], manifest["project_id"]
    if kind not in ROLES:
        raise ValueError("Unknown checkpoint kind")
    per_project = kind in {"generation", "finalization"}
    if (per_project and pid not in manifest["plan"]["project_ids"]) or (not per_project and pid is not None):
        raise ValueError("Checkpoint project mismatch")
    entries = manifest["artifacts"]
    if not isinstance(entries, list) or not 1 <= len(entries) < MAX_MEMBERS:
        raise ValueError("Invalid artifact count")
    paths, roles, total = set(), set(), 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "role", "project_id", "sha256", "size_bytes"}:
            raise ValueError("Invalid artifact record")
        safe_path(entry["path"])
        if entry["path"] in paths:
            raise ValueError("Duplicate artifact path")
        paths.add(entry["path"])
        if entry["role"] not in ROLES[kind]:
            raise ValueError("Unexpected artifact role")
        roles.add(entry["role"])
        if not isinstance(entry["sha256"], str) or not HEX64.fullmatch(entry["sha256"]):
            raise ValueError("Invalid artifact hash")
        if type(entry["size_bytes"]) is not int or not 0 < entry["size_bytes"] <= MAX_BYTES:
            raise ValueError("Invalid artifact size")
        total += entry["size_bytes"]
        if entry["project_id"] != pid:
            raise ValueError("Artifact project mismatch")
    if roles != ROLES[kind] or total > MAX_BYTES:
        raise ValueError("Missing required roles or checkpoint exceeds 32 MiB")
    if kind == "publication" and any(sum(e["role"] == role for e in entries) != 1 for role in ROLES[kind]):
        raise ValueError("Publication requires one artifact for each role")


def create_archive(plan, kind, project_id, artifacts, root, output):
    plan_hash = validate_plan(plan)
    manifest = {"schema_version": 1, "plan": plan, "plan_sha256": plan_hash,
                "kind": kind, "project_id": project_id, "artifacts": []}
    payloads = {}
    total = 0
    for entry in artifacts:
        if not isinstance(entry, dict) or set(entry) != {"path", "role", "project_id"}:
            raise ValueError("Artifact specification needs path, role and project_id")
        data = artifact_bytes(root, entry["path"])
        total += len(data)
        if total > MAX_BYTES:
            raise ValueError("Checkpoint exceeds 32 MiB")
        payloads[entry["path"]] = data
        manifest["artifacts"].append({**entry, "sha256": digest(data), "size_bytes": len(data)})
    manifest["artifacts"].sort(key=lambda entry: entry["path"])
    validate_manifest(manifest)
    payloads["checkpoint.json"] = encode(manifest)
    if sum(map(len, payloads.values())) > MAX_BYTES:
        raise ValueError("Checkpoint exceeds 32 MiB including its manifest")
    # Account for ZIP headers before creating the immutable destination.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(info, data)
    packed = buffer.getvalue()
    if len(packed) > MAX_BYTES:
        raise ValueError("Checkpoint exceeds 32 MiB including ZIP headers")
    inspect_archive_bytes(packed)
    try:
        write_new_bytes(output, packed)
    except FileExistsError:
        raise ValueError("Checkpoint already exists; inspect it before retrying") from None
    return {"archive_sha256": digest(packed), "manifest": manifest}


def inspect_archive(path):
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError("Checkpoint exceeds 32 MiB")
    return inspect_archive_bytes(path.read_bytes())


def inspect_archive_bytes(data):
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError("Checkpoint exceeds 32 MiB")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS or len({i.filename for i in infos}) != len(infos):
            raise ValueError("Duplicate or excessive ZIP members")
        if any(i.flag_bits & 1 or stat.S_IFMT(i.external_attr >> 16) not in (0, stat.S_IFREG) or i.is_dir() for i in infos):
            raise ValueError("Only unencrypted regular ZIP files are allowed")
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError("Expanded checkpoint exceeds 32 MiB")
        # Metadata and every member are checked without extracting any paths.
        manifest = decode_json(archive.read("checkpoint.json"))
        validate_manifest(manifest)
        if set(archive.namelist()) != {"checkpoint.json", *(a["path"] for a in manifest["artifacts"])}:
            raise ValueError("ZIP inventory mismatch")
        for entry in manifest["artifacts"]:
            data = archive.read(entry["path"])
            if len(data) != entry["size_bytes"] or digest(data) != entry["sha256"]:
                raise ValueError(f"Artifact hash mismatch: {entry['path']}")
        if manifest["kind"] == "publication":
            index = next(e for e in manifest["artifacts"] if e["role"] == "recovery_index")
            recovery = decode_json(archive.read(index["path"]))
            validate_recovery_index(recovery, manifest)
            candidate = next(e for e in manifest["artifacts"] if e["role"] == "candidate")
            candidate_data = decode_json(archive.read(candidate["path"]))
            if not isinstance(candidate_data, dict) or candidate_data.get("candidate_revision") != recovery["candidate_revision"]:
                raise ValueError("Candidate revision differs from recovery index")
        return manifest


def validate_recovery_index(index, manifest):
    if not isinstance(index, dict) or set(index) != {"plan_sha256", "candidate_revision", "images"}:
        raise ValueError("Invalid recovery index")
    if index["plan_sha256"] != manifest["plan_sha256"]:
        raise ValueError("Recovery index plan mismatch")
    if not isinstance(index["candidate_revision"], str) or not HEX40.fullmatch(index["candidate_revision"]):
        raise ValueError("Recovery index requires exact candidate revision")
    if not isinstance(index["images"], dict) or set(index["images"]) != set(manifest["plan"]["project_ids"]):
        raise ValueError("Recovery index must cover every planned project")
    for pid, receipts in index["images"].items():
        if not isinstance(receipts, dict) or set(receipts) != {"generation", "finalization"}:
            raise ValueError("Recovery index requires generation and finalization receipts")
        for kind, receipt in receipts.items():
            validate_receipt(receipt, manifest["plan_sha256"], kind, pid)


def verify_candidate(plan, index, root, archives):
    """Bind current final bytes and curated records to every backed-up archive."""
    plan_hash = validate_plan(plan)
    validate_recovery_index(index, {"plan": plan, "plan_sha256": plan_hash})
    root, archives = Path(root), Path(archives)
    art = read_json(root / "data/specimen_art.json")["artworks"]
    cutouts = read_json(root / "site/specimens/cutouts.json")["cutouts"]
    lock = read_json(root / "brand/assets.lock.json")["files"]
    for pid in plan["project_ids"]:
        for kind in ("generation", "finalization"):
            receipt = index["images"][pid][kind]
            path = archives / (receipt["archive_sha256"] + ".zip")
            manifest = inspect_archive(path)
            if digest(path.read_bytes()) != receipt["archive_sha256"]:
                raise ValueError("Recovery archive differs from its receipt")
            if (manifest["plan_sha256"], manifest["kind"], manifest["project_id"]) != (plan_hash, kind, pid):
                raise ValueError("Recovery archive belongs to another checkpoint")
            if kind == "generation":
                continue
            roles = {}
            with zipfile.ZipFile(path) as archive:
                for entry in manifest["artifacts"]:
                    if entry["role"] in roles:
                        raise ValueError("Finalization requires one artifact for each role")
                    roles[entry["role"]] = archive.read(entry["path"])
            if decode_json(roles["artwork_record"]) != art[pid] or decode_json(roles["cutout_record"]) != cutouts[pid]:
                raise ValueError(f"Candidate records differ from finalization: {pid}")
            expected_paths = {"final": f"site/specimens/{pid}.webp",
                              "cutout": f"site/specimens/cutouts/{pid}.webp"}
            if art[pid]["path"] != expected_paths["final"][5:] or cutouts[pid]["path"] != expected_paths["cutout"][5:]:
                raise ValueError("Candidate asset path differs from project identity")
            archived_checksums = decode_json(roles["checksums"])
            if archived_checksums != {path: lock[path] for path in expected_paths.values()}:
                raise ValueError(f"Candidate checksums differ from finalization: {pid}")
            for role, relative in expected_paths.items():
                data = artifact_bytes(root, relative)
                if data != roles[role] or lock[relative] != {"bytes": len(data), "sha256": digest(data)}:
                    raise ValueError(f"Candidate image differs from finalization: {pid}")
    return {"status": "candidate_files_match", "candidate_revision": index["candidate_revision"],
            "project_count": len(plan["project_ids"])}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamp requires UTC")
    return parsed


def validate_receipt(receipt, plan_hash, kind, project_id):
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version", "plan_sha256", "kind", "project_id", "archive_sha256",
        "verified_at", "storage"
    } or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise ValueError("Invalid restore receipt")
    if (receipt["plan_sha256"], receipt["kind"], receipt["project_id"]) != (plan_hash, kind, project_id):
        raise ValueError("Restore receipt belongs to another plan or checkpoint")
    if not isinstance(receipt["archive_sha256"], str) or not HEX64.fullmatch(receipt["archive_sha256"]):
        raise ValueError("Invalid archive hash")
    timestamp(receipt["verified_at"])
    storage = receipt["storage"]
    if not isinstance(storage, dict) or set(storage) != {"provider", "destination", "object_id", "version"} or any(
        not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in storage.values()
    ):
        raise ValueError("Record provider, destination, object ID and exact version")


def verify_restore(original, restored, storage, now=None):
    original, restored = Path(original), Path(restored)
    if original.samefile(restored):
        raise ValueError("Restore must be a separately retrieved file")
    first = inspect_archive(original)
    second = inspect_archive(restored)
    original_hash = digest(original.read_bytes())
    if original_hash != digest(restored.read_bytes()) or first != second:
        raise ValueError("Restored archive differs from original")
    receipt = {"schema_version": 1, "plan_sha256": first["plan_sha256"],
               "kind": first["kind"], "project_id": first["project_id"],
               "archive_sha256": original_hash,
               "verified_at": (now or datetime.now(timezone.utc)).isoformat(), "storage": storage}
    validate_receipt(receipt, first["plan_sha256"], first["kind"], first["project_id"])
    return receipt


def next_project(plan, state, now=None):
    plan_hash = validate_plan(plan)
    state = Path(state)
    now = now or datetime.now(timezone.utc)
    probes = [read_json(p) for p in (state / "receipts/probes").glob("*.json")]
    if not probes:
        raise ValueError("A restored storage probe is required before generation")
    for probe in probes:
        validate_receipt(probe, plan_hash, "probe", None)
    probe = max(probes, key=lambda item: timestamp(item["verified_at"]))
    age = now - timestamp(probe["verified_at"])
    if not timedelta(0) <= age <= PROBE_AGE:
        raise ValueError("Storage probe is stale or future-dated; round-trip again")
    started = state / "started"
    known = set(plan["project_ids"])
    if started.exists() and any(p.name != p.stem + ".json" or p.stem not in known for p in started.iterdir()):
        raise ValueError("Unknown generation marker")
    next_id = None
    gap = False
    for pid in plan["project_ids"]:
        marker, receipt_path = started / f"{pid}.json", state / f"receipts/{pid}.json"
        if marker.exists():
            if gap or read_json(marker) != {"plan_sha256": plan_hash, "project_id": pid}:
                raise ValueError("Generation markers conflict with plan order")
            if not receipt_path.exists():
                raise ValueError(f"Recover outstanding image before generation: {pid}")
            receipt = read_json(receipt_path)
            validate_receipt(receipt, plan_hash, "generation", pid)
            if timestamp(receipt["verified_at"]) > now:
                raise ValueError("Future-dated image receipt")
            if {k: receipt["storage"][k] for k in ("provider", "destination")} != {
                k: probe["storage"][k] for k in ("provider", "destination")
            }:
                raise ValueError("Image receipt and current storage probe destination differ")
        else:
            if receipt_path.exists():
                raise ValueError("Unreserved image receipt; reconcile the interrupted state")
            gap = True
            next_id = next_id or pid
    return next_id


def write_new_bytes(path, data):
    path = Path(path)
    parents = [path.parent]
    ancestor = path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
        parents.append(ancestor)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    for parent in parents:
        directory = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def write_new(path, value):
    write_new_bytes(path, encode(value))


def begin(plan, state, now=None):
    pid = next_project(plan, state, now)
    if pid is not None:
        write_new(Path(state) / "started" / f"{pid}.json",
                  {"plan_sha256": validate_plan(plan), "project_id": pid})
    return pid


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    for name in ("plan", "artifacts", "root", "output", "kind"):
        pack.add_argument("--" + name, required=True)
    pack.add_argument("--project-id")
    check = commands.add_parser("inspect")
    check.add_argument("archive")
    restore = commands.add_parser("verify-restore")
    for name in ("original", "restored", "storage", "receipt"):
        restore.add_argument("--" + name, required=True)
    candidate = commands.add_parser("verify-candidate")
    for name in ("plan", "index", "root", "archives"):
        candidate.add_argument("--" + name, required=True)
    for name in ("next", "begin"):
        command = commands.add_parser(name)
        command.add_argument("--plan", required=True)
        command.add_argument("--state", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "pack":
            result = create_archive(read_json(args.plan), args.kind, args.project_id,
                                    read_json(args.artifacts), args.root, args.output)
        elif args.command == "inspect":
            result = inspect_archive(args.archive)
        elif args.command == "verify-candidate":
            result = verify_candidate(read_json(args.plan), read_json(args.index), args.root, args.archives)
        elif args.command == "verify-restore":
            result = verify_restore(args.original, args.restored, read_json(args.storage))
            write_new(args.receipt, result)
        else:
            method = begin if args.command == "begin" else next_project
            pid = method(read_json(args.plan), args.state)
            result = {"status": "reserved" if pid and args.command == "begin" else "ready" if pid else "generation_complete",
                      "project_id": pid}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Artwork checkpoint blocked: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
