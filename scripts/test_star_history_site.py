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
    def test_deployment_and_star_pilots_coexist_after_main_integration(self):
        deployment = json.loads((self.root/'data/deployment_evidence.json').read_text())
        star_cache = star_history.load_optional(self.root/'data/star_history.json')
        catalog = build_catalog.build_catalog(self.source,self.metrics,self.alternatives,self.hn,
            function_summaries=build_catalog.load_function_summaries(self.root/'data/function_summaries.json'),
            deployment_evidence=deployment,star_evidence=star_cache)
        combined = [p for p in catalog['projects'] if p.get('star_history')]
        self.assertEqual(len(combined),3)
        for project in combined:
            self.assertTrue(project.get('deployment'))
            card = build_site.project_html(project,{c['id']:c['name'] for c in catalog['categories']},catalog)
            self.assertIn('class="deployment-evidence"',card)
            self.assertIn('class="signal evidence-note star-history"',card)
            self.assertLess(card.index('class="signal evidence-note star-history"'),card.index('class="deployment-evidence"'))
            self.assertIn('Function',card)

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
