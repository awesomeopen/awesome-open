"""Bounded record-only activity derived from dated retained evidence."""
import json
from datetime import datetime, timezone
from html import escape

LIMIT = 8
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
        if not date:
            continue
        kind = observation['kind']
        item = event(date['value'], kind, {'hn': 'HN evidence collected', 'stars': 'Star history collected'}[kind],
                     REPO + 'data/chart_observations.json#' + oid)
        indexed.setdefault((kind, observation['identity']), []).append(item)
    metrics = json.loads((root / 'data/github_metrics.json').read_text())
    return indexed, metrics.get('repositories', {})


def derive(project, context):
    indexed, repositories = context
    repo = (project.get('github') or {}).get('repo')
    events = list(indexed.get(('hn', project['url']), [])) + list(indexed.get(('stars', repo), []))
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
    unique = {(e['at'], e['kind'], e['source']): e for e in events}
    return sorted(unique.values(), key=lambda e: (e['at'], e['kind'], e['source']))[-LIMIT:]


def render(events):
    esc = lambda value: escape(value, quote=True)
    rows = ''.join(f'<li data-event-kind="{esc(e["kind"])}"><time datetime="{esc(e["at"])}">{esc(e["at"].replace("T", " ").replace("Z", " UTC"))}</time> '
                   f'<a href="{esc(e["source"])}">{esc(e["label"])}</a></li>' for e in events)
    latest = events[-3:]
    lines = ''.join(f'<span>{esc(e["at"][:10])} · {esc(e["label"])}</span>' for e in latest)
    return ('<section class="pg-box pg-collection" aria-label="Collection log" data-log-version="1">'
            '<h4 class="pg-title">Collection log</h4><p class="collection-caption">Recorded activity</p>'
            f'<div class="collection-replay" aria-hidden="true">{lines}</div>'
            '<details class="pg-info"><summary aria-label="Collection log overview">i</summary><div class="pg-pop">'
            '<p>Recent dated records retained for this project, oldest first. Review dates describe evidence review. '
            'This overview covers available records, rather than a complete history since inclusion.</p>'
            + (f'<ol class="collection-events">{rows}</ol>' if events else '<p>No dated collection records retained.</p>')
            + '</div></details></section>')
