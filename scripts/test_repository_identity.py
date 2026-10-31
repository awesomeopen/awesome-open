"""Repository endpoint observations produce review candidates, never rename events."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import render_readme
import update_stats as stats


class RepositoryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.stamp = "2026-10-31T08:00:00Z"
        self.api = {
            "id": 1413392799,
            "full_name": "TwilightDuck/OpenQuill",
            "html_url": "https://github.com/TwilightDuck/OpenQuill",
            "archived": False, "created_at": "2026-10-10T16:07:55Z",
            "pushed_at": "2026-10-12T09:59:42Z", "license": None,
            "stargazers_count": 0,
        }
        self.repo = "twilightduck/openwhisper"

    def identity(self, **changes):
        api = {**self.api, **changes}
        return stats.observe_repository_identity(self.repo, api, self.stamp)

    def snapshot(self, identity=None):
        record = {
            "archived": False, "created_at": self.api["created_at"],
            "pushed_at": self.api["pushed_at"], "license": None,
            "stargazers_count": 0, "status": "fresh",
            "last_success_at": self.stamp,
            "last_attempt": {"at": self.stamp, "status": "ok", "http_status": 200, "reason": None},
        }
        if identity is not None:
            record["repository_identity"] = identity
        return {"schema_version": 2, "as_of": "2026-10-31", "repositories": {self.repo: record}}

    def test_first_observation_keeps_request_and_resolved_identity(self):
        identity = self.identity()
        self.assertEqual(identity, {
            "repository_id": 1413392799, "requested_full_name": self.repo,
            "resolved_full_name": "TwilightDuck/OpenQuill",
            "resolved_url": self.api["html_url"], "observed_at": self.stamp,
        })
        snapshot = self.snapshot(identity)
        render_readme.validate_snapshot(snapshot)
        candidate, = stats.repository_change_candidates(snapshot)
        self.assertEqual(candidate["kind"], "repository_path_mismatch")
        self.assertEqual(candidate["project_url"], "https://github.com/" + self.repo)
        self.assertEqual(candidate["observed_at"], self.stamp)
        self.assertNotIn("occurred", candidate)
        self.assertNotIn("software_rename", candidate.values())
        self.assertEqual(list(snapshot["repositories"]), [self.repo])

    def test_case_only_difference_is_not_a_candidate(self):
        identity = self.identity(full_name="TwilightDuck/OpenWhisper",
                                 html_url="https://github.com/TwilightDuck/OpenWhisper")
        self.assertEqual(stats.repository_change_candidates(self.snapshot(identity)), [])

    def test_known_same_id_allows_path_change_without_changing_old_observation(self):
        prior = {"repository_identity": self.identity(full_name="TwilightDuck/OpenWhisper",
                        html_url="https://github.com/TwilightDuck/OpenWhisper")}
        before = deepcopy(prior)
        observed = stats.observe_repository_identity(self.repo, self.api, self.stamp, prior)
        self.assertEqual(observed["repository_id"], prior["repository_identity"]["repository_id"])
        self.assertEqual(prior, before)

    def test_changed_id_is_a_failure_not_a_rename_candidate(self):
        prior = {"repository_identity": self.identity()}
        with self.assertRaisesRegex(RuntimeError, "identity changed.*possible reused endpoint"):
            stats.observe_repository_identity(self.repo, {**self.api, "id": 42}, self.stamp, prior)

    def test_legacy_snapshots_remain_valid_without_identity_baseline(self):
        v2 = self.snapshot()
        render_readme.validate_snapshot(v2)
        self.assertEqual(stats.repository_change_candidates(v2), [])
        v1 = deepcopy(v2)
        v1["schema_version"] = 1
        for key in ("status", "last_success_at", "last_attempt"):
            del v1["repositories"][self.repo][key]
        render_readme.validate_snapshot(v1)
        self.assertEqual(stats.repository_change_candidates(v1), [])

    def test_malformed_api_identity_is_not_invented(self):
        for change in ({"id": None}, {"id": True}, {"id": 0},
                       {"full_name": "../owner/repo"}, {"full_name": "owner/repo\n"},
                       {"html_url": "https://example.com/TwilightDuck/OpenQuill"},
                       {"html_url": self.api["html_url"] + "?query=1"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.identity(**change)

    def test_identity_schema_rejects_drift_and_timestamp_relabeling(self):
        for changes in ({"requested_full_name": "other/project"},
                        {"observed_at": "2026-10-30T08:00:00Z"},
                        {"observed_at": "2026-02-31T08:00:00Z"},
                        {"resolved_url": "https://github.com/other/project"},
                        {"extra": "not permitted"}):
            snapshot = self.snapshot({**self.identity(), **changes})
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                render_readme.validate_snapshot(snapshot)

    def run_collection(self, root, result):
        with patch.object(stats, "ROOT", root), patch.object(stats, "fetch", side_effect=result), \
                patch.dict(stats.os.environ, {"GH_TOKEN": "test"}), \
                redirect_stderr(io.StringIO()) as warnings, redirect_stdout(io.StringIO()):
            stats.main()
        return json.loads((root / "data/github_metrics.json").read_text()), warnings.getvalue()

    def test_collection_persists_candidate_and_404_retains_original_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            source = ("| [Open Quill](https://github.com/TwilightDuck/OpenWhisper) | Dictation. |\n"
                      "| [Other](https://github.com/example/other) | Other. |\n")
            (root / "README.source.md").write_text(source)
            (root / "README.md").write_text("Published output.\n")
            def response(repo, token):
                if repo == self.repo:
                    return self.api
                return {**self.api, "id": 7, "full_name": "example/other",
                        "html_url": "https://github.com/example/other"}
            snapshot, warnings = self.run_collection(root, response)
            original_identity = deepcopy(snapshot["repositories"][self.repo]["repository_identity"])
            self.assertIn("REVIEW: twilightduck/openwhisper resolves to TwilightDuck/OpenQuill", warnings)
            self.assertIn("observation does not date a software rename", warnings)
            def unavailable(repo, token):
                if repo == self.repo:
                    raise stats.RepositoryUnavailable("HTTP 404")
                return response(repo, token)
            stale, warnings = self.run_collection(root, unavailable)
            self.assertEqual(stale["repositories"][self.repo]["repository_identity"], original_identity)
            self.assertEqual(stats.repository_change_candidates(stale)[0]["metrics_status"], "stale")
            self.assertEqual((root / "README.source.md").read_text(), source)
            self.assertEqual((root / "README.md").read_text(), "Published output.\n")

    def test_identity_reuse_aborts_atomic_update_and_preserves_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "README.source.md").write_text(
                "| [Open Quill](https://github.com/TwilightDuck/OpenWhisper) | Dictation. |\n")
            self.run_collection(root, lambda repo, token: self.api)
            output = root / "data/github_metrics.json"
            original = output.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                self.run_collection(root, lambda repo, token: {**self.api, "id": 99})
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

