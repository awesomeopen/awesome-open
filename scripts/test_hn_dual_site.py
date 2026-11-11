"""Dual HN evidence stays labeled, linked, and distinct from matched rankings."""
from copy import deepcopy
import unittest

import build_site
import plate_grid
import test_build_catalog


class HNDualSiteTests(unittest.TestCase):
    def setUp(self):
        fixture = test_build_catalog.CatalogTests()
        fixture.setUp()
        self.fixture = fixture
        self.record = fixture.add_hn()
        self.record.update(monthly_counts=[8]+[0]*23)
        self.window = dict(first="2024-11", last="2026-10", monthly_maximum=160)

    def project(self, broad=True):
        if broad:
            self.record.update(broad_story_count=34, broad_monthly_counts=[34]+[0]*23,
                               broad_search_url="https://hn.algolia.com/?query=open&prefix=false")
        catalog = self.fixture.build()
        catalog["hn_window"] = self.window
        return catalog["projects"][0], catalog

    def test_overlay_and_counts_have_distinct_evidence_links_and_text_labels(self):
        project, catalog = self.project()
        html = plate_grid.hn_box(project, self.window)
        self.assertIn('src="assets/hn/open-comparison.svg"', html)
        self.assertIn('href="assets/hn/open-evidence.html#broad">34 possible</a>', html)
        self.assertIn('href="assets/hn/open-evidence.html#matched">8 matched</a>', html)
        self.assertIn('matched stories in narrow red foreground bars', html)
        self.assertIn('0–160 stories/month, shared across HN charts and both series', html)
        self.assertIn('Possible matches come from title and URL searches', html)
        self.assertIn('2024-11', html)
        self.assertIn('2026-10', html)
        self.assertNotIn('Square-root', html)

    def test_small_chart_shows_possible_count_and_evidence_link(self):
        project, catalog = self.project()
        page = build_site.project_html(project, {"ai--language-models":"AI & Language Models"}, catalog, deferred=True)
        self.assertIn('class="name-sparkline-link" href="assets/hn/open-evidence.html#broad"', page)
        self.assertIn('alt="HN possible matches / past 2y"', page)
        self.assertIn('34 possible matches', page)
        self.assertNotIn('8 possible matches', page)

    def test_old_cache_remains_matched_only(self):
        project, catalog = self.project(broad=False)
        html = plate_grid.hn_box(project, self.window)
        self.assertIn('src="assets/hn/open.svg"', html)
        self.assertIn('Broader search has not been collected', html)
        self.assertNotIn('comparison.svg', html)
        self.assertNotIn('0 possible', html)
        self.assertNotIn('#broad', html)
        page = build_site.project_html(project, {"ai--language-models":"AI & Language Models"}, catalog, deferred=True)
        self.assertIn('href="assets/hn/open-evidence.html#matched"', page)
        self.assertIn('8 matched stories', page)

    def test_zero_matched_is_explicit_when_broad_candidates_exist(self):
        self.record.update(story_count=0, monthly_counts=[0]*24)
        project, catalog = self.project()
        self.assertIsNotNone(project["hn"])
        self.assertEqual(project["hn"]["total_stories"], 0)
        html = plate_grid.hn_box(project, self.window)
        self.assertIn('>0 matched</a>', html)
        self.assertIn('>34 possible</a>', html)

    def test_missing_evidence_is_unknown(self):
        self.assertIn('Unknown', plate_grid.hn_box({"hn":None}, self.window))
        self.assertNotIn('0 matched', plate_grid.hn_box({"hn":None}, self.window))


if __name__ == '__main__':
    unittest.main()
