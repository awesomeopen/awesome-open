#!/usr/bin/env python3
"""Collect optional website release/Scorecard evidence without candidate execution.

Only upstream availability failures are fail-soft. Invalid local snapshots,
provider schema and repository identity are fatal before the atomic write.
"""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import http.client
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import signals
import update_stats

ROOT = Path(__file__).resolve().parents[1]
RETRY_CODES = {500, 502, 503, 504}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    # A renamed repository needs a reviewed identity update. Do not leak the
    # GitHub credential to another host or silently attach another repo's data.
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def request_json(url, headers, timeout):
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise ValueError('Optional provider response exceeds 2 MB')
            return response.status, dict(response.headers.items()), (json.loads(payload) if response.status == 200 else None)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers.items()), None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
        return None, {}, None


def normalize_release(payload, repo, at):
    if not isinstance(payload, dict) or payload.get('draft') is not False or payload.get('prerelease') is not False:
        raise ValueError('Latest GitHub release must be a published non-prerelease')
    good = dict(observed_at=payload.get('published_at'), fetched_at=at, source_commit=None,
                tool_version=None, tool_commit=None, value={
                    'release_id': payload.get('id'), 'tag_name': payload.get('tag_name'),
                    'published_at': payload.get('published_at'), 'html_url': payload.get('html_url')})
    signals.validate_good(good, repo, 'release')
    return good


def normalize_scorecard(payload, repo, at):
    if not isinstance(payload, dict) or not isinstance(payload.get('repo'), dict) or not isinstance(payload.get('scorecard'), dict):
        raise ValueError('Invalid Scorecard result schema')
    name = payload['repo'].get('name')
    if not isinstance(name, str) or name.lower() != 'github.com/' + repo:
        raise ValueError('Scorecard repository identity mismatch')
    date = payload.get('date')
    observed = date + 'T00:00:00Z' if isinstance(date, str) and len(date) == 10 else date
    checks = payload.get('checks')
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        raise ValueError('Invalid Scorecard checks')
    # -1 is inconclusive, never zero. Omitted checks are not fabricated.
    def result(value):
        if value == -1 and type(value) in (int, float):
            return None
        signals.score(value)
        return value
    good = dict(observed_at=observed, fetched_at=at,
                source_commit=payload['repo'].get('commit'),
                tool_version=payload['scorecard'].get('version'),
                tool_commit=payload['scorecard'].get('commit'),
                value={'repository': name.lower(), 'score': result(payload.get('score')),
                       'checks': [{'name': c.get('name'), 'score': result(c.get('score')),
                                   'reason': c.get('reason')} for c in checks]})
    signals.validate_good(good, repo, 'scorecard')
    return good


def retry_time(headers, now, default_seconds=3600):
    headers = {key.lower(): value for key, value in headers.items()}
    values = [now + timedelta(seconds=default_seconds)]
    value = headers.get('retry-after')
    if value:
        try:
            values.append(now + timedelta(seconds=max(0, int(value))))
        except (ValueError, OverflowError):
            try:
                values.append(parsedate_to_datetime(value).astimezone(timezone.utc))
            except (ValueError, TypeError, OverflowError, AttributeError):
                pass
    try:
        values.append(datetime.fromtimestamp(int(headers.get('x-ratelimit-reset', '')), timezone.utc))
    except (ValueError, OverflowError, OSError):
        pass
    return signals.iso(max(values))


def due(record, provider, now):
    if record['retry_after'] and signals.timestamp(record['retry_after']) > now:
        return False
    if record['checked_at'] is None:
        return True
    # Negative Scorecard results are slower to recheck; errors retry next day.
    days = 14 if provider == 'scorecard' and record['fetch_status'] == 'not_found' else (7 if provider == 'scorecard' and record['fetch_status'] in {'ok', 'not_modified'} else 1)
    return now - signals.timestamp(record['checked_at']) >= timedelta(days=days)


def collect(repositories, previous=None, *, now=None, source_sha=None, token=None,
            providers=signals.PROVIDERS, release_budget=350, scorecard_budget=50,
            max_seconds=300, fetch=request_json, monotonic=time.monotonic, sleep=time.sleep):
    if not 0 <= release_budget <= 350 or not 0 <= scorecard_budget <= 50 or not 0 <= max_seconds <= 300:
        raise ValueError('Optional collection ceilings are 350 release requests, 50 Scorecard requests, and 300 seconds')
    now = now or datetime.now(timezone.utc)
    at = signals.iso(now)
    if previous is not None:
        signals.validate_snapshot(previous)
    result = deepcopy(previous) if previous is not None else signals.empty_snapshot(at)
    result.update(collected_at=at, source_sha=source_sha)
    repos = sorted(set(repositories))
    if any(not isinstance(repo, str) or not signals.REPO.fullmatch(repo) for repo in repos):
        raise ValueError('Collector requires canonical lowercase repository identities')
    result['repositories'] = {repo: result['repositories'].get(repo, {p: signals.empty_signal(repo, p) for p in signals.PROVIDERS}) for repo in repos}
    summary = Counter()
    deadline = monotonic() + max_seconds
    budgets = {'release': release_budget, 'scorecard': scorecard_budget}
    for provider in providers:
        if provider not in signals.PROVIDERS:
            raise ValueError('Unknown optional provider')
        provider_delay = result['provider_retry_after'][provider]
        if provider_delay and signals.timestamp(provider_delay) > now:
            summary[provider + ':backoff'] += 1
            continue
        result['provider_retry_after'][provider] = None
        # Least-recently attempted first: a bounded run progresses through the
        # catalogue rather than repeatedly starving the alphabetical tail.
        queue = sorted(repos, key=lambda repo: (result['repositories'][repo][provider]['checked_at'] or '', repo))
        for repo in queue:
            record = result['repositories'][repo][provider]
            if not due(record, provider, now):
                continue
            if budgets[provider] <= 0 or monotonic() >= deadline:
                summary[provider + ':budget_deferred'] += 1
                continue
            if provider == 'release' and not token:
                summary['release:no_token'] += 1
                continue
            headers = {'Accept': 'application/json', 'User-Agent': 'awesome-open-signals/1'}
            if provider == 'release':
                headers.update(Authorization='Bearer ' + token, Accept='application/vnd.github+json',
                               **{'X-GitHub-Api-Version': '2022-11-28'})
            if record['etag'] and record['last_good']:
                headers['If-None-Match'] = record['etag']
            code, response_headers, payload = None, {}, None
            attempted = False
            for attempt in range(2):
                remaining = deadline - monotonic()
                if budgets[provider] <= 0 or remaining <= 0:
                    break
                attempted = True
                budgets[provider] -= 1
                summary[provider + ':requests'] += 1
                code, response_headers, payload = fetch(record['source_url'], headers, min(10, remaining))
                if (code not in RETRY_CODES and code is not None) or any(key.lower() == 'retry-after' for key in response_headers):
                    break
                if attempt == 0 and budgets[provider] > 0 and deadline - monotonic() > 1:
                    sleep(1)
                else:
                    break
            if not attempted:
                summary[provider + ':budget_deferred'] += 1
                continue
            response_headers = {key.lower(): value for key, value in response_headers.items()}
            record.update(checked_at=at, check_time_precision='second', http_status=code, error=None, retry_after=None)
            if code == 200:
                record['last_good'] = (normalize_release if provider == 'release' else normalize_scorecard)(payload, repo, at)
                record.update(fetch_status='ok', last_success_at=at, success_time_precision='second', etag=response_headers.get('etag'))
            elif code == 304:
                if not record['last_good'] or not headers.get('If-None-Match'):
                    raise ValueError('304 optional response without cached value and validator')
                record.update(fetch_status='not_modified', last_success_at=at, success_time_precision='second',
                              etag=response_headers.get('etag', record['etag']))
            elif code == 404:
                record.update(fetch_status='not_found', error='not_found', etag=None)
            elif code == 202:
                record.update(fetch_status='pending', error='provider_pending')
                record['retry_after'] = retry_time(response_headers, now, 86400)
            else:
                record.update(fetch_status='error', error='transport_error' if code is None else 'http_' + str(code))
                if code in {403, 429} or (code in RETRY_CODES and 'retry-after' in response_headers):
                    record['retry_after'] = retry_time(response_headers, now)
                    result['provider_retry_after'][provider] = record['retry_after']
                elif code in {301, 302, 303, 307, 308}:
                    raise ValueError('Optional provider redirected repository identity; review source mapping')
            summary[provider + ':' + record['fetch_status']] += 1
            # Also stop when a successful response uses the reserved quota.
            try:
                low_quota = provider == 'release' and int(response_headers.get('x-ratelimit-remaining', '1000')) <= 100
            except ValueError:
                low_quota = False
            if low_quota:
                result['provider_retry_after'][provider] = retry_time(response_headers, now)
            if result['provider_retry_after'][provider]:
                break
            if monotonic() + 0.1 < deadline:
                sleep(0.1)
    for providers_for_repo in result['repositories'].values():
        for provider, record in providers_for_repo.items():
            record['status'] = signals.effective_status(record, provider, at)
    signals.validate_snapshot(result)
    return result, dict(sorted(summary.items()))


def write_snapshot(path, document):
    signals.validate_snapshot(document)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    try:
        temporary.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/project_signals.json')
    parser.add_argument('--source-sha')
    parser.add_argument('--providers', nargs='+', choices=signals.PROVIDERS, default=list(signals.PROVIDERS))
    parser.add_argument('--release-budget', type=int, default=350)
    parser.add_argument('--scorecard-budget', type=int, default=50)
    parser.add_argument('--max-seconds', type=int, default=300)
    args = parser.parse_args()
    if not 0 <= args.release_budget <= 350 or not 0 <= args.scorecard_budget <= 50 or not 0 <= args.max_seconds <= 300:
        parser.error('Optional collection ceilings are 350 release requests, 50 Scorecard requests, and 300 seconds')
    source = (ROOT / 'README.source.md').read_text(encoding='utf-8')
    repositories = update_stats.repositories(source, require_markers=False)
    document, summary = collect(repositories, signals.load_optional(args.output), source_sha=args.source_sha,
                                token=os.environ.get('GH_TOKEN'), providers=args.providers,
                                release_budget=args.release_budget, scorecard_budget=args.scorecard_budget,
                                max_seconds=args.max_seconds)
    write_snapshot(args.output, document)
    print(json.dumps({'optional_signals': summary, 'repositories': len(repositories)}, sort_keys=True))


if __name__ == '__main__':
    main()
