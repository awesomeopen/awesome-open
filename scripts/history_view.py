"""Offline name-history presentation shared by all specimen record modes."""
from datetime import date
from html import escape

from project_history import BASES, KINDS, exact_events


def day(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def event_title(event):
    return f"{KINDS[event['kind']]}: {event['old_name']} → {event['new_name']}"


def target(pid, event_id):
    return f'history-{pid}-{event_id}'


def timeline(created, release, pushed, events, pid):
    """One numbered lane per point: coincident/near dates never shift in time."""
    points = []
    for label, value, key in [('Repository created', created, 'created'),
                              ('GitHub release' + (f' · {release[1]}' if release else ''), release[0] if release else None, 'release'),
                              ('Repository push', pushed, 'pushed')]:
        if day(value):
            points.append((day(value), label, key, None))
    for event in exact_events(events):
        occurrence = event['occurred']
        points.append((day(occurrence['value']), event_title(event) + f" ({BASES[occurrence['basis']]})", event['id'], event))
    if not points:
        return ''
    points.sort(key=lambda p: (p[0], p[2]))
    lo = date(min(p[0] for p in points).year, 1, 1)
    hi = date(max(p[0] for p in points).year + 1, 1, 1)
    pct = lambda d: round((d - lo).days / (hi - lo).days * 100, 4)
    axis = len(points) * 1.75 + .75
    markers, rows = [], []
    for i, (when, label, key, event) in enumerate(points, 1):
        tid = target(pid, ('event-' if event else 'repository-') + key)
        markers.append(f'<a class="history-marker" href="#{tid}" data-record-anchor="{tid}" '
                       f'aria-label="{escape(str(i) + ". " + label + ", " + when.isoformat(), quote=True)}" '
                       f'style="left:{pct(when)}%;top:{(i-1)*1.75}rem;--stem:{axis-(i-1)*1.75-1.375}rem">{i}</a>')
        source = '' if event is None else f' · <a href="{escape(event["occurred"]["source_url"], quote=True)}">Source</a>'
        rows.append(f'<li id="{tid}" tabindex="-1"><time datetime="{when.isoformat()}">{when.isoformat()}</time> · {escape(label)}{source}</li>')
    # The repository lifetime segment starts at creation, even when project events predate it.
    created_day = day(created)
    repository_days = [p[0] for p in points if p[3] is None]
    span = ''
    if created_day:
        end = max(repository_days)
        span = f'<span class="history-repository-span" style="left:{pct(created_day)}%;width:{max(0,pct(end)-pct(created_day))}%"></span>'
    return (f'<div class="history-timeline"><div class="history-axis" style="height:{axis+2.25}rem;--axis:{axis}rem">'
            + ''.join(markers) + span
            + f'<span class="history-start">{lo.year}</span><span class="history-end">{hi.year}</span></div>'
            + '<ol class="history-dates">' + ''.join(rows) + '</ol></div>')


def evidence(events):
    if not events:
        return ''
    rows = []
    for event in events:
        occurred = event['occurred']
        if occurred is None:
            timing = 'Rename date unknown' if event['kind'] != 'owner_transfer' else 'Transfer date unknown'
        else:
            timing = f"{BASES[occurred['basis']].capitalize()} {occurred['value']}"
            if occurred['precision'] != 'day':
                timing += f" ({occurred['precision']} precision; not plotted)"
        observed = f" · First observed {event['first_observed_at']}" if 'first_observed_at' in event else ''
        sources = ' / '.join(f'<a href="{escape(s["url"], quote=True)}">{escape(s["title"])}</a>'
                             + f' ({escape(s["role"])}' + (f', {s["date"]}' if s['date'] else '') + ')'
                             for s in event['sources'])
        rows.append(f'<li><p>{escape(event_title(event))}. {escape(timing)}.</p><p>{escape(event["note"])}</p>'
                    f'<p>{sources}</p><p>Reviewed {event["checked_at"]} · {escape(event["reviewed_by"])}{escape(observed)}</p></li>')
    return '<details class="history-evidence fine-print"><summary>Name-change evidence</summary><ul>' + ''.join(rows) + '</ul></details>'
