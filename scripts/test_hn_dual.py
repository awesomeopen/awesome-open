"""Synthetic dual HN evidence: no live collection or production-cache writes."""
import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import update_hn as hn
import chart_observations as archive
from test_hn_queue import project, empty, NOW


class DualTests(unittest.TestCase):
    def setUp(self):
        self.identity = dict(project(), broad_queries=['OpenThing', 'Other alias'])
        self.start, self.end, self.months = hn.window(NOW)
        self.hits = [
            {'objectID': '11', 'title': 'OpenThing release', 'url': 'https://github.com/org/openthing', 'created_at_i': int(self.start.timestamp())},
            {'objectID': '12', 'title': 'Unrelated Other alias', 'url': 'https://example.org', 'created_at_i': int(self.start.timestamp())},
        ]
        self.calls = []

    def getter(self, url):
        self.calls.append(parse_qs(urlsplit(url).query))
        return {'hits': self.hits, 'nbPages': 1, 'nbHits': len(self.hits)}

    def collected(self):
        return hn.collect_project(self.identity, self.start, self.end, self.months, self.getter)

    def test_exact_word_title_url_union_and_subset(self):
        result = self.collected()
        self.assertEqual([q['query'][0] for q in self.calls], ['OpenThing', 'Other alias'])
        for q in self.calls:
            self.assertEqual(q['queryType'], ['prefixNone'])
            self.assertEqual(q['restrictSearchableAttributes'], ['title,url'])
            self.assertEqual(q['typoTolerance'], ['false'])
        self.assertEqual(result['story_count'], 1)
        self.assertEqual(result['broad_story_count'], 2)
        self.assertEqual(result['monthly_counts'], [1] + [0]*23)
        self.assertEqual(result['broad_monthly_counts'], [2] + [0]*23)
        hn.validate_collection(result, self.months)

    def test_subset_and_counts_are_validated(self):
        good = self.collected()
        for field, value in [('broad_stories', good['broad_stories'][1:]),
                             ('broad_monthly_counts', [0]*24), ('broad_story_count', True)]:
            bad = copy.deepcopy(good); bad[field] = value
            with self.assertRaises(ValueError): hn.validate_collection(bad, self.months)
        bad = copy.deepcopy(good); bad['broad_stories'][0]['title'] = 'Different story'
        with self.assertRaises(ValueError): hn.validate_collection(bad, self.months)

    def test_broad_only_display_and_shared_overlay(self):
        good = self.collected()
        data = hn.display_evidence({'projects':[good], 'months':self.months})
        self.assertEqual(data['shared_monthly_maximum'], 2)
        root = ET.fromstring(hn.svg(good, data, comparison=True))
        bars = root.findall('{http://www.w3.org/2000/svg}rect')
        self.assertEqual(len(bars),48)
        self.assertEqual(bars[0].get('height'),'20.000')
        self.assertEqual(bars[24].get('height'),'15.874')
        self.assertEqual(bars[0].get('width'),'4')
        self.assertEqual(bars[24].get('width'),'2')
        only = dict(good, story_count=0, monthly_counts=[0]*24)
        self.assertTrue(hn.chart_displayable(only))

    def test_html_escapes_provider_content_and_uses_hn_ids(self):
        good = self.collected()
        good['broad_stories'][0]['title'] = '<script>alert(1)</script>'
        good['broad_stories'][0]['url'] = 'javascript:alert(1)'
        page = hn.evidence_html(good, {'months':self.months})
        self.assertNotIn('<script>', page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('id="broad"',page); self.assertIn('id="matched"',page)
        with tempfile.TemporaryDirectory() as tmp:
            hn.render({'projects':[good], 'months':self.months},Path(tmp))
            self.assertEqual(len(list(Path(tmp).iterdir())),3)

    def test_legacy_matched_cache_remains_visible_while_broad_refresh_due(self):
        old = project()
        legacy = hn.collect_project(old,self.start,self.end,self.months,self.getter)
        good = {'identity_key':hn.identity_key(old),'project':legacy,'months':self.months,
                'collected_at':(NOW-timedelta(days=1)).isoformat()}
        self.assertTrue(hn.identity_matches(good,self.identity))
        prior = {'schema_version':2,'months':self.months,'projects':[legacy], 'queue':{
            old['readme_url']:{'status':'ok','checked_at':good['collected_at'],'last_good':good}}}
        out = hn.refresh(now=NOW,projects=[self.identity],existing=prior,metadata={},getter=self.getter,request_budget=0)
        self.assertEqual(out['projects'],[legacy])
        self.assertEqual(out['selection_report']['due_projects'],1)
        self.assertEqual(out['queue'][old['readme_url']]['last_good'],good)
        out = hn.refresh(now=NOW,projects=[self.identity],existing=prior,metadata={},getter=self.getter)
        self.assertEqual(out['projects'][0]['broad_story_count'],2)

    def test_archive_round_trip_preserves_both_series(self):
        out = hn.refresh(now=NOW,projects=[self.identity],existing=empty(),metadata={},getter=self.getter)
        saved=archive.add_hn(archive.empty(),out)
        archive.validate(saved)
        recovered=archive.materialize(saved,next(iter(saved['observations'].values())))
        self.assertEqual(recovered['project'],out['projects'][0])

    def test_old_prefix_pages_cannot_complete_exact_word_refresh(self):
        old = dict(project(), queries=['OpenThing', 'Other alias'])
        partial = hn.refresh(now=NOW,projects=[old],existing=empty(),metadata={},getter=self.getter,request_budget=1)
        self.assertEqual(partial['queue'][old['readme_url']]['status'],'deferred')
        previous = list(partial['queue'][old['readme_url']]['pending'])
        self.assertNotIn('queryType=prefixNone',previous[0])
        self.calls.clear()
        new = dict(old,broad_queries=['OpenThing','Other alias'])
        done = hn.refresh(now=NOW+timedelta(days=1),projects=[new],existing=partial,metadata={},getter=self.getter)
        self.assertEqual(len(self.calls),2)
        self.assertTrue(all(q['queryType']==['prefixNone'] for q in self.calls))
        self.assertEqual(done['projects'][0]['broad_story_count'],2)

    def test_obs_precision(self):
        from project_aliases import load_optional
        reviewed=json.loads(hn.PROJECTS_PATH.read_text())['projects']
        obs=next(p for p in hn.catalog_projects(hn.SOURCE_PATH.read_text(),reviewed,load_optional(hn.ROOT/'data/project_aliases.json')) if p['name']=='OBS Studio')
        self.assertIn('OBS',obs['broad_queries'])
        for title,url in [('Release','https://obsproject.com/blog/release'),('OBS streaming plugin','https://example.org'),('OBS Studio released','https://example.org')]:
            self.assertTrue(hn.identity_reason({'title':title,'url':url},obs))
        for title,url in [('Radio Astro Obs','https://public.nrao.edu'),('Obs.js performance','https://github.com/csswizardry/Obs.js'),('OBS','https://example.org'),('Article','https://obsproject.com.evil.test')]:
            self.assertIsNone(hn.identity_reason({'title':title,'url':url},obs))
