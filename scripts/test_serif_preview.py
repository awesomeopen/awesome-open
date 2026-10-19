"""URL-only serif preview packaging and provenance contracts."""
import hashlib
import json
from pathlib import Path
import unittest
from site_test_fixtures import baseline_site

ROOT = Path(__file__).resolve().parents[1]

class SerifPreviewTests(unittest.TestCase):
    def test_hosted_and_offline_scope(self):
        output, catalog = baseline_site()
        for path in ['index.html', 'observatory/index.html', 'spotlight/index.html',
                     'records/' + catalog['projects'][0]['id'] + '.html']:
            self.assertIn('serif-preview.js', (output / path).read_text())
        for path in ['standalone.html', 'observatory/report.html']:
            self.assertNotIn('serif-preview.js', (output / path).read_text())
        for choice in ['instrument', 'poltawski']:
            self.assertTrue((output / 'vendor/serif-preview' / (choice + '.woff2')).is_file())

    def test_font_hashes_and_notices(self):
        directory = ROOT / 'site/vendor/serif-preview'
        provenance = json.loads((directory / 'provenance.json').read_text())
        self.assertEqual(len(provenance['source_revision']), 40)
        self.assertEqual(len(provenance['fonts']), 2)
        for entry in provenance['fonts']:
            data = (directory / entry['output']).read_bytes()
            self.assertEqual(data[:4], b'wOF2')
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry['output_sha256'])
            self.assertEqual(len(data), entry['bytes'])
            self.assertEqual(entry['css_weight'], 400)
            self.assertEqual(entry['style'], 'normal')
            self.assertIn('SIL OPEN FONT LICENSE Version 1.1', (directory / entry['license']).read_text())
            self.assertIn('weight: 400', (directory / entry['metadata']).read_text())

    def test_default_bundle_unchanged_by_candidates(self):
        css = (ROOT / 'site/vendor/fonts.css').read_text()
        self.assertNotIn('Instrument', css)
        self.assertNotIn('Poltawski', css)
        runtime = (ROOT / 'site/serif-preview.js').read_text()
        self.assertNotIn('localStorage', runtime)
        self.assertNotIn('sessionStorage', runtime)
        self.assertNotIn('https://fonts.', runtime)
