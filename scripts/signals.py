#!/usr/bin/env python3
"""Validated, optional website evidence. No network or wall clock in this module."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import json
import re
from urllib.parse import unquote, urlsplit

PROVIDERS = ('release', 'scorecard')
METHOD_VERSION = '1'
REPO = re.compile(r'[a-z0-9_.-]+/[a-z0-9_.-]+')
SHA = re.compile(r'[0-9a-f]{40}')
STATUSES = {'available', 'unavailable', 'pending', 'partial', 'stale'}
FETCH_STATUSES = {'not_checked', 'ok', 'not_modified', 'not_found', 'pending', 'error', 'deferred'}


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError('Expected an ISO UTC signal timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def precision(value, level):
    if level not in {'second', 'day'} or (level == 'day' and not value.endswith('T00:00:00Z')):
        raise ValueError('Invalid signal timestamp precision')


def iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid ' + label)
    return value


def score(value, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError('Signal score must be in [0, 10] or inconclusive')


def source_url(repo, provider):
    return (f'https://api.github.com/repos/{repo}/releases/latest' if provider == 'release'
            else f'https://api.scorecard.dev/projects/github.com/{repo}')


def empty_signal(repo, provider):
    return dict(source_url=source_url(repo, provider), status='pending', fetch_status='not_checked',
                checked_at=None, last_success_at=None, http_status=None, retry_after=None,
                etag=None, error=None, last_good=None)


def empty_snapshot(at, source_sha=None):
    return dict(schema_version=1, method_version=METHOD_VERSION, collected_at=at,
                source_sha=source_sha, repositories={}, provider_retry_after={p: None for p in PROVIDERS})


def effective_status(record, provider, at):
    good = record['last_good']
    if good is None:
        return 'pending' if record['fetch_status'] in {'not_checked', 'pending', 'deferred'} else 'unavailable'
    if record['fetch_status'] not in {'ok', 'not_modified'}:
        return 'stale'
    # Release age describes a release, not cache freshness. Scorecard scan age is
    # separate from HTTP revalidation; a fresh 304 does not make an old scan new.
    basis = good['observed_at'] if provider == 'scorecard' else record['last_success_at']
    days = 30 if provider == 'scorecard' else 3
    if timestamp(at) - timestamp(basis) > timedelta(days=days):
        return 'stale'
    if provider == 'scorecard' and (not good['value']['checks'] or good['value']['score'] is None or
            any(check['score'] is None for check in good['value']['checks'])):
        return 'partial'
    return 'available'


def validate_good(good, repo, provider):
    required = {'observed_at', 'fetched_at', 'source_commit', 'tool_version', 'tool_commit', 'value'}
    if not isinstance(good, dict) or not required <= good.keys():
        raise ValueError('Expected last-good signal object')
    for key in ('observed_at', 'fetched_at'):
        timestamp(good.get(key))
    precision(good['fetched_at'], good.get('fetch_time_precision', 'second'))
    for key in ('source_commit', 'tool_commit'):
        if good.get(key) is not None and (not isinstance(good[key], str) or not SHA.fullmatch(good[key])):
            raise ValueError('Invalid signal ' + key)
    if good.get('tool_version') is not None:
        text(good['tool_version'], 'tool version')
    value = good.get('value')
    if not isinstance(value, dict):
        raise ValueError('Expected signal value object')
    required = {'release_id', 'tag_name', 'published_at', 'html_url'} if provider == 'release' else {'repository', 'score', 'checks'}
    if not required <= value.keys():
        raise ValueError('Missing signal value field')
    if provider == 'release':
        text(value.get('tag_name'), 'release tag')
        if type(value.get('release_id')) is not int or value['release_id'] <= 0:
            raise ValueError('Invalid release ID')
        timestamp(value.get('published_at'))
        url = text(value.get('html_url'), 'release URL')
        parsed = urlsplit(url)
        decoded = unquote(parsed.path)
        unsafe_path = ('\\' in decoded or any(ord(c) < 33 for c in decoded)
                       or any(part in {'.', '..'} for part in decoded.split('/')))
        prefix = '/' + repo + '/releases/tag/'
        if (parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com'
                or not parsed.path.lower().startswith(prefix) or len(parsed.path) <= len(prefix)
                or parsed.query or parsed.fragment or unsafe_path):
            raise ValueError('Release URL does not match repository identity')
        if good['observed_at'] != value['published_at'] or good['source_commit'] is not None:
            raise ValueError('Release publication provenance is inconsistent')
    else:
        if value.get('repository') != 'github.com/' + repo:
            raise ValueError('Scorecard repository identity mismatch')
        score(value.get('score'), nullable=True)
        checks = value.get('checks')
        if not isinstance(checks, list):
            raise ValueError('Expected Scorecard checks list')
        names = set()
        for check in checks:
            if not isinstance(check, dict) or not {'name', 'score', 'reason'} <= check.keys():
                raise ValueError('Expected Scorecard check object')
            name = text(check.get('name'), 'check name')
            if name in names:
                raise ValueError('Duplicate Scorecard check')
            names.add(name)
            score(check.get('score'), nullable=True)
            text(check.get('reason'), 'check reason')
        if good['source_commit'] is None or good['tool_version'] is None:
            raise ValueError('Missing Scorecard scan provenance')


def validate_snapshot(document):
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document.get('schema_version') != 1 or document.get('method_version') != METHOD_VERSION:
        raise ValueError('Unsupported optional signal schema or method')
    if not {'schema_version', 'method_version', 'collected_at', 'source_sha', 'repositories', 'provider_retry_after'} <= document.keys():
        raise ValueError('Missing optional snapshot provenance')
    at = document.get('collected_at')
    timestamp(at)
    sha = document.get('source_sha')
    if sha is not None and (not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ValueError('Invalid optional signal source SHA')
    delays = document.get('provider_retry_after')
    if not isinstance(delays, dict) or set(delays) != set(PROVIDERS):
        raise ValueError('Expected optional provider retry times')
    for value in delays.values():
        if value is not None:
            timestamp(value)
    repositories = document.get('repositories')
    if not isinstance(repositories, dict):
        raise ValueError('Expected optional signal repositories')
    for repo, providers in repositories.items():
        if not isinstance(repo, str) or not REPO.fullmatch(repo) or not isinstance(providers, dict) or set(providers) != set(PROVIDERS):
            raise ValueError('Invalid optional repository identity/providers')
        for provider, record in providers.items():
            required = {'source_url', 'status', 'fetch_status', 'checked_at', 'last_success_at', 'http_status', 'retry_after', 'etag', 'error', 'last_good'}
            if not isinstance(record, dict) or not required <= record.keys() or record.get('source_url') != source_url(repo, provider):
                raise ValueError('Optional signal source identity mismatch')
            if record.get('status') not in STATUSES or record.get('fetch_status') not in FETCH_STATUSES:
                raise ValueError('Invalid optional signal status')
            for key in ('checked_at', 'last_success_at', 'retry_after'):
                if record.get(key) is not None:
                    timestamp(record[key])
            for key in ('etag', 'error'):
                if record.get(key) is not None:
                    text(record[key], key)
            code = record.get('http_status')
            if code is not None and (type(code) is not int or not 100 <= code <= 599):
                raise ValueError('Invalid HTTP status')
            if record.get('checked_at'):
                precision(record['checked_at'], record.get('check_time_precision', 'second'))
            if record.get('last_success_at'):
                precision(record['last_success_at'], record.get('success_time_precision', 'second'))
            good = record.get('last_good')
            if good is not None:
                validate_good(good, repo, provider)
                if not record.get('last_success_at') or not record.get('checked_at'):
                    raise ValueError('Missing last-good collection time')
                if not timestamp(good['fetched_at']) <= timestamp(record['last_success_at']) <= timestamp(record['checked_at']):
                    raise ValueError('Inconsistent last-good collection time')
            elif record.get('last_success_at') is not None or record.get('fetch_status') in {'ok', 'not_modified'}:
                raise ValueError('Successful signal has no last-good value')
            if record.get('checked_at') and timestamp(record['checked_at']) > timestamp(at):
                raise ValueError('Signal checked after snapshot')
            if record['status'] != effective_status(record, provider, at):
                raise ValueError('Signal availability status is inconsistent')
    return document


def load_optional(path):
    path = Path(path)
    if not path.exists():
        return None
    return validate_snapshot(json.loads(path.read_text(encoding='utf-8')))


def for_repository(document, repo):
    if document is None or repo not in document['repositories']:
        return None
    return deepcopy(document['repositories'][repo])
