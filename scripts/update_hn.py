#!/usr/bin/env python3
"""Auditable HN submission counts; stdlib only. Cached render is network-free.

Run a bounded catalog queue via daily CI: python3 scripts/update_hn.py. Force fresh collection
with --refresh; render cached SVGs/README with render_readme.py. Story
submission dates, NOT current points/comments, supply all historical values.
"""
import argparse
from datetime import datetime, timedelta, timezone
import html
import hashlib
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / 'data/hn_evidence.json'
PROJECTS_PATH = ROOT / 'data/hn_projects.json'
SOURCE_PATH = ROOT / 'README.source.md'
METADATA_PATH = ROOT / 'data/github_metrics.json'
DEFAULT_REQUESTS, DEFAULT_PROJECTS, DEFAULT_SECONDS = 160, 50, 300
LANES = ('new', 'refresh', 'continuation')
PROJECT_SHARES = {'new': 20, 'refresh': 25, 'continuation': 5}
REQUEST_SHARES = {'new': 64, 'refresh': 80, 'continuation': 16}
PROJECT_REQUESTS = 24
REFRESH_DAYS = 30
API = 'https://hn.algolia.com/api/v1/search_by_date'
MIN_STORIES, MIN_MONTHS = 6, 3
COLLECTED_KEYS = {'monthly_counts', 'eligible', 'story_count', 'active_months',
                  'stories', 'excluded_candidates', 'query_sources', 'search_url'}
MARKER = re.compile(r'(?:<br\s*/?>)?<!-- HN:START -->.*?<!-- HN:END -->', re.S)


def window(now=None):
    now = now or datetime.now(timezone.utc)
    end = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    start = end.replace(year=end.year - 2)
    months = [f'{(start.year * 12 + start.month - 1 + i) // 12:04d}-{(start.month - 1 + i) % 12 + 1:02d}' for i in range(24)]
    return start, end, months


def identity_reason(story, project):
    """Trust parsed hosts/repo path boundaries, never substring domains."""
    parsed = urlsplit(story.get('url') or '')
    host = (parsed.hostname or '').lower().removeprefix('www.')
    title = story.get('title') or ''
    title_match = any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', title, re.I) for alias in project['title_aliases'])
    excluded_context = project.get('other_project_pattern')
    if excluded_context and re.search(excluded_context, title + ' ' + parsed.path, re.I) and not title_match:
        return None
    for official in project.get('exact_urls', []):
        try:
            exact_match = canonical_url(story.get('url') or '') == canonical_url(official)
        except ValueError:
            exact_match = False
        if exact_match:
            return 'reviewed/catalog exact URL: ' + official
    for domain in project['domains']:
        if host == domain or host.endswith('.' + domain):
            return 'official domain: ' + domain
    path = parsed.path.lower().rstrip('/')
    for repo in project.get('excluded_repositories', []):
        prefix = '/' + repo.lower()
        if host == 'github.com' and (path == prefix or path.startswith(prefix + '/')):
            return None
    for repo in project['repositories']:
        prefix = '/' + repo.lower()
        if host == 'github.com' and (path == prefix or path.startswith(prefix + '/')):
            return 'repository: ' + repo
    title = story.get('title') or ''
    for alias in project['title_aliases']:
        if re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', title, re.I):
            context = project.get('title_context_pattern')
            if not context or re.search(context, title, re.I):
                return 'title alias: ' + alias + ('; required context matched' if context else '')
    return None


def get_json(url):
    for attempt in range(4):
        try:
            request = Request(url, headers={'User-Agent': 'awesome-open-hn-history/1.0'})
            with urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def fetch_query(query, start, end, getter=get_json):
    """Page every query; split time ranges before Algolia's 1,000-hit cap."""
    hits, sources = [], []
    page = 0
    expected_totals = None
    seen_ids = set()
    while True:
        url = API + '?' + urlencode({'query': query, 'tags': 'story', 'restrictSearchableAttributes': 'title,url', 'typoTolerance': 'false', 'numericFilters': f'created_at_i>={start},created_at_i<{end}', 'hitsPerPage': 100, 'page': page})
        data = getter(url)
        sources.append(url)
        totals = (data.get('nbHits'), data.get('nbPages'))
        if expected_totals is not None and totals != expected_totals:
            raise PaginationChanged('Algolia results changed during pagination')
        expected_totals = totals
        if page == 0 and data.get('nbHits', 0) >= 1000:
            if end - start <= 1:
                raise UpstreamFailure('Cannot enumerate this one-second interval completely')
            mid = (start + end) // 2
            left, ls = fetch_query(query, start, mid, getter)
            right, rs = fetch_query(query, mid, end, getter)
            return left + right, sources + ls + rs
        ids = [str(hit['objectID']) for hit in data['hits']]
        if len(set(ids)) != len(ids) or seen_ids.intersection(ids):
            raise PaginationChanged('Duplicate story across Algolia pages')
        seen_ids.update(ids)
        hits.extend(data['hits'])
        page += 1
        if page >= data.get('nbPages', 1):
            return hits, sources


def collect_project(project, start, end, months, getter=None):
    accepted, rejected, sources = {}, {}, []
    for query in project['queries']:
        args = (query, int(start.timestamp()), int(end.timestamp()))
        hits, urls = fetch_query(*args, getter=getter) if getter else fetch_query(*args)
        sources.extend(urls)
        for hit in hits:
            sid = str(hit['objectID'])
            stamp = int(hit['created_at_i'])
            if not int(start.timestamp()) <= stamp < int(end.timestamp()):
                continue
            reason = identity_reason(hit, project)
            record = {'id': sid, 'title': hit.get('title') or '', 'url': hit.get('url') or '', 'created_at': datetime.fromtimestamp(stamp, timezone.utc).isoformat(), 'month': datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m'), 'hn_url': 'https://news.ycombinator.com/item?id=' + sid, 'source_url': 'https://hn.algolia.com/api/v1/items/' + sid}
            if reason:
                record['reason'] = reason
                accepted[sid] = record
                rejected.pop(sid, None)
            elif sid not in accepted:
                record['reason'] = 'Excluded: no exact official host/repository or permitted title alias/context'
                rejected[sid] = record
    stories = sorted(accepted.values(), key=lambda item: (item['created_at'], int(item['id'])))
    counts = [sum(story['month'] == month for story in stories) for month in months]
    eligible = len(stories) >= MIN_STORIES and sum(value > 0 for value in counts) >= MIN_MONTHS
    return {**project, 'monthly_counts': counts, 'eligible': eligible, 'story_count': len(stories), 'active_months': sum(value > 0 for value in counts), 'stories': stories, 'excluded_candidates': sorted(rejected.values(), key=lambda item: int(item['id'])), 'query_sources': sorted(set(sources)), 'search_url': 'https://hn.algolia.com/?' + urlencode({'q': project['title_aliases'][0] if project['title_aliases'] else project['queries'][0], 'type': 'story', 'dateRange': 'custom', 'dateStart': int(start.timestamp()), 'dateEnd': int(end.timestamp()) - 1, 'sort': 'byDate'})}


def canonical_url(url):
    # Share catalog identity rules, including case-sensitive non-GitHub paths.
    from build_catalog import canonical_url as catalog_url
    return catalog_url(url)


def catalog_projects(source, reviewed):
    """Every catalog identity enters; aliases/domain expansion remain reviewed."""
    # Lazy import avoids render_readme's import of this module becoming circular.
    from render_readme import ENTRY, validate_source
    validate_source(source)
    overrides = {}
    slugs = set()
    for project in reviewed:
        key = canonical_url(project['readme_url'])
        if key in overrides or project['slug'] in slugs:
            raise ValueError('Duplicate reviewed HN identity')
        for field in ('queries', 'domains', 'repositories', 'title_aliases'):
            if not isinstance(project.get(field), list) or any(not isinstance(v, str) or not v for v in project[field]):
                raise ValueError('Invalid reviewed HN ' + field)
        if not project['queries']:
            raise ValueError('HN identity needs discovery queries')
        overrides[key] = project
        slugs.add(project['slug'])
    result = {}
    for line in source.splitlines():
        match = ENTRY.fullmatch(line)
        if not match:
            continue
        name, url = match.group(1, 2)
        key = canonical_url(url)
        if key in result:
            continue
        if key in overrides:
            result[key] = overrides[key]
            continue
        parsed = urlsplit(url)
        repo = (parsed.path.strip('/') if parsed.hostname == 'github.com'
                and re.fullmatch(r'/[\w.-]+/[\w.-]+/?', parsed.path) else None)
        # A website can be shared infrastructure: never infer host ownership,
        # aliases, repo redirects or GitHub identities from a marketing URL.
        result[key] = {
            'name': name, 'slug': 'catalog-' + hashlib.sha256(key.encode()).hexdigest()[:16],
            'readme_url': url, 'repositories': [repo] if repo else [],
            'domains': [], 'title_aliases': [], 'exact_urls': [] if repo else [url],
            'queries': ['github.com/' + repo if repo else url.removeprefix(parsed.scheme + '://')],
            'identity_sources': [url], 'coverage': 'catalog-url-only',
            'scope_note': 'Only the catalog repository or exact URL is matched. Name aliases and broader official domains require review; this is not comprehensive attention coverage.',
        }
    if len({p['slug'] for p in result.values()}) != len(result):
        raise ValueError('HN asset slug collision')
    return list(result.values())


def identity_key(project):
    return hashlib.sha256(json.dumps(project, sort_keys=True).encode()).hexdigest()


def write_evidence(path, document):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


class Deferred(RuntimeError):
    pass


class UpstreamFailure(RuntimeError):
    pass


class PaginationChanged(UpstreamFailure):
    pass


def validate_response(data):
    if not isinstance(data, dict) or not isinstance(data.get('hits'), list):
        raise UpstreamFailure('Invalid Algolia response')
    if any(type(data.get(k)) is not int or data[k] < 0 for k in ('nbPages', 'nbHits')):
        raise UpstreamFailure('Invalid Algolia pagination')
    if len(data['hits']) > 100 or data['nbPages'] > 1000:
        raise UpstreamFailure('Invalid Algolia page size')
    if data['nbHits'] < 1000 and data['nbPages'] != math.ceil(data['nbHits'] / 100):
        raise UpstreamFailure('Inconsistent Algolia pagination')
    hits = []
    for hit in data['hits']:
        if (not isinstance(hit, dict) or not str(hit.get('objectID', '')).isdigit()
                or type(hit.get('created_at_i')) is not int
                or any(not isinstance(hit.get(k), (str, type(None))) for k in ('title', 'url'))):
            raise UpstreamFailure('Invalid Algolia story')
        hits.append({k: hit.get(k) for k in ('objectID', 'created_at_i', 'title', 'url')})
    # Ignore points, comment counts, bodies and unused response metadata.
    return {'hits': hits, 'nbPages': data['nbPages'], 'nbHits': data['nbHits']}


def fetch_page(url):
    request = Request(url, headers={'User-Agent': 'awesome-open-hn-history/2.0'})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def validate_collection(project, months):
    if (not isinstance(project, dict) or len(months) != 24
            or not all(isinstance(m, str) and re.fullmatch(r'\d{4}-\d{2}', m) for m in months)
            or len(set(months)) != 24):
        raise ValueError('Invalid local HN collection')
    stories = project.get('stories')
    counts = project.get('monthly_counts')
    if (not isinstance(stories, list) or not isinstance(counts, list) or len(counts) != 24
            or any(type(n) is not int or n < 0 for n in counts)):
        raise ValueError('Invalid local HN stories/counts')
    ids = set()
    for story in stories:
        if (not isinstance(story, dict) or not isinstance(story.get('id'), str)
                or not story['id'].isdigit() or story['id'] in ids
                or story.get('month') not in months or not identity_reason(story, project)):
            raise ValueError('Invalid local HN story identity')
        stamp = datetime.fromisoformat(story['created_at'])
        if stamp.tzinfo is None or stamp.astimezone(timezone.utc).strftime('%Y-%m') != story['month']:
            raise ValueError('Invalid local HN story timestamp')
        ids.add(story['id'])
    expected = [sum(s['month'] == month for s in stories) for month in months]
    active = sum(n > 0 for n in expected)
    if (counts != expected or type(project.get('story_count')) is not int
            or project['story_count'] != len(stories) or project.get('active_months') != active
            or type(project.get('eligible')) is not bool
            or project['eligible'] != (len(stories) >= MIN_STORIES and active >= MIN_MONTHS)):
        raise ValueError('Inconsistent local HN collection')


def validate_budget(budget):
    if (not isinstance(budget, dict) or type(budget.get('requests_used')) is not int
            or budget['requests_used'] < 0 or type(budget.get('limit')) is not int
            or not 0 <= budget['limit'] <= 160 or type(budget.get('paused')) is not bool
            or not isinstance(budget.get('utc_date'), str)):
        raise ValueError('Invalid HN budget')
    datetime.strptime(budget['utc_date'], '%Y-%m-%d')
    if 'projects_used' in budget:
        if (type(budget['projects_used']) is not int or budget['projects_used'] < 0
                or type(budget.get('project_limit')) is not int or not 1 <= budget['project_limit'] <= 50
                or not isinstance(budget.get('attempted_urls'), list)
                or not all(isinstance(k, str) for k in budget['attempted_urls'])
                or len(set(budget['attempted_urls'])) != len(budget['attempted_urls'])
                or len(budget['attempted_urls']) > budget['projects_used']):
            raise ValueError('Invalid daily HN project budget')
        for field, total in [('lane_projects', 'projects_used'), ('lane_requests', 'requests_used')]:
            value = budget.get(field)
            if (not isinstance(value, dict) or set(value) != set(LANES)
                    or any(type(n) is not int or n < 0 for n in value.values())
                    or sum(value.values()) > budget[total]):
                raise ValueError('Invalid daily HN lane budget')


def checkpoint_budget(path, budget):
    try:
        write_evidence(path, budget)
    except OSError as error:
        # A broken quota guard is a local publication error, not an optional
        # upstream failure that can be skipped for the next project.
        raise RuntimeError('Cannot checkpoint HN request budget') from error


def validate_queue(existing):
    if not isinstance(existing, dict) or existing.get('schema_version') not in (1, 2):
        raise ValueError('Invalid local HN evidence schema')
    if not isinstance(existing.get('projects'), list) or len(existing.get('months', [])) != 24:
        raise ValueError('Invalid local HN evidence')
    for project in existing['projects']:
        validate_collection(project, existing['months'])
    if existing.get('budget') is not None:
        validate_budget(existing['budget'])
    records = existing.get('queue', {})
    if not isinstance(records, dict):
        raise ValueError('Invalid local HN queue')
    for key, record in records.items():
        if not isinstance(key, str) or not isinstance(record, dict):
            raise ValueError('Invalid HN queue record')
        if record.get('status') not in ('ok', 'deferred', 'unavailable'):
            raise ValueError('Invalid HN queue status')
        if not isinstance(record.get('checked_at'), str) or datetime.fromisoformat(record['checked_at']).tzinfo is None:
            raise ValueError('HN attempt must have a timezone')
        if not isinstance(record.get('pending', {}), dict):
            raise ValueError('Invalid pending HN pages')
        for url, data in record.get('pending', {}).items():
            if not url.startswith(API + '?'):
                raise ValueError('Invalid pending HN source')
            try:
                validate_response(data)
                validate_page(url, data)
            except UpstreamFailure as error:
                raise ValueError('Corrupt pending HN page') from error
        good = record.get('last_good')
        if good:
            if (not isinstance(good, dict) or len(good.get('months', [])) != 24
                    or canonical_url(good['project']['readme_url']) != key):
                raise ValueError('Invalid last-good HN identity/window')
            validate_collection(good['project'], good['months'])
            identity = {k: v for k, v in good['project'].items() if k not in COLLECTED_KEYS}
            if good.get('identity_key') != identity_key(identity):
                raise ValueError('Corrupt last-good HN identity fingerprint')
    return existing


def validate_page(url, data):
    # Capped first pages are split before publishing. Below the cap, every
    # reported hit must fit the requested page; never accept a truncated zero.
    params = parse_qs(urlsplit(url).query)
    page = int(params['page'][0])
    interval = re.fullmatch(r'created_at_i>=(\d+),created_at_i<(\d+)', params['numericFilters'][0])
    if not interval or any(not int(interval[1]) <= hit['created_at_i'] < int(interval[2]) for hit in data['hits']):
        raise UpstreamFailure('Algolia story outside requested interval')
    expected = min(100, max(0, data['nbHits'] - page * 100))
    if data['nbHits'] < 1000 and len(data['hits']) != expected:
        raise UpstreamFailure('Incomplete Algolia page')


def refresh(now=None, *, existing=None, projects=None, metadata=None, getter=None,
            request_budget=DEFAULT_REQUESTS, max_projects=DEFAULT_PROJECTS,
            seconds=DEFAULT_SECONDS, force=False, invocation_budget_file=None,
            checkpoint=None, monotonic=time.monotonic, sleeper=time.sleep):
    live_clock = now is None
    now = now or datetime.now(timezone.utc)
    start, end, months = window(now)
    if (type(request_budget) is not int or not 0 <= request_budget <= 160
            or type(max_projects) is not int or not 1 <= max_projects <= 50
            or not 0 < seconds <= 300):
        raise ValueError('HN limits exceed bounded collection policy')
    if projects is None:
        projects = catalog_projects(SOURCE_PATH.read_text(), json.loads(PROJECTS_PATH.read_text())['projects'])
    if existing is None:
        existing = json.loads(EVIDENCE_PATH.read_text()) if EVIDENCE_PATH.exists() else {
            'schema_version': 1, 'months': months, 'projects': []}
    validate_queue(existing)
    # JSON copy prevents partial mutation of the caller's last-good snapshot.
    records = json.loads(json.dumps(existing.get('queue', {})))
    if not records:
        for project in existing['projects']:
            identity = {k: v for k, v in project.items() if k not in COLLECTED_KEYS}
            records[canonical_url(project['readme_url'])] = {
                'checked_at': existing.get('refreshed_utc_date', now.date().isoformat()) + 'T00:00:00+00:00',
                'status': 'ok', 'last_good': {'months': existing['months'],
                    'identity_key': identity_key(identity), 'project': project},
            }
    identities = {canonical_url(p['readme_url']): p for p in projects}
    records = {k: v for k, v in records.items() if k in identities}
    today = now.date().isoformat()
    budget = {'utc_date': today, 'requests_used': 0, 'limit': request_budget, 'paused': False,
              'projects_used': 0, 'project_limit': max_projects, 'attempted_urls': [],
              'lane_projects': dict.fromkeys(LANES, 0), 'lane_requests': dict.fromkeys(LANES, 0)}
    def merge_budget(prior):
        validate_budget(prior)
        if prior['utc_date'] != today:
            return
        budget['requests_used'] = max(budget['requests_used'], prior['requests_used'])
        budget['paused'] = budget['paused'] or prior['paused']
        # Old request-only guards cannot prove how many project attempts were
        # made. Charge one project per used request conservatively on migration.
        budget['projects_used'] = max(budget['projects_used'], prior.get('projects_used', prior['requests_used']))
        budget['attempted_urls'] = sorted(set(budget['attempted_urls']) | set(prior.get('attempted_urls', [])))
        for field in ('lane_projects', 'lane_requests'):
            for lane in LANES:
                budget[field][lane] = max(budget[field][lane], prior.get(field, {}).get(lane, 0))
    if existing.get('budget'):
        merge_budget(existing['budget'])
    budget_path = Path(invocation_budget_file) if invocation_budget_file else None
    if budget_path and budget_path.exists():
        merge_budget(json.loads(budget_path.read_text()))
    known_today = {key for key, record in records.items()
                   if datetime.fromisoformat(record['checked_at']).astimezone(timezone.utc).date() == now.date()}
    budget['attempted_urls'] = sorted(set(budget['attempted_urls']) | known_today)
    budget['projects_used'] = max(budget['projects_used'], len(budget['attempted_urls']),
                                  sum(budget['lane_projects'].values()))
    budget['requests_used'] = max(budget['requests_used'], sum(budget['lane_requests'].values()))
    # A main-branch retry may discard the evidence but retain its quota guard.
    # Preserve an honest failed-attempt placeholder rather than treating that
    # identity as unseen again tomorrow or inventing the discarded result.
    for key in budget['attempted_urls']:
        if key in identities and key not in known_today:
            record = records.setdefault(key, {})
            record.update(checked_at=now.isoformat(), status='unavailable',
                          error='Earlier invocation attempt has no retained result; retry on a later UTC day')
    validate_budget(budget)
    deadline = monotonic() + seconds
    metadata = metadata if metadata is not None else json.loads(METADATA_PATH.read_text())
    def due(p):
        record = records.get(canonical_url(p['readme_url']), {})
        good = record.get('last_good', {})
        return (force or good.get('months') != months or good.get('identity_key') != identity_key(p)
                or now - datetime.fromisoformat(record.get('checked_at', '1970-01-01T00:00:00+00:00')) >= timedelta(days=REFRESH_DAYS)
                or record.get('status') != 'ok')
    def stars_key(p):
        values = [metadata.get('repositories', {}).get(repo.lower(), {}).get('stargazers_count')
                  for repo in p['repositories']]
        known = [n for n in values if type(n) is int and n >= 0]
        return (not known, -max(known, default=0), canonical_url(p['readme_url']))
    def lane_for(p):
        record = records.get(canonical_url(p['readme_url']), {})
        if (record.get('status') == 'deferred' and record.get('pending')
                and record.get('pending_identity_key') == identity_key(p)
                and record.get('pending_months') == months):
            return 'continuation'
        return 'refresh' if record.get('checked_at') else 'new'
    def priority(p):
        record = records.get(canonical_url(p['readme_url']), {})
        if lane_for(p) == 'new':
            return stars_key(p)
        changed = (record.get('last_good', {}).get('identity_key') not in (None, identity_key(p))
                   and record.get('pending_identity_key') != identity_key(p))
        return (0 if changed else 1, record.get('checked_at', ''), *stars_key(p))
    waiting = [p for p in projects if due(p)]
    queues = {lane: sorted((p for p in waiting if lane_for(p) == lane
                           and canonical_url(p['readme_url']) not in budget['attempted_urls']), key=priority)
              for lane in LANES}
    attempted = 0
    def allowance(lane, kind):
        shares = PROJECT_SHARES if kind == 'projects' else REQUEST_SHARES
        limit = max_projects if kind == 'projects' else request_budget
        # Scale reservations for deliberately smaller test/manual budgets.
        scale = limit / (DEFAULT_PROJECTS if kind == 'projects' else DEFAULT_REQUESTS)
        reserved = 0
        for other in LANES:
            if other == lane or not queues[other]:
                continue
            if kind == 'requests' and allowance(other, 'projects') <= 0:
                continue
            need = max(0, math.floor(shares[other] * scale) - budget['lane_' + kind][other])
            reserved += min(need, len(queues[other])) if kind == 'projects' else need
        return max(0, limit - budget[kind + '_used'] - reserved)
    def day_closed():
        return live_clock and datetime.now(timezone.utc).date() != now.date()
    def selected_projects():
        # Interleave lanes so a short time budget also reaches refresh work.
        # Unused reservations are borrowable only when the other queue is empty.
        while any(queues.values()):
            progressed = False
            for lane in ('continuation', 'new', 'refresh', 'refresh', 'new'):
                if (queues[lane] and allowance(lane, 'projects') > 0
                        and allowance(lane, 'requests') > 0):
                    progressed = True
                    yield lane, queues[lane].pop(0)
            if not progressed:
                break
    def document():
        current = []
        for key, p in identities.items():
            good = records.get(key, {}).get('last_good', {})
            if good.get('months') == months and good.get('identity_key') == identity_key(p):
                current.append(good['project'])
        maximum = max((max(p['monthly_counts']) for p in current if p['eligible']), default=1)
        return {'schema_version': 2, 'window_start': start.isoformat(), 'window_end_exclusive': end.isoformat(),
                'months': months, 'refreshed_utc_date': today,
                'metric': 'Deduplicated HN story submissions per UTC month, regardless of points, comments or sentiment. Search coverage is best-effort and depends on the HN Algolia index; absence is not proof of no discussion.',
                'eligibility': {'minimum_stories': MIN_STORIES, 'minimum_active_months': MIN_MONTHS},
                'shared_monthly_maximum': maximum, 'projects': current, 'queue': records, 'budget': budget,
                'selection_report': {'catalog_projects': len(projects), 'due_projects': len(waiting),
                                     'attempted_projects': attempted, 'current_window_projects': len(current),
                                     'never_attempted_projects': sum(k not in records for k in identities)},
                'refresh_policy': {'successful_refresh_days': REFRESH_DAYS, 'max_projects_per_utc_day': max_projects,
                                   'project_reservations': PROJECT_SHARES, 'request_reservations': REQUEST_SHARES,
                                   'max_requests_per_project_run': PROJECT_REQUESTS, 'max_seconds_per_run': seconds,
                                   'max_seconds_per_project_when_queued': min(90, seconds / 3),
                                   'selection': 'interleaved reserved lanes; new backlog stars descending, unknown last; retries/refreshes and continuations oldest attempt; once per project per UTC day',
                                   'coverage': 'reviewed aliases or conservative catalog URL/repository only'}}
    for lane, project in selected_projects():
        started = monotonic()
        if budget['projects_used'] >= max_projects or budget['paused'] or budget['requests_used'] >= request_budget or started >= deadline or day_closed():
            break
        # Reserve time for other waiting work as well as project/request slots.
        project_deadline = min(deadline, started + min(90, seconds / 3)) if any(queues.values()) else deadline
        key = canonical_url(project['readme_url'])
        prior_record = records.get(key)
        record = json.loads(json.dumps(prior_record or {}))
        records[key] = record
        signature = identity_key(project)
        if record.get('pending_identity_key') != signature or record.get('pending_months') != months:
            record['pending'] = {}
        record.update(pending_identity_key=signature, pending_months=months)
        project_requests = 0
        def bounded_get(url):
            nonlocal project_requests, attempted
            if url in record['pending']:
                return record['pending'][url]
            if (allowance(lane, 'requests') <= 0 or project_requests >= PROJECT_REQUESTS
                    or monotonic() >= project_deadline or day_closed()):
                raise Deferred('Collection budget reached; partial pages retained')
            # Every network attempt counts, including failures. Persist before
            # request so a publisher retry cannot reset the invocation quota.
            if project_requests == 0:
                attempted += 1
                budget['projects_used'] += 1
                budget['lane_projects'][lane] += 1
                budget['attempted_urls'].append(key)
                record['checked_at'] = now.isoformat()
            budget['requests_used'] += 1
            budget['lane_requests'][lane] += 1
            project_requests += 1
            if budget_path:
                checkpoint_budget(budget_path, budget)
            try:
                data = validate_response((getter or fetch_page)(url))
                validate_page(url, data)
            except HTTPError as error:
                if error.code in (429, 403):
                    budget['paused'] = True
                    if budget_path:
                        checkpoint_budget(budget_path, budget)
                raise UpstreamFailure('Algolia HTTP ' + str(error.code)) from error
            finally:
                if getter is None:
                    sleeper(0.5)
            record['pending'][url] = data
            return data
        try:
            collected = collect_project(project, start, end, months, getter=bounded_get)
            record['last_good'] = {'months': months, 'identity_key': signature, 'project': collected,
                                   'collected_at': now.isoformat()}
            record['status'] = 'ok'
            record['pending'] = {}
            record.pop('error', None)
        except Deferred:
            record['status'] = 'deferred'
            record['error'] = 'Incomplete collection; resume saved pages on a later run'
        except PaginationChanged:
            record['status'] = 'unavailable'
            record['pending'] = {}
            record['error'] = 'Pagination changed; discard partial pages and retry later'
        except (UpstreamFailure, URLError, OSError, TimeoutError, ValueError):
            record['status'] = 'unavailable'
            record['error'] = 'Algolia collection failed; prior evidence and partial pages retained'
        if project_requests == 0 and record.get('status') != 'ok':
            if prior_record is None:
                records.pop(key, None)
            else:
                records[key] = prior_record
        if checkpoint:
            checkpoint(document())
    result = document()
    validate_queue(result)
    return result



def svg(project, evidence):
    counts = project['monthly_counts']
    if len(counts) != 24 or any(not isinstance(n, int) or n < 0 for n in counts):
        raise ValueError('Expected exactly 24 nonnegative monthly counts')
    maximum = max(1, evidence['shared_monthly_maximum'])
    title = html.escape(project['name'] + ': HN discussions / 2y')
    desc = html.escape(f"Monthly HN story submissions, {evidence['months'][0]} through {evidence['months'][-1]}; oldest at left. Shared square-root scale: 0–{maximum} stories/month. Counts: " + ', '.join(map(str, counts)) + '. Attention includes critical coverage; not endorsement.')
    bars = []
    for i, count in enumerate(counts):
        height = math.sqrt(count / maximum) * 20
        bars.append(f'<rect x="{i*5}" y="{22-height:.3f}" width="4" height="{height:.3f}" fill="#64748b"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="24" viewBox="0 0 120 24" role="img" aria-labelledby="title desc"><title id="title">{title}</title><desc id="desc">{desc}</desc>' + ''.join(bars) + '</svg>\n'


def decorate_readme(text, evidence=None):
    evidence = evidence if evidence is not None else json.loads(EVIDENCE_PATH.read_text())
    text = MARKER.sub('', text)
    by_url = {canonical_url(p['readme_url']): p for p in evidence['projects'] if p['eligible']}
    pattern = re.compile(r'^(\| (?:\*\*)?\[[^\]]+\]\(([^)]+)\)(?:\*\*)?)(?=\s*\|)', re.M)
    def decorate(match):
        project = by_url.get(canonical_url(match.group(2)))
        if not project:
            return match.group(0)
        image = f"[![HN discussions / 2y](assets/hn/{project['slug']}.svg \"HN discussions / 2y\")]({project['search_url']})"
        return match.group(0) + '<br><!-- HN:START -->' + image + '<!-- HN:END -->'
    return pattern.sub(decorate, text)


def render(evidence, directory=None):
    directory = directory if directory is not None else ROOT / 'assets/hn'
    directory.mkdir(parents=True, exist_ok=True)
    keep = set()
    for project in evidence['projects']:
        if project['eligible']:
            path = directory / (project['slug'] + '.svg')
            path.write_text(svg(project, evidence))
            keep.add(path)
    for path in directory.glob('*.svg'):
        if path not in keep:
            path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Make all projects due; budgets still apply')
    parser.add_argument('--invocation-budget-file', type=Path)
    args = parser.parse_args()
    evidence = refresh(force=args.refresh, invocation_budget_file=args.invocation_budget_file,
                       checkpoint=lambda document: write_evidence(EVIDENCE_PATH, document))
    write_evidence(EVIDENCE_PATH, evidence)
    report = evidence['selection_report']
    print(f"HN history: {sum(p['eligible'] for p in evidence['projects'])} eligible charts; "
          f"{len(evidence['projects'])}/{report['catalog_projects']} current-window collections; "
          f"{report['attempted_projects']} attempted; {evidence['budget']['requests_used']} requests today")


if __name__ == '__main__':
    main()
