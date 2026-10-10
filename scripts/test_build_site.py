"""Offline site checks also run in the existing unittest workflow."""

import copy
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from build_site import ROOT, build, json_for_html, render_html


RUNTIME_SCRIPTS = ('catalog.js', 'vendor/gsap.min.js', 'vendor/ScrollTrigger.min.js', 'motion.js')
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Element:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.text = ''

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()

    def descendants(self, tag=None):
        return [node for child in self.children for node in [child, *child.descendants()]
                if tag is None or node.tag == tag]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.cards = []
        self.links = []
        self.images = []
        self.elements = []
        self.by_id = {}
        self.stack = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        node = Element(tag, attrs)
        self.elements.append(node)
        if self.stack:
            self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
            self.by_id[attrs['id']] = node
        if 'data-project-id' in attrs:
            self.cards.append(attrs['data-project-id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        for node in self.stack:
            node.text += data

    def nodes(self, tag):
        return [node for node in self.elements if node.tag == tag]


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

    def test_specimen_drawers_preserve_full_names_descriptions_and_sources(self):
        categories = {c['id']: c['name'] for c in self.catalog['categories']}
        for project in self.catalog['projects']:
            with self.subTest(project=project['name']):
                card = self.page.by_id['project-' + project['id']]
                self.assertEqual(card.tag, 'article')
                self.assertNotIn('hidden', card.attrs)
                self.assertEqual(card.attrs['data-project-id'], project['id'])
                drawers = [node for node in card.descendants('details') if node.has_class('specimen-drawer')]
                self.assertEqual(len(drawers), 1)
                drawer = drawers[0]
                self.assertEqual(drawer.children[0].tag, 'summary')
                summary = drawer.children[0]
                name = [node for node in summary.descendants() if node.has_class('specimen-name')]
                self.assertEqual([node.text for node in name], [project['name']])
                self.assertIn(project['description'], summary.text)
                self.assertEqual(len(card.descendants('h3')), 1)
                links = card.descendants('a')
                self.assertEqual([node.attrs['href'] for node in links if node.has_class('source-link')], [project['url']])
                self.assertEqual([node.attrs['href'] for node in links if node.has_class('permalink')], ['#project-' + project['id']])
                tags = [node for node in links if node.has_class('tag')]
                self.assertEqual([node.attrs['data-category'] for node in tags], project['categories'])
                self.assertEqual([node.text for node in tags], [categories[cid] for cid in project['categories']])
                for alternative in project['alternatives']:
                    self.assertIn(alternative['source_url'], [node.attrs['href'] for node in links])
                    self.assertIn(alternative['name'], card.text)
                    self.assertIn(alternative['scope'], card.text)
                    self.assertIn(alternative['checked_utc_date'], card.text)

    def test_memberships_navigation_and_evidence_limits_are_explicit(self):
        self.assertEqual(self.catalog['category_memberships'], sum(len(p['categories']) for p in self.catalog['projects']))
        self.assertEqual(self.catalog['category_memberships'], sum(c['count'] for c in self.catalog['categories']))
        bands = [node for node in self.page.elements if node.has_class('collection-band')]
        self.assertEqual(len(bands), 1)
        for label in (f"{len(self.catalog['projects'])} distinct projects",
                      f"{self.catalog['category_memberships']} category memberships",
                      f"{len(self.catalog['categories'])} functional categories"):
            self.assertIn(label, bands[0].text)
        nav = [node for node in self.page.nodes('nav') if node.has_class('category-nav')][0]
        self.assertEqual(len(nav.descendants('a')), len(self.catalog['categories']) + 1)
        for category, link in zip(self.catalog['categories'], nav.descendants('a')[1:]):
            self.assertEqual(link.attrs['data-category'], category['id'])
            self.assertIn(category['name'], link.text)
            self.assertTrue(link.attrs['href'].endswith('/README.source.md#' + category['id']))
        for qualification in ('Missing data is not evidence of a proprietary license.',
                              'Lineage and motives are not inferred.',
                              'Repository creation is not project birth; last push is not maintenance status.',
                              'Missing charts do not mean no discussion.'):
            self.assertIn(qualification, self.html)

    def test_form_labels_status_and_native_disclosures_are_accessible(self):
        self.assertEqual(len(self.page.nodes('h1')), 1)
        self.assertEqual(len(self.page.nodes('main')), 1)
        self.assertEqual(self.page.by_id['catalog'].attrs['tabindex'], '-1')
        self.assertIn('hidden', self.page.by_id['filters'].attrs)
        self.assertIn('disabled', self.page.by_id['sort-order'].attrs)
        labels = {node.attrs.get('for'): node.text.strip() for node in self.page.nodes('label')}
        for control in self.page.nodes('input') + self.page.nodes('select'):
            self.assertTrue(labels.get(control.attrs['id']), control.attrs)
        for node in self.page.nodes('details'):
            self.assertTrue(node.children)
            self.assertEqual(node.children[0].tag, 'summary')
            self.assertTrue(node.children[0].text.strip())
        result = self.page.by_id['result-count'].attrs
        self.assertEqual(result['role'], 'status')
        self.assertEqual(result['aria-live'], 'polite')
        self.assertEqual(result['aria-atomic'], 'true')
        self.assertEqual(self.page.by_id['project-link-notice'].attrs['role'], 'status')
        for node in self.page.elements:
            for attribute in ('aria-labelledby', 'aria-describedby'):
                for reference in node.attrs.get(attribute, '').split():
                    self.assertIn(reference, self.page.by_id)

    def test_focusable_hidden_controls_have_a_focus_reveal_or_skip_tab_order(self):
        css = (self.output / 'styles.css').read_text()
        for node in self.page.elements:
            if not node.has_class('visually-hidden') or node.tag not in {'a', 'button', 'input', 'select', 'textarea'}:
                continue
            if node.attrs.get('tabindex') == '-1':
                continue
            self.assertRegex(css, r'\.visually-hidden(?::focus(?:-visible)?|:not\(:focus(?:-visible)?\))', node.attrs)

    def assert_safe_script_allowlist(self, page):
        scripts = page.nodes('script')
        self.assertEqual(len(scripts), 5)
        self.assertEqual([node.attrs.get('src') for node in scripts[:-1]], list(RUNTIME_SCRIPTS))
        for node in scripts[:-1]:
            self.assertIn('defer', node.attrs)
            self.assertEqual(node.text, '')
        self.assertEqual(scripts[-1].attrs, {'id': 'catalog-data', 'type': 'application/json'})
        for node in page.elements:
            self.assertFalse(any(key.lower().startswith('on') for key in node.attrs), node.attrs)
            for attribute in ('href', 'src'):
                self.assertFalse(node.attrs.get(attribute, '').lstrip().lower().startswith('javascript:'), node.attrs)

    def test_only_allowlisted_local_scripts_execute_and_embedded_data_is_exact(self):
        self.assert_safe_script_allowlist(self.page)
        self.assertEqual(json.loads(self.page.by_id['catalog-data'].text), self.catalog)
        for name in RUNTIME_SCRIPTS:
            self.assertEqual((self.output / name).read_bytes(), (ROOT / 'site' / name).read_bytes())

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
        for stylesheet in self.page.nodes('link'):
            if stylesheet.attrs.get('rel') == 'stylesheet':
                href = stylesheet.attrs['href']
                self.assertFalse(href.startswith(('/', 'http:', 'https:')))
                self.assertTrue((self.output / href).is_file(), href)
        self.assertTrue((self.output / 'vendor/FONT-LICENSE.txt').is_file())
        self.assertTrue((self.output / 'vendor/FONT-PROVENANCE.json').is_file())

    def test_standalone_preserves_every_record_and_embeds_all_runtime_resources(self):
        page = Page((self.output / 'standalone.html').read_text())
        self.assertEqual(page.cards, self.page.cards)
        self.assertEqual(json.loads(page.by_id['catalog-data'].text), self.catalog)
        self.assertEqual(len(page.nodes('script')), 5)
        self.assertEqual(len(page.nodes('link')), 0)
        for name, script in zip(RUNTIME_SCRIPTS, page.nodes('script')[:-1]):
            self.assertIn('defer', script.attrs)
            self.assertEqual(script.text, '')
            prefix, encoded = script.attrs['src'].split(',', 1)
            self.assertEqual(prefix, 'data:text/javascript;base64')
            self.assertEqual(base64.b64decode(encoded, validate=True), (self.output / name).read_bytes())
        for image in page.images:
            prefix, encoded = image['src'].split(',', 1)
            self.assertEqual(prefix, 'data:image/svg+xml;base64')
            self.assertIn(b'<svg', base64.b64decode(encoded, validate=True))
            self.assertEqual(image['alt'], 'HN discussions / 2y')
        expected_downloads = {'catalog.json': self.catalog,
                              'hn_evidence.json': json.loads((ROOT / 'data/hn_evidence.json').read_text()),
                              'alternatives.json': json.loads((ROOT / 'data/alternatives.json').read_text())}
        actual_downloads = {}
        for link in page.nodes('a'):
            href = link.attrs['href']
            if href.startswith('data:'):
                prefix, encoded = href.split(',', 1)
                self.assertEqual(prefix, 'data:application/json;base64')
                actual_downloads[link.attrs['download']] = json.loads(base64.b64decode(encoded, validate=True))
            elif href.startswith('#'):
                self.assertIn(href[1:], page.ids)
            else:
                self.assertTrue(href.startswith(('https://', 'http://')), href)
        self.assertEqual(actual_downloads, expected_downloads)
        for style in page.nodes('style'):
            self.assertNotRegex(style.text, r'@import\b')
            # Consume the complete quoted URL. The paper-grain data SVG contains
            # an inner url(%23n) filter reference, not a second CSS dependency.
            tokens = re.findall(r'''url\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|([^\s)'"]+))\s*\)''', style.text)
            for token in tokens:
                resource = next(value for value in token if value)
                self.assertTrue(resource.startswith('data:'), resource[:100])

    def test_optional_motion_has_reduced_motion_and_missing_dependency_guards(self):
        motion = (self.output / 'motion.js').read_text()
        css = (self.output / 'styles.css').read_text()
        self.assertRegex(motion, r'if\s*\([^)]*!window\.gsap[^)]*!window\.ScrollTrigger[^)]*\)\s*return')
        self.assertIn('gsap.matchMedia()', motion)
        self.assertIn('(prefers-reduced-motion: no-preference)', motion)
        self.assertRegex(css, r'@media\s*\(prefers-reduced-motion:\s*reduce\)')
        self.assertRegex(css, r'scroll-behavior:\s*auto')
        self.assertRegex(css, r'transition:\s*none\s*!important')

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
        self.assert_safe_script_allowlist(Page(document))
        self.assertEqual(json.loads(Page(document).by_id['catalog-data'].text), catalog)

    def test_prefix_suffix_and_comparison_text_cannot_inject_attributes_or_scripts(self):
        catalog = copy.deepcopy(self.catalog)
        payload = '\" autofocus onfocus=alert(1)><script>alert(1)</script>&'
        project = next(p for p in catalog['projects'] if p['alternatives'] and p['github'])
        project['name'] = 'Open' + payload
        project['description'] = payload
        project['github']['license'] = payload
        project['alternatives'][0]['name'] = payload
        project['alternatives'][0]['scope'] = payload
        catalog['categories'][0]['name'] = payload
        document = render_html(catalog)
        page = Page(document)
        self.assert_safe_script_allowlist(page)
        self.assertEqual(json.loads(page.by_id['catalog-data'].text), catalog)
        card = page.by_id['project-' + project['id']]
        names = [node.text for node in card.descendants() if node.has_class('specimen-name')]
        self.assertEqual(names, [project['name']])
        self.assertNotIn('<script>alert(1)</script>', document)

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
