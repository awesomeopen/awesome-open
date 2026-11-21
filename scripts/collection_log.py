"""Complete retained activity, with a bounded record-only replay."""
import json
from datetime import datetime, timezone
from html import escape
from build_catalog import canonical_url

LIMIT = 4
REPO = 'https://github.com/awesomeopen/awesome-open/blob/main/'


def event(at, kind, label, source):
    if not at:
        return None
    parsed = datetime.fromisoformat(at.replace('Z', '+00:00'))
    day = len(at) == 10
    if not day:
        if parsed.tzinfo is None:
            raise ValueError('Activity timestamp needs a timezone')
        parsed = parsed.astimezone(timezone.utc)
    return {'at': parsed.strftime('%Y-%m-%d' if day else '%Y-%m-%dT%H:%M:%SZ'),
            'precision': 'day' if day else 'second', 'kind': kind,
            'label': label, 'source': source}


def load(root):
    """Index once; never attach the archive to the published catalog."""
    path = root / 'data/chart_observations.json'
    archive = json.loads(path.read_text()) if path.exists() else {}
    indexed = {}
    for oid, observation in archive.get('observations', {}).items():
        date = observation.get('observed_at')
        kind = observation['kind']
        item = event(date['value'] if date else None, kind, {'hn': 'HN evidence collected', 'stars': 'Star history collected'}[kind],
                     REPO + 'data/chart_observations.json')
        if item:
            item['reference'] = oid
        indexed.setdefault((kind, observation['identity']), []).append(item)
    metrics = json.loads((root / 'data/github_metrics.json').read_text())
    reviews = {}
    def add(url, at, kind, label, file):
        item = event(at, kind, label, REPO + 'data/' + file + '.json')
        if item:
            reviews.setdefault(canonical_url(url), []).append(item)
    aliases = json.loads((root / 'data/project_aliases.json').read_text())
    for row in aliases.get('projects', []):
        add(row['project_url'], row.get('checked_at'), 'alias_review', 'Alias evidence reviewed', 'project_aliases')
    artwork = json.loads((root / 'data/specimen_art.json').read_text())
    for row in artwork.get('artworks', {}).values():
        if row.get('review_status') == 'approved':
            add(row['project_url'], row.get('created_at'), 'artwork_created', 'Specimen artwork created', 'specimen_art')
    return indexed, metrics.get('repositories', {}), reviews


def derive(project, context):
    indexed, repositories = context[:2]
    repo = (project.get('github') or {}).get('repo')
    events = list(indexed.get(('hn', project['url']), [])) + list(indexed.get(('stars', repo), []))
    events = [e for e in events if e]
    if len(context) > 2:
        events.extend(context[2].get(project['url'], []))
    metadata = repositories.get(repo, {})
    for at, kind, label in [((metadata.get('last_attempt') or {}).get('at'), 'metadata_attempt', 'Metadata collection attempted'),
                            (metadata.get('last_success_at'), 'metadata_success', 'Metadata collected')]:
        item = event(at, kind, label, REPO + 'data/github_metrics.json')
        if item:
            events.append(item)
    summary = project.get('function_summary') or {}
    item = event(summary.get('checked_at'), 'summary_review', 'Function evidence reviewed', REPO + 'data/function_summaries.json')
    if item:
        events.append(item)
    for history in project.get('history', []):
        item = event(history.get('checked_at'), 'history_review', 'Name-change evidence reviewed', REPO + 'data/project_history.json')
        if item:
            events.append(item)
    def add(at, kind, label, file):
        item = event(at, kind, label, REPO + 'data/' + file + '.json')
        if item:
            events.append(item)
    deployment = project.get('deployment') or {}
    if deployment.get('review_status') == 'approved':
        add(deployment.get('checked_at'), 'deployment_review', 'Deployment evidence reviewed', 'deployment_evidence')
    for alternative in project.get('alternatives', []):
        add(alternative.get('checked_utc_date'), 'alternative_review', 'Alternative evidence reviewed', 'alternatives')
    for feature in summary.get('features', []):
        add(feature.get('checked_at'), 'feature_review', 'Feature evidence reviewed', 'function_summaries')
    for kind, signal in (project.get('signals') or {}).items():
        title = {'release':'Release', 'languages':'Language', 'scorecard':'Scorecard'}.get(kind)
        if not title:
            continue
        add(signal.get('checked_at'), kind + '_attempt', title + ' collection attempted', 'project_signals')
        add(signal.get('last_success_at'), kind + '_success', title + ' evidence checked successfully', 'project_signals')
        add((signal.get('last_good') or {}).get('fetched_at'), kind + '_fetch', title + ' evidence collected', 'project_signals')
    unique = {(e['at'], e['kind'], e['source'], e.get('reference')): e for e in events}
    return sorted(unique.values(), key=lambda e: (e['at'], e['kind'], e.get('reference', '')))


def payload(project, events, context):
    # Intern repeated labels/sources once per file; keep every dated observation.
    types = sorted({(e['kind'], e['label'], e['source']) for e in events})
    rows = [[e['at'], types.index((e['kind'], e['label'], e['source']))] +
            ([e['reference']] if e.get('reference') else []) for e in events]
    repo = (project.get('github') or {}).get('repo')
    undated = {kind: sum(e is None for e in context[0].get((kind, identity), []))
               for kind, identity in [('hn', project['url']), ('stars', repo)]}
    return {'version': 1, 'types': types, 'events': rows,
            'undated': {kind: count for kind, count in undated.items() if count}}



def render(events, project_id=''):
    esc = lambda value: escape(value, quote=True)
    recent = events[-LIMIT:]
    replay = json.dumps([[e['at'][:10], e['label']] for e in recent], separators=(',', ':'))
    lines = ''.join(f'<span>{esc(e["at"][:10])} · {esc(e["label"])}</span>' for e in recent[-3:])
    url = 'collection/' + project_id + '.json'
    return ('<section class="pg-box pg-collection" aria-label="Collection log" data-log-version="1" '
            f'data-replay="{esc(replay)}">'
            '<h4 class="pg-title">Collection log</h4><p class="collection-caption">Recorded activity</p>'
            f'<div class="collection-replay" aria-hidden="true">{lines}</div>'
            '<details class="pg-info collection-overview"><summary aria-label="Collection log overview">i</summary><div class="pg-pop">'
            '<p>Retained collections and evidence reviews, oldest first. Earlier activity may be absent; '
            'review dates describe review, and the inclusion date is not recorded here.</p>'
            '<div class="collection-history">Open this overview to load retained records.</div>'
            f'<p><a class="collection-source" href="{esc(url)}">Download retained records</a></p>'
            '</div></details></section>')
