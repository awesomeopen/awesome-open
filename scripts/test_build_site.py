"""Offline site checks also run in the existing unittest workflow."""

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from build_site import ROOT, build, json_for_html, render_html


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.cards = []
        self.links = []
        self.images = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'data-project-id' in attrs:
            self.cards.append(attrs['data-project-id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name) / 'site'
        cls.catalog = build(cls.output, source_sha='a' * 40)
        cls.html = (cls.output / 'index.html').read_text()
        cls.page = Page(cls.html)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_projects_are_rendered_without_javascript(self):
        self.assertEqual(len(self.page.cards), len(self.catalog['projects']))
        self.assertEqual(set(self.page.cards), {p['id'] for p in self.catalog['projects']})
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for p in self.catalog['projects']:
            self.assertIn(p['url'], self.page.links)
            self.assertIn('#project-' + p['id'], self.page.links)
        self.assertIn('<noscript>', self.html)
        self.assertIn('id="filters" class="catalog-toolbar" hidden', self.html)

    def test_local_assets_evidence_and_portable_paths(self):
        self.assertTrue((self.output / 'styles.css').is_file())
        self.assertTrue((self.output / 'catalog.js').is_file())
        self.assertTrue((self.output / '.nojekyll').is_file())
        self.assertEqual(json.loads((self.output / 'catalog.json').read_text()), self.catalog)
        for name in ('hn_evidence.json', 'alternatives.json'):
            self.assertEqual((self.output / 'data' / name).read_bytes(), (ROOT / 'data' / name).read_bytes())
        for image in self.page.images:
            self.assertEqual(image['alt'], 'HN discussions / 2y')
            self.assertFalse(image['src'].startswith('/'))
            self.assertTrue((self.output / image['src']).is_file())
        for href in self.page.links:
            if href.startswith('#'):
                self.assertIn(href[1:], self.page.ids)
            elif not href.startswith(('https://', 'http://')) and href != './':
                self.assertTrue((self.output / href).is_file(), href)

    def test_output_deterministic_and_revision_explicit(self):
        before = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        build(self.output, source_sha='a' * 40)
        after = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertIn('/commit/' + 'a' * 40, self.html)
        local = copy.deepcopy(self.catalog)
        local['source_sha'] = None
        self.assertIn('Local preview (revision not supplied)', render_html(local))

    def test_untrusted_text_never_becomes_markup_or_closes_json(self):
        catalog = copy.deepcopy(self.catalog)
        evil = '</script><img src=x onerror=alert(1)>'
        project = catalog['projects'][0]
        project['name'] = evil
        project['description'] = evil
        if project['github']:
            project['github']['license'] = evil
        document = render_html(catalog)
        self.assertNotIn(evil, document)
        self.assertIn('&lt;/script&gt;', document)
        self.assertEqual(json.loads(json_for_html({'text': evil + '\u2028\u2029&'})), {'text': evil + '\u2028\u2029&'})
        self.assertEqual(document.count('<script'), 2)

    def test_source_directories_cannot_be_overwritten(self):
        for output in (ROOT, ROOT.parent, ROOT / 'site', ROOT / 'data', ROOT / 'scripts', ROOT / 'assets', ROOT / 'site/generated'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build(output)

    @unittest.skipUnless(shutil.which('node'), 'Node is optional for JS helper tests')
    def test_javascript_helpers(self):
        result = subprocess.run(['node', '--test', 'site/test_catalog.js'], cwd=ROOT, text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
