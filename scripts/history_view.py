"""Offline name-history presentation shared by all specimen record modes."""
from datetime import date
from html import escape

from project_history import BASES, KINDS, exact_events

# Short timeline labels; the full kind stays in the details and evidence text.
TIMELINE_KINDS = {'software_rename': 'Renamed', 'repository_rename': 'Repository renamed',
                  'owner_transfer': 'Transferred'}


def day(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def event_title(event):
    return f"{KINDS[event['kind']]}: {event['old_name']} → {event['new_name']}"


def timeline_title(event):
    return f"{TIMELINE_KINDS[event['kind']]}: {event['old_name']} → {event['new_name']}"


def sources(event):
    return ' / '.join(f'<a href="{escape(s["url"], quote=True)}">{escape(s["title"])}</a>'
                      + f' ({escape(s["role"])}' + (f', {s["date"]}' if s['date'] else '') + ')'
                      for s in event['sources'])


def details(event):
    """The sources behind one plotted event, opened from its timeline label.

    The label already carries the names and date; kind, basis, note and review
    provenance stay in the history data and its contract (B-PR158-01).
    """
    return f'<p>Sources: {sources(event)}</p>'


def timeline_events(events):
    """(date, title, details HTML) for verified day-precision occurrences only."""
    return [(day(e['occurred']['value']), timeline_title(e), details(e)) for e in exact_events(events)]


def evidence(events):
    """Events without an exact occurrence date stay in folded secondary evidence."""
    plotted = {id(e) for e in exact_events(events)}
    events = [e for e in events if id(e) not in plotted]
    if not events:
        return ''
    rows = []
    for event in events:
        occurred = event['occurred']
        if occurred is None:
            timing = 'Rename date unknown' if event['kind'] != 'owner_transfer' else 'Transfer date unknown'
        else:
            timing = (f"{BASES[occurred['basis']].capitalize()} {occurred['value']}"
                      f" ({occurred['precision']} precision; not plotted)")
        observed = f" · First observed {event['first_observed_at']}" if 'first_observed_at' in event else ''
        rows.append(f'<li><p>{escape(event_title(event))}. {escape(timing)}.</p><p>{escape(event["note"])}</p>'
                    f'<p>{sources(event)}</p><p>Reviewed {event["checked_at"]} · {escape(event["reviewed_by"])}{escape(observed)}</p></li>')
    return '<details class="history-evidence fine-print"><summary>Name-change evidence</summary><ul>' + ''.join(rows) + '</ul></details>'
