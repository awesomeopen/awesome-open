"""Synthetic browser responses, rendered offline; never used by a site build.

The pinned summary/setup record supplies realistic long content. All collection
observations are synthetic and fixed to October 2026, independent of main's cache.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import build_catalog
import build_site
import star_history
import update_hn as hn
import update_star_history as collector

ROOT = Path(__file__).resolve().parent
REPO = 'opentofu/opentofu'
URL = 'https://github.com/' + REPO
NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def fixture(state='complete'):
    if state not in ('complete', 'empty', 'partial', 'unavailable', 'rollover'):
        raise ValueError('Unknown browser evidence state')
    curated = json.loads((ROOT / 'fixtures/browser_layout.json').read_text())
    source = ('## Infrastructure & DevOps\n\n| Project | Description |\n| --- | --- |\n'
              f'| [OpenTofu]({URL}) | Synthetic layout fixture. |\n'
              '| [OpenSample](https://example.org/open-sample) | Synthetic sparse chart fixture. |\n')
    metrics = dict(schema_version=1, as_of='2026-10-13', repositories={REPO: dict(
        created_at='2020-01-01T00:00:00Z', pushed_at='2026-10-01T00:00:00Z',
        license={'spdx_id': 'MPL-2.0'}, stargazers_count=1234)})
    start, end, months = hn.window(NOW)
    projects = [dict(name=name, readme_url=url, slug=slug, eligible=False,
                     story_count=count, monthly_counts=[count]+[0]*23,
                     search_url='https://hn.algolia.com/?q='+name+'&type=story')
                for name, url, slug, count in [('OpenTofu', URL, 'fixture-tofu', 3),
                    ('OpenSample', 'https://example.org/open-sample', 'fixture-sample', 1)]]
    evidence = dict(schema_version=1, projects=projects, months=months,
                    window_start=start.isoformat(), window_end_exclusive=end.isoformat(),
                    shared_monthly_maximum=3)
    newest = int(end.timestamp()) - 86400
    weeks = [dict(week=newest-i*604800, total=7, days=[1]*7) for i in range(106)]
    def getter(url):
        page = int(url.rsplit('page=', 1)[1])
        return weeks[(page-1)*30:page*30]
    good = collector.collect_repository(REPO, now=NOW, getter=getter, source_sha='a'*40)
    record = dict(repo=REPO, name='OpenTofu', readme_url=URL, status='ok',
                  checked_at='2026-10-13T00:00:00Z',
                  source_url=f'https://api.github.com/repos/{REPO}/stargazers/history', last_good=good)
    stars = dict(schema_version=1, repositories={REPO: record})
    if state == 'empty':
        evidence['projects'] = []
        stars['repositories'] = {}
    elif state in ('partial', 'unavailable'):
        record.update(status=state, last_good=None)
        if state == 'unavailable':
            evidence['projects'] = []
    elif state == 'rollover':
        start, end, months = hn.window(datetime(2026, 11, 1, tzinfo=timezone.utc))
        evidence.update(projects=[], months=months, window_start=start.isoformat(), window_end_exclusive=end.isoformat())
    catalog = build_catalog.build_catalog(source, metrics, {'schema_version': 1, 'projects': []},
        evidence, source_sha='a'*40, function_summaries=curated['function_summaries'],
        deployment_evidence=curated['deployment_evidence'], star_evidence=stars)
    display = hn.display_evidence(evidence)
    catalog['hn_window'] = dict(first=months[0], last=months[-1], monthly_maximum=display['shared_monthly_maximum'])
    for project in catalog['projects']:
        if project['url'] == URL:
            project['artwork'] = deepcopy(curated['artwork'])
    cutouts = build_site.attach_specimen_cutouts(catalog, build_site.ROOT)
    variants = build_site.attach_specimen_variants(build_site.ROOT)
    categories = {c['id']: c['name'] for c in catalog['categories']}
    responses = {'': build_site.render_html(catalog)}
    for number, project in enumerate(catalog['projects'], 1):
        responses['records/'+project['id']+'.html'] = build_site.render_record(project, categories, catalog, number, cutouts, variants=variants)
        if project.get('star_history', {}).get('chart_url'):
            responses[project['star_history']['chart_url']] = star_history.svg(project)
    for project in display['projects']:
        responses['assets/hn/'+project['slug']+'.svg'] = hn.svg(project, display)
    responses['data/star_history.json'] = json.dumps(stars)
    return dict(data=build_site.published_catalog(deepcopy(catalog)), responses=responses)


if __name__ == '__main__':
    print(json.dumps({state: fixture(state) for state in ('complete', 'empty', 'partial', 'unavailable', 'rollover')}))
