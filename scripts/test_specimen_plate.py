"""Specimen plate for every record: label, QR code, cut-outs, timeline and archived status."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import warnings

import qr
from build_site import PERMALINK_BASE, attach_specimen_cutouts, project_html, qr_path, timeline, specimen_geometry
from render_readme import validate_snapshot

PID = 'b' * 64
PROJECT = {
    'id': PID, 'name': 'OpenExample', 'url': 'https://github.com/example/openexample',
    'description': 'Example tool.', 'categories': ['tools'], 'alternatives': [], 'hn': None,
    'github': {'repo': 'example/openexample', 'stars': 1200, 'license': None,
               'created_at': '2015-03-01T00:00:00Z', 'pushed_at': '2021-11-15T00:00:00Z'},
}
CATALOG = {'source_sha': 'a' * 40}


def render(project, cutouts=None):
    return project_html(project, {'tools': 'Developer Tools', 'data': 'Databases'}, CATALOG, 150, cutouts)


def matrix_hash(text):
    return hashlib.sha256(''.join('1' if v else '0' for row in qr.encode(text) for v in row).encode()).hexdigest()


class QRTests(unittest.TestCase):
    def test_known_codes_are_stable(self):
        # Both matrices were decoded back to their exact text with an independent reader (jsQR 1.4.0).
        self.assertEqual(len(qr.encode('HELLO')), 21)
        self.assertEqual(matrix_hash('HELLO'), '32fbc389880456d584e32bdf2c31372391c92f9f853e119a75bec5e14c380a23')
        link = PERMALINK_BASE + 'a2b374fddf2f0492141da0f237e94a0c0ba11325c8ad3c4b8883d097f5ede99d'
        self.assertEqual(len(qr.encode(link)), 45)
        self.assertEqual(matrix_hash(link), 'c4c3324f34ec3f82e581b738e4b5325529c1e39d665a396c299b8b5d992fe492')

    def test_finder_patterns_and_svg(self):
        modules = qr.encode(PERMALINK_BASE + PID)
        size = len(modules)
        for x, y in ((0, 0), (size - 7, 0), (0, size - 7)):
            ring = [modules[y][x + i] for i in range(7)]
            self.assertEqual(ring, [True] * 7)
            self.assertFalse(modules[y + 1][x + 1])
            self.assertTrue(modules[y + 3][x + 3])
        svg = qr.svg(PERMALINK_BASE + PID, 'QR code: <permalink> & "x"')
        self.assertTrue(svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 45 45"'))
        self.assertIn('aria-label="QR code: &lt;permalink&gt; &amp; &quot;x&quot;"', svg)
        self.assertEqual(svg, qr.svg(PERMALINK_BASE + PID, 'QR code: <permalink> & "x"'))

    def test_too_long_text_is_rejected(self):
        with self.assertRaises(ValueError):
            qr.encode('x' * 400)


class PlateTests(unittest.TestCase):
    def test_every_record_gets_a_plate_label_and_departure(self):
        html = render(copy.deepcopy(PROJECT))
        self.assertIn('class="specimen-interior specimen-plate without-art"', html)
        self.assertNotIn('class="plate-stage"', html)
        self.assertNotIn('class="plate-field"', html)
        self.assertIn(f'href="{PERMALINK_BASE + PID}" aria-label="QR code: permalink to OpenExample"', html)
        self.assertIn(f'src="{qr_path(PROJECT)}"', html)
        self.assertIn('Domain: <a class="tag" data-category="tools"', html)
        self.assertIn('Specimen: OpenExample (permalink)', html)
        self.assertIn('Awesome Open* · Field record', html)
        self.assertIn('Explore OpenExample on GitHub', html)
        labels = re.findall(r'<span class="sheet-label">([^<]+)</span>', html)
        self.assertEqual(labels, ['I / Function', 'II / Repository record', 'In the wild'])

    def test_unknown_license_is_labelled_unknown(self):
        html = render(copy.deepcopy(PROJECT))
        self.assertIn('<dt>Detected license</dt><dd>Unknown</dd>', html)
        # The compact ledger row keeps an unknown license blank; the open record names it.
        self.assertIn('<span class="license-readout"></span>', html)

    def test_archived_status_comes_only_from_github(self):
        self.assertNotIn('Archived on GitHub', render(copy.deepcopy(PROJECT)))
        archived = copy.deepcopy(PROJECT)
        archived['github']['archived'] = True
        html = render(archived)
        self.assertIn('<span class="label-status">Archived on GitHub</span>', html)
        self.assertNotIn('Field record', html)
        snapshot = {'schema_version': 1, 'as_of': '2026-10-14', 'repositories': {
            'example/openexample': {'stargazers_count': 1, 'created_at': '2015-03-01T00:00:00Z', 'archived': 'yes'}}}
        with self.assertRaises(ValueError):
            validate_snapshot(snapshot)

    def test_timeline_positions_are_literal_dates(self):
        line = timeline('2012-01-01', ('2026-03-04', '3.10.1'), '2026-10-11')
        self.assertIn('style="left:0.0%"', line)
        self.assertIn('GitHub release<br><span class="metric-value">2026-03-04</span> · 3.10.1', line)
        self.assertIn('aria-label="Repository created 2012-01-01; GitHub release 2026-03-04 (3.10.1); Repository push 2026-10-11"', line)
        self.assertEqual(timeline('unknown', None, None), '')

    def test_close_timeline_endpoints_have_opposing_labels(self):
        line = timeline('2026-10-01', None, '2026-10-02')
        self.assertIn('style="right:25.21%;margin-right:8px;text-align:right">Repository created', line)
        self.assertIn('style="left:75.07%;margin-left:8px;text-align:left">Repository push', line)
        marks = re.findall(r'class="timeline-mark" style="left:([0-9.]+)%"', line)
        self.assertEqual(len(marks), 2)
        self.assertGreater(float(marks[1]), float(marks[0]))
        self.assertLess(float(marks[1]) - float(marks[0]), 1)

    def test_same_day_timeline_labels_extend_away_from_shared_marker(self):
        line = timeline('2026-10-17', None, '2026-10-17')
        self.assertIn('right:20.82%;margin-right:8px;text-align:right', line)
        self.assertIn('left:79.18%;margin-left:8px;text-align:left', line)



class SpecimenGeometryTests(unittest.TestCase):
    art = {'width': 1254, 'height': 1254}

    def test_short_subject_only_trims_empty_canvas_with_safety_margin(self):
        geometry = specimen_geometry(self.art, [.01, .3365, .98, .6802])
        self.assertAlmostEqual(geometry['top'], .2565)
        self.assertAlmostEqual(geometry['bottom'], .7602)
        self.assertAlmostEqual(geometry['height'], .5037)
        self.assertAlmostEqual(geometry['offset'] * geometry['height'], -.2565)
        self.assertAlmostEqual(geometry['ground'] * geometry['height'], .4237)

    def test_subject_near_edges_retains_full_canvas(self):
        geometry = specimen_geometry(self.art, [.2, .0064, .8, .9896])
        self.assertEqual((geometry['top'], geometry['bottom'], geometry['height']), (0, 1, 1))
        self.assertEqual(geometry['offset'], 0)
        self.assertAlmostEqual(geometry['ground'], .9896)

    def test_non_square_source_keeps_intrinsic_aspect_ratio(self):
        for ratio in [.5, 2]:
            with self.subTest(ratio=ratio):
                geometry = specimen_geometry({'width': 1000, 'height': 1000 * ratio}, [.1, .2, .9, .8])
                self.assertAlmostEqual(geometry['height'], .76 * ratio)
                self.assertAlmostEqual(geometry['offset'], -.12 / .76)

    def test_invalid_or_missing_bbox_keeps_full_canvas(self):
        invalid = [None, [], [0, 0, 1], '0 0 1 1', [0, .8, 1, .2],
                   [0, .5, 1, .5], [.8, 0, .2, 1], [-.1, 0, 1, 1],
                   [0, 0, 1, 1.1], [False, 0, 1, 1], ['0', 0, 1, 1],
                   [0, float('nan'), 1, 1], [0, 0, 1, float('inf')]]
        for bbox in invalid:
            with self.subTest(bbox=bbox):
                geometry = specimen_geometry(self.art, bbox)
                self.assertEqual(geometry['bbox'], [0, 0, 1, 1])
                self.assertEqual((geometry['top'], geometry['bottom'], geometry['height'], geometry['offset']), (0, 1, 1, 0))
                self.assertEqual(geometry['ground'], .86)

    def test_zero_edge_bounds_are_valid(self):
        for bbox in [[0, 0, 1, .4], [0, .6, 1, 1], [0, 0, 1, 1]]:
            with self.subTest(bbox=bbox):
                geometry = specimen_geometry(self.art, bbox)
                self.assertEqual(geometry['bbox'], bbox)
                self.assertGreater(geometry['height'], 0)
                self.assertGreaterEqual(geometry['fade_start'], .5)
                self.assertGreaterEqual(geometry['fade_end'], geometry['fade_start'])


class CutoutTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / 'site/specimens/cutouts').mkdir(parents=True)
        self.source = self.root / f'site/specimens/{PID}.webp'
        self.derivative = self.root / f'site/specimens/cutouts/{PID}.webp'
        self.source.write_bytes(b'RIFF0000WEBPsource')
        self.derivative.write_bytes(b'RIFF0000WEBPcutout')
        self.project = copy.deepcopy(PROJECT)
        self.project['artwork'] = {'path': f'specimens/{PID}.webp', 'alt': 'A tool.', 'width': 1254, 'height': 1254}
        self.entry = {'source': f'specimens/{PID}.webp', 'path': f'specimens/cutouts/{PID}.webp',
                      'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                      'sha256': hashlib.sha256(self.derivative.read_bytes()).hexdigest(), 'subject_bbox': [0.1, 0.2, 0.9, 0.8]}

    def tearDown(self):
        self.directory.cleanup()

    def attach(self, entry):
        (self.root / 'site/specimens/cutouts.json').write_text(json.dumps({'schema_version': 1, 'cutouts': {PID: entry}}))
        return attach_specimen_cutouts({'projects': [self.project]}, self.root)

    def test_matching_cutout_is_used_with_its_subject_box(self):
        cutouts = self.attach(self.entry)
        self.assertEqual(cutouts, {PID: {'path': f'specimens/cutouts/{PID}.webp', 'bbox': [0.1, 0.2, 0.9, 0.8]}})
        html = render(self.project, cutouts)
        self.assertIn(f'src="specimens/cutouts/{PID}.webp"', html)
        self.assertIn('data-cutout="true" data-bbox="0.1 0.2 0.9 0.8"', html)
        self.assertIn('class="plate-stage"', html)
        self.assertIn('--plate-height:0.760000;', html)
        self.assertIn('width="1254" height="1254"', html)

    def test_stale_cutout_falls_back_to_the_original(self):
        stale = dict(self.entry, source_sha256='0' * 64)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            cutouts = self.attach(stale)
        self.assertEqual(cutouts, {})
        self.assertIn('older than its source', str(caught[0].message))
        html = render(self.project, cutouts)
        self.assertIn(f'src="specimens/{PID}.webp"', html)
        self.assertIn('data-cutout="false" data-bbox="0 0 1 1"', html)
        self.assertIn('--plate-height:1.000000;', html)

    def test_changed_derivative_or_path_is_rejected(self):
        with self.assertRaises(ValueError):
            self.attach(dict(self.entry, sha256='0' * 64))
        with self.assertRaises(ValueError):
            self.attach(dict(self.entry, path='specimens/other.webp'))

    def test_committed_cutouts_match_their_sources(self):
        root = Path(__file__).resolve().parents[1]
        document = json.loads((root / 'site/specimens/cutouts.json').read_text())
        for pid, entry in document['cutouts'].items():
            with self.subTest(pid=pid):
                self.assertEqual(hashlib.sha256((root / 'site' / entry['source']).read_bytes()).hexdigest(), entry['source_sha256'])
                self.assertEqual(hashlib.sha256((root / 'site' / entry['path']).read_bytes()).hexdigest(), entry['sha256'])


if __name__ == '__main__':
    unittest.main()
