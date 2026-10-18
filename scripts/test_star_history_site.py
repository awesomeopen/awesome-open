"""Site-only aligned charts with no false zeros or external chart requests."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import build_catalog
import build_site
import star_history
import update_star_history as collector
from datetime import datetime, timezone

class StarSiteTests(unittest.TestCase):
    def setUp(self):
        self.root = build_site.ROOT
        self.source = (self.root/'README.source.md').read_text()
        self.metrics, self.alternatives, self.hn = [json.loads((self.root/'data'/p).read_text()) for p in ('github_metrics.json','alternatives.json','hn_evidence.json')]
        self.repo = 'opentofu/opentofu'
        now = datetime.fromisoformat(self.hn['window_end_exclusive'])
        newest = int(now.timestamp()) - 86400
        weeks = [dict(week=newest-i*604800,total=7,days=[1]*7) for i in range(106)]
        def getter(url):
            page = int(url.rsplit('page=',1)[1])
            return weeks[(page-1)*30:page*30]
        self.good = collector.collect_repository(self.repo,now=now,getter=getter,source_sha='a'*40)
        self.snapshot = dict(schema_version=1,repositories={self.repo:dict(repo=self.repo, name='OpenTofu', readme_url='https://github.com/'+self.repo, status='ok', checked_at='2026-10-13T00:00:00Z', source_url='https://api.github.com/repos/'+self.repo+'/stargazers/history',last_good=self.good)})
    def catalog(self):
        return build_catalog.build_catalog(self.source,self.metrics,self.alternatives,self.hn,star_evidence=self.snapshot)
    def test_chart_is_offline_additive_aligned_and_private(self):
        before=deepcopy(self.snapshot)
        with patch('urllib.request.urlopen',side_effect=AssertionError('offline')):
            catalog=self.catalog()
            page=build_site.render_html(catalog)
        self.assertEqual(before,self.snapshot)
        matches=[p for p in catalog['projects'] if p.get('star_history')]
        self.assertEqual(len(matches),1)
        project=matches[0]
        self.assertTrue(project['star_history']['chart_url'].startswith('assets/stars/'))
        svg=star_history.svg(project)
        self.assertEqual(svg.count('<rect '),24)
        self.assertIn('Monthly stars retained at fetch',page)
        self.assertIn('Independent square-root scale: 0–31',page)
        self.assertIn('not guaranteed UTC',page)
        self.assertNotIn('<script src="https://',page)
        card=page.split('id="project-'+project['id']+'"')[1].split('</article>')[0]
        self.assertGreater(card.index('star-history'),card.index('<div class="specimen-interior'))
    def test_unavailable_partial_and_window_mismatch_never_zero(self):
        record=self.snapshot['repositories'][self.repo]
        record.update(status='partial',last_good=None)
        project=next(p for p in self.catalog()['projects'] if p.get('star_history'))
        self.assertIsNone(project['star_history']['chart_url'])
        self.assertIn('no zero values inferred',star_history.render(project))
        record['last_good']=self.good
        # A valid previous window is safe to retain but cannot pair with current HN.
        self.hn['months'] = self.hn['months'][1:] + ['2099-01']
        project=next(p for p in self.catalog()['projects'] if p.get('star_history'))
        self.assertIsNone(project['star_history']['chart_url'])
        self.assertIn('withheld until aligned',star_history.render(project))
    def test_failed_refresh_retains_last_good_with_stale_label(self):
        self.snapshot['repositories'][self.repo]['status']='unavailable'
        project=next(p for p in self.catalog()['projects'] if p.get('star_history'))
        self.assertIsNotNone(project['star_history']['chart_url'])
        self.assertIn('Stale cached result',star_history.render(project))
    def test_reviewed_openremote_endpoint_preserves_project_id_and_chart_attachment(self):
        from test_update_star_history import NOW, OPENREMOTE, pager, weekly_series
        baseline = self.catalog()
        original = next(p for p in baseline['projects'] if p['url'] == OPENREMOTE['readme_url'])
        self.snapshot = collector.refresh([OPENREMOTE], now=NOW, getter=pager(weekly_series()))
        updated = next(p for p in self.catalog()['projects'] if p['url'] == OPENREMOTE['readme_url'])
        self.assertEqual(updated['id'], original['id'])
        self.assertEqual(updated['url'], original['url'])
        self.assertIsNotNone(updated['star_history']['chart_url'])
        self.assertIn('https://api.github.com/repos/openremote/core/stargazers/history', star_history.render(updated))
    def test_reviewed_openomsi_endpoint_preserves_project_id_and_chart_attachment(self):
        from test_update_star_history import NOW, OPENOMSI, pager, weekly_series
        baseline = self.catalog()
        original = next(p for p in baseline['projects'] if p['url'] == OPENOMSI['readme_url'])
        self.snapshot = collector.refresh([OPENOMSI], now=NOW, getter=pager(weekly_series()))
        updated = next(p for p in self.catalog()['projects'] if p['url'] == OPENOMSI['readme_url'])
        self.assertEqual(updated['id'], original['id'])
        self.assertEqual(updated['url'], original['url'])
        self.assertIsNotNone(updated['star_history']['chart_url'])
        self.assertIn('https://api.github.com/repos/openomsi-org/openomsi/stargazers/history', star_history.render(updated))
    def test_reviewed_openbrender_endpoint_preserves_project_id_and_chart_attachment(self):
        from test_update_star_history import NOW, OPENBRENDER, pager, weekly_series
        baseline = self.catalog()
        original = next(p for p in baseline['projects'] if p['url'] == OPENBRENDER['readme_url'])
        self.snapshot = collector.refresh([OPENBRENDER], now=NOW, getter=pager(weekly_series()))
        updated = next(p for p in self.catalog()['projects'] if p['url'] == OPENBRENDER['readme_url'])
        self.assertEqual(updated['id'], original['id'])
        self.assertEqual(updated['url'], original['url'])
        self.assertEqual(updated['name'], original['name'])
        self.assertIsNotNone(updated['star_history']['chart_url'])
        self.assertIn('https://api.github.com/repos/gptchatly/drawplotia/stargazers/history', star_history.render(updated))
    def test_identity_and_invalid_counts_rejected_non_github_omitted(self):
        record=self.snapshot['repositories'][self.repo]
        record['repo']='wrong/repo'
        with self.assertRaises(ValueError):self.catalog()
        record['repo']=self.repo
        self.good['monthly_counts'][0]=True
        with self.assertRaises(ValueError):self.catalog()
        projects={'x':dict(url='https://www.openbsd.org',id='x')}
        self.good['monthly_counts'] = collector.monthly_counts(self.good['weeks'], self.good['months'])
        star_history.attach(projects,self.snapshot,self.hn)
        self.assertNotIn('star_history',projects['x'])
    def integrated_catalog(self, star_cache, deployment):
        return build_catalog.build_catalog(self.source,self.metrics,self.alternatives,self.hn,
            function_summaries=build_catalog.load_function_summaries(self.root/'data/function_summaries.json'),
            deployment_evidence=deployment,star_evidence=star_cache)

    def assert_history_coverage(self, catalog, star_cache, deployment):
        # Derive membership from the catalog without history attachment. A broken
        # attachment must not shrink both the actual and expected sets together.
        baseline = self.integrated_catalog(None, deployment)
        records = collector.validate_cache(star_cache)['repositories']
        expected = {p['url'] for p in baseline['projects']
                    if p['url'].startswith('https://github.com/')
                    and p['url'].removeprefix('https://github.com/') in records}
        actual = {p['url'] for p in catalog['projects'] if p.get('star_history')}
        self.assertEqual(actual, expected)
        approved = {entry['project_url'] for entry in deployment['projects'].values()
                    if entry['review_status'] == 'approved'}
        combined = {p['url'] for p in catalog['projects']
                    if p.get('star_history') and p.get('deployment')}
        self.assertEqual(combined, expected & approved)
        categories = {c['id']:c['name'] for c in catalog['categories']}
        for project in catalog['projects']:
            if project['url'] not in expected:
                continue
            card = build_site.project_html(project,categories,catalog)
            self.assertEqual('class="signal evidence-note star-history"' in card,
                             project['url'] in expected)
            if project['url'] in expected & approved:
                self.assertIn('<div class="deployment-evidence">',card)
                self.assertNotIn('Deployment and installation',card)
                self.assertIn('Function',card)
        return expected, combined

    def test_all_cached_histories_and_approved_deployment_overlap_render(self):
        deployment = json.loads((self.root/'data/deployment_evidence.json').read_text())
        star_cache = star_history.load_optional(self.root/'data/star_history.json')
        catalog = self.integrated_catalog(star_cache, deployment)
        expected, combined = self.assert_history_coverage(catalog, star_cache, deployment)
        # Preserve the three original integration pilots without limiting expansion.
        pilots = {'https://github.com/'+repo for repo in
                  ('opentofu/opentofu', 'open-webui/open-webui', 'openwrt/openwrt')}
        self.assertTrue(pilots <= expected)
        self.assertTrue(pilots <= combined)

    def test_expanded_history_only_missing_and_unlisted_records(self):
        deployment = json.loads((self.root/'data/deployment_evidence.json').read_text())
        baseline = self.integrated_catalog(None, deployment)
        approved = {entry['project_url'] for entry in deployment['projects'].values()
                    if entry['review_status'] == 'approved'}
        urls = [p['url'] for p in baseline['projects']
                if p['url'].startswith('https://github.com/') and p['url'] not in approved][:4]
        self.assertEqual(len(urls),4)
        cache = deepcopy(self.snapshot)
        for url in urls + ['https://github.com/not-in-catalog/history-fixture']:
            repo = url.removeprefix('https://github.com/')
            record = deepcopy(self.snapshot['repositories'][self.repo])
            record.update(repo=repo,readme_url=url,
                          source_url='https://api.github.com/repos/'+repo+'/stargazers/history')
            record['last_good']['source_urls'] = [value.replace(self.repo,repo)
                                                for value in record['last_good']['source_urls']]
            cache['repositories'][repo] = record
        catalog = self.integrated_catalog(cache, deployment)
        expected, combined = self.assert_history_coverage(catalog, cache, deployment)
        self.assertEqual(len(expected),5)
        self.assertEqual(combined,{'https://github.com/'+self.repo})
        # A missing attachment or an invented attachment cannot pass coverage.
        broken = deepcopy(catalog)
        next(p for p in broken['projects'] if p['url']==urls[0]).pop('star_history')
        with self.assertRaises(AssertionError):
            self.assert_history_coverage(broken, cache, deployment)
        broken = deepcopy(catalog)
        next(p for p in broken['projects'] if p['url'] not in expected)['star_history'] = deepcopy(
            next(p['star_history'] for p in catalog['projects'] if p.get('star_history')))
        with self.assertRaises(AssertionError):
            self.assert_history_coverage(broken, cache, deployment)
        del cache['repositories'][urls[0].removeprefix('https://github.com/')]
        self.assert_history_coverage(self.integrated_catalog(cache,deployment),cache,deployment)
        self.assert_history_coverage(self.integrated_catalog(dict(schema_version=1,repositories={}),deployment),
                                     dict(schema_version=1,repositories={}),deployment)

    def test_assets_evidence_standalone_and_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'root'; output=Path(directory)/'preview';root.mkdir()
            shutil.copyfile(self.root/'README.source.md',root/'README.source.md')
            for name in ('site','data'):shutil.copytree(self.root/name,root/name)
            (root/'data/star_history.json').write_text(json.dumps(self.snapshot))
            build_site.build(output,root=root)
            self.assertEqual(len(list((output/'assets/stars').glob('*.svg'))),1)
            standalone=(output/'standalone.html').read_text()
            self.assertNotIn('src="assets/stars/',standalone)
            self.assertIn('download="star_history.json" href="data:application/json;base64,',standalone)
            (root/'data/star_history.json').unlink()
            build_site.build(output,root=root)
            self.assertFalse(list((output/'assets/stars').glob('*.svg')))
            self.assertFalse((output/'data/star_history.json').exists())
if __name__=='__main__':unittest.main()
