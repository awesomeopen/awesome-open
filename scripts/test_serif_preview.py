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

    def test_demand_loaded_hosted_and_embedded_offline_fonts(self):
        from font_assets import standalone_font_css
        css = (ROOT / 'site/vendor/fonts.css').read_text()
        self.assertNotIn('base64,', css)
        self.assertIn('serif-preview/poltawski.woff2', css)
        self.assertIn('fraunces.woff2', css)
        embedded = standalone_font_css(ROOT)
        self.assertIn("font-family:'Poltawski Nowy'", embedded)
        self.assertIn("font-family:'Commit Mono'", embedded)
        self.assertNotIn("font-family:'Fraunces'", embedded)
        self.assertNotIn("font-family:'Instrument Serif'", embedded)
        self.assertEqual(embedded.count('data:font/woff2;base64,'), 2)
        self.assertIn('SIL OPEN FONT LICENSE', embedded)
        output, _ = baseline_site()
        for path in ['standalone.html', 'observatory/report.html']:
            page = (output / path).read_text()
            self.assertIn(embedded, page)
            self.assertNotIn('src:url(serif-preview/', page)
        runtime = (ROOT / 'site/serif-preview.js').read_text()
        self.assertNotIn('localStorage', runtime)
        self.assertNotIn('sessionStorage', runtime)
        self.assertNotIn('https://fonts.', runtime)

    def test_extracted_original_font_bytes(self):
        vendor = ROOT / 'site/vendor'
        provenance = json.loads((vendor / 'FONT-PROVENANCE.json').read_text())
        for font in provenance['fonts']:
            data = (vendor / font['output']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), font['embedded_woff2_sha256'])
            self.assertEqual(len(data), font['embedded_bytes'])
        self.assertEqual(hashlib.sha256((vendor / 'fonts.css').read_bytes()).hexdigest(), provenance['output_css_sha256'])

    def test_private_reference_hashes_and_custom_root(self):
        import tempfile
        from font_assets import font_asset_url, standalone_font_css
        page = (ROOT / 'site/design/index.html').read_text()
        for name in ['vendor/fonts.css', 'tokens.css', 'serif-preview.js']:
            self.assertIn(font_asset_url(name), page)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'site').mkdir()
            (root / 'site/serif-preview.js').write_text('different source')
            self.assertNotEqual(font_asset_url('serif-preview.js', root), font_asset_url('serif-preview.js'))
        historical = standalone_font_css(ROOT, serif='fraunces')
        self.assertIn("font-family:'Fraunces'", historical)
        self.assertNotIn("font-family:'Poltawski Nowy'", historical)
        self.assertEqual(historical.count('data:font/woff2;base64,'), 2)

    def test_poltawski_bold_uses_existing_variable_font(self):
        from font_assets import standalone_font_css
        declaration = "font-family:'Poltawski Nowy';font-style:normal;font-weight:400 700;"
        self.assertIn(declaration, (ROOT / 'site/vendor/fonts.css').read_text())
        self.assertIn(declaration, standalone_font_css(ROOT))
        provenance = json.loads((ROOT / 'site/vendor/serif-preview/provenance.json').read_text())
        font = next(item for item in provenance['fonts'] if item['choice'] == 'poltawski')
        self.assertEqual(font['css_weight_range'], [400, 700])
        self.assertEqual(font['variation_axes']['wght'], {'min': 400, 'default': 400, 'max': 700})
        self.assertEqual(font['bytes'], 124040)
