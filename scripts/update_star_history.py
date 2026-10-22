#!/usr/bin/env python3
"""Cache aggregate GitHub star history; renderers never make network requests.

Only GET /repos/{owner}/{repo}/stargazers/history is queried. No individual
stargazer records are requested or stored. Eligibility is configured in
star_history_projects.json; the default selects every canonical GitHub
repository from README.source.md.

Default limits are 16 HTTP attempts per UTC day and four repositories per run.
Successful windows become due after 14 days and at month rollover. Retries count
against the persisted daily budget; failed attempts rotate behind other work.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from update_hn import window

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / 'data/star_history.json'
PROJECTS_PATH = ROOT / 'data/star_history_projects.json'
METADATA_PATH = ROOT / 'data/github_metrics.json'
DOCUMENTATION_URL = 'https://docs.github.com/en/rest/activity/starring#get-repository-star-history'
API = 'https://api.github.com/repos/'
API_VERSION = '2026-03-10'
PER_PAGE, DAY, WEEK = 30, 86400, 7 * 86400
DEFAULT_REQUEST_BUDGET, DEFAULT_MAX_REPOSITORIES, REFRESH_DAYS = 16, 4, 14
BOUNDARY_NOTE = ('Monthly buckets assign each source daily bin by its week timestamp plus day offset; '
                 'GitHub week/day boundaries may differ from UTC, so month-boundary attribution is approximate.')
METRIC = ('Stars retained on the repository at fetch time, grouped by the month their stars were created. '
          'Removed stars are absent and past buckets can change.')
REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
SHA = re.compile(r'[0-9a-f]{40}')
# Reviewed 2026-10-16: the old GitHub API path redirects to repository ID
# 50994619, and /repos/openremote/core reports that same ID. See CONTRIBUTING.
# This changes only the aggregate endpoint, never the catalog/cache identity.
# Do not learn aliases from a response or follow redirects automatically.
REVIEWED_REPOSITORY_RENAMES = {
    'openremote/openremote': 'openremote/core',
    # Reviewed 2026-10-17: both API identities resolve to repository 1391454845.
    'openomsi-project/openomsi': 'openomsi-org/openomsi',
    # Reviewed 2026-10-18: both API identities resolve to repository 1409342562.
    'gptchatly/openbrender': 'gptchatly/drawplotia',
    # Reviewed 2026-10-19: both API identities resolve to repository 1412123384.
    'sophontrace/opennex': 'sophontrace/openlnku',
    # Reviewed 2026-10-19: both API identities resolve to repository 1414588015.
    'hzdavy/openmijia': 'hzdavy/openmexia',
    # Reviewed 2026-10-20: both API identities resolve to repository 1413392799.
    'twilightduck/openwhisper': 'twilightduck/openquill',
    # Reviewed 2026-10-20: both API identities resolve to repository 1409520720.
    'shoemoney/openskitch': 'shoemoney/opensnap',
}


class HistoryError(RuntimeError):
    """A failed or incomplete history must not replace last_good."""
    def __init__(self, message, status='partial', halt=False):
        super().__init__(message)
        self.status, self.halt = status, halt


class BudgetExhausted(HistoryError):
    def __init__(self):
        super().__init__('Daily star-history request budget exhausted', 'deferred', True)


class NoRedirect(HTTPRedirectHandler):
    # A rename must be reviewed. Never leak a credential or remap identities.
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class RequestBudget:
    def __init__(self, limit=DEFAULT_REQUEST_BUDGET, used=0, paused_reason=None, checkpoint=None):
        if type(limit) is not int or not 0 <= limit <= 64 or type(used) is not int or used < 0:
            raise ValueError('Request budget must be 0–64 attempts; used must be nonnegative')
        self.limit, self.used, self.paused_reason = limit, used, paused_reason
        self.checkpoint = checkpoint

    @property
    def remaining(self):
        return 0 if self.paused_reason else max(0, self.limit - self.used)

    def consume(self):
        if self.paused_reason:
            raise HistoryError(self.paused_reason, 'deferred', True)
        if not self.remaining:
            raise BudgetExhausted()
        self.used += 1
        if self.checkpoint:
            self.checkpoint(self)

    def pause(self, reason):
        self.paused_reason = reason
        if self.checkpoint:
            self.checkpoint(self)


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError('Expected an ISO timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return result.astimezone(timezone.utc)


def normalize_repo(value):
    if not isinstance(value, str) or REPOSITORY.fullmatch(value) is None:
        raise ValueError('Expected owner/repository identity')
    if any(part in {'.', '..'} for part in value.split('/')):
        raise ValueError('Invalid repository identity')
    return value.lower()


def history_source_url(repo):
    repo = normalize_repo(repo)
    return API + REVIEWED_REPOSITORY_RENAMES.get(repo, repo) + '/stargazers/history'


def accepted_history_sources(repo):
    """Keep original evidence valid without rewriting its historical URLs."""
    repo = normalize_repo(repo)
    return {API + repo + '/stargazers/history', history_source_url(repo)}


def repo_from_url(value):
    """Never infer a repository from an unrelated host or nested GitHub URL."""
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com'
                or parsed.query or parsed.fragment):
            return None
        if re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', parsed.path) is None:
            return None
        return normalize_repo(parsed.path.removeprefix('/').removesuffix('/'))
    except ValueError:
        return None


def validate_projects(document):
    if not isinstance(document, dict) or document.get('schema_version') != 1:
        raise ValueError('Invalid star-history project schema')
    projects, seen = document.get('projects'), set()
    if not isinstance(projects, list):
        raise ValueError('Expected curated projects list')
    normalized = []
    for entry in projects:
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str) or not entry['name'].strip():
            raise ValueError('Expected project name')
        repo = normalize_repo(entry.get('repo'))
        if repo_from_url(entry.get('readme_url')) != repo:
            raise ValueError('Star-history GitHub repository identity mismatch: ' + repo)
        if repo in seen:
            raise ValueError('Duplicate star-history repository: ' + repo)
        seen.add(repo)
        normalized.append({'repo': repo, 'name': entry['name'], 'readme_url': entry['readme_url']})
    return normalized


def load_projects(document, source):
    """Schema 2 derives identities from the source; schema 1 remains explicit."""
    if isinstance(document, dict) and document.get('schema_version') == 1:
        return validate_projects(document)
    if document != {'schema_version': 2, 'scope': 'catalog_github'}:
        raise ValueError('Invalid star-history eligibility configuration')
    # Import lazily: build_catalog also imports the offline history presenter.
    from build_catalog import canonical_url
    from render_readme import ENTRY, validate_source
    validate_source(source)
    projects = {}
    for line in source.splitlines():
        match = ENTRY.fullmatch(line)
        if match is None:
            continue
        name, url, _ = match.groups()
        url = canonical_url(url)
        repo = repo_from_url(url)
        if repo is None:
            continue
        project = {'name': name, 'repo': repo, 'readme_url': url}
        if repo in projects and projects[repo] != project:
            raise ValueError('Conflicting catalog history identity: ' + repo)
        projects[repo] = project
    return validate_projects({'schema_version': 1, 'projects': list(projects.values())})


def priority_key(project, records, metadata):
    """Unseen first by stars; attempted work rotates oldest first, stars break ties."""
    record = records.get(project['repo'], {})
    checked = record.get('checked_at')
    # Compare timestamps rather than their textual offsets.
    attempted_at = parse_time(checked).timestamp() if checked else float('-inf')
    stars = (metadata or {}).get('repositories', {}).get(project['repo'], {}).get('stargazers_count')
    known = type(stars) is int and stars >= 0
    return (attempted_at, not known, -stars if known else 0, project['repo'])


def validate_weeks(rows, previous=None, now=None):
    """Check pagination continuity, including a possible clock-offset transition.

    Calendar-week offsets can change; allow at most two hours around seven days,
    without assuming that the source's Sunday starts at UTC midnight.
    """
    if not isinstance(rows, list) or len(rows) > PER_PAGE:
        raise HistoryError('Expected at most 30 aggregate weeks per page')
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            raise HistoryError('Invalid weekly aggregate')
        week, total, days = row.get('week'), row.get('total'), row.get('days')
        if (type(week) is not int or week < 0 or type(total) is not int or total < 0
                or not isinstance(days, list) or len(days) != 7
                or any(type(n) is not int or n < 0 for n in days) or sum(days) != total):
            raise HistoryError('Invalid weekly timestamp, total, or seven-day counts')
        if now is not None and week > int(now.timestamp()):
            raise HistoryError('Future weekly aggregate')
        if previous is not None:
            interval = previous - week
            if not WEEK - 7200 <= interval <= WEEK + 7200:
                raise HistoryError('Duplicate, unordered, or missing week in aggregate history')
        clean.append({'week': week, 'total': total, 'days': list(days)})
        previous = week
    return clean


@lru_cache(maxsize=None)
def _utc_month(day_number):
    return datetime.fromtimestamp(day_number * DAY, timezone.utc).strftime('%Y-%m')


def monthly_counts(weeks, months):
    counts = dict.fromkeys(months, 0)
    for row in weeks:
        for day, count in enumerate(row['days']):
            # The UTC month depends only on the UTC day, shared across histories.
            month = _utc_month((row['week'] + day * DAY) // DAY)
            if month in counts:
                counts[month] += count
    return list(counts.values())


def request_page(url, token, budget, opener=None, sleeper=time.sleep):
    """At most two attempts, both budgeted. Never log headers or token values."""
    opener = opener or build_opener(NoRedirect).open
    if not re.fullmatch(r'https://api\.github\.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/stargazers/history\?per_page=30&page=[1-9][0-9]*', url):
        raise ValueError('Only aggregate star-history API URLs are allowed')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': API_VERSION,
               'User-Agent': 'awesome-open-star-history/1.0'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    for attempt in range(2):
        budget.consume()
        try:
            with opener(Request(url, headers=headers), timeout=30) as response:
                remaining = response.headers.get('X-RateLimit-Remaining')
                if remaining is not None:
                    try:
                        if int(remaining) <= 20:
                            budget.pause('GitHub API rate-limit reserve reached')
                    except (ValueError, TypeError):
                        raise HistoryError('Invalid GitHub rate-limit header', 'unavailable', True)
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise HistoryError('Aggregate history response exceeds size limit')
                return json.loads(body)
        except HTTPError as error:
            # A permission or rate-limit response must not trigger a retry storm.
            if error.code in {403, 429}:
                budget.pause('GitHub history HTTP ' + str(error.code))
                raise HistoryError('GitHub history HTTP ' + str(error.code), 'unavailable', True) from error
            if error.code not in {500, 502, 503, 504} or attempt == 1:
                raise HistoryError('GitHub history HTTP ' + str(error.code), 'unavailable') from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt == 1:
                raise HistoryError('GitHub history request failed', 'unavailable') from error
        except (ValueError, UnicodeDecodeError) as error:
            raise HistoryError('GitHub returned invalid aggregate JSON') from error
        sleeper(2 ** (attempt + 1))


def collect_repository(repo, now=None, getter=None, token=None, budget=None, created_at=None, source_sha=None):
    """Return a full window or raise; callers never receive padded partial data.

    `getter(url)` is a test/collection seam returning one aggregate page. It is
    also charged one request per call, so injected transports cannot bypass the
    budget. A creation date comes from the existing metadata cache, not another
    network request. Terminal pages must reach that known creation week; when
    metadata is absent a terminal page alone cannot justify zero padding.
    """
    repo = normalize_repo(repo)
    now, budget = now or utc_now(), budget or RequestBudget()
    start, end, months = window(now)
    created = parse_time(created_at) if created_at else None
    if created and created > now:
        raise HistoryError('Repository creation timestamp is in the future')
    rows, sources, terminal, creation_reached = [], [], None, False
    for page in range(1, 101):
        url = history_source_url(repo) + '?' + urlencode({'per_page': PER_PAGE, 'page': page})
        if getter is None:
            payload = request_page(url, token, budget)
        else:
            budget.consume()
            payload = getter(url)
        sources.append(url)
        batch = validate_weeks(payload, rows[-1]['week'] if rows else None, now)
        rows.extend(batch)
        if len(batch) < PER_PAGE:
            terminal = page
            if rows:
                oldest = rows[-1]['week']
                # One source-day tolerance for unspecified source boundary zone.
                creation_reached = bool(created and
                    oldest - DAY <= created.timestamp() < oldest + WEEK + DAY)
                if not creation_reached and oldest > start.timestamp():
                    raise HistoryError('Terminal page stopped before the known repository creation week' if created
                                       else 'Terminal page needs repository creation metadata to establish coverage')
            else:
                # Empty history alone cannot prove zero history for an old repo.
                creation_reached = bool(created and created >= end)
                if not creation_reached:
                    raise HistoryError('Empty history cannot establish complete-window coverage')
        if rows and rows[0]['week'] + WEEK < end.timestamp():
            raise HistoryError('Aggregate history does not cover the end of the requested window')
        old_boundary_reached = bool(rows and rows[-1]['week'] <= start.timestamp())
        if old_boundary_reached or (terminal is not None and creation_reached):
            break
        if terminal is not None:
            raise HistoryError('Terminal history has incomplete coverage')
    else:
        raise HistoryError('Aggregate history exceeded the endpoint page limit')
    return {
        'months': months, 'monthly_counts': monthly_counts(rows, months),
        'window_start': start.isoformat(), 'window_end_exclusive': end.isoformat(),
        'fetched_at': now.isoformat(), 'source_sha': source_sha,
        'source_boundary_note': BOUNDARY_NOTE, 'weeks': rows, 'source_urls': sources,
        'coverage': {'oldest_week': rows[-1]['week'] if rows else None,
                     'newest_week': rows[0]['week'] if rows else None,
                     'terminal_page': terminal, 'creation_week_reached': creation_reached,
                     'repository_created_at': created.isoformat() if created else None},
    }


def validate_cache(document):
    if not isinstance(document, dict) or document.get('schema_version') != 1 or not isinstance(document.get('repositories'), dict):
        raise ValueError('Invalid star-history cache schema')
    budget = document.get('budget', {})
    if budget:
        parse_time(budget['utc_date'] + 'T00:00:00+00:00')
        RequestBudget(budget['limit'], budget['requests_used'])
    report = document.get('selection_report')
    if report is not None:
        keys = {'eligible_repositories', 'due_repositories', 'attempted_repositories', 'unattempted_repositories'}
        if (not isinstance(report, dict) or set(report) != keys
                or any(type(n) is not int or n < 0 for n in report.values())
                or report['attempted_repositories'] > report['due_repositories']
                or report['due_repositories'] > report['eligible_repositories']
                or report['unattempted_repositories'] > report['eligible_repositories']):
            raise ValueError('Invalid history selection report')
    for repo, record in document['repositories'].items():
        if (normalize_repo(repo) != repo or not isinstance(record, dict) or record.get('repo') != repo
                or repo_from_url(record.get('readme_url')) != repo
                or record.get('status') not in {'ok', 'partial', 'unavailable', 'deferred'}):
            raise ValueError('Invalid star-history cache identity or status: ' + repo)
        if record.get('source_url') not in accepted_history_sources(repo):
            raise ValueError('Cache source URL does not match repository identity')
        if record.get('source_sha') is not None and (not isinstance(record['source_sha'], str) or SHA.fullmatch(record['source_sha']) is None):
            raise ValueError('Invalid cache source revision')
        if record.get('checked_at') is not None:
            parse_time(record['checked_at'])
        good = record.get('last_good')
        if good is None:
            if record['status'] == 'ok':
                raise ValueError('Successful history is missing last_good')
            continue
        if not isinstance(good, dict):
            raise ValueError('Invalid last_good history')
        if good.get('source_sha') is not None and (not isinstance(good['source_sha'], str) or SHA.fullmatch(good['source_sha']) is None):
            raise ValueError('Invalid last-good source revision')
        end = parse_time(good['window_end_exclusive'])
        if parse_time(good['fetched_at']) < end:
            raise ValueError('History window extends beyond its fetch timestamp')
        expected_start, expected_end, months = window(end)
        if end != expected_end or good.get('months') != months or parse_time(good['window_start']) != expected_start:
            raise ValueError('History window does not contain 24 complete months')
        counts = good.get('monthly_counts')
        if not isinstance(counts, list) or len(counts) != 24 or any(type(n) is not int or n < 0 for n in counts):
            raise ValueError('Expected 24 nonnegative monthly counts')
        rows, previous = good.get('weeks'), None
        if not isinstance(rows, list):
            raise ValueError('Missing aggregate evidence')
        # Validation is paged only to reuse the source-response size constraint.
        for offset in range(0, len(rows), PER_PAGE):
            batch = validate_weeks(rows[offset:offset + PER_PAGE], previous, parse_time(good['fetched_at']))
            previous = batch[-1]['week']
        if monthly_counts(rows, months) != counts:
            raise ValueError('Monthly counts do not match aggregate evidence')
        coverage = good.get('coverage')
        if not isinstance(coverage, dict) or type(coverage.get('creation_week_reached')) is not bool:
            raise ValueError('Missing complete-window coverage proof')
        terminal = coverage.get('terminal_page')
        if terminal is not None and (type(terminal) is not int or not 1 <= terminal <= 100):
            raise ValueError('Invalid terminal page')
        if coverage.get('oldest_week') != (rows[-1]['week'] if rows else None) or coverage.get('newest_week') != (rows[0]['week'] if rows else None):
            raise ValueError('Coverage bounds do not match raw aggregate evidence')
        if rows and rows[0]['week'] + WEEK < end.timestamp():
            raise ValueError('History does not cover the last complete month')
        if not (rows and rows[-1]['week'] <= expected_start.timestamp()):
            created_at = coverage.get('repository_created_at')
            if terminal is None or not coverage['creation_week_reached'] or not created_at:
                raise ValueError('History does not cover the first complete month')
            created = parse_time(created_at)
            fetched = parse_time(good['fetched_at'])
            if created > fetched:
                raise ValueError('Repository creation is in the future')
            if rows:
                if not rows[-1]['week'] - DAY <= created.timestamp() < rows[-1]['week'] + WEEK + DAY:
                    raise ValueError('Terminal history does not reach repository creation')
            elif created < end:
                raise ValueError('Empty history cannot prove complete-window zeros')
        source_urls = good.get('source_urls')
        if (not isinstance(source_urls, list) or not 1 <= len(source_urls) <= 100
                or not any(source_urls == [
                    source + '?' + urlencode({'per_page': PER_PAGE, 'page': page})
                    for page in range(1, len(source_urls) + 1)]
                    for source in accepted_history_sources(repo))):
            raise ValueError('History source URLs do not match repository identity')
        if source_urls[0].split('?')[0] != record['source_url']:
            raise ValueError('History source URL differs from its last-good evidence')
        if terminal is not None:
            if terminal != len(source_urls) or not (terminal - 1) * PER_PAGE <= len(rows) < terminal * PER_PAGE:
                raise ValueError('Terminal page does not match stored aggregate count')
        elif len(rows) != len(source_urls) * PER_PAGE:
            raise ValueError('Nonterminal pages must contain complete weekly batches')
    return document


def needs_refresh(record, now, months, force=False):
    if not record:
        return True
    # Failed attempts retry on the next UTC date, rather than every publisher run.
    checked = parse_time(record['checked_at']) if record.get('checked_at') else None
    if not force and checked and checked.date() == now.date() and record.get('status') != 'ok':
        return False
    good = record.get('last_good')
    return (force or not good or good.get('months') != months
            or now - parse_time(good['fetched_at']) >= timedelta(days=REFRESH_DAYS)
            or record.get('status') != 'ok')


def refresh(projects, existing=None, metadata=None, now=None, getter=None, token=None,
            request_budget=DEFAULT_REQUEST_BUDGET, max_repositories=DEFAULT_MAX_REPOSITORIES,
            source_sha=None, force=False, invocation_budget_file=None, retain=None):
    now = now or utc_now()
    if source_sha is not None and (not isinstance(source_sha, str) or SHA.fullmatch(source_sha) is None):
        raise ValueError('Expected a full lowercase source SHA')
    if type(max_repositories) is not int or not 1 <= max_repositories <= 16:
        raise ValueError('Expected 1–16 repositories per run')
    projects = validate_projects({'schema_version': 1, 'projects': projects})
    existing = validate_cache(existing) if existing is not None else {'schema_version': 1, 'repositories': {}}
    old_budget = existing.get('budget', {})
    used = old_budget.get('requests_used', 0) if old_budget.get('utc_date') == now.date().isoformat() else 0
    paused = old_budget.get('paused_reason') if old_budget.get('utc_date') == now.date().isoformat() else None
    checkpoint = None
    if invocation_budget_file is not None:
        path = Path(invocation_budget_file)
        if path.exists() and path.stat().st_size:
            invocation = json.loads(path.read_text(encoding='utf-8'))
            if invocation.get('utc_date') == now.date().isoformat():
                RequestBudget(invocation['limit'], invocation['requests_used'])
                used = max(used, invocation['requests_used'])
                paused = paused or invocation.get('paused_reason')
        def checkpoint(current):
            state = {'utc_date': now.date().isoformat(), 'requests_used': current.used,
                     'limit': current.limit, 'paused_reason': current.paused_reason}
            temporary = path.with_suffix(path.suffix + '.tmp')
            temporary.write_text(json.dumps(state) + '\n', encoding='utf-8')
            temporary.replace(path)
    budget = RequestBudget(request_budget, used, paused, checkpoint)
    eligible = {p['repo'] for p in projects}
    records = {repo: deepcopy(record) for repo, record in existing['repositories'].items() if repo in eligible}
    # Removing a curated identity also removes it from the published cache.
    due = [p for p in projects if needs_refresh(records.get(p['repo']), now, window(now)[2], force)]
    due.sort(key=lambda p: priority_key(p, records, metadata))
    attempted = 0
    for project in due:
        if attempted >= max_repositories or not budget.remaining:
            break
        repo = project['repo']
        prior = records.get(repo, {})
        record = {**prior, **project, 'checked_at': now.isoformat(), 'source_sha': source_sha,
                  'source_url': prior['source_url'] if prior.get('last_good') else history_source_url(repo)}
        record.pop('error', None)
        attempted += 1
        try:
            good = collect_repository(
                repo, now, getter, token, budget,
                (metadata or {}).get('repositories', {}).get(repo, {}).get('created_at'), source_sha)
        except (HistoryError, ValueError, OSError, TimeoutError) as error:
            # Store bounded, non-sensitive diagnostics rather than arbitrary
            # response bodies or transport exception strings that may hold URLs.
            status = error.status if isinstance(error, HistoryError) else 'unavailable'
            record['status'] = status
            record['error'] = str(error) if isinstance(error, HistoryError) else 'History collection failed'
            records[repo] = record
            if getattr(error, 'halt', False):
                break
        else:
            completed = {**record, 'source_url': history_source_url(repo), 'last_good': good, 'status': 'ok'}
            # Retention failures are local errors: never swallow them as an
            # optional upstream outage or replace last_good before archiving.
            if retain:
                retain(repo, completed)
            record = completed
        records[repo] = record
    result = {
        'schema_version': 1, 'metric': METRIC, 'source_boundary_note': BOUNDARY_NOTE,
        'documentation_url': DOCUMENTATION_URL, 'updated_at': now.isoformat(), 'source_sha': source_sha,
        'budget': {'utc_date': now.date().isoformat(), 'requests_used': budget.used, 'limit': budget.limit, 'paused_reason': budget.paused_reason},
        'refresh_policy': {'successful_refresh_days': REFRESH_DAYS, 'max_repositories_per_run': max_repositories,
                           'month_rollover_refresh': True,
                           'selection': 'unseen-stars-desc-then-oldest-attempt-stars-desc'},
        'selection_report': {'eligible_repositories': len(projects), 'due_repositories': len(due),
                             'attempted_repositories': attempted,
                             'unattempted_repositories': sum(not records.get(p['repo'], {}).get('checked_at') for p in projects)},
        'repositories': records,
    }
    validate_cache(result)
    return result


def source_revision():
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def write_cache(path, document):
    validate_cache(document)
    path = Path(path)
    content = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') == content:
        return
    temporary = path.with_suffix('.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Make all histories due before their 14-day interval; daily budget and fair rotation still apply')
    parser.add_argument('--request-budget', type=int, default=DEFAULT_REQUEST_BUDGET)
    parser.add_argument('--max-repositories', type=int, default=DEFAULT_MAX_REPOSITORIES)
    parser.add_argument('--source-sha')
    parser.add_argument('--invocation-budget-file', type=Path, help='Persist every HTTP attempt across publisher worktree retries')
    parser.add_argument('--cache', type=Path, default=CACHE_PATH)
    parser.add_argument('--archive', type=Path, help='Observation archive (defaults beside the cache)')
    parser.add_argument('--projects', type=Path, default=PROJECTS_PATH)
    parser.add_argument('--metadata', type=Path, default=METADATA_PATH)
    parser.add_argument('--source', type=Path, default=ROOT / 'README.source.md')
    args = parser.parse_args()
    projects = load_projects(json.loads(args.projects.read_text(encoding='utf-8')), args.source.read_text(encoding='utf-8'))
    existing = json.loads(args.cache.read_text(encoding='utf-8')) if args.cache.exists() else None
    metadata = json.loads(args.metadata.read_text(encoding='utf-8')) if args.metadata.exists() else None
    import chart_observations as observations
    archive_path = args.archive or args.cache.with_name('chart_observations.json')
    archive = observations.load(archive_path)
    if existing is not None:
        observations.add_stars(archive, existing)
    observations.save(archive_path, archive)
    def retain(repo, record):
        observations.add_stars(archive, {'schema_version': 1, 'repositories': {repo: record}})
        observations.save(archive_path, archive)
    result = refresh(projects, existing, metadata, token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN'),
                     request_budget=args.request_budget, max_repositories=args.max_repositories,
                     source_sha=args.source_sha or source_revision(), force=args.refresh,
                     invocation_budget_file=args.invocation_budget_file, retain=retain)
    write_cache(args.cache, result)
    records = result['repositories']
    print(f"Star history: {sum(r['status'] == 'ok' for r in records.values())}/{len(records)} complete; "
          f"{result['budget']['requests_used']}/{result['budget']['limit']} HTTP attempts used today; "
          f"{len(projects)} eligible, {result['selection_report']['unattempted_repositories']} not yet attempted")
    for project in projects:
        record = records.get(project['repo'], {})
        if record.get('error'):
            print(project['repo'] + ': ' + record['error'] + '; last-good evidence retained if available')


if __name__ == '__main__':
    main()
