"""Plate details (B-PR146-01): inline panels, icon triggers, one sprite, evidence links."""
import unittest

import plate_detail
from build_site import replace_literals_once


class PlateDetailTests(unittest.TestCase):
    def test_sprite_has_one_symbol_per_referenced_glyph(self):
        sprite = plate_detail.sprite()
        for key in plate_detail.SPRITE:
            self.assertEqual(sprite.count(f'<symbol id="icon-{key}"'), 1, key)
        self.assertNotIn("<title>", sprite)
        self.assertNotIn("display:none", sprite)

    def test_every_status_glyph_is_in_the_sprite(self):
        for glyph in plate_detail.STATE.values():
            self.assertIn(f"{glyph}-m", plate_detail.SPRITE)

    def test_trigger_keeps_label_and_panel_holds_title_body_links(self):
        trigger, panel = plate_detail.detail(
            "detail-x-1", "state.aged", "Stale", "Box: history", "<p>Body</p>",
            [plate_detail.link("https://example.org/", "Source")])
        self.assertIn('<span class="detail-static">Stale</span>', trigger)
        self.assertIn('data-detail="detail-x-1" aria-haspopup="dialog"', trigger)
        self.assertIn('href="#icon-state.aged-m"', trigger)
        self.assertIn("<span>Stale</span>", trigger)
        self.assertIn('<span class="visually-hidden">: Box: history</span>', trigger)
        self.assertTrue(panel.startswith('<div class="detail-body" id="detail-x-1" data-title="Box: history">'))
        self.assertLess(panel.index("Box: history</p>"), panel.index("<p>Body</p>"))
        self.assertLess(panel.index("<p>Body</p>"), panel.index('class="detail-links"'))

    def test_links_mark_site_evidence_files_only(self):
        self.assertIn('class="evidence-file" href="data/hn_evidence.json"',
                      plate_detail.link("data/hn_evidence.json", "HN evidence", "data"))
        remote = plate_detail.link("https://github.com/o/r/blob/x/data/github_metrics.json", "Snapshot", "data")
        self.assertNotIn("evidence-file", remote)
        self.assertIn('href="#icon-link.data-s"', remote)
        self.assertIn('class="feature-source" href="https://example.org/"',
                      plate_detail.link("https://example.org/", "Feature source", cls="feature-source"))

    def test_standalone_points_plate_evidence_at_the_footer_copy(self):
        page = (plate_detail.link("data/hn_evidence.json", "HN evidence", "data")
                + '<a id="hn-evidence" href="data/hn_evidence.json">HN evidence</a>')
        replacements = {
            'class="evidence-file" href="data/hn_evidence.json"': 'class="evidence-file" href="#hn-evidence"',
            'href="data/hn_evidence.json"': 'download="hn_evidence.json" href="data:application/json;base64,e30="',
        }
        out = replace_literals_once(page, replacements)
        self.assertEqual(out.count("base64,e30="), 1)
        self.assertIn('class="evidence-file" href="#hn-evidence"', out)


if __name__ == "__main__":
    unittest.main()
