"""Reviewed current-name equivalence and review-only candidate regression tests."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import build_observatory as obs
import name_matching as matching


def projects():
    return [
        dict(id="a", name="Open Whisper", url="https://example.org/whisper"),
        dict(id="b", name="OpenWhispr", url="https://example.org/whispr"),
    ]


def document():
    return dict(schema_version=1, groups=[dict(
        id="whisper-spelling", reason="spelling", basis="Reviewed omitted-vowel spelling.",
        checked_at="2026-10-31", reviewed_by="Junge (AI)",
        members=[dict(project_url=p["url"], name=p["name"], source_url=p["url"])
                 for p in projects()])])


class ReviewedNames(unittest.TestCase):
    def load(self, data, rows=None):
        return matching.load_reviewed(dict(projects=rows or projects()), data)

    def test_reviewed_spelling_annotation_is_explicit_and_nonmutating(self):
        rows = projects()
        original = deepcopy(rows)
        self.assertEqual(obs.shared_names(rows)["tool_count"], 0)
        reviewed = self.load(document())
        annotated = matching.annotate(rows, reviewed)
        self.assertEqual(rows, original)
        group = obs.shared_names(annotated)["variants"][0]
        self.assertEqual(group["tags"], ["Spacing", "Spelling"])
        self.assertEqual(obs.shared_names(annotated), obs.shared_names(list(reversed(annotated))))
        self.assertEqual(matching.candidates(rows, reviewed), [])

    def test_current_name_drift_is_rejected_not_applied_to_former_name(self):
        rows = projects()
        rows[0].update(name="Open Quill", aliases=["Open Whisper"])
        with self.assertRaises(ValueError):
            self.load(document(), rows)
        self.assertEqual(obs.shared_names(rows)["tool_count"], 0)
        self.assertEqual(matching.candidates(rows), [])

    def test_schema_rejects_unknown_identity_bad_date_and_overlapping_groups(self):
        mutations = [
            lambda d: d.update(schema_version=True),
            lambda d: d["groups"][0].update(reason="phonetic"),
            lambda d: d["groups"][0].update(reason=[]),
            lambda d: d["groups"][0].update(checked_at="20261031"),
            lambda d: d["groups"][0].update(basis=""),
            lambda d: d["groups"][0]["members"][0].update(project_url="https://example.org/missing"),
            lambda d: d["groups"][0]["members"][0].update(source_url="http://example.org/whisper"),
            lambda d: d["groups"][0]["members"][0].update(source_url="https://example.org:bad/whisper"),
            lambda d: d["groups"][0]["members"][0].update(source_url="https://example.org/white space"),
            lambda d: d["groups"].append(dict(deepcopy(d["groups"][0]), id="overlap")),
            lambda d: d["groups"][0].update(reason="plural"),
        ]
        for mutate in mutations:
            data = document()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)

    def test_builtin_registry_applies_only_to_present_current_members(self):
        self.assertEqual(matching.load_reviewed(dict(projects=projects())), {})
        rows = [dict(id=str(i), url=member["project_url"], name=member["name"])
                for i, member in enumerate(matching.REVIEWED_EQUIVALENCES["groups"][0]["members"])]
        reviewed = matching.load_reviewed(dict(projects=rows))
        self.assertEqual(set(reviewed), {"opentask", "opentasks"})
        rows[0]["name"] = "Open Other"
        with self.assertRaises(ValueError):
            matching.load_reviewed(dict(projects=rows))

    def test_plural_is_reviewed_not_automatic(self):
        rows = [dict(p, name=n) for p, n in zip(projects(), ["OpenTask", "OpenTasks"])]
        data = document()
        data["groups"][0]["reason"] = "plural"
        for member, row in zip(data["groups"][0]["members"], rows):
            member["name"] = row["name"]
        self.assertEqual(obs.shared_names(rows)["tool_count"], 0)
        annotated = matching.annotate(rows, self.load(data, rows))
        self.assertEqual(obs.shared_names(annotated)["variants"][0]["tags"], ["Plural"])

    def test_review_only_candidates_are_bounded_deterministic_and_not_groups(self):
        rows = projects()
        found = matching.candidates(rows + [rows[0]])
        self.assertEqual(len(found), 1)
        self.assertEqual(found, matching.candidates(list(reversed(rows))))
        self.assertEqual(found[0]["status"], "needs_review")
        self.assertEqual(found[0]["reason"], "one-letter-edit")
        self.assertEqual(obs.shared_names(rows)["tool_count"], 0)
        for names in [("OpenCat", "OpenCats"), ("OpenTool", "OpenTale"),
                      ("OpenTask", "OpenTask."), ("Open Voice", "OpenVoice"),
                      ("Whisper", "Whispr")]:
            pair = [dict(p, name=n) for p, n in zip(rows, names)]
            with self.subTest(names=names):
                self.assertEqual(matching.candidates(pair), [])
        for left, right, expected in [
            ("whisper", "whispr", True), ("tools", "tool", True),
            ("tall", "tell", True), ("tool", "tool", False),
            ("tool", "tale", False), ("ab", "ba", False),
        ]:
            self.assertEqual(matching.one_edit(left, right), expected)

    def test_cli_keeps_review_candidates_separate_and_does_not_write_inputs(self):
        snapshot = {
            "schema_version": 2, "as_of": "2026-10-31",
            "repositories": {"twilightduck/openwhisper": {
                "archived": False, "created_at": "2026-01-01T00:00:00Z",
                "pushed_at": None, "license": None, "stargazers_count": 0,
                "status": "fresh", "last_success_at": "2026-10-31T08:00:00Z",
                "last_attempt": {"at": "2026-10-31T08:00:00Z", "status": "ok",
                                 "http_status": 200, "reason": None},
                "repository_identity": {
                    "repository_id": 1413392799,
                    "requested_full_name": "twilightduck/openwhisper",
                    "resolved_full_name": "TwilightDuck/OpenQuill",
                    "resolved_url": "https://github.com/TwilightDuck/OpenQuill",
                    "observed_at": "2026-10-31T08:00:00Z",
                },
            }},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = {
                "catalog.json": dict(source_sha="a" * 40, projects=projects()),
                "metrics.json": snapshot,
            }
            for name, data in inputs.items():
                (root / name).write_text(json.dumps(data), encoding="utf-8")
            before = {name: (root / name).read_bytes() for name in inputs}
            command = [
                sys.executable, str(Path(__file__).with_name("name_matching.py")),
                "--catalog", str(root / "catalog.json"),
                "--metrics", str(root / "metrics.json"),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = json.loads(result.stdout)
            self.assertEqual(len(output["candidates"]), 1)
            self.assertEqual(output["candidates"][0]["status"], "needs_review")
            self.assertEqual(output["repository_changes"], [{
                "kind": "repository_path_mismatch",
                "project_url": "https://github.com/twilightduck/openwhisper",
                "repository_id": 1413392799,
                "requested_full_name": "twilightduck/openwhisper",
                "resolved_full_name": "TwilightDuck/OpenQuill",
                "resolved_url": "https://github.com/TwilightDuck/OpenQuill",
                "observed_at": "2026-10-31T08:00:00Z", "metrics_status": "fresh",
            }])
            self.assertEqual({name: (root / name).read_bytes() for name in inputs}, before)
            (root / "metrics.json").write_text('{"schema_version":99}', encoding="utf-8")
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, "")


    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_python_javascript_current_name_grouping_parity(self):
        rows = matching.annotate(projects(), self.load(document()))
        script = "const o=require('./site/observatory.js');let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(o.sharedNames(JSON.parse(s)))));"
        result = subprocess.run(["node", "-e", script], input=json.dumps(rows),
                                text=True, capture_output=True, check=True,
                                cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(json.loads(result.stdout), obs.shared_names(rows))


if __name__ == "__main__":
    unittest.main()

