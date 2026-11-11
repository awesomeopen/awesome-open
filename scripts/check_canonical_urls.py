#!/usr/bin/env python3
"""Probe every canonical URL in a catalog and record only observed HTTP facts.

Implements Phase 1 (offline implementation) of the Canonical URL health
audit contract in ``automation/canonical-url-health.md``. Python standard
library only. No network access in tests: the probe takes an injectable
``fetch`` callable, and the test suite replays recorded redirect chains
through it.

Owner decisions are recorded in ``automation/canonical-url-health.md``.

The checker never edits the catalog, a name, a URL, an alias, or a history
record. It writes the ``--output`` evidence file (changed-only records plus
a sweep summary). A dry run writes that file only when ``--write-output``
is given; without ``--fixtures`` it prints probe order and writes nothing.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import sys
import threading
import time
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

USER_AGENT = "awesome-open-canonical-url-health/1.0 (+https://github.com/awesomeopen/awesome-open)"
CHECKED_BY = "canonical-url-health/1"
SCHEMA_VERSION = 1

MAX_HOPS = 5
HEAD_TIMEOUT_SECONDS = 10
GET_TIMEOUT_SECONDS = 30
MAX_BODY_BYTES = 65536
MAX_REQUESTS_PER_RUN = 1200
MAX_MINUTES_PER_RUN = 45
MAX_WORKERS = 8
INTERVAL_SECONDS_GITHUB = 1.0
INTERVAL_SECONDS_OTHER_HOSTS = 0.5
RETRY_PAUSE_SECONDS = 5

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
PERMANENT_STATUSES = {301, 308}
METHOD_REJECTION_STATUSES = {405, 501}
TAXONOMY = {
    "reachable", "redirect-permanent", "redirect-temporary", "client-error",
    "server-error", "blocked", "transport-error", "unknown",
}
ERROR_KINDS = {
    "timeout", "dns", "tls", "connection", "rate-limited", "redirect-loop",
    "too-many-hops", None,
}

# http_status and final_url are the final response after the redirect chain,
# so a permanent redirect whose target answers 200 records http_status 200.


class EvidenceError(ValueError):
    """Catalog or evidence validation failed."""


class ProbeFailure(Exception):
    """A transport failure. ``kind`` is one of the contract error kinds."""

    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


@dataclass(frozen=True)
class HopResponse:
    status: int
    headers: dict = field(default_factory=dict)

    def header(self, name):
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return None


@dataclass
class Observation:
    catalog_id: str
    project_url: str
    canonical_url_checked: str
    checked_at: str
    status: str
    http_status: int | None
    final_url: str | None
    redirect_chain: list
    error_kind: str | None
    attempts: int
    review_note: str
    github_repo_id_before: int | None = None
    github_repo_id_after: int | None = None
    github_identity_verified: bool | None = None


class _NoRedirect(HTTPRedirectHandler):
    # Each hop must be observed and recorded separately. Never follow a
    # redirect automatically, and never leak a credential on a redirect.
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _classify_urllib_error(error):
    reason = getattr(error, "reason", error)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(reason, socket.gaierror):
        return "dns"
    if isinstance(reason, ssl.SSLError):
        return "tls"
    if isinstance(reason, (ConnectionError, OSError)):
        return "connection"
    return "connection"


def live_fetch(method, url, timeout, opener=None):
    """One HTTP request with no redirect following. Raises ProbeFailure."""
    request = Request(url, method=method, headers={"User-Agent": USER_AGENT})
    opener = opener or build_opener(_NoRedirect).open
    try:
        response = opener(request, timeout=timeout)
    except HTTPError as error:
        # urllib raises for 4xx/5xx; those are responses, not transport
        # failures. Read the capped body only for GET, then close.
        if method == "GET":
            error.read(MAX_BODY_BYTES + 1)
        return HopResponse(error.code, dict(error.headers or {}))
    except URLError as error:
        raise ProbeFailure(_classify_urllib_error(error)) from error
    except (TimeoutError, socket.timeout) as error:
        raise ProbeFailure("timeout") from error
    except OSError as error:
        raise ProbeFailure(_classify_urllib_error(error)) from error
    try:
        if method == "GET":
            response.read(MAX_BODY_BYTES + 1)
        return HopResponse(response.status, dict(response.headers or {}))
    finally:
        response.close()


class HostPacer:
    """Serialise one host and enforce the minimum interval between requests.

    The lock is held across the whole fetch, so at most one request per
    host is ever in flight, and the next request to the same host waits
    the full interval after the previous one finished.
    """

    def __init__(self, sleep=time.sleep, monotonic=time.monotonic):
        self._sleep = sleep
        self._monotonic = monotonic
        self._state = {}
        self._state_lock = threading.Lock()

    @contextmanager
    def pacing(self, host):
        host = (host or "").lower()
        interval = INTERVAL_SECONDS_GITHUB if host == "github.com" else INTERVAL_SECONDS_OTHER_HOSTS
        with self._state_lock:
            lock = self._state.setdefault(host, (threading.Lock(), 0.0))[0]
        with lock:
            # Re-read inside the lock: a worker that queued on the lock
            # must see the value set by the previous holder, not the
            # stale value captured before it blocked.
            with self._state_lock:
                next_allowed = self._state[host][1]
            now = self._monotonic()
            if now < next_allowed:
                self._sleep(next_allowed - now)
            try:
                yield
            finally:
                with self._state_lock:
                    self._state[host] = (lock, self._monotonic() + interval)


def _host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _has_credentials(url):
    try:
        parsed = urlsplit(url)
    except ValueError:
        return True
    return parsed.username is not None or parsed.password is not None or "%" in parsed.netloc


def _is_github_repo_url(url):
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return parsed.hostname == "github.com" and len(parts) >= 2


def _repo_path(url):
    parsed = urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    return "/".join(parts[:2]).lower()


def _request_with_pacer(fetch, pacer, method, url, timeout):
    with pacer.pacing(_host_of(url)):
        return fetch(method, url, timeout)


def _probe_hop(url, fetch, pacer, sleep):
    """Probe one hop. Returns (response, attempts, methods, note).

    HEAD first; on a method rejection or a HEAD transport failure, one
    GET fallback with the longer timeout; on a GET transport failure, one
    retry as GET after a pause. A HEAD timeout alone is never an error.
    """
    attempts = 0
    methods = []
    try:
        attempts += 1
        methods.append("HEAD")
        response = _request_with_pacer(fetch, pacer, "HEAD", url, HEAD_TIMEOUT_SECONDS)
        if response.status not in METHOD_REJECTION_STATUSES:
            return response, attempts, methods, None
        note = "HEAD rejected with %d; GET fallback used." % response.status
    except ProbeFailure as error:
        note = "HEAD %s; GET fallback used." % error.kind
    # GET fallback, then one GET retry on a transport failure.
    for attempt in (1, 2):
        if attempt == 2:
            sleep(RETRY_PAUSE_SECONDS)
        attempts += 1
        methods.append("GET")
        try:
            return _request_with_pacer(fetch, pacer, "GET", url, GET_TIMEOUT_SECONDS), attempts, methods, note
        except ProbeFailure as error:
            if attempt == 2:
                error.attempts = attempts
                error.methods = methods
                error.note = note
                raise
            note = (note + " GET %s; retried once as GET." % error.kind) if note else "GET %s; retried once as GET." % error.kind


def probe_url(url, fetch, pacer, sleep=time.sleep):
    """Probe one canonical URL. Returns an Observation; never raises for
    an HTTP result. Transport failures become transport-error records."""
    chain = []
    seen = {url}
    current = url
    attempts = 0
    methods_seen = []
    notes = []
    while True:
        try:
            response, hop_attempts, methods, note = _probe_hop(current, fetch, pacer, sleep)
        except ProbeFailure as error:
            hop_attempts = getattr(error, "attempts", 1)
            hop_methods = getattr(error, "methods", [])
            if getattr(error, "note", None):
                notes.append(error.note)
            methods_seen.extend(m for m in hop_methods if m not in methods_seen)
            note_parts = list(notes)
            if len(methods_seen) > 1 or "GET" in methods_seen:
                note_parts.append("Methods: %s." % ", ".join(methods_seen))
            note_parts.append("Transport error recorded only after the GET fallback and retry.")
            return Observation(
                catalog_id="", project_url=url, canonical_url_checked=url,
                checked_at="", status="transport-error", http_status=None,
                final_url=None, redirect_chain=chain, error_kind=error.kind,
                attempts=attempts + hop_attempts,
                review_note=" ".join(p for p in note_parts if p),
            )
        attempts += hop_attempts
        methods_seen.extend(m for m in methods if m not in methods_seen)
        if note:
            notes.append(note)
        status = response.status
        location = response.header("Location")
        if status == 429:
            retry_after = response.header("Retry-After")
            note = "429 rate limit; stopped for this run."
            if retry_after:
                note += " Retry-After: %s." % retry_after
            return _observation(url, chain, status, current, "blocked",
                                "rate-limited", attempts, methods_seen, notes + [note])
        if status in REDIRECT_STATUSES and location:
            if len(chain) >= MAX_HOPS:
                return _observation(url, chain, status, current, "blocked",
                                    "too-many-hops", attempts, methods_seen,
                                    notes + ["Redirect chain truncated at %d hops." % MAX_HOPS])
            target = urljoin(current, location)
            if _has_credentials(target):
                chain.append({"status": status, "location": location})
                return _observation(url, chain, status, current, "blocked",
                                    None, attempts, methods_seen,
                                    notes + ["Redirect target carries credentials; not followed."])
            chain.append({"status": status, "location": location})
            if target in seen:
                return _observation(url, chain, status, target, "blocked",
                                    "redirect-loop", attempts, methods_seen,
                                    notes + ["Redirect loop; stopped."])
            seen.add(target)
            current = target
            continue
        # First non-redirect response ends the chain.
        if chain and any(hop["status"] in PERMANENT_STATUSES for hop in chain):
            observed = "redirect-permanent"
        elif chain:
            observed = "redirect-temporary"
        elif 200 <= status < 300:
            observed = "reachable"
        elif status in (403,):
            observed = "blocked"
        elif 400 <= status < 500:
            observed = "client-error"
        elif 500 <= status < 600:
            observed = "server-error"
        else:
            observed = "unknown"
        return _observation(url, chain, status, current, observed, None,
                            attempts, methods_seen, notes)


def _observation(url, chain, http_status, final_url, status, error_kind,
                attempts, methods, notes):
    parts = list(notes)
    if len(methods) > 1 or "GET" in methods:
        parts.append("Methods: %s." % ", ".join(methods))
    if status == "transport-error":
        parts.append("Transport error recorded only after the GET fallback and retry.")
    return Observation(
        catalog_id="", project_url=url, canonical_url_checked=url,
        checked_at="", status=status, http_status=http_status,
        final_url=final_url, redirect_chain=list(chain), error_kind=error_kind,
        attempts=attempts, review_note=" ".join(p for p in parts if p),
    )


def triage_class(canonical_url, final_url, chain):
    """Classify a permanent redirect for the run report only.

    Class A: the final URL differs only by a trailing slash, a scheme, or
    another difference the builder's canonical_url() absorbs. Classes B
    (move) and C (rename) cannot be told apart from the chain alone; they
    need an official source, so this returns ``"B-or-C"`` and never
    invents a name change. Triage never changes a catalog entry.
    """
    if not chain or final_url is None:
        return None

    def normalised(value):
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        path = parsed.path
        if host == "github.com":
            segments = path.split("/")
            segments[1:3] = [part.lower() for part in segments[1:3]]
            path = "/".join(segments)
            if re.fullmatch(r"/[\w.-]+/[\w.-]+/", path):
                path = path[:-1]
        if path == "/":
            path = ""
        return (parsed.scheme, host, path)

    old, new = normalised(canonical_url), normalised(final_url)
    if old == new or (old[1:] == new[1:]):
        return "A"
    if old[1] == new[1] and old[2].rstrip("/") == new[2].rstrip("/"):
        return "A"
    return "B-or-C"


def verify_github_identity(old_url, new_url, api_fetch):
    """Compare repository IDs for the old and new GitHub paths.

    Returns (id_before, id_after, verified, reason). ``api_fetch`` takes
    a ``repos/<owner>/<repo>`` path and returns its API record dict.
    The token, if any, lives only inside ``api_fetch`` and is never
    returned, logged, or written here.
    """
    if not _is_github_repo_url(old_url) or not _is_github_repo_url(new_url):
        return None, None, False, "Final URL is not a GitHub repository path."
    try:
        before = api_fetch("repos/" + _repo_path(old_url))
        after = api_fetch("repos/" + _repo_path(new_url))
    except Exception as error:  # API unavailable: record, do not invent.
        return None, None, False, "Repository API lookup failed: %s." % type(error).__name__
    id_before = before.get("id") if isinstance(before, dict) else None
    id_after = after.get("id") if isinstance(after, dict) else None
    if type(id_before) is not int or type(id_after) is not int:
        return None, None, False, "Repository API record has no integer ID."
    if id_before == id_after:
        return id_before, id_after, True, ""
    return id_before, id_after, False, "Repository IDs differ; no identity established."


def live_api_fetch(token, timeout=HEAD_TIMEOUT_SECONDS):
    """Build an api.github.com fetcher. The token goes only to api.github.com."""

    def fetch(path):
        request = Request(
            "https://api.github.com/" + path,
            headers={"User-Agent": USER_AGENT,
                     "Accept": "application/vnd.github+json",
                     "Authorization": "Bearer " + token},
        )
        with build_opener(_NoRedirect).open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    return fetch


def load_catalog(path):
    """Load a catalog JSON file as built by scripts/build_catalog.py."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError("Cannot read catalog %s: %s" % (path, error)) from error
    if not isinstance(document, dict) or not isinstance(document.get("projects"), list):
        raise EvidenceError("Catalog must be an object with a projects list")
    projects = []
    seen = set()
    for project in document["projects"]:
        if not isinstance(project, dict):
            raise EvidenceError("Catalog project must be an object")
        catalog_id = project.get("id")
        url = project.get("url")
        if (not isinstance(catalog_id, str)
                or re.fullmatch(r"[0-9a-f]{64}", catalog_id) is None
                or not isinstance(url, str) or not url):
            raise EvidenceError("Catalog project needs a full SHA-256 id and a URL")
        if hashlib.sha256(url.encode("utf-8")).hexdigest() != catalog_id:
            raise EvidenceError("Catalog id does not match SHA-256 of URL: " + url)
        if catalog_id in seen:
            raise EvidenceError("Duplicate catalog id: " + catalog_id)
        seen.add(catalog_id)
        projects.append({"id": catalog_id, "url": url,
                         "name": project.get("name", url)})
    return {"source_sha": document.get("source_sha"), "projects": projects}


def load_evidence(path):
    """Load an existing evidence file, or an empty one if absent."""
    if path is None or not Path(path).exists():
        return {"schema_version": SCHEMA_VERSION, "last_sweep": None, "records": {}}
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError("Cannot read evidence %s: %s" % (path, error)) from error
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("Evidence schema_version must be 1")
    records = document.get("records")
    if not isinstance(records, dict):
        raise EvidenceError("Evidence records must be an object keyed by catalog id")
    return {"schema_version": SCHEMA_VERSION,
            "last_sweep": document.get("last_sweep"), "records": records}


def compute_digest(observations):
    """SHA-256 of sorted ``catalog_id:status:http_status:final_url`` lines."""
    lines = sorted(
        "%s:%s:%s:%s" % (obs.catalog_id, obs.status,
                         "" if obs.http_status is None else obs.http_status,
                         "" if obs.final_url is None else obs.final_url)
        for obs in observations)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _observation_fields(observation):
    return (observation.status, observation.http_status, observation.final_url,
            tuple((hop["status"], hop["location"]) for hop in observation.redirect_chain),
            observation.github_repo_id_before, observation.github_repo_id_after,
            observation.github_identity_verified, observation.error_kind)


def _record_snapshot(record):
    return {key: value for key, value in record.items() if key != "observations"}


def record_from_observation(project, observation, previous):
    """Build the evidence record for one observation.

    Unchanged observations keep the previous record untouched, including
    its review status. New or changed observations start as pending.
    """
    record = {
        "project_url": project["url"],
        "canonical_url_checked": observation.canonical_url_checked,
        "checked_at": observation.checked_at,
        "checked_by": CHECKED_BY,
        "status": observation.status,
        "http_status": observation.http_status,
        "final_url": observation.final_url,
        "redirect_chain": observation.redirect_chain,
        "error_kind": observation.error_kind,
        "attempts": observation.attempts,
        "review_status": "pending",
        "review_note": observation.review_note,
        "observations": [],
    }
    if observation.github_identity_verified is not None:
        record["github_repo_id_before"] = observation.github_repo_id_before
        record["github_repo_id_after"] = observation.github_repo_id_after
        record["github_identity_verified"] = observation.github_identity_verified
    if previous is not None:
        record["observations"] = ([_record_snapshot(previous)]
                                  + list(previous.get("observations") or []))[:3]
    return record


def merge_evidence(previous_records, observations, checked_at, catalog_by_id,
                   catalog_source_sha):
    """Apply changed-only records and pruning. Returns (records, changed, pruned).

    A record that answers cleanly (reachable, no redirect) is kept for one
    further sweep and removed on the next clean sweep. Cleanliness is
    read from the previous record's top-level fields, so no extra field
    is added to the schema. ``catalog_source_sha`` is the previous sweep's
    catalog SHA, written to ``last_present_source_sha`` when an ID has left
    the catalog and that record has no stamp yet.
    """
    records = {}
    changed_ids = []
    pruned_ids = []
    by_id = {obs.catalog_id: obs for obs in observations}
    for catalog_id, previous in previous_records.items():
        if catalog_id not in by_id:
            if (catalog_id not in catalog_by_id
                    and isinstance(previous, dict)
                    and not previous.get("last_present_source_sha")
                    and catalog_source_sha):
                previous = dict(previous)
                previous["last_present_source_sha"] = catalog_source_sha
            records[catalog_id] = previous
    for observation in observations:
        project = catalog_by_id[observation.catalog_id]
        previous = previous_records.get(observation.catalog_id)
        clean = observation.status == "reachable" and not observation.redirect_chain
        if clean and previous is None:
            # First observation, clean: not actionable (section 7) and
            # nothing changed since a previous sweep, so no record.
            continue
        if clean and previous is not None:
            previous_clean = (previous.get("status") == "reachable"
                              and not previous.get("redirect_chain"))
            if previous_clean:
                pruned_ids.append(observation.catalog_id)
                changed_ids.append(observation.catalog_id)
                continue
        if previous is not None and _observation_fields(observation) == _record_fields(previous):
            records[observation.catalog_id] = previous
            continue
        records[observation.catalog_id] = record_from_observation(project, observation, previous)
        changed_ids.append(observation.catalog_id)
    return records, sorted(changed_ids), sorted(pruned_ids)


def _record_fields(record):
    chain = tuple((hop["status"], hop["location"]) for hop in record.get("redirect_chain") or [])
    return (record.get("status"), record.get("http_status"), record.get("final_url"),
            chain, record.get("github_repo_id_before"),
            record.get("github_repo_id_after"),
            record.get("github_identity_verified"), record.get("error_kind"))


def validate_evidence(evidence, catalog_by_id):
    """Validate an evidence document against the freshly built catalog."""
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("Evidence schema_version must be 1")
    records = evidence.get("records")
    if not isinstance(records, dict):
        raise EvidenceError("Evidence records must be an object")
    for catalog_id, record in records.items():
        if not isinstance(record, dict):
            raise EvidenceError("Evidence record must be an object: " + str(catalog_id))
        retained = catalog_id not in catalog_by_id
        if retained and not record.get("last_present_source_sha"):
            raise EvidenceError("Retained record needs last_present_source_sha: " + catalog_id)
        if not retained and record.get("project_url") != catalog_by_id[catalog_id]["url"]:
            raise EvidenceError("Evidence project_url does not match catalog: " + catalog_id)
        if record.get("status") not in TAXONOMY:
            raise EvidenceError("Evidence status outside taxonomy: " + catalog_id)
        checked_at = record.get("checked_at")
        if not isinstance(checked_at, str):
            raise EvidenceError("Evidence checked_at must be a date: " + catalog_id)
        try:
            date.fromisoformat(checked_at)
        except ValueError as error:
            raise EvidenceError("Evidence checked_at must be a valid UTC date: " + catalog_id) from error
        if len(record.get("redirect_chain") or []) > MAX_HOPS:
            raise EvidenceError("Redirect chain longer than 5 hops: " + catalog_id)
        if record.get("error_kind") not in ERROR_KINDS:
            raise EvidenceError("Evidence error_kind outside allowed values: " + catalog_id)
        if record.get("github_identity_verified") is True and (
                type(record.get("github_repo_id_before")) is not int
                or type(record.get("github_repo_id_after")) is not int):
            raise EvidenceError("Verified GitHub identity needs both IDs: " + catalog_id)
        observations = record.get("observations")
        if observations is not None and (not isinstance(observations, list) or len(observations) > 3):
            raise EvidenceError("Observations must keep at most three entries: " + catalog_id)


def _probe_one(project, fetch, pacer, sleep, checked_at, api_fetch):
    observation = probe_url(project["url"], fetch, pacer, sleep)
    observation.catalog_id = project["id"]
    observation.checked_at = checked_at
    if (api_fetch is not None and observation.redirect_chain
            and _host_of(project["url"]) == "github.com"
            and observation.final_url):
        before, after, verified, reason = verify_github_identity(
            project["url"], observation.final_url, api_fetch)
        observation.github_repo_id_before = before
        observation.github_repo_id_after = after
        observation.github_identity_verified = verified
        if verified:
            observation.review_note = (observation.review_note + " GitHub identity verified: same repository ID %d." % before).strip()
        else:
            observation.review_note = (observation.review_note + " GitHub identity unverified: %s" % reason).strip()
    elif observation.redirect_chain and _host_of(project["url"]) == "github.com":
        observation.github_repo_id_before = None
        observation.github_repo_id_after = None
        observation.github_identity_verified = False
        observation.review_note = (observation.review_note + " GitHub identity unverified: no token available.").strip()
    return observation


def run_sweep(catalog, fetch, *, pacer=None, sleep=time.sleep, checked_at=None,
              api_fetch=None, max_workers=MAX_WORKERS, max_urls=None,
              previous_records=None, clock=None):
    """Probe the catalog in ascending catalog-ID order.

    Returns (observations, report, blockers). Observations are sorted by
    catalog ID, so the digest is deterministic for a given catalog and
    set of HTTP results. A rate-limit blocker (>10 URLs returning 429)
    stops the sweep and preserves the observations already recorded.
    """
    checked_at = checked_at or datetime.now(timezone.utc).date().isoformat()
    clock = clock or time.monotonic
    pacer = pacer or HostPacer(sleep=sleep)
    projects = sorted(catalog["projects"], key=lambda item: item["id"])
    if max_urls is not None:
        projects = projects[:max_urls]
    started = clock()
    observations = []
    blockers = []
    rate_limited = 0
    total_requests = 0
    stop = threading.Event()

    def work(project):
        if stop.is_set():
            return None
        return _probe_one(project, fetch, pacer, sleep, checked_at, api_fetch)

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        for observation in pool.map(work, projects):
            if observation is None:
                continue
            observations.append(observation)
            total_requests += observation.attempts
            if observation.error_kind == "rate-limited":
                rate_limited += 1
                if rate_limited > 10:
                    blockers.append("More than 10 URLs returned 429; sweep stopped.")
                    stop.set()
                    break
            if total_requests > MAX_REQUESTS_PER_RUN:
                blockers.append("Request bound of %d exceeded; sweep stopped." % MAX_REQUESTS_PER_RUN)
                stop.set()
                break
            if clock() - started > MAX_MINUTES_PER_RUN * 60:
                blockers.append("45-minute run bound exceeded; sweep stopped.")
                stop.set()
                break
    observations.sort(key=lambda obs: obs.catalog_id)
    counts = {status: 0 for status in sorted(TAXONOMY)}
    for observation in observations:
        counts[observation.status] += 1
    previous_records = previous_records or {}
    persistent = []
    for observation in observations:
        previous = previous_records.get(observation.catalog_id)
        if (previous and observation.status in {"client-error", "server-error", "transport-error"}
                and previous.get("status") == observation.status
                and previous.get("error_kind") == observation.error_kind
                and previous.get("checked_at") != checked_at):
            persistent.append(observation.catalog_id)
    triage = []
    for observation in observations:
        if observation.status != "redirect-permanent" and not (
                observation.status == "redirect-temporary"
                and observation.github_identity_verified):
            continue
        label = triage_class(observation.canonical_url_checked,
                             observation.final_url, observation.redirect_chain)
        if label:
            triage.append({"catalog_id": observation.catalog_id, "class": label})
    report = {
        "date": checked_at,
        "catalog_source_sha": catalog.get("source_sha"),
        "checked": len(observations),
        "counts": counts,
        "digest": compute_digest(observations),
        "requests": total_requests,
        "elapsed_seconds": round(clock() - started, 1),
        "persistent_failures": sorted(persistent),
        "redirect_triage": triage,
        "blockers": blockers,
    }
    return observations, report, blockers


def build_fixture_fetch(spec):
    """Build a no-network fetch from a recorded-chain spec.

    ``spec`` maps ``"METHOD <url>"`` to a list of responses, consumed in
    order. A response is ``{"status": int, "location": "..."}`` or
    ``{"error_kind": "..."}``. An unscripted request answers 200.
    """
    queues = {}
    lock = threading.Lock()
    for key, responses in (spec or {}).items():
        queues[key] = list(responses)

    def fetch(method, url, timeout):
        with lock:
            queue = queues.get(method + " " + url, [])
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

    return fetch


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Canonical URL health audit: probe a catalog and record "
                    "observed HTTP facts. Standard library only.")
    parser.add_argument("--catalog", type=Path, required=True,
                        help="Catalog JSON from scripts/build_catalog.py")
    parser.add_argument("--evidence", type=Path,
                        help="Existing evidence file, if any")
    parser.add_argument("--output", type=Path, required=True,
                        help="Evidence file to write (not written in dry-run mode "
                             "unless --write-output is also given)")
    parser.add_argument("--dry-run", action="store_true",
                        help="No network. Without --fixtures, print probe order "
                             "and write nothing. With --fixtures, replay them and "
                             "write the output only when --write-output is given.")
    parser.add_argument("--write-output", action="store_true",
                        help="Write the output file even in dry-run mode.")
    parser.add_argument("--fixtures", type=Path,
                        help="Recorded-chain spec for dry-run mode (see build_fixture_fetch).")
    parser.add_argument("--checked-date",
                        help="UTC date for this sweep, YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--limit", type=int,
                        help="Probe only the first N URLs in catalog-ID order (pilot bound)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help="Probe workers, at most 8, 1 in flight per host")
    args = parser.parse_args(argv)
    if args.checked_date:
        try:
            date.fromisoformat(args.checked_date)
        except ValueError:
            parser.error("checked-date must be YYYY-MM-DD")
    if not 1 <= args.workers <= MAX_WORKERS:
        parser.error("workers must be 1 to 8")
    catalog = load_catalog(args.catalog)
    previous = load_evidence(args.evidence)
    previous_records = previous["records"]
    if args.dry_run:
        if args.fixtures is None:
            print("Dry-run without fixtures: probe order only, no network, nothing written.")
            for project in sorted(catalog["projects"], key=lambda item: item["id"]):
                print(project["id"], project["url"])
            return 0
        try:
            spec = json.loads(args.fixtures.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            parser.error("cannot read fixtures: %s" % error)
        fetch = build_fixture_fetch(spec.get("responses", {}))
        api_fetch = None
    else:
        fetch = live_fetch
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        api_fetch = live_api_fetch(token) if token else None
        if token is None:
            print("No GitHub token in GH_TOKEN or GITHUB_TOKEN; "
                  "GitHub redirects stay identity-unverified.", file=sys.stderr)
    observations, report, blockers = run_sweep(
        catalog, fetch, checked_at=args.checked_date, api_fetch=api_fetch,
        max_workers=args.workers, max_urls=args.limit, previous_records=previous_records)
    last_sweep = previous.get("last_sweep")
    previous_catalog_sha = (last_sweep.get("catalog_source_sha")
                            if isinstance(last_sweep, dict) else None)
    records, changed_ids, pruned_ids = merge_evidence(
        previous_records, observations, report["date"],
        {p["id"]: p for p in catalog["projects"]}, previous_catalog_sha)
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "last_sweep": {
            "date": report["date"],
            "catalog_source_sha": report["catalog_source_sha"],
            "checked": report["checked"],
            "counts": report["counts"],
            "changed_ids": changed_ids,
            "pruned_ids": pruned_ids,
            "digest": report["digest"],
            "requests": report["requests"],
            "elapsed_seconds": report["elapsed_seconds"],
            "limits_hit": report["blockers"],
        },
        "records": records,
    }
    validate_evidence(evidence, {p["id"]: p for p in catalog["projects"]})
    print(json.dumps(report, indent=2, sort_keys=True))
    if blockers:
        print("Blockers: " + "; ".join(blockers), file=sys.stderr)
    if args.dry_run and not args.write_output:
        print("Dry-run: output not written. Pass --write-output to write it.")
        return 3 if blockers else 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                        encoding="utf-8")
    os.replace(tmp_path, args.output)
    print("Wrote %s: %d records, %d changed, %d pruned."
          % (args.output, len(records), len(changed_ids), len(pruned_ids)))
    return 3 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
