#!/usr/bin/env python3
"""One-time, bounded aggregate-history collection. No schedule or new credential.

Each repository is checkpointed locally; batches merge onto fresh main using an
ordinary fast-forward push. The publisher workflow supplies the shared lock.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

import publish_readme as publisher
import update_star_history as history

ROOT = Path(__file__).resolve().parents[1]
RATE_URL = 'https://api.github.com/rate_limit'
URL = re.compile(r'https://api\.github\.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/stargazers/history\?per_page=30&page=[1-9][0-9]*')


class StopBackfill(RuntimeError):
    def __init__(self, reason, resumable=False):
        super().__init__(reason)
        self.resumable = resumable


class Transport:
    """Sequential bounded requests; live headers, not a guessed hourly quota."""
    def __init__(self, token, reserve, seconds=900, opener=None, clock=time.time, sleep=time.sleep):
        if not token:
            raise StopBackfill('Existing GITHUB_TOKEN is required')
        if type(reserve) is not int or reserve < 20 or not 1 <= seconds <= 900:
            raise ValueError('Invalid reserve or bounded duration')
        self.token, self.reserve = token, reserve
        self.open = opener or build_opener(history.NoRedirect).open
        self.clock, self.sleep = clock, sleep
        self.started = clock()
        self.deadline = self.started + seconds
        self.remaining, self.reset, self.attempts = None, None, 0
        self.not_before = None

    def wait(self, seconds):
        if seconds < 0 or self.clock() + seconds + 35 >= self.deadline:
            raise StopBackfill('Time limit reached; resume from the saved progress', True)
        self.sleep(seconds)

    def observe(self, headers):
        try:
            remaining = int(headers['X-RateLimit-Remaining'])
            reset = int(headers['X-RateLimit-Reset'])
            if remaining < 0 or reset <= 0:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise StopBackfill('Missing or invalid GitHub quota headers')
        self.remaining, self.reset = remaining, reset

    def retry_after(self, headers):
        value = headers.get('Retry-After')
        if value is None:
            return 0
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = parsedate_to_datetime(value).timestamp() - self.clock()
            except (ValueError, TypeError, OverflowError):
                raise StopBackfill('Invalid GitHub Retry-After header')
        if not 0 <= delay < 86400:
            raise StopBackfill('Invalid GitHub Retry-After delay')
        return delay

    def __call__(self, url):
        if url != RATE_URL and URL.fullmatch(url) is None:
            raise ValueError('Only quota and aggregate history endpoints are allowed')
        if self.remaining is None and url != RATE_URL:
            self(RATE_URL)
        for retry in range(4):
            if self.clock() + 35 >= self.deadline or self.attempts >= (910 if url == RATE_URL else 900):
                raise StopBackfill('Bounded run budget reached; resume from the saved progress', True)
            if url != RATE_URL and self.remaining <= self.reserve:
                raise StopBackfill('Quota floor reached; checkpoint and wait for reset', True)
            request = Request(url, headers={
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': history.API_VERSION,
                'User-Agent': 'awesome-open-history-backfill/1.0',
                'Authorization': 'Bearer ' + self.token,
            })
            self.attempts += 1
            try:
                with self.open(request, timeout=30) as response:
                    self.observe(response.headers)
                    body = response.read(2_000_001)
                    if len(body) > 2_000_000:
                        raise StopBackfill('Oversized aggregate response')
                    try:
                        return json.loads(body)
                    except (ValueError, UnicodeDecodeError):
                        raise StopBackfill('Invalid GitHub JSON response')
            except HTTPError as error:
                # Never log the response body, transport exception or token.
                if error.code in {401, 301, 302, 307, 308}:
                    raise StopBackfill('GitHub authentication or identity response requires review')
                if error.code in {403, 429}:
                    self.observe(error.headers)
                    raw = error.read(4096).decode('utf-8', errors='replace').lower()
                    limited = (self.remaining == 0 or error.code == 429
                               or 'secondary rate limit' in raw or 'abuse detection' in raw)
                    if not limited:
                        raise StopBackfill('GitHub denied access; review permissions without automatic retries')
                    delay = max(self.retry_after(error.headers), 60 * 2 ** retry)
                    if self.remaining == 0:
                        delay = max(delay, self.reset - self.clock() + 2)
                    self.not_before = self.clock() + delay
                    if self.remaining <= self.reserve:
                        raise StopBackfill('GitHub quota response reached the publisher reserve; resume after reset', True)
                    if retry == 3:
                        raise StopBackfill('Repeated GitHub rate limit; paused for review', True)
                    self.wait(delay)
                elif error.code in {500, 502, 503, 504} and retry < 3:
                    self.wait(2 ** (retry + 1))
                else:
                    raise StopBackfill('Unexpected GitHub HTTP ' + str(error.code) + '; paused for review')
            except (URLError, TimeoutError, OSError):
                if retry == 3:
                    raise StopBackfill('Repeated transport failure; paused for review', True)
                self.wait(2 ** (retry + 1))
        raise StopBackfill('Request retry limit reached')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(path)


def load(root):
    root = Path(root)
    projects = history.load_projects(json.loads((root / 'data/star_history_projects.json').read_text()),
                                     (root / 'README.source.md').read_text())
    cache = history.validate_cache(json.loads((root / 'data/star_history.json').read_text()))
    metadata = json.loads((root / 'data/github_metrics.json').read_text())
    return projects, cache, metadata


def merge_records(cache, projects, records):
    """Merge only eligible, newer successful observations, never stale snapshots."""
    result = deepcopy(cache)
    eligible = {p['repo']: p for p in projects}
    for repo, record in records.items():
        if repo not in eligible or record.get('status') != 'ok':
            continue
        previous = result['repositories'].get(repo, {}).get('last_good')
        if previous and history.parse_time(previous['fetched_at']) >= history.parse_time(record['last_good']['fetched_at']):
            continue
        result['repositories'][repo] = {**deepcopy(record), **eligible[repo]}
    # Budget and other publisher-owned metadata remain from current main.
    history.validate_cache(result)
    return result


def flush(root, records):
    if not records:
        return
    for attempt in range(5):
        base = publisher.latest_main(root)
        with tempfile.TemporaryDirectory(prefix='history-checkpoint-') as directory:
            worktree = Path(directory) / 'checkout'
            publisher.git(root, 'worktree', 'add', '--detach', str(worktree), base)
            try:
                projects, cache, _ = load(worktree)
                merged = merge_records(cache, projects, records)
                history.write_cache(worktree / 'data/star_history.json', merged)
                changed = publisher.changed_paths(worktree)
                if changed - {'data/star_history.json'}:
                    raise StopBackfill('Checkpoint modified an unauthorized path')
                if not changed:
                    return
                publisher.run(worktree, 'python3', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py')
                if publisher.latest_main(root) != base:
                    continue
                publisher.git(worktree, 'add', '--', 'data/star_history.json')
                publisher.git(worktree, '-c', 'user.name=github-actions[bot]', '-c',
                              'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                              'commit', '-m', 'chore: checkpoint aggregate star-history backfill')
                commit = publisher.git(worktree, 'rev-parse', 'HEAD').stdout.strip()
                pushed = publisher.git(worktree, 'push', 'origin', 'HEAD:refs/heads/main', check=False)
                if pushed.returncode == 0:
                    return
                current = publisher.latest_main(root)
                if publisher.git(root, 'merge-base', '--is-ancestor', commit, current, check=False).returncode == 0:
                    return
                if current == base:
                    raise StopBackfill('Checkpoint push blocked; retained the recovery artifact')
            finally:
                publisher.git(root, 'worktree', 'remove', '--force', str(worktree))
    raise StopBackfill('Main kept advancing; retained the recovery artifact')


def collect(projects, cache, metadata, transport, source_sha, checkpoint, flush_records, now=None):
    now = now or history.utc_now()
    months = history.window(now)[2]
    missing = [p for p in projects if cache['repositories'].get(p['repo'], {}).get('last_good', {}).get('months') != months]
    missing.sort(key=lambda p: history.priority_key(p, cache['repositories'], metadata))
    state = {'schema_version': 1, 'source_sha': source_sha, 'started_at': now.isoformat(),
             'eligible': len(projects), 'initial_missing': len(missing), 'records': {},
             'status': 'running', 'remaining': len(missing), 'failed_repositories': []}
    pending = {}
    atomic_json(checkpoint, state)
    try:
        for project in missing:
            repo = project['repo']
            try:
                good = history.collect_repository(repo, now=now, getter=transport,
                    budget=history.RequestBudget(64),
                    created_at=metadata.get('repositories', {}).get(repo, {}).get('created_at'), source_sha=source_sha)
            except history.HistoryError:
                state['failed_repositories'].append(repo)
                atomic_json(checkpoint, state)
                continue
            record = {**project, 'checked_at': now.isoformat(), 'source_sha': source_sha,
                      'source_url': history.API + repo + '/stargazers/history', 'status': 'ok', 'last_good': good}
            history.validate_cache({'schema_version': 1, 'repositories': {repo: record}})
            state['records'][repo] = record
            pending[repo] = record
            state['remaining'] -= 1
            atomic_json(checkpoint, state)
            if len(pending) >= 20:
                flush_records(pending)
                pending = {}
        state['status'] = 'blocked' if state['failed_repositories'] else 'complete'
        if state['failed_repositories']:
            state['reason'] = 'Some aggregate histories failed coverage validation; review the checkpoint'
    except StopBackfill as error:
        state.update(status='partial' if error.resumable else 'blocked', reason=str(error))
    except (history.HistoryError, ValueError, RuntimeError, OSError):
        state.update(status='blocked', reason='Collection or checkpoint validation failed; review before resuming')
    # Completed repositories survive a later page failure. A failed flush must
    # remain failed, not be disguised as a successful or complete collection.
    try:
        flush_records(pending)
    except (RuntimeError, OSError):
        state.update(status='blocked', reason='Checkpoint publication failed; recover validated local evidence')
    state['requests'] = transport.attempts
    state['quota_reset_at'] = datetime.fromtimestamp(transport.reset, timezone.utc).isoformat() if getattr(transport, 'reset', None) else None
    state['quota_remaining'] = getattr(transport, 'remaining', None)
    resume_after = max(getattr(transport, 'reset', None) or 0, getattr(transport, 'not_before', None) or 0)
    state['resume_after'] = datetime.fromtimestamp(resume_after + 2, timezone.utc).isoformat() if resume_after else None
    atomic_json(checkpoint, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, default=ROOT / 'tmp/history-backfill/checkpoint.json')
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    # workflow checkout uses main; pull latest before establishing the manifest.
    base = publisher.latest_main(ROOT)
    with tempfile.TemporaryDirectory(prefix='history-input-') as directory:
        worktree = Path(directory) / 'checkout'
        publisher.git(ROOT, 'worktree', 'add', '--detach', str(worktree), base)
        try:
            projects, cache, metadata = load(worktree)
        finally:
            publisher.git(ROOT, 'worktree', 'remove', '--force', str(worktree))
    reserve = len(projects) + 350 + history.DEFAULT_REQUEST_BUDGET + 20
    transport = Transport(os.environ.get('GITHUB_TOKEN'), reserve, args.seconds)
    state = collect(projects, cache, metadata, transport, base, args.checkpoint, lambda records: flush(ROOT, records))
    summary = (f"History backfill: {state['status']}; {len(state['records'])} completed this run; "
               f"{state['remaining']} remaining in this run's manifest; {state['requests']} HTTP attempts. "
               f"Normal publisher reserve: {reserve}. Quota reset: {state['quota_reset_at']}; remaining: {state['quota_remaining']}. "
               f"If partial, resume no earlier than {state['resume_after']}. " + state.get('reason', ''))
    print(summary)
    if output := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(output, 'a') as stream:
            stream.write(summary + '\n')
    if state['status'] == 'blocked':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
