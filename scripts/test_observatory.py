"""Deterministic snapshot accounting, static fallback and thin route payload."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build_observatory as obs
import build_site
from test_build_site import Page


def fixture():
    return dict(source_sha='a'*40, metrics_as_of='2026-10-13', signals_collected_at=None,
                categories=[dict(id='one',name='One'),dict(id='two',name='Two')], projects=[
        dict(id='a',name='Alpha',url='https://github.com/example/alpha',categories=['one','two'],
             github=dict(stars=0,license=None,created_at='2026-10-13T23:59:59Z',pushed_at=None)),
        dict(id='b',name='Beta',url='https://example.com/beta',categories=['one'],github=None),
        dict(id='c',name='Gamma',url='https://github.com/example/gamma',categories=['two'],
             github=dict(stars=100,license='MIT',created_at='2020-01-01T00:00:00Z',pushed_at='2026-10-12T00:00:00Z'),
             signals=dict(release=dict(status='stale',checked_at='2026-10-12T00:00:00Z',last_good=dict(value=dict(published_at='2026-10-01T00:00:00Z'))),
                          scorecard=dict(status='partial',checked_at='2026-10-12T00:00:00Z',last_good=dict(value=dict(score=0))))),
    ])


class ObservatoryAccountingTests(unittest.TestCase):
    def test_unique_totals_overlapping_categories_and_zero_vs_unknown(self):
        catalog=fixture(); before=deepcopy(catalog)
        index=obs.project_index(catalog); counts=obs.aggregate(index)
        self.assertEqual(catalog,before)
        self.assertEqual((counts['total'],counts['mapped'],counts['stars'],counts['known_license']),(3,2,100,1))
        self.assertEqual(counts['categories'],[['One',2],['Two',2]])
        self.assertEqual(index['projects'][0]['stars'],0)
        self.assertIsNone(index['projects'][1]['stars'])
        self.assertEqual(sum(v for _,v in counts['licenses']),3)
        self.assertEqual(counts['ages'][0][1],1)
        self.assertEqual(counts['pushes'][-1][1],2)
        self.assertEqual(counts['releases'][0][1],1)
        self.assertEqual(index['projects'][2]['release_status'],'stale')
        self.assertNotIn('signals',json.dumps(index))

    def test_duplicate_identity_rejected_and_duplicate_category_deduplicated(self):
        catalog=fixture();catalog['projects'][0]['categories'].append('one')
        self.assertEqual(obs.project_index(catalog)['projects'][0]['categories'],['one','two'])
        catalog['projects'].append(catalog['projects'][0])
        with self.assertRaises(ValueError):obs.project_index(catalog)

    def test_calendar_dates_boundaries_and_invalid_future_values(self):
        from datetime import date,timedelta
        as_of='2026-10-13'
        for days,bucket in [(0,0),(30,0),(31,1),(90,1),(91,2),(365,2),(366,3),(730,3),(731,4)]:
            value=(date.fromisoformat(as_of)-timedelta(days=days)).isoformat()+'T23:59:59Z'
            self.assertEqual(obs.days_before(value,as_of),days)
            bins=obs.histogram([{'d':value}],'d',as_of,obs.RECENCY)
            self.assertEqual(bins[bucket][1],1)
        for value in [None,'','bad','2026-02-30','2026-10-14T00:00:00Z','2026-1-01']:
            self.assertIsNone(obs.days_before(value,as_of))
        self.assertEqual(obs.days_before('2024-02-29T00:00:00Z','2024-03-01'),1)
        self.assertEqual(obs.days_before('2026-09-12T23:30:00-02:00',as_of),30)
        self.assertEqual(obs.days_before('2026-10-14T00:30:00+02:00',as_of),0)

    def test_concentration_uses_unique_star_counts_with_ties_and_empty(self):
        index=obs.project_index(fixture())
        counts=obs.aggregate(index,[])
        self.assertIsNone(counts['concentration'])
        self.assertEqual(counts['stars'],0)
        self.assertEqual(counts['star_rows'],[])
        index['projects']=[dict(id=str(i),name=str(i),github=True,stars=10,categories=['one'],license='MIT',created_at=None,pushed_at=None,release_at=None) for i in range(12)]
        counts=obs.aggregate(index)
        self.assertEqual(counts['concentration'],83.3)
        self.assertEqual(counts['star_rows'][-1],['Other mapped projects',20])
        self.assertEqual(sum(n for _,n in counts['star_rows']),120)

    def test_hn_global_dedup_and_partial_scorecard_remain_explicit(self):
        catalog=fixture()
        hn=dict(projects=[dict(readme_url='https://github.com/Example/Alpha/',eligible=True,stories=[{'id':'1'},{'id':'1'},{'id':'2'}]),dict(readme_url='https://example.com/beta',eligible=False,stories=[{'id':'2'}])])
        covered=obs.coverage(catalog,hn)
        self.assertEqual((covered['hn_tracked'],covered['hn_eligible'],covered['hn_unique_stories'],covered['hn_project_matches']),(2,1,2,3))
        self.assertEqual(covered['scorecard']['states'],{'not checked':2,'partial':1})
        self.assertEqual(covered['release']['states'],{'not checked':2,'stale':1})

    def test_unstamped_preview_has_a_valid_metrics_source_link(self):
        catalog=fixture();catalog['source_sha']=None;index=obs.project_index(catalog)
        html=obs.render(index,obs.aggregate(index),obs.coverage(catalog,{}))
        self.assertIn('https://github.com/awesomeopen/awesome-open/blob/main/data/github_metrics.json',html)
        self.assertIn('Local preview; source revision not supplied',html)

    def test_csv_and_html_escape_untrusted_names(self):
        catalog=fixture();catalog['projects'][0]['name']='=SUM(1,2)';index=obs.project_index(catalog)
        rows=list(csv.DictReader(io.StringIO(obs.csv_text(index))))
        self.assertEqual(rows[0]['name'],"'=SUM(1,2)")
        self.assertEqual(rows[0]['stars'],'0');self.assertEqual(rows[1]['stars'],'')
        self.assertEqual(rows[0]['metrics_as_of'],index['metrics_as_of'])
        self.assertEqual(rows[0]['source_sha'],'a'*40)
        for value in [' =1','+1','-1','@SUM(A1)','\t=1','\r=1']:
            self.assertTrue(obs.safe_csv(value).startswith("'"))
        index['projects'][0]['name']='</script><img src=x onerror=alert(1)>'
        html=obs.render(index,obs.aggregate(index),obs.coverage(catalog,{}))
        self.assertNotIn('</script><img',html)
        self.assertIn('\\u003c/script',html)
        self.assertIn('&lt;/script&gt;',html)


class ObservatoryBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.output=Path(cls.temp.name)/'site'
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline build')):
            cls.catalog=build_site.build(cls.output,source_sha='a'*40)
        cls.html=(cls.output/'observatory/index.html').read_text();cls.page=Page(cls.html)
        cls.snapshot=json.loads((cls.output/'observatory/snapshot.json').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_integrated_same_revision_complete_static_records(self):
        index=self.snapshot
        self.assertEqual(index['source_sha'],self.catalog['source_sha'])
        self.assertEqual(index['metrics_as_of'],self.catalog['metrics_as_of'])
        self.assertEqual([p['id'] for p in index['projects']],[p['id'] for p in self.catalog['projects']])
        rows=self.page.by_id['project-table'].descendants('tbody')[0].children
        self.assertEqual([r.attrs['data-id'] for r in rows],[p['id'] for p in index['projects']])
        self.assertFalse(any('hidden' in r.attrs for r in rows))
        self.assertIn('hidden',self.page.by_id['observatory-filters'].attrs)
        self.assertEqual(len(self.page.ids),len(set(self.page.ids)))
        for chart in ['category','license','star','age','push','release']:
            node=self.page.by_id[chart+'-chart']
            self.assertEqual(len(node.descendants('table')),1)
            self.assertEqual(node.descendants('svg')[0].attrs['aria-hidden'],'true')
        self.assertIn('href="observatory/"',(self.output/'index.html').read_text())
        self.assertNotIn('observatory.js',(self.output/'index.html').read_text())

    def test_project_data_disclosure_and_copy_in_both_outputs(self):
        for name in ['index.html', 'report.html']:
            text=(self.output/'observatory'/name).read_text(); page=Page(text)
            disclosure=page.by_id['project-data']
            self.assertEqual(disclosure.tag, 'details')
            self.assertNotIn('open', disclosure.attrs)
            self.assertEqual(disclosure.children[0].tag, 'summary')
            self.assertEqual(disclosure.children[0].text, 'Data table')
            self.assertIn(page.by_id['project-table'], disclosure.descendants('table'))
            self.assertNotIn(page.by_id['export-csv'], disclosure.descendants('a'))
            for copy in ['Projects by category', 'Top 10 (by GitHub stars).',
                         'Days since GitHub repository creation.', 'Dates are UTC.']:
                self.assertIn(copy, text)
            for removed in ['Where the collection gathers', 'Attention is uneven',
                            'Read the distribution', 'Inspect or take the data',
                            'What is actually covered?', 'not the project founding date']:
                self.assertNotIn(removed, text)

    def test_csv_covers_displayed_project_fields(self):
        rows=list(csv.DictReader(io.StringIO((self.output/'observatory/projects.csv').read_text())))
        self.assertEqual(len(rows), len(self.snapshot['projects']))
        for row, project in zip(rows, self.snapshot['projects']):
            for key in ['id', 'name', 'url', 'license', 'stars', 'created_at',
                        'pushed_at', 'release_at', 'release_status', 'release_checked_at']:
                self.assertEqual(row[key], obs.safe_csv(project[key]))
            self.assertEqual(row['categories'], '; '.join(project['categories']))
            self.assertEqual(row['source_sha'], self.snapshot['source_sha'])

    def test_requested_logo_and_standalone_embedding(self):
        import base64
        logo=build_site.ROOT/'site/brand/botanical-128.png'
        for name in ['index.html', 'report.html']:
            page=Page((self.output/'observatory'/name).read_text())
            self.assertEqual(len(page.images), 1)
            image=page.images[0]
            self.assertEqual(image['class'], 'obs-logo')
            self.assertEqual((image['width'], image['height']), ('128', '128'))
            self.assertEqual(image['alt'], 'Awesome Open* botanical logo')
            self.assertEqual(page.nodes('figcaption'), [])
            expected=('../brand/botanical-128.png' if name == 'index.html' else
                      'data:image/png;base64,'+base64.b64encode(logo.read_bytes()).decode('ascii'))
            self.assertEqual(image['src'], expected)
        self.assertEqual((self.output/'brand/botanical-128.png').read_bytes(), logo.read_bytes())

    def test_thin_index_and_no_runtime_remote_dependencies(self):
        node=self.page.by_id['observatory-data'];data=json.loads(node.text)
        self.assertLess(len(node.text.encode()),len(json.dumps(self.catalog).encode())/3)
        for key in ['description','signals','artwork','function_summary','alternatives','star_history']:
            self.assertFalse(any(key in p for p in data['projects']))
        for script in self.page.nodes('script'):
            self.assertFalse(script.attrs.get('src','').startswith(('https:','http:')))
        for node in self.page.nodes('script')+self.page.nodes('link')+self.page.nodes('img'):
            path=node.attrs.get('src') or node.attrs.get('href')
            if path and not path.startswith(('https:','http:','data:','#')):
                self.assertTrue((self.output/'observatory'/path).is_file(),path)
        self.assertLessEqual(len(self.page.images),1)

    def test_standalone_embeds_runtime_and_downloads(self):
        text=(self.output/'observatory/report.html').read_text();page=Page(text)
        for node in page.nodes('script')+page.nodes('img')+page.nodes('link'):
            url=node.attrs.get('src') or node.attrs.get('href')
            if url:self.assertTrue(url.startswith('data:'),url)
        self.assertIn('data:application/json;base64,',text)
        self.assertIn('data:text/csv;base64,',text)
        self.assertNotIn('href="report.html"',text)
        self.assertIn('SIL OPEN FONT LICENSE',text)

    def test_repeat_build_is_deterministic(self):
        before={p.name:p.read_bytes() for p in (self.output/'observatory').iterdir()}
        build_site.build(self.output,source_sha='a'*40)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.output/'observatory').iterdir()})

    @unittest.skipUnless(shutil.which('node'),'Node is needed for route logic tests')
    def test_browser_independent_route_logic(self):
        test=build_site.ROOT/'site/test_observatory.js'
        self.assertTrue(test.is_file())
        result=subprocess.run(['node','--test',str(test)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
