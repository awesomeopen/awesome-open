"""Weekly selection, archival and jar-fit contracts; no GitHub requests."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

import weekly_draw as draw
from build_jar_preview import (assign_to_jars, fitted_image, subject_box, composition_box,
                               DISPLAY, SPECIMEN_INTERIORS, SPECIMEN_BODY_SPANS,
                               SPECIMEN_INTERIOR_CONTOURS, interior_clip)
from build_draw_archive import build as build_archive, week_label

ROOT = Path(__file__).resolve().parents[1]


def catalog(n=45):
    return {'categories': [{'id': 'tools', 'name': 'Tools'}], 'projects': [
        {'id': str(i), 'name': f'Open {i}', 'url': f'https://example.com/{i}',
         'description': 'A tool.', 'categories': ['tools'],
         'artwork': {'path': f'specimens/{i}.webp', 'alt': 'A drawing.', 'width': 100, 'height': 100}}
        for i in range(n)]}


class WeeklyDrawTests(unittest.TestCase):
    def test_fixed_seed_order_independence_and_stars_independence(self):
        cat = catalog()
        a = draw.advance(draw.empty(), cat, date(2026, 10, 16))
        cat['projects'].reverse()
        for p in cat['projects']:
            p['github'] = {'stars': 999999}
        b = draw.advance(draw.empty(), cat, date(2026, 10, 16))
        self.assertEqual(a, b)
        again = draw.advance(a, catalog(100), date(2026, 10, 18))
        self.assertEqual(a['editions'], again['editions'])
        self.assertEqual(a['editions'][0]['draw_week'], '2026-10-12')
        self.assertEqual(a['editions'][0]['display_week'], '2026-10-19')
        self.assertEqual(draw.visible(a), [])

    def test_cooldown_and_next_week_activation(self):
        doc = draw.empty()
        for week in range(12):
            doc = draw.advance(doc, catalog(), date(2026, 10, 12) + timedelta(weeks=week))
        self.assertEqual(len(doc['editions']), 12)
        for index, item in enumerate(doc['editions']):
            ids = {p['id'] for p in item['projects']}
            preceding = doc['editions'][max(0,index-4):index]
            self.assertFalse(ids & {p['id'] for e in preceding for p in e['projects']})
        self.assertEqual(draw.current(doc, catalog()), doc['editions'][-2])

    def test_illustration_required_strict_cooldown_and_missed_weeks(self):
        cat = catalog(7)
        cat['projects'].append({'id': 'no-art', 'github': {'stars': 999999}})
        first = draw.advance(draw.empty(), cat, date(2026, 10, 12))
        second = draw.advance(first, cat, date(2026, 10, 19))
        self.assertEqual(len(second['editions']), 1)
        self.assertEqual(draw.current(second, cat), first['editions'][0])
        missed = draw.advance(second, cat, date(2026, 12, 1))
        self.assertEqual(len(missed['editions']), 2)
        self.assertEqual(missed['editions'][-1]['draw_week'], '2026-11-30')
        self.assertNotIn('no-art', missed['editions'][-1]['candidates'])

    def test_missing_current_art_falls_back_without_redraw(self):
        doc = draw.advance(draw.empty(), catalog(), date(2026, 10, 12))
        doc = draw.advance(doc, catalog(), date(2026, 10, 19))
        doc = draw.advance(doc, catalog(), date(2026, 10, 26))
        cat = catalog()
        missing = doc['editions'][1]['projects'][0]['id']
        del next(p for p in cat['projects'] if p['id'] == missing)['artwork']
        self.assertEqual(draw.current(doc, cat), doc['editions'][0])
        self.assertEqual(len(doc['editions']), 3)

    def test_corrupt_selection_and_reverse_clock_rejected(self):
        doc = draw.advance(draw.empty(), catalog(), date(2026, 10, 16))
        bad = deepcopy(doc)
        bad['editions'][0]['projects'].reverse()
        with self.assertRaises(ValueError):
            draw.validate(bad)
        with self.assertRaises(ValueError):
            draw.advance(doc, catalog(), date(2026, 10, 15))

    def test_archive_hides_pending_and_escapes_snapshot_copy(self):
        cat = catalog()
        cat['projects'][0]['description'] = '<script>bad</script>'
        doc = draw.advance(draw.empty(), cat, date(2026, 10, 12))
        with tempfile.TemporaryDirectory() as tmp:
            build_archive(cat, doc, tmp, ROOT)
            self.assertNotIn('id="2026-W43"', (Path(tmp)/'spotlight/index.html').read_text())
            empty = (Path(tmp)/'spotlight/index.html').read_text()
            # B42: the archive uses the Observatory route shell, not bare ledger styles.
            for marker in ('href="../observatory/observatory.css?v=', 'class="obs-header"', 'aria-current="page">Spotlight', 'class="obs-closing-mark"', 'class="obs-footer"', 'Source revision:'):
                self.assertIn(marker, empty)
            doc = draw.advance(doc, cat, date(2026, 10, 19))
            build_archive(cat, doc, tmp, ROOT)
            html = (Path(tmp)/'spotlight/index.html').read_text()
            self.assertIn('id="2026-W43"', html)
            self.assertNotIn('id="2026-W44"', html)
            self.assertNotIn('<script>bad</script>', html)
            self.assertIn('href="#2026-W43">2026-W43</a>', html)
            self.assertIn('<span data-metric>2026-W43</span>', html)
            for removed in ('Week of ', 'How the draw works', 'Stars do not affect the draw.',
                            'class="obs-finding', 'Return to project ledger', '>Observatory</a>', '#week-'):
                self.assertNotIn(removed, html)
            self.assertIn('class="obs-jump draw-jump" aria-label="Sections" hidden', html)
            footer = html.split('<footer class="obs-footer">', 1)[1]
            self.assertIn('href="draws.json" download>Download draw records</a> · ', footer)
            self.assertLess(footer.index('Draw contract</a>'), footer.index('>GitHub</a>'))
            self.assertFalse((Path(tmp) / 'draws').exists())

            self.assertEqual(len(json.loads((Path(tmp)/'spotlight/draws.json').read_text())['editions']), 1)

    def test_iso_week_labels_use_the_iso_year_at_calendar_boundaries(self):
        self.assertEqual(week_label('2026-10-19'), '2026-W43')
        self.assertEqual(week_label('2025-12-29'), '2026-W01')
        self.assertEqual(week_label('2027-01-01'), '2026-W53')

    def test_fit_assigns_wide_and_tall_without_changing_jars(self):
        assets = {a['id']: a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
        projects = catalog(7)['projects']
        for i, p in enumerate(projects):
            p['artwork']['width'] = 30 + i * 50
        ordered = assign_to_jars(projects, assets, {})
        self.assertEqual({p['id'] for p in ordered}, {p['id'] for p in projects})
        self.assertEqual(ordered, assign_to_jars(list(reversed(projects)), assets, {}))
        for project, slot in zip(ordered, DISPLAY):
            style = fitted_image(project, slot, assets[slot[1]], {})
            scale = float(style.split('%')[0].split(':')[1])/100
            interior = SPECIMEN_INTERIORS[slot[1]]
            ratio = assets[slot[1]]['width']/assets[slot[1]]['height']*interior[2]/interior[3]
            self.assertLessEqual(scale, 1)
            self.assertLessEqual(scale*ratio*project['artwork']['height']/project['artwork']['width'], 1)


    def test_week_one_preserves_selected_set_and_protects_worst_fit(self):
        assets = {a['id']: a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
        projects = json.loads((ROOT/'data/weekly_draws.json').read_text())['editions'][0]['projects']
        manifest = json.loads((ROOT/'site/specimens/cutouts.json').read_text())['cutouts']
        cutouts = {pid: {'bbox': entry['subject_bbox']} for pid, entry in manifest.items()}
        ordered = assign_to_jars(projects, assets, cutouts)
        self.assertEqual(len(ordered), 7)
        self.assertEqual({p['id'] for p in ordered}, {p['id'] for p in projects})
        self.assertEqual(ordered, assign_to_jars(projects[::-1], assets, cutouts))
        self.assertEqual(ordered[3]['name'], 'OpenObserve')
        self.assertNotEqual(ordered[3]['name'], 'Open Library')
        for p in projects:
            self.assertIn(p['id'], cutouts)

    def test_invalid_or_missing_bounds_use_full_canvas(self):
        p = catalog(1)['projects'][0]
        for box in (None, [], [0, 0, 0, 1], [-1, 0, 1, 1], [0, 0, 2, 1],
                    [0, 0, float('nan'), 1], [0, 0, float('inf'), 1],
                    [False, 0, 1, 1], ['0', 0, 1, 1]):
            self.assertEqual(subject_box(p, {'0': {'bbox': box}}), [0, 0, 1, 1])
        self.assertEqual(subject_box(p, {}), [0, 0, 1, 1])
        self.assertEqual(subject_box(p, {'0': {'bbox': [.1, .2, .8, .9]}}), [.1, .2, .8, .9])

    def test_unreviewed_subjects_fit_wall_width_and_keep_vertical_clearance(self):
        assets = {a['id']: a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
        for slot in DISPLAY:
            asset = assets[slot[1]]
            h = round(slot[3] * (.94 if slot[1] == 'central' else .82))
            w = round(h * asset['width'] / asset['height'])
            interior = SPECIMEN_INTERIORS[slot[1]]
            ww, wh = w * interior[2] / 100, h * interior[3] / 100
            for ratio in (.15, .5, 1, 2, 5):
                p = catalog(1)['projects'][0]
                p['artwork']['width'] = 100 * ratio
                box = [.1, .2, .85, .9]
                style = fitted_image(p, slot, asset, {'0': {'bbox': box}})
                scale = float(style.split('%')[0].split(':')[1]) / 100
                subject_w = ww * scale * (box[2] - box[0])
                subject_h = ww * scale / ratio * (box[3] - box[1])
                self.assertLessEqual(subject_w, ww + .001)
                self.assertLessEqual(subject_h + 4.5, wh + .01)

    def test_wall_width_and_grounded_base_without_horizontal_shrink(self):
        assets = {a['id']: a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())}
        for slot in DISPLAY:
            asset = assets[slot[1]]
            h = round(slot[3] * (.94 if slot[1] == 'central' else .82))
            w = round(h * asset['width'] / asset['height'])
            x, y, iw, ih = SPECIMEN_INTERIORS[slot[1]]
            self.assertTrue(0 <= x < x + iw <= 100)
            self.assertTrue(0 <= y < y + ih <= 100)
            ww, wh = w * iw / 100, h * ih / 100
            p = catalog(1)['projects'][0]
            p['artwork']['width'] = 300
            style = fitted_image(p, slot, asset, {})
            scale = float(style.split('%')[0].split(':')[1]) / 100
            top = float(style.split('top:')[1].split('%')[0]) / 100 * wh
            subject_h = ww * scale / 3
            bottom = wh - top - subject_h
            self.assertAlmostEqual(ww * scale, ww, places=3)
            self.assertAlmostEqual(bottom, 2.25, places=2)

    def test_reviewed_body_recovers_original_scale_without_changing_art(self):
        pid = next(iter(SPECIMEN_BODY_SPANS))
        project = {'id': pid, 'artwork': {'path': f'specimens/{pid}.webp',
                                         'width': 1254, 'height': 1254}}
        box = [.2057, .0183, .7289, .9745]
        cutouts = {pid: {'bbox': box}}
        self.assertEqual(composition_box(project, cutouts), [.415, box[1], .68, box[3]])
        self.assertEqual(composition_box(project, {}), [0, 0, 1, 1])
        self.assertEqual(composition_box(project, {pid: {'bbox': None}}), [0, 0, 1, 1])
        asset = next(a for a in json.loads((ROOT/'site/jars/provenance.json').read_text())
                     if a['id'] == 'central')
        style = fitted_image(project, DISPLAY[3], asset, cutouts)
        scale = float(style.split('%')[0].split(':')[1]) / 100
        height = 207 * SPECIMEN_INTERIORS['central'][2] / 100 * scale * (box[3] - box[1])
        self.assertGreater(height, 150)
        self.assertLess(height, 165)
        from unittest.mock import patch
        with patch.dict(SPECIMEN_BODY_SPANS[pid], {'source_sha256': 'stale'}):
            self.assertEqual(composition_box(project, cutouts), box)

    def test_real_interiors_do_not_redefine_glass_geometry(self):
        self.assertEqual(DISPLAY[3][5:9], (37, 29, 26, 55))
        self.assertEqual(SPECIMEN_INTERIORS['central'], (40.1, 22, 20.6, 63.7))
        self.assertEqual(SPECIMEN_INTERIORS['low-lid'][0] + SPECIMEN_INTERIORS['low-lid'][2], 72.5)
        for kind, points in SPECIMEN_INTERIOR_CONTOURS.items():
            self.assertGreater(len(points), 10)
            self.assertTrue(all(0 <= x <= 100 and 0 <= y <= 100 for x, y in points))
            self.assertTrue(interior_clip(kind).startswith('polygon('))
        # Trace the lid occlusion and curved floor, not the old x66% rectangle.
        self.assertIn((66.6, 59.2), SPECIMEN_INTERIOR_CONTOURS['low-lid'])
        self.assertIn((82, 45), SPECIMEN_INTERIOR_CONTOURS['low-lid'])
        self.assertIn((53, 85.7), SPECIMEN_INTERIOR_CONTOURS['central'])
