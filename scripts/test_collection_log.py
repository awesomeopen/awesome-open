import unittest
import collection_log as log


class CollectionLogTests(unittest.TestCase):
    def test_truthful_dates_bounded_and_no_occurrence_as_collection(self):
        p = {'url':'https://example.org','github':{'repo':'a/b'},
             'history':[{'occurred':{'value':'2000-01-01'},'checked_at':'2026-11-18'}]}
        archive = {('hn',p['url']):[log.event(f'2026-10-{d:02d}', 'hn','HN evidence collected','https://example.org') for d in range(1,25)]}
        events = log.derive(p,(archive,{}))
        self.assertEqual(len(events),8)
        self.assertEqual(events[-1]['at'],'2026-11-18')
        self.assertEqual(events[-1]['label'],'Name-change evidence reviewed')
        self.assertNotIn('2000',str(events))
        self.assertEqual(log.derive({'url':'https://empty'},({},{})),[])

    def test_precision_and_escape(self):
        self.assertEqual(log.event('2026-11-18T01:00:00+02:00','hn','Collected','x')['at'],'2026-11-17T23:00:00Z')
        item = log.event('2026-11-18','review','<script>','https://example.org')
        html = log.render([item])
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertIn('aria-hidden="true"',html)
        self.assertNotIn('aria-live',html)
        self.assertIn('No dated collection records retained',log.render([]))

    def test_real_payload_is_bounded_and_catalog_is_untouched(self):
        import copy
        from build_site import search_index, search_text
        # Published catalog is deliberately independent of the record-only log.
        project = {'id':'a'*64,'url':'https://example.org','name':'Open Test',
                   'description':'Test','categories':[], 'history':[]}
        original = copy.deepcopy(project)
        records = [log.event('2026-11-18T12:00:00Z','hn','HN evidence collected',
                   log.REPO+'data/chart_observations.json#'+'a'*64)] * 8
        self.assertLess(len(log.render(records).encode()),4096)
        log.derive(project,({},{}))
        self.assertEqual(project,original)
        catalog={'projects':[project], 'metrics_as_of':None,'categories':[]}
        self.assertNotIn('collection',str(search_index(catalog)))
        self.assertNotIn('collection',search_text(catalog))
