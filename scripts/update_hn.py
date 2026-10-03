#!/usr/bin/env python3
"""Auditable HN submission counts; stdlib only. Cached render is network-free.

Run monthly via daily CI: python3 scripts/update_hn.py. Force fresh collection
with --refresh; reproduce checked-in SVGs/README with --render-only. Story
submission dates, NOT current points/comments, supply all historical values.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / 'data/hn_evidence.json'
PROJECTS_PATH = ROOT / 'data/hn_projects.json'
API = 'https://hn.algolia.com/api/v1/search_by_date'
MIN_STORIES, MIN_MONTHS = 6, 3
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
    while True:
        url = API + '?' + urlencode({'query': query, 'tags': 'story', 'restrictSearchableAttributes': 'title,url', 'typoTolerance': 'false', 'numericFilters': f'created_at_i>={start},created_at_i<{end}', 'hitsPerPage': 100, 'page': page})
        data = getter(url)
        sources.append(url)
        if page == 0 and data.get('nbHits', 0) >= 1000:
            if end - start <= 1:
                raise RuntimeError('Cannot enumerate this one-second interval completely')
            mid = (start + end) // 2
            left, ls = fetch_query(query, start, mid, getter)
            right, rs = fetch_query(query, mid, end, getter)
            return left + right, sources + ls + rs
        hits.extend(data['hits'])
        page += 1
        if page >= data.get('nbPages', 1):
            return hits, sources


def collect_project(project, start, end, months):
    accepted, rejected, sources = {}, {}, []
    for query in project['queries']:
        hits, urls = fetch_query(query, int(start.timestamp()), int(end.timestamp()))
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
    return {**project, 'monthly_counts': counts, 'eligible': eligible, 'story_count': len(stories), 'active_months': sum(value > 0 for value in counts), 'stories': stories, 'excluded_candidates': sorted(rejected.values(), key=lambda item: int(item['id'])), 'query_sources': sorted(set(sources)), 'search_url': 'https://hn.algolia.com/?' + urlencode({'q': project['domains'][0] if project.get('title_context_pattern') else project['title_aliases'][0], 'type': 'story', 'dateRange': 'custom', 'dateStart': int(start.timestamp()), 'dateEnd': int(end.timestamp()) - 1, 'sort': 'byDate'})}


def refresh(now=None):
    start, end, months = window(now)
    identities = json.loads(PROJECTS_PATH.read_text())['projects']
    with ThreadPoolExecutor(max_workers=4) as pool:
        projects = list(pool.map(lambda p: collect_project(p, start, end, months), identities))
    maximum = max((max(p['monthly_counts']) for p in projects if p['eligible']), default=1)
    return {'schema_version': 1, 'window_start': start.isoformat(), 'window_end_exclusive': end.isoformat(), 'months': months, 'refreshed_utc_date': (now or datetime.now(timezone.utc)).strftime('%Y-%m-%d'), 'metric': 'Deduplicated HN story submissions per UTC month, regardless of points, comments or sentiment. Search coverage is best-effort and depends on the HN Algolia index; absence is not proof of no discussion.', 'eligibility': {'minimum_stories': MIN_STORIES, 'minimum_active_months': MIN_MONTHS}, 'shared_monthly_maximum': maximum, 'projects': projects}


def svg(project, evidence):
    counts = project['monthly_counts']
    if len(counts) != 24 or any(not isinstance(n, int) or n < 0 for n in counts):
        raise ValueError('Expected exactly 24 nonnegative monthly counts')
    maximum = max(1, evidence['shared_monthly_maximum'])
    title = html.escape(project['name'] + ': HN discussions / 2y')
    desc = html.escape(f"Monthly HN story submissions, {evidence['months'][0]} through {evidence['months'][-1]}; oldest at left. Shared scale: 0–{maximum} stories/month. Counts: " + ', '.join(map(str, counts)) + '. Attention includes critical coverage; not endorsement.')
    bars = []
    for i, count in enumerate(counts):
        height = count / maximum * 20
        bars.append(f'<rect x="{i*5}" y="{22-height:.3f}" width="4" height="{height:.3f}" fill="#64748b"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="24" viewBox="0 0 120 24" role="img" aria-labelledby="title desc"><title id="title">{title}</title><desc id="desc">{desc}</desc>' + ''.join(bars) + '</svg>\n'


def decorate_readme(text, evidence=None):
    evidence = evidence if evidence is not None else json.loads(EVIDENCE_PATH.read_text())
    text = MARKER.sub('', text)
    by_url = {p['readme_url'].lower().rstrip('/'): p for p in evidence['projects'] if p['eligible']}
    pattern = re.compile(r'^(\| (?:\*\*)?\[[^\]]+\]\(([^)]+)\)(?:\*\*)?)(?=\s*\|)', re.M)
    def decorate(match):
        project = by_url.get(match.group(2).lower().rstrip('/'))
        if not project:
            return match.group(0)
        image = f"[![HN discussions / 2y](assets/hn/{project['slug']}.svg \"HN discussions / 2y\")]({project['search_url']})"
        return match.group(0) + '<br><!-- HN:START -->' + image + '<!-- HN:END -->'
    return pattern.sub(decorate, text)


def render(evidence):
    directory = ROOT / 'assets/hn'
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
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--render-only', action='store_true')
    parser.add_argument('--no-readme', action='store_true')
    args = parser.parse_args()
    if args.refresh and args.render_only:
        parser.error('--refresh and --render-only are mutually exclusive')
    evidence = json.loads(EVIDENCE_PATH.read_text()) if EVIDENCE_PATH.exists() else None
    if not args.render_only and (args.refresh or evidence is None or evidence['months'] != window()[2]):
        evidence = refresh()
        # Do not publish partial evidence when any network query fails.
        temporary = EVIDENCE_PATH.with_suffix('.tmp')
        temporary.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + '\n')
        temporary.replace(EVIDENCE_PATH)
    if evidence is None:
        parser.error('No cached evidence; run --refresh first')
    render(evidence)
    if not args.no_readme:
        readme = ROOT / 'README.md'
        readme.write_text(decorate_readme(readme.read_text(), evidence))
    print(f"HN history: {sum(p['eligible'] for p in evidence['projects'])}/{len(evidence['projects'])} eligible; {evidence['months'][0]}–{evidence['months'][-1]}; shared maximum {evidence['shared_monthly_maximum']}")


if __name__ == '__main__':
    main()
