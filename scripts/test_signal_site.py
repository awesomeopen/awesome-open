"""Offline website-only evidence integration, provenance, and safety."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import build_catalog
import build_site
import render_readme
import signals
import update_signals
from test_build_site import Page


class SignalSiteTests(unittest.TestCase):
    def setUp(self):
        self.root = build_site.ROOT
        self.source = (self.root / 'README.source.md').read_text()
        self.metrics, self.alternatives, self.hn = [json.loads((self.root / 'data' / p).read_text()) for p in
                                                 ('github_metrics.json','alternatives.json','hn_evidence.json')]
        self.at = '2026-10-10T00:00:00Z'
        self.optional = signals.empty_snapshot(self.at, 'a' * 40)
        self.repo = 'openemr/openemr'
        self.optional['repositories'][self.repo] = {p: signals.empty_signal(self.repo, p) for p in signals.PROVIDERS}
        payload = {'id': 12, 'tag_name': '<tag>', 'published_at': '2020-01-01T00:00:00Z',
                   'created_at': '2010-01-01T00:00:00Z', 'draft': False, 'prerelease': False,
                   'html_url': 'https://github.com/openemr/openemr/releases/tag/v1'}
        release = self.optional['repositories'][self.repo]['release']
        release.update(last_good=update_signals.normalize_release(payload,self.repo,self.at),
                       checked_at=self.at,last_success_at=self.at,fetch_status='ok',status='available',http_status=200)
        payload = {'date':'2026-10-05','repo':{'name':'github.com/openemr/openemr','commit':'c'*40},
                   'scorecard':{'version':'v-test','commit':'d'*40},'score':4.2,
                   'checks':[{'name':'Example','score':-1,'reason':'<script>not executed</script>'},
                             {'name':'Other','score':0,'reason':'A scored zero.'}]}
        record = self.optional['repositories'][self.repo]['scorecard']
        record.update(last_good=update_signals.normalize_scorecard(payload,self.repo,self.at),
                      checked_at=self.at,last_success_at=self.at,fetch_status='ok',status='partial',http_status=200,
                      check_time_precision='day',success_time_precision='day')
        record['last_good']['fetch_time_precision']='day'

    def catalog(self, optional):
        return build_catalog.build_catalog(self.source,self.metrics,self.alternatives,self.hn,'b'*40,optional)

    def test_optional_is_additive_immutable_offline_and_keeps_identities(self):
        baseline=self.catalog(None)
        before=deepcopy(self.optional)
        with patch('urllib.request.urlopen',side_effect=AssertionError('No network')):
            catalog=self.catalog(self.optional)
        self.assertEqual(self.optional,before)
        self.assertEqual((len(catalog['projects']),catalog['category_memberships']),(370,392))
        self.assertEqual([(p['id'],p['categories'],p['github']) for p in baseline['projects']],
                         [(p['id'],p['categories'],p['github']) for p in catalog['projects']])
        found=[p for p in catalog['projects'] if p['signals']]
        self.assertEqual(len(found),1)
        self.assertEqual(catalog['signals_source_sha'],'a'*40)
        self.assertEqual(catalog['source_sha'],'b'*40)
        self.assertEqual(catalog,self.catalog(self.optional))

    def test_drawer_technical_labels_coverage_dates_and_html_escaping(self):
        catalog=self.catalog(self.optional)
        html=build_site.render_html(catalog)
        page=Page(html)
        project=next(p for p in catalog['projects'] if p['signals'])
        card=page.by_id['project-'+project['id']]
        for text in ('Latest GitHub release','OpenSSF Scorecard','4.2/10','1 scored / 2 returned checks',
                     'Inconclusive','Published 2020-01-01 UTC','Scanned 2026-10-05',
                     '2026-10-10 UTC (date only)','Check results and scan provenance'):
            self.assertIn(text,card.text)
        self.assertNotIn('<tag>',html)
        self.assertNotIn('<script>not executed</script>',html)
        self.assertIn('&lt;script&gt;not executed&lt;/script&gt;',html)
        self.assertNotIn('2010-01-01',card.text)
        self.assertIn('https://github.com/openemr/openemr/commit/'+'c'*40,page.links)
        self.assertIn('Release: 1 cached results / 1 checked',html)
        self.assertIn('Scorecard: 1 cached results / 1 checked',html)
        self.assertIn('Inconclusive and omitted checks remain unknown.',html)

    def test_unavailable_pending_and_stale_preserve_distinct_labels(self):
        records=self.optional['repositories'][self.repo]
        records['release'].update(fetch_status='not_found',status='stale',http_status=404)
        records['scorecard']=signals.empty_signal(self.repo,'scorecard')
        html=build_site.render_html(self.catalog(self.optional))
        self.assertIn('Stale',html)
        self.assertIn('Published 2020-01-01 UTC',html)
        self.assertIn('Not checked',html)
        self.assertIn('Latest attempt: not found',html)
        records['scorecard'].update(fetch_status='not_found',status='unavailable',http_status=404,checked_at=self.at,error='not_found')
        html=build_site.render_html(self.catalog(self.optional))
        self.assertIn('No result returned',html)
        self.assertNotIn('0/10',html)

    def test_source_identity_or_schema_corruption_fails_catalog(self):
        for mutate in (lambda d:d.update(schema_version=2),
                       lambda d:d['repositories'][self.repo]['release'].update(source_url='https://evil.example'),
                       lambda d:d['repositories'][self.repo]['scorecard']['last_good']['value'].update(repository='github.com/other/repo')):
            bad=deepcopy(self.optional);mutate(bad)
            with self.assertRaises(ValueError):self.catalog(bad)

    def test_release_source_rejects_browser_path_normalization_escapes(self):
        for suffix in ('../../other/repo', '%2e%2e/%2e%2e/other/repo', '%5c..%5cother', '%0av1'):
            document = deepcopy(self.optional)
            good = document['repositories'][self.repo]['release']['last_good']
            good['value']['html_url'] = 'https://github.com/openemr/openemr/releases/tag/' + suffix
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.catalog(document)

    def test_signal_changes_cannot_change_readme_bytes(self):
        expected=render_readme.render_text(self.source,self.metrics,self.hn)
        self.catalog(self.optional)
        self.optional['repositories']={}
        self.catalog(self.optional)
        self.assertEqual(expected,render_readme.render_text(self.source,self.metrics,self.hn))
        self.assertEqual(expected,(self.root/'README.md').read_text())

    def test_optional_file_is_embedded_and_absent_file_removes_old_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'root'; output=Path(directory)/'preview'
            root.mkdir()
            for name in ('README.source.md',):shutil.copyfile(self.root/name,root/name)
            for name in ('site','data'):shutil.copytree(self.root/name,root/name)
            update_signals.write_snapshot(root/'data/project_signals.json',self.optional)
            build_site.build(output,root=root)
            self.assertEqual(json.loads((output/'data/project_signals.json').read_text()),self.optional)
            html=(output/'standalone.html').read_text()
            self.assertIn('download="project_signals.json" href="data:application/json;base64,',html)
            self.assertNotIn('href="data/project_signals.json"',html)
            (root/'data/project_signals.json').unlink()
            catalog=build_site.build(output,root=root)
            self.assertTrue(all(p['signals'] is None for p in catalog['projects']))
            self.assertFalse((output/'data/project_signals.json').exists())
            self.assertNotIn('project_signals.json',(output/'index.html').read_text())


if __name__ == '__main__':unittest.main()
