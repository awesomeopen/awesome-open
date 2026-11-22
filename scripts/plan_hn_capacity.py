"""Offline empirical HN planning scenarios; no collection or retention changes."""
import json
import math
from pathlib import Path
from statistics import mean, median
from build_site import compact_json
from published_hn import publish, materialize


def measure(root):
    source = json.loads((root / 'data/hn_evidence.json').read_text())
    doc = publish(source)
    assert materialize(doc) == source
    size = lambda x: len(compact_json(x).encode('utf-8'))
    fields = {'stories', 'broad_stories', 'excluded_candidates', 'monthly_counts', 'broad_monthly_counts'}
    rows = [(size(p), size({k:v for k,v in p.items() if k in fields}), bool(p.get('stories') or p.get('broad_stories') or p.get('excluded_candidates'))) for p in doc['projects']]
    rich = [r for r in rows if r[2]]
    sparse = [r for r in rows if not r[2]]
    fixed = mean(r[0]-r[1] for r in rich)
    history = mean(r[1] for r in rich)
    overhead = size({k:v for k,v in doc.items() if k != 'projects'}) / len(rows)
    # Replace today's sparse mix with 1,000 projects drawn from the richer cohort.
    # Preserve its observed tail, then add five further copies of today's largest project.
    scenarios = {}
    for years in (2, 5, 10):
        current = 1000 * (fixed + history * years / 2 + overhead)
        recovery = .25 * 1000 * (fixed + history * years / 2)
        tail = 5 * max(r[0] for r in rows) * years / 2
        scenarios[str(years)] = {'richer_full_coverage': math.ceil(current),
            'plus_25pct_distinct_recovery_and_five_extra_largest': math.ceil(current+recovery+tail)}
    return {'window':[doc['window_start'],doc['window_end_exclusive']],
        'published_bytes':size(doc), 'projects':len(rows),
        'rich':{'count':len(rich),'mean':mean(r[0] for r in rich),'median':median(r[0] for r in rich)},
        'sparse':{'count':len(sparse),'mean':mean(r[0] for r in sparse)},
        'largest_project':max(r[0] for r in rows), 'rich_fixed_mean':fixed,
        'rich_history_mean':history,'overhead_per_project':overhead,
        'recovery_refs':sum('project_ref' in (q.get('last_good') or {}) for q in doc['queue'].values()),
        'scenarios_1000_projects':scenarios}


if __name__ == '__main__':
    print(json.dumps(measure(Path(__file__).resolve().parents[1]),indent=2))
