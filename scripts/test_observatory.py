"""Deterministic snapshot accounting, static fallback and thin route payload."""
from copy import deepcopy
import csv
import io
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build_observatory as obs
import build_site
from site_test_fixtures import baseline_site, copy_site_fixture
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

    def test_finding_segments_use_leader_count_and_escape_labels(self):
        index=obs.project_index(fixture())
        template=index['projects'][0]
        for values in [list(range(12,0,-1)), [10,0], [0,0], [], [None]]:
            with self.subTest(values=values):
                index['projects']=[dict(template,id=str(i),name=f'Project {i}',stars=value) for i,value in enumerate(values)]
                if values: index['projects'][0]['name']='Other projects'
                if len(values)>1: index['projects'][1]['name']='A <b> & "quoted"'
                counts=obs.aggregate(index)
                # Renaming the aggregate row must never change its membership.
                if len(values)>10: counts['star_rows'][-1][0]='A renamed tail'
                page=Page(obs.finding_html(counts))
                segments=[n for n in page.elements if n.has_class('obs-strip-segment')]
                expected=counts['star_rows'][:counts['leader_count']] if counts['stars'] else []
                leaders=[n for n in segments if n.has_class('obs-strip-leader')]
                self.assertEqual(len(leaders),len(expected))
                for node,(name,value) in zip(leaders,expected):
                    self.assertEqual(node.attrs['aria-label'],f'{name} · {value:,} stars')
                    self.assertEqual(node.attrs['title'],node.attrs['aria-label'])
                    self.assertEqual(node.attrs.get('tabindex'),'0' if value else None)
                    self.assertEqual(node.attrs['style'],f"width: {obs.bar_width(value,counts['stars'])}")
                if segments:
                    self.assertEqual(sum(int(n.attrs['data-stars']) for n in segments),counts['stars'])
                    self.assertFalse(any(n.tag=='b' for n in page.elements))
                    self.assertFalse(any(n.has_class('obs-strip') and n.attrs.get('aria-hidden')=='true' for n in page.elements))

    @staticmethod
    def shared_summary(result):
        groups = lambda kind: [dict(name=g['name'], ids=[p['id'] for p in g['projects']], tags=g['tags']) for g in result[kind]]
        return dict(identical=groups('identical'), variants=groups('variants'), tool_count=result['tool_count'],
                    identical_tool_count=result['identical_tool_count'], variant_tool_count=result['variant_tool_count'])

    EMPTY_SHARED = dict(identical=[], variants=[], tool_count=0, identical_tool_count=0, variant_tool_count=0)

    @staticmethod
    def named_projects(pairs):
        base=obs.project_index(fixture())['projects'][0]
        return [dict(base,id=identifier,name=name,url='https://example.com/'+identifier) for identifier,name in pairs]

    def test_shared_names_identical_pairs_three_way_and_deterministic_order(self):
        projects=self.named_projects([('z2','Zebra'),('a3','Alpha'),('z1','Zebra'),
                                      ('a1','Alpha'),('a2','Alpha'),('solo','Unique')])
        before=deepcopy(projects);result=obs.shared_names(projects)
        self.assertEqual(self.shared_summary(result),dict(
            identical=[dict(name='Alpha',ids=['a1','a2','a3'],tags=[]),dict(name='Zebra',ids=['z1','z2'],tags=[])],
            variants=[],tool_count=5,identical_tool_count=5,variant_tool_count=0))
        self.assertEqual(result['identical'][0]['projects'][0],projects[3])
        self.assertEqual(projects,before)
        self.assertEqual(obs.shared_names(list(reversed(projects))),result)

    def test_shared_names_sort_unicode_codepoints_including_supplementary_planes(self):
        bmp='\ue000';supplementary='\U00010000'
        projects=self.named_projects([('a2',supplementary),('b2',bmp),('a1',supplementary),('b1',bmp),
            (supplementary,'Tie'),(bmp,'Tie'),('case-a2',supplementary+'a'),('case-b2',bmp+'a'),
            ('case-a1',supplementary+'A'),('case-b1',bmp+'A')])
        self.assertEqual(self.shared_summary(obs.shared_names(projects)),dict(
            identical=[dict(name='Tie',ids=[bmp,supplementary],tags=[]),dict(name=bmp,ids=['b1','b2'],tags=[]),
                       dict(name=supplementary,ids=['a1','a2'],tags=[])],
            variants=[dict(name=bmp+'A / '+bmp+'a',ids=['case-b1','case-b2'],tags=['Case']),
                      dict(name=supplementary+'A / '+supplementary+'a',ids=['case-a1','case-a2'],tags=['Case'])],
            tool_count=10,identical_tool_count=6,variant_tool_count=4))

    def test_shared_names_deduplicate_identity_across_categories(self):
        first,other=self.named_projects([('a','Shared'),('b','Shared')])
        repeated=dict(first,categories=['two'])
        self.assertEqual(self.shared_summary(obs.shared_names([first,repeated])),self.EMPTY_SHARED)
        self.assertEqual(self.shared_summary(obs.shared_names([first,repeated,other])),dict(
            identical=[dict(name='Shared',ids=['a','b'],tags=[])],variants=[],tool_count=2,identical_tool_count=2,variant_tool_count=0))

    def test_shared_names_one_key_combines_case_and_separators(self):
        projects=self.named_projects([('a','OpenPilot'),('b','openpilot'),('c','Open pilot'),
            ('d','open-dashboard'),('e','OpenDashboard'),('f','Open_Tool'),('g','Open Tool'),
            ('h','OpenBot'),('i','OpenBot'),('j','openbot')])
        result=obs.shared_names(projects)
        self.assertEqual(self.shared_summary(result),dict(identical=[],variants=[
            dict(name='Open Tool / Open_Tool',ids=['g','f'],tags=['Spacing']),
            dict(name='Open pilot / OpenPilot / openpilot',ids=['c','a','b'],tags=['Case','Spacing']),
            dict(name='OpenBot / openbot',ids=['h','i','j'],tags=['Case','Exact duplicates']),
            dict(name='OpenDashboard / open-dashboard',ids=['e','d'],tags=['Case','Spacing'])],
            tool_count=10,identical_tool_count=0,variant_tool_count=10))
        self.assertEqual(result['tags'],{'Case':3,'Spacing':3,'Plural':0,'Spelling':0,'Exact duplicates':1})
        ids=[p['id'] for group in result['identical']+result['variants'] for p in group['projects']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(obs.shared_names(list(reversed(projects))),result)

    def test_reviewed_plural_pair_is_a_spelling_variant(self):
        rows = self.named_projects([('a', 'OpenTask'), ('b', 'OpenTasks')])
        for row in rows: row['name_match'] = {'key': 'reviewed:opentask-plural', 'reason': 'plural'}
        result = obs.shared_names(rows + [rows[0]])
        self.assertEqual(result['tool_count'], 2)
        self.assertEqual(result['variants'][0]['tags'], ['Plural'])
        self.assertEqual(obs.shared_names(list(reversed(rows))), result)
        self.assertEqual(obs.shared_names(rows[:1])['tool_count'], 0)
        self.assertNotEqual(obs.name_key('OpenTask'), obs.name_key('OpenTasks'))
        self.assertEqual(obs.marked_name('OpenTasks', ['OpenTask', 'OpenTasks']),
                         'OpenTask<span class="name-diff">s</span>')
        self.assertEqual(obs.marked_name('OpenTask', ['OpenTasks', 'OpenTask']), 'OpenTask')
        expanded_case = self.named_projects([('a', 'Openİ'), ('b', 'Openi\u0307')])
        self.assertEqual(obs.shared_names(expanded_case)['variants'][0]['tags'], ['Case'])
        mixed = self.named_projects([('a', 'Open Task'), ('b', 'openTasks')])
        for row in mixed: row['name_match'] = {'key': 'reviewed:opentask-plural', 'reason': 'plural'}
        self.assertEqual(obs.shared_names(mixed)['variants'][0]['tags'], ['Case', 'Spacing', 'Plural'])
        for names in [('OpenTool', 'OpenTools'), ('OpenNew', 'OpenNews'), ('OpenTask', 'OpenTasks.')]:
            self.assertEqual(obs.shared_names(self.named_projects(list(zip(('a', 'b'), names))))['tool_count'], 0)

    def test_shared_names_no_alias_inference_and_empty_singleton(self):
        for pairs in [[],[('a','Tool')],[('a','Tool'),('b','Tool.'),('c','Tools'),('d','Tool OSS'),('e','T00l')],
                      [('a','---'),('b','_ _')],[('a','OpenTool'),('b','Open\u200bTool'),('c','Open\ufeffTool')]]:
            with self.subTest(pairs=pairs):
                self.assertEqual(self.shared_summary(obs.shared_names(self.named_projects(pairs))),self.EMPTY_SHARED)

    def test_shared_names_separator_set_is_unicode_white_space_hyphen_underscore(self):
        separators=[*range(0x09,0x0e),0x20,0x85,0xa0,0x1680,*range(0x2000,0x200b),
                    0x2028,0x2029,0x202f,0x205f,0x3000,ord('-'),ord('_')]
        for codepoint in separators:
            with self.subTest(codepoint=hex(codepoint)):
                result=obs.shared_names(self.named_projects([('a','OpenTool'),('b','Open'+chr(codepoint)+'Tool')]))
                self.assertEqual((result['tool_count'],result['variant_tool_count']),(2,2))
                self.assertEqual(result['variants'][0]['tags'],['Spacing'])
        # Python str.isspace and JavaScript \s differ from Unicode White_Space.
        for codepoint in [0x1c,0x1d,0x1e,0x1f,0x180e,0x200b,0xfeff,ord('.'),0x2010,0x2013]:
            with self.subTest(excluded=hex(codepoint)):
                result=obs.shared_names(self.named_projects([('a','OpenTool'),('b','Open'+chr(codepoint)+'Tool')]))
                self.assertEqual(result['tool_count'],0)

    def test_marked_names_flag_case_and_separator_positions(self):
        names=['Open pilot','OpenPilot','openpilot']
        self.assertEqual(obs.marked_name('Open pilot',names),
            '<span class="name-diff">O</span>pen<span class="name-diff name-gap"> </span><span class="name-diff">p</span>ilot')
        self.assertEqual(obs.marked_name('OpenPilot',names),
            '<span class="name-diff">O</span>pen<span class="name-diff name-nogap" aria-hidden="true"></span><span class="name-diff">P</span>ilot')
        self.assertEqual(obs.marked_name('<b>',['<b>']),'&lt;b&gt;')
        self.assertEqual(obs.marked_name('A&b',['A&b','a&b']),'<span class="name-diff">A</span>&amp;b')

    def test_shared_names_aggregate_uses_only_selected_category_and_license(self):
        index=obs.project_index(fixture())
        index['projects']=self.named_projects([('a','Shared'),('b','Shared'),('c','Shared'),('d','shared')])
        for project,categories,license in zip(index['projects'],
                [['one','two'],['one'],['two'],['two']],['MIT','MIT',None,None]):
            project.update(categories=categories,license=license)
        self.assertEqual(self.shared_summary(obs.aggregate(index)['shared_names']),dict(
            identical=[],variants=[dict(name='Shared / shared',ids=['a','b','c','d'],tags=['Case','Exact duplicates'])],
            tool_count=4,identical_tool_count=0,variant_tool_count=4))
        def selected(category,known):
            return [p for p in index['projects'] if category in p['categories'] and bool(p['license'])==known]
        self.assertEqual(self.shared_summary(obs.aggregate(index,selected('one',True))['shared_names']),dict(
            identical=[dict(name='Shared',ids=['a','b'],tags=[])],variants=[],tool_count=2,identical_tool_count=2,variant_tool_count=0))
        self.assertEqual(self.shared_summary(obs.aggregate(index,selected('two',False))['shared_names']),dict(
            identical=[],variants=[dict(name='Shared / shared',ids=['c','d'],tags=['Case'])],tool_count=2,identical_tool_count=0,variant_tool_count=2))
        for category,known in [('one',False),('two',True)]:
            self.assertEqual(self.shared_summary(obs.aggregate(index,selected(category,known))['shared_names']),self.EMPTY_SHARED)

    def test_shared_names_render_plates_escaped_and_empty_selection(self):
        catalog=fixture();index=obs.project_index(catalog)
        dangerous='</h4><img src=x onerror=alert(1)>'
        index['projects']=self.named_projects([('b',dangerous),('a',dangerous),('d','CASE'),('c','case')])
        index['projects'][0]['url']='https://github.com/own"er/b?x=1&y="quoted"'
        index['projects'][0]['description']='<script>alert(1)</script>'
        html=obs.render(index,obs.aggregate(index),obs.coverage(catalog,{}));page=Page(html)
        self.assertEqual(page.by_id['shared-name-count'].text,'4')
        self.assertEqual(page.by_id['identical-name-count'].text,'2')
        self.assertEqual(page.by_id['variant-name-count'].text,'2')
        self.assertNotIn(dangerous,html);self.assertNotIn('<script>alert',html)
        disclosure=page.by_id['name-groups']
        self.assertEqual(disclosure.tag,'details');self.assertNotIn('open',disclosure.attrs)
        self.assertEqual(disclosure.children[0].tag,'summary')
        # The native control needs a label, but ordinary wording is editable.
        summary=page.by_id['name-group-summary']
        self.assertTrue(disclosure.children[0].text.replace(summary.text,'').strip())
        self.assertIn(page.by_id['name-group-summary'],disclosure.children[0].descendants())
        self.assertIn(page.by_id['name-group-bands'],disclosure.descendants('div'))
        self.assertEqual(page.by_id['name-group-summary'].text,'2 groups · 4 tools')
        method=page.by_id['name-method']
        self.assertIn(method,disclosure.descendants('details'));self.assertNotIn('open',method.attrs)
        plates=page.by_id['identical-name-groups'].descendants('article')
        self.assertEqual(len(plates),1)
        self.assertEqual([n.attrs['data-project-id'] for n in plates[0].descendants('div') if 'data-project-id' in n.attrs],['a','b'])
        repo=[n for n in plates[0].descendants('a') if n.has_class('obs-repo')][1]
        self.assertEqual(repo.attrs['href'],index['projects'][0]['url'])
        self.assertEqual([n.text for n in repo.descendants('span') if n.has_class('obs-repo-owner')],['own"er'])
        records=[n for n in plates[0].descendants('a') if n.has_class('obs-record')]
        self.assertEqual([n.attrs['href'] for n in records],['../#project-a','../#project-b'])
        tally=page.by_id['name-tally']
        clusters=[n for n in tally.descendants('a') if n.has_class('obs-cluster')]
        self.assertEqual([n.attrs['href'] for n in clusters],['#name-group-1','#name-group-2'])
        groups = obs.aggregate(index)['shared_names']
        for cluster, group in zip(clusters, groups['identical'] + groups['variants']):
            labels = [p['name'] + ' (' + re.sub(r'^https?://(github\.com/)?', '', p['url']) + ')' for p in group['projects']]
            marks = [n for n in cluster.descendants('span') if n.has_class('obs-mark')]
            self.assertEqual([n.attrs['title'] for n in marks], labels)
            for label in labels:
                self.assertIn(label, cluster.attrs['title'])
                self.assertIn(label, cluster.attrs['aria-label'])
            self.assertIn(cluster.attrs['href'][1:], page.by_id)
        self.assertEqual(sum(1 for n in tally.descendants('span') if n.has_class('obs-tally-break')),1)
        self.assertEqual(len(page.images),1)
        index['projects']=[]
        page=Page(obs.render(index,obs.aggregate(index),obs.coverage(catalog,{})))
        for key in ['shared-name-count','identical-name-count','variant-name-count']:
            self.assertEqual(page.by_id[key].text,'0')
        self.assertEqual(page.by_id['identical-name-groups'].descendants('article'),[])
        self.assertIn('No shared names in this selection.',page.by_id['name-tally'].text)
        self.assertIn('No identical name in this selection.',page.by_id['identical-name-groups'].text)
        self.assertEqual(page.by_id['selection-summary'].text,'0/0 selected.')

    def test_hn_global_dedup_and_partial_scorecard_remain_explicit(self):
        catalog=fixture()
        hn=dict(projects=[dict(readme_url='https://github.com/Example/Alpha/',eligible=True,story_count=2,stories=[{'id':'1'},{'id':'1'},{'id':'2'}]),dict(readme_url='https://example.com/beta',eligible=False,story_count=1,stories=[{'id':'2'}])])
        covered=obs.coverage(catalog,hn)
        self.assertEqual((covered['hn_tracked'],covered['hn_eligible'],covered['hn_unique_stories'],covered['hn_project_matches']),(2,2,2,3))
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
        self.assertEqual(list(rows[0])[:4],['id','name','url','description'])
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
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline build')):
            cls.output,cls.catalog=baseline_site(source_sha='a'*40)
        cls.html=(cls.output/'observatory/index.html').read_text();cls.page=Page(cls.html)
        cls.snapshot=json.loads((cls.output/'observatory/snapshot.json').read_text())

    def test_integrated_same_revision_complete_static_records(self):
        index=self.snapshot
        self.assertEqual(index['source_sha'],self.catalog['source_sha'])
        self.assertEqual(index['metrics_as_of'],self.catalog['metrics_as_of'])
        self.assertEqual([p['id'] for p in index['projects']],[p['id'] for p in self.catalog['projects']])
        self.assertIn('hidden',self.page.by_id['observatory-filters'].attrs)
        self.assertEqual(len(self.page.ids),len(set(self.page.ids)))
        for chart in ['category','license','star','age','push','release']:
            node=self.page.by_id[chart+'-chart']
            self.assertEqual(len(node.descendants('table')),1)
            visual=[n for n in node.descendants('div') if n.has_class('obs-bars')]
            self.assertEqual(len(visual),1)
            self.assertEqual(visual[0].attrs['aria-hidden'],'true')
            self.assertEqual(node.descendants('svg'),[])
            rows=[(n.attrs['data-key'],int(n.attrs['data-count'])) for n in visual[0].descendants('li')]
            table=[(r.attrs['data-key'],int(r.attrs['data-count'])) for r in node.descendants('tbody')[0].children]
            self.assertEqual(rows,table)
        shared=max(v for _,v in self.snapshot['aggregate']['pushes']+self.snapshot['aggregate']['releases'])
        self.assertIn('· shared scale',self.page.by_id['release-chart'].text)
        self.assertIn(f'{shared:,} projects',self.page.by_id['push-chart'].text)
        counts=[v for _,v in self.snapshot['aggregate']['categories'] if _!='Unknown']
        self.assertEqual(counts,sorted(counts,reverse=True))
        self.assertIn('href="observatory/"',(self.output/'index.html').read_text())
        self.assertNotIn('observatory.js',(self.output/'index.html').read_text())

    def test_header_uses_ledger_links(self):
        nav=next(n for n in self.page.elements if n.has_class('obs-nav'))
        links=nav.descendants('a')
        self.assertEqual(len(links),4)
        self.assertEqual([a.attrs['href'] for a in links],['../#catalog','./','../scoreboard/','../spotlight/'])
        self.assertEqual([a.attrs.get('aria-current') for a in links],[None,'page',None,None])

    def test_metric_art_sources_and_label_backings(self):
        expected={c['id']:c['artwork']['variants']['s']['path']
                  for c in self.catalog['categories'] if c.get('artwork')}
        self.assertTrue(expected)
        page=self.page
        options=page.by_id['category-filter'].descendants('option')
        self.assertNotIn('data-metric-art', options[0].attrs)
        for option in options[1:]:
            source=option.attrs.get('data-metric-art','')
            path=expected.get(option.attrs['value'])
            if not path:
                self.assertEqual(source,'')
            else:
                self.assertEqual(source,'../'+path)
                self.assertTrue((self.output/path).is_file())
        for metric in page.by_id['metrics'].children:
            self.assertEqual(len(metric.descendants('dt')[0].children),1)
            self.assertEqual(metric.descendants('dt')[0].children[0].tag,'span')

    def test_project_data_downloads_and_copy(self):
        text=self.html; page=self.page
        section=page.by_id['project-records']
        self.assertEqual([(a.attrs['href'], a.text) for a in section.descendants('a')],
                         [('projects.csv', 'Download selection CSV'), ('snapshot.json', 'Download complete snapshot JSON')])
        self.assertEqual(section.descendants('table'), [])
        self.assertEqual(section.descendants('details'), [])
        for retired in ['project-data', 'project-table', 'project-count']:
            self.assertNotIn(retired, page.ids)
        for copy in ['Projects by category', 'Top 10 specimen by GitHub stars.', 'Cached GitHub license identifiers.',
                     'Days since last GitHub release (cached).',
                     'Days since GitHub repository creation.', 'Dates are UTC.', 'License detected']:
            self.assertIn(copy, text)
        for removed in ['Where the collection gathers', 'Attention is uneven',
                        'Read the distribution', 'Inspect or take the data',
                        'What is actually covered?', 'not the project founding date',
                        'obs-kicker', 'Detected license available', 'Unaffected by filters',
                        'Sorted by count', 'Variant groups with', 'Data table', 'standalone report']:
            self.assertNotIn(removed, text)

    def test_top_ten_share_is_computed_and_displayed(self):
        # Derive the value from project observations, not the renderer's aggregate.
        stars=sorted((p['stars'] for p in self.snapshot['projects']
                      if p['github'] and p['stars'] is not None),reverse=True)
        expected=round(100 * sum(stars[:10]) / sum(stars),1)
        self.assertGreater(len(stars),10)
        self.assertEqual(self.snapshot['aggregate']['concentration'],expected)
        page=self.page
        finding=page.by_id['obs-finding-text']
        aside=next(n for n in page.elements if n.has_class('obs-finding'))
        leaders=[n for n in page.elements if n.has_class('obs-strip-leader')]
        tail=[n for n in page.elements if n.has_class('obs-strip-tail')]
        ranked=sorted((p for p in self.snapshot['projects'] if p['github'] and p['stars'] is not None),key=lambda p:(-p['stars'],p['name'],p['id']))
        self.assertEqual(len(leaders),min(10,len(ranked)))
        total=sum(p['stars'] for p in ranked)
        for node,project in zip(leaders,ranked):
            self.assertEqual(node.attrs['aria-label'],f"{project['name']} · {project['stars']:,} stars")
            self.assertEqual(node.attrs['style'],f"width: {obs.bar_width(project['stars'],total)}")
        self.assertEqual(sum(int(n.attrs['data-stars']) for n in leaders+tail),total)
        self.assertEqual(aside.tag,'aside')
        self.assertEqual(aside.attrs['aria-labelledby'],'obs-finding-text')
        self.assertIn(finding,aside.descendants('p'))
        self.assertEqual(re.findall(r'(\d+(?:\.\d+)?)%',finding.text),[f'{expected:.1f}'])
        # Keep the subject, unit and top-ten scope, without fixing a sentence.
        for meaning in [r'\b10\b',r'\bprojects\b',r'\bstars\b']:
            self.assertRegex(finding.text,meaning)

    def test_shared_names_static_match_snapshot(self):
        expected=obs.shared_names(self.snapshot['projects'])
        page=self.page
        self.assertEqual(page.by_id['shared-name-count'].text,str(expected['tool_count']))
        self.assertEqual(page.by_id['identical-name-count'].text,str(expected['identical_tool_count']))
        self.assertEqual(page.by_id['variant-name-count'].text,str(expected['variant_tool_count']))
        self.assertEqual(len(page.ids),len(set(page.ids)))
        disclosure=page.by_id['name-groups']
        self.assertEqual(disclosure.tag,'details');self.assertNotIn('open',disclosure.attrs)
        marks=[n for n in page.by_id['name-tally'].descendants('span') if n.has_class('obs-mark')]
        self.assertEqual(len(marks),expected['tool_count'])
        self.assertEqual(sum(n.has_class('obs-mark-identical') for n in marks),expected['identical_tool_count'])
        number=0
        for container,key in [('identical-name-groups','identical'),('variant-name-groups','variants')]:
            plates=page.by_id[container].descendants('article')
            self.assertEqual(len(plates),len(expected[key]))
            for plate,wanted in zip(plates,expected[key]):
                number+=1
                self.assertEqual(plate.attrs['id'],f'name-group-{number}')
                self.assertEqual(plate.attrs['data-name'],wanted['name'])
                self.assertEqual([t.text for t in plate.descendants('span') if t.has_class('obs-tag')],wanted['tags'])
                columns=[n for n in plate.descendants('div') if n.has_class('obs-plate-project')]
                self.assertEqual([c.attrs['data-project-id'] for c in columns],[p['id'] for p in wanted['projects']])
                for column,project in zip(columns,wanted['projects']):
                    repo=[n for n in column.descendants('a') if n.has_class('obs-repo')][0]
                    self.assertEqual(repo.attrs['href'],project['url'])
                    self.assertEqual([n.text for n in column.descendants('p') if n.has_class('obs-plate-desc')],[project['description']])

    def test_csv_covers_displayed_project_fields(self):
        rows=list(csv.DictReader(io.StringIO((self.output/'observatory/projects.csv').read_text())))
        self.assertEqual(len(rows), len(self.snapshot['projects']))
        for row, project in zip(rows, self.snapshot['projects']):
            for key in ['id', 'name', 'url', 'description', 'license', 'stars', 'created_at',
                        'pushed_at', 'release_at', 'release_status', 'release_checked_at']:
                self.assertEqual(row[key], obs.safe_csv(project[key]))
            self.assertEqual(row['categories'], '; '.join(project['categories']))
            self.assertEqual(row['source_sha'], self.snapshot['source_sha'])

    def test_prefooter_logo(self):
        logo=build_site.ROOT/'site/brand/botanical-128.png'
        page=self.page
        logos=[image for image in page.images if image.get('class') == 'obs-logo']
        self.assertEqual(len(logos), 1)
        image=logos[0]
        self.assertEqual(image['class'], 'obs-logo')
        self.assertEqual((image['width'], image['height']), ('128', '128'))
        self.assertEqual(image['alt'], 'Awesome Open* botanical logo')
        self.assertEqual([n for n in page.nodes('figcaption') if any(n in c.descendants('figcaption') for c in page.elements if c.has_class('obs-closing-mark'))], [])
        self.assertEqual(image['src'], '../brand/botanical-128.png')
        main=page.by_id['observatory-main']
        closing=[node for node in page.elements if node.has_class('obs-closing-mark')]
        self.assertEqual(len(closing), 1)
        self.assertIs(main.children[-1], closing[0])
        self.assertEqual(closing[0].tag, 'div')
        self.assertEqual([node.tag for node in closing[0].children], ['img'])
        self.assertEqual(closing[0].text.strip(), '')
        self.assertEqual(closing[0].children[0].attrs, image)
        hero=next(node for node in page.elements if node.has_class('obs-hero'))
        self.assertEqual(hero.descendants('img'), [])
        parent=next(node for node in page.elements if main in node.children)
        self.assertTrue(parent.children[parent.children.index(main)+1].has_class('obs-footer'))
        self.assertEqual((self.output/'brand/botanical-128.png').read_bytes(), logo.read_bytes())

    def test_thin_index_and_no_runtime_remote_dependencies(self):
        node=self.page.by_id['observatory-data'];data=json.loads(node.text)
        self.assertLess(len(node.text.encode()),len(json.dumps(self.catalog).encode())/3)
        self.assertTrue(all(isinstance(p['description'],str) and p['description'] for p in data['projects']))
        for key in ['signals','artwork','function_summary','alternatives','star_history']:
            self.assertFalse(any(key in p for p in data['projects']))
        for script in self.page.nodes('script'):
            self.assertFalse(script.attrs.get('src','').startswith(('https:','http:')))
        for node in self.page.nodes('script')+self.page.nodes('link')+self.page.nodes('img'):
            path=node.attrs.get('src') or node.attrs.get('href')
            if path and not path.startswith(('https:','http:','data:','#')):
                self.assertTrue((self.output/'observatory'/path.split('?')[0]).is_file(),path)
        specimens=[image for image in self.page.images if image.get('class') == 'obs-pair-art']
        expected={p['id']:p['specimen'] for p in data['projects'] if p.get('specimen')}
        self.assertEqual(len(specimens),len(expected))
        for plate in self.page.elements:
            if not plate.has_class('obs-plate-project'):
                continue
            pid=plate.attrs['data-project-id']
            art=plate.descendants('img')
            self.assertEqual(len(art), int(pid in expected))
            if art:
                self.assertEqual(art[0].attrs['src'],expected[pid]['path'])
                self.assertEqual(art[0].attrs['alt'],expected[pid]['alt'])
            facts=plate.descendants('dl')[0]
            self.assertEqual(facts.children[-2].text,'Catalog')
            self.assertEqual(facts.children[-1].text,'OP-'+pid[:8].upper())

    def test_footer_pattern_resolves_to_exact_source_bytes(self):
        pattern = 'patterns/navypattern2.png'
        source = (build_site.ROOT / 'site' / pattern).read_bytes()
        css = (self.output / 'observatory/observatory.css').read_text()
        self.assertIn(f'url(../{pattern})', css)
        self.assertNotIn('/awesome-open/', css)
        self.assertEqual((self.output / 'observatory' / '..' / pattern).read_bytes(), source)

    def test_repeat_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            output=copy_site_fixture(self.output,Path(temp)/'site')
            before={p.name:p.read_bytes() for p in (output/'observatory').iterdir()}
            build_site.build(output,source_sha='a'*40)
            self.assertEqual(before,{p.name:p.read_bytes() for p in (output/'observatory').iterdir()})

    @unittest.skipUnless(shutil.which('node'),'Node is needed for route logic tests')
    def test_browser_independent_route_logic(self):
        test=build_site.ROOT/'site/test_observatory.js'
        self.assertTrue(test.is_file())
        result=subprocess.run(['node','--test',str(test)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()

