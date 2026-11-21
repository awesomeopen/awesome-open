import unittest
import collection_log as log


class CollectionLogTests(unittest.TestCase):
    def test_truthful_dates_bounded_and_no_occurrence_as_collection(self):
        p = {'url':'https://example.org','github':{'repo':'a/b'},
             'history':[{'occurred':{'value':'2000-01-01'},'checked_at':'2026-11-18'}]}
        archive = {('hn',p['url']):[log.event(f'2026-10-{d:02d}', 'hn','HN evidence collected','https://example.org') for d in range(1,25)]}
        events = log.derive(p,(archive,{}))
        self.assertEqual(len(events),25)
        self.assertEqual(events[-1]['at'],'2026-11-18')
        self.assertEqual(events[-1]['label'],'Name-change evidence reviewed')
        self.assertNotIn('2000',str(events))
        self.assertEqual(events[0]['at'], '2026-10-01')
        data = log.payload(p, events, (archive, {}))
        self.assertEqual(len(data['events']), 25)
        self.assertEqual(data['events'][0][0], '2026-10-01')
        self.assertNotIn('2026-10-01', log.render(events, 'a'*64))
        self.assertIn('collection/'+'a'*64+'.json', log.render(events, 'a'*64))
        self.assertEqual(log.derive({'url':'https://empty'},({},{})),[])

    def test_undated_and_distinct_observations_survive(self):
        p = {'url':'https://example.org'}
        e = log.event('2026-10-01', 'hn', 'HN evidence collected', log.REPO+'data/chart_observations.json')
        archive = {('hn',p['url']):[dict(e, reference='a'), dict(e, reference='b'), None]}
        data = log.payload(p, log.derive(p, (archive, {})), (archive, {}))
        self.assertEqual(len(data['events']), 2)
        self.assertEqual(data['undated'], {'hn':1})
        self.assertEqual([r[2] for r in data['events']], ['a','b'])

    def test_review_and_fetch_semantics(self):
        p = {'url':'https://example.org', 'signals':{'release':{
            'checked_at':'2026-11-18T01:00:00Z', 'last_success_at':'2026-11-17T01:00:00Z',
            'last_good':{'fetched_at':'2026-11-16T01:00:00Z', 'observed_at':'2000-01-01'}}},
            'deployment':{'review_status':'approved','checked_at':'2026-10-01'},
            'function_summary':{'checked_at':'2026-10-02','features':[{'checked_at':'2026-10-03'},{}]}}
        events = log.derive(p, ({}, {}))
        self.assertEqual({e['kind'] for e in events}, {'release_attempt','release_success',
            'release_fetch','deployment_review','summary_review','feature_review'})
        self.assertNotIn('2000', str(events))
        self.assertEqual(next(e['at'] for e in events if e['kind']=='release_fetch'), '2026-11-16T01:00:00Z')

    def test_precision_and_escape(self):
        self.assertEqual(log.event('2026-11-18T01:00:00+02:00','hn','Collected','x')['at'],'2026-11-17T23:00:00Z')
        item = log.event('2026-11-18','review','<script>','https://example.org')
        html = log.render([item])
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertIn('aria-hidden="true"',html)
        self.assertNotIn('aria-live',html)
        self.assertNotIn('Download retained records',log.render([]))
        self.assertNotIn('<h4', html)
        self.assertNotIn('<summary', html)
        self.assertIn('aria-haspopup="dialog"', html)

    def test_real_payload_is_bounded_and_catalog_is_untouched(self):
        import copy
        from build_site import search_index, search_text
        # Published catalog is deliberately independent of the record-only log.
        project = {'id':'a'*64,'url':'https://example.org','name':'Open Test',
                   'description':'Test','categories':[], 'history':[]}
        original = copy.deepcopy(project)
        records = [log.event('2026-11-18T12:00:00Z','hn','HN evidence collected',
                   log.REPO+'data/chart_observations.json#'+'a'*64)] * 4
        self.assertLess(len(log.render(records).encode()),4096)
        log.derive(project,({},{}))
        self.assertEqual(project,original)
        catalog={'projects':[project], 'metrics_as_of':None,'categories':[]}
        self.assertNotIn('collection',str(search_index(catalog)))
        self.assertNotIn('collection',search_text(catalog))
