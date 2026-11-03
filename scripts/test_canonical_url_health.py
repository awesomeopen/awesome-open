#!/usr/bin/env python3
"""Offline fixture tests for the Canonical URL health audit checker.

No network access. Every test replays recorded redirect chains through
an injectable fetch callable, as the contract requires in section 7:
a permanent redirect, a temporary redirect, a 404, a timeout, a
redirect loop, a HEAD timeout followed by a successful GET, a slow host
that answers GET only after 10 seconds, and a GitHub rename with
matching and mismatching repository IDs.

Run:  python3 scripts/test_canonical_url_health.py
      python3 -m unittest discover -s scripts -p 'test_canonical_url_health.py'
"""

import hashlib
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_canonical_urls as checker
from check_canonical_urls import HopResponse, ProbeFailure


def catalog_id(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def make_catalog(urls):
    return {"source_sha": "a" * 40,
            "projects": [{"id": catalog_id(url), "url": url, "name": url}
                         for url in urls]}


class FixtureFetch:
    """Thread-safe replay of scripted (method, url) responses."""

    def __init__(self, script):
        self._script = {key: list(value) for key, value in script.items()}
        self._lock = threading.Lock()
        self.calls = []

    def __call__(self, method, url, timeout):
        with self._lock:
            self.calls.append((method, url, timeout))
            queue = self._script.get(method + " " + url, [])
            if queue:
                scripted = queue.pop(0)
            else:
                scripted = {"status": 200}
        if "error_kind" in scripted:
            raise ProbeFailure(scripted["error_kind"])
        headers = {}
        if scripted.get("location"):
            headers["Location"] = scripted["location"]
        return HopResponse(scripted["status"], headers)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def sweep(catalog, fetch, **kwargs):
    clock = kwargs.pop("clock", FakeClock())
    pacer = checker.HostPacer(sleep=clock.sleep, monotonic=clock.monotonic)
    observations, report, blockers = checker.run_sweep(
        catalog, fetch, pacer=pacer, sleep=clock.sleep, clock=clock.monotonic,
        max_workers=kwargs.pop("max_workers", 2), **kwargs)
    return observations, report, blockers, clock


def api_fetch_for(records):
    def fetch(path):
        if path not in records:
            raise KeyError(path)
        return records[path]
    return fetch


class ProbeTests(unittest.TestCase):
    def test_permanent_redirect(self):
        fetch = FixtureFetch({
            "HEAD https://github.com/example/openexample": [
                {"status": 301, "location": "https://github.com/example/openexample-core"}],
            "HEAD https://github.com/example/openexample-core": [{"status": 200}],
        })
        obs = checker.probe_url("https://github.com/example/openexample", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "redirect-permanent")
        self.assertEqual(obs.http_status, 200)
        self.assertEqual(obs.final_url, "https://github.com/example/openexample-core")
        self.assertEqual(obs.redirect_chain,
                         [{"status": 301, "location": "https://github.com/example/openexample-core"}])

    def test_temporary_redirect(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/open": [
                {"status": 302, "location": "https://example.org/open-new"}],
        })
        obs = checker.probe_url("https://example.org/open", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "redirect-temporary")
        self.assertEqual(obs.final_url, "https://example.org/open-new")

    def test_404_is_client_error_not_withdrawal(self):
        fetch = FixtureFetch({"HEAD https://example.org/gone": [{"status": 404}]})
        obs = checker.probe_url("https://example.org/gone", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "client-error")
        self.assertEqual(obs.http_status, 404)

    def test_405_falls_back_to_get(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/tool": [{"status": 405}],
            "GET https://example.org/tool": [{"status": 200}],
        })
        obs = checker.probe_url("https://example.org/tool", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "reachable")
        self.assertIn("GET", obs.review_note)

    def test_head_timeout_then_get_success_is_reachable(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/slow": [{"error_kind": "timeout"}],
            "GET https://example.org/slow": [{"status": 200}],
        })
        obs = checker.probe_url("https://example.org/slow", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "reachable")
        self.assertIsNone(obs.error_kind)
        self.assertEqual(obs.attempts, 2)

    def test_slow_host_answering_get_only_after_10s(self):
        # OpenSesame pattern: HEAD never answers within 10s, GET answers
        # after ~11s. The record is reachable with the GET fallback noted,
        # never a transport error and never a persistent-failure candidate.
        fetch = FixtureFetch({
            "HEAD https://osdoc.cogsci.nl": [{"error_kind": "timeout"}],
            "GET https://osdoc.cogsci.nl": [{"status": 200}],
        })
        obs = checker.probe_url("https://osdoc.cogsci.nl", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "reachable")
        self.assertEqual(obs.error_kind, None)
        self.assertIn("HEAD timeout", obs.review_note)

    def test_timeout_after_get_retry_is_transport_error(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/down": [{"error_kind": "timeout"}],
            "GET https://example.org/down": [{"error_kind": "timeout"},
                                             {"error_kind": "timeout"}],
        })
        sleeps = []
        obs = checker.probe_url("https://example.org/down", fetch,
                                checker.HostPacer(sleep=lambda s: None),
                                sleep=sleeps.append)
        self.assertEqual(obs.status, "transport-error")
        self.assertEqual(obs.error_kind, "timeout")
        self.assertIsNone(obs.http_status)
        self.assertIsNone(obs.final_url)
        self.assertEqual(obs.attempts, 3)
        self.assertEqual(sleeps, [5])

    def test_redirect_loop_is_blocked(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/a": [{"status": 302, "location": "https://example.org/b"}],
            "HEAD https://example.org/b": [{"status": 302, "location": "https://example.org/a"}],
        })
        obs = checker.probe_url("https://example.org/a", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(obs.error_kind, "redirect-loop")

    def test_too_many_hops(self):
        script = {}
        for index in range(7):
            script["HEAD https://example.org/hop%d" % index] = [
                {"status": 301, "location": "https://example.org/hop%d" % (index + 1)}]
        fetch = FixtureFetch(script)
        obs = checker.probe_url("https://example.org/hop0", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(obs.error_kind, "too-many-hops")
        self.assertEqual(len(obs.redirect_chain), 5)

    def test_429_records_retry_after_and_stops(self):
        fetch = FixtureFetch({})
        # Build the response with a Retry-After header through a custom
        # fetch, since the scripted format carries no other headers.
        def fetch429(method, url, timeout):
            return HopResponse(429, {"Retry-After": "60"})
        obs = checker.probe_url("https://example.org/limited", fetch429,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(obs.error_kind, "rate-limited")
        self.assertIn("Retry-After: 60", obs.review_note)

    def test_credential_redirect_is_not_followed(self):
        fetch = FixtureFetch({
            "HEAD https://example.org/start": [
                {"status": 301, "location": "https://user:secret@example.org/target"}],
        })
        obs = checker.probe_url("https://example.org/start", fetch,
                                checker.HostPacer(sleep=lambda s: None))
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(len(obs.redirect_chain), 1)
        self.assertEqual(fetch.calls[0][1], "https://example.org/start")


class IdentityTests(unittest.TestCase):
    def test_github_rename_matching_ids(self):
        catalog = make_catalog(["https://github.com/twilightduck/openwhisper"])
        fetch = FixtureFetch({
            "HEAD https://github.com/twilightduck/openwhisper": [
                {"status": 301, "location": "https://github.com/TwilightDuck/OpenQuill"}],
        })
        api = api_fetch_for({
            "repos/twilightduck/openwhisper": {"id": 1413392799},
            "repos/twilightduck/openquill": {"id": 1413392799},
        })
        observations, _, _, _ = sweep(catalog, fetch, api_fetch=api,
                                      checked_at="2026-10-31")
        obs = observations[0]
        self.assertEqual(obs.status, "redirect-permanent")
        self.assertTrue(obs.github_identity_verified)
        self.assertEqual(obs.github_repo_id_before, 1413392799)
        self.assertEqual(obs.github_repo_id_after, 1413392799)

    def test_github_rename_mismatching_ids(self):
        catalog = make_catalog(["https://github.com/example/old"])
        fetch = FixtureFetch({
            "HEAD https://github.com/example/old": [
                {"status": 301, "location": "https://github.com/other/new"}],
        })
        api = api_fetch_for({
            "repos/example/old": {"id": 111},
            "repos/other/new": {"id": 222},
        })
        observations, _, _, _ = sweep(catalog, fetch, api_fetch=api,
                                      checked_at="2026-10-31")
        obs = observations[0]
        self.assertFalse(obs.github_identity_verified)
        self.assertEqual(obs.github_repo_id_before, 111)
        self.assertEqual(obs.github_repo_id_after, 222)
        self.assertIn("IDs differ", obs.review_note)

    def test_no_token_leaves_github_unverified(self):
        catalog = make_catalog(["https://github.com/example/old"])
        fetch = FixtureFetch({
            "HEAD https://github.com/example/old": [
                {"status": 301, "location": "https://github.com/example/new"}],
        })
        observations, _, _, _ = sweep(catalog, fetch, api_fetch=None,
                                      checked_at="2026-10-31")
        obs = observations[0]
        self.assertFalse(obs.github_identity_verified)
        self.assertIsNone(obs.github_repo_id_before)


class EvidenceTests(unittest.TestCase):
    def test_digest_is_sorted_and_reproducible(self):
        catalog = make_catalog(["https://example.org/b", "https://example.org/a"])
        fetch = FixtureFetch({})
        observations, report, _, _ = sweep(catalog, fetch, checked_at="2026-10-31")
        digest = checker.compute_digest(observations)
        self.assertEqual(digest, report["digest"])
        self.assertEqual(digest, checker.compute_digest(list(reversed(observations))))

    def test_changed_only_merge_and_pruning(self):
        url = "https://example.org/flaky"
        catalog = make_catalog([url])
        by_id = {p["id"]: p for p in catalog["projects"]}

        def run(script, previous):
            fetch = FixtureFetch(script)
            observations, _, _, _ = sweep(catalog, fetch, checked_at="2026-10-31",
                                          previous_records=previous)
            records, changed, pruned = checker.merge_evidence(
                previous, observations, "2026-10-31", by_id, catalog["source_sha"])
            return records, changed, pruned

        records, changed, _ = run({"HEAD " + url: [{"status": 404}]}, {})
        self.assertEqual(changed, [catalog_id(url)])
        self.assertEqual(records[catalog_id(url)]["status"], "client-error")
        # First clean sweep: record kept, updated to clean.
        records, changed, pruned = run({}, records)
        self.assertEqual(records[catalog_id(url)]["status"], "reachable")
        self.assertEqual(pruned, [])
        # Second clean sweep: record pruned, listed as changed.
        records, changed, pruned = run({}, records)
        self.assertEqual(records, {})
        self.assertEqual(pruned, [catalog_id(url)])

    def test_validation_rejects_unknown_status_and_stale_key(self):
        catalog = make_catalog(["https://example.org/a"])
        by_id = {p["id"]: p for p in catalog["projects"]}
        good = {"schema_version": 1, "last_sweep": None, "records": {}}
        checker.validate_evidence(good, by_id)
        bad_status = {"schema_version": 1, "last_sweep": None, "records": {
            catalog_id("https://example.org/a"): {
                "project_url": "https://example.org/a", "checked_at": "2026-10-31",
                "status": "dead", "redirect_chain": [], "error_kind": None}}}
        with self.assertRaises(checker.EvidenceError):
            checker.validate_evidence(bad_status, by_id)
        stale = {"schema_version": 1, "last_sweep": None, "records": {
            "0" * 64: {"project_url": "https://example.org/gone",
                       "checked_at": "2026-10-31", "status": "reachable",
                       "redirect_chain": [], "error_kind": None}}}
        with self.assertRaises(checker.EvidenceError):
            checker.validate_evidence(stale, by_id)

    def test_triage_class_a_trailing_slash(self):
        self.assertEqual(
            checker.triage_class("https://www.openldap.org/software",
                                 "https://www.openldap.org/software/",
                                 [{"status": 301, "location": "https://www.openldap.org/software/"}]),
            "A")
        self.assertEqual(
            checker.triage_class("https://github.com/example/old",
                                 "https://github.com/example/new",
                                 [{"status": 301, "location": "https://github.com/example/new"}]),
            "B-or-C")

    def test_per_host_pacing(self):
        catalog = make_catalog(["https://github.com/example/a",
                                "https://github.com/example/b"])
        clock = FakeClock()
        fetch = FixtureFetch({})
        sweep(catalog, fetch, clock=clock, max_workers=1, checked_at="2026-10-31")
        # The second github.com request waits the full 1.0s interval.
        self.assertTrue(any(s >= 1.0 for s in clock.sleeps))


if __name__ == "__main__":
    unittest.main()
