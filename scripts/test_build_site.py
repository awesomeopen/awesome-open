"""Offline site checks also run in the existing unittest workflow."""

import copy
from html.parser import HTMLParser
import json
from font_assets import font_asset_url
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

from build_site import BRAND_ASSETS, ROOT, build, json_for_html, load_site_catalog, render_html, search_index
from site_test_fixtures import baseline_site, copy_site_fixture


RUNTIME_SCRIPTS = ('catalog.js',)
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
        if tag == 'article' and 'data-project-id' in attrs:
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
    def test_static_default_has_result_positions_and_alphabetical_detail_folios(self):
        from build_site import search_index
        script = "const c=require('./site/catalog.js'); const d=JSON.parse(require('node:fs').readFileSync(0,'utf8')); console.log(JSON.stringify(d.projects.slice().sort(c.comparator('stars')).map(p=>p.id)))"
        result = subprocess.run(['node', '-e', script], input=json.dumps(search_index(self.catalog)),
                                cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(self.page.cards, json.loads(result.stdout))
        options = self.page.by_id['sort-order'].descendants('option')
        self.assertEqual([o.attrs['value'] for o in options if 'selected' in o.attrs], ['stars'])
        self.assertIn('List numbers show position in current results', self.html)
        self.assertIn('Folio numbers show alphabetical position', self.html)
        folios = {p['id']: i + 1 for i, p in enumerate(self.catalog['projects'])}
        for position, pid in enumerate(self.page.cards, 1):
            row = next(node for node in self.page.by_id['project-' + pid].descendants() if node.has_class('folio'))
            card = self.records[pid].by_id['project-' + pid]
            detail = next(node for node in card.descendants() if node.has_class('sheet-folio'))
            registry = next(node for node in card.descendants() if node.has_class('registry'))
            self.assertEqual(row.text, f'{position:03d}')
            self.assertEqual(row.attrs['title'], 'Position in current results')
            self.assertEqual(detail.text, f'Folio {folios[pid]:03d}')
            self.assertEqual(registry.text, 'OP-' + pid[:8].upper())
            self.assertIn(f'Field notes / {folios[pid]:03d}', card.text)

    @classmethod
    def setUpClass(cls):
        cls.output, cls.catalog = baseline_site(source_sha='a' * 40)
        cls.html = render_html(cls.catalog)
        cls.page = Page(cls.html)
        # Plates are written only to the static records the ledger links.
        cls.records = {p['id']: Page((cls.output / 'records' / (p['id'] + '.html')).read_text(encoding='utf-8'))
                       for p in cls.catalog['projects']}

    def test_production_entry_contains_hero_without_preview_metadata(self):
        from build_jar_preview import build as build_hero
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            # A rebuild over an older output removes the retired downloads.
            (output / 'observatory').mkdir()
            for retired in ('standalone.html', 'observatory/report.html'):
                (output / retired).write_text('old', encoding='utf-8')
            build(output, 'a' * 40)
            build_hero(output, production=True)
            self.assertFalse((output / 'standalone.html').exists())
            self.assertFalse((output / 'observatory/report.html').exists())
            page = (output / 'index.html').read_text()
            self.assertEqual(page.count('class="jar-hall"'), 1)
            self.assertIn('class="jar-page"', page)
            self.assertNotIn('noindex', page)
            self.assertNotIn('<title>Preview', page)
            for asset in ('jars.css', 'jars.js', 'jars/provenance.json'):
                self.assertTrue((output / asset).is_file())
            build_hero(output)
            self.assertEqual((output / 'jars.html').read_text().count('class="jar-hall"'), 1)
            self.assertIn('noindex', (output / 'jars.html').read_text())

    def test_all_projects_are_rendered_without_javascript(self):
        self.assertEqual(len(self.page.cards), len(self.catalog['projects']))
        self.assertEqual(set(self.page.cards), {p['id'] for p in self.catalog['projects']})
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for p in self.catalog['projects']:
            self.assertIn(f'records/{p["id"]}.html', self.page.links)
            self.assertIn(p['url'], self.records[p['id']].links)
            self.assertIn('#project-' + p['id'], self.records[p['id']].links)
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
                card = self.records[project['id']].by_id['project-' + project['id']]
                self.assertEqual(len(card.descendants('h3')), 0)
                links = card.descendants('a')
                departures = [n for n in card.descendants() if n.has_class('plate-departure')]
                self.assertEqual([[a.attrs['href'] for a in n.descendants('a')] for n in departures], [[project['url']]])
                self.assertEqual([node.attrs['href'] for node in links if node.has_class('permalink')], ['#project-' + project['id']])
                tags = [node for node in links if node.has_class('tag')]
                self.assertEqual([node.attrs['data-category'] for node in tags], project['categories'])
                self.assertEqual([node.text for node in tags], [categories[cid] for cid in project['categories']])
                for alternative in project['alternatives']:
                    self.assertIn(alternative['source_url'], [node.attrs['href'] for node in links])
                    self.assertIn(alternative['name'], card.text)
                    self.assertIn(alternative['scope'], card.text)
                    self.assertIn(alternative['checked_utc_date'], card.text)

    def test_memberships_navigation_and_evidence_methods_are_explicit(self):
        self.assertEqual(self.catalog['category_memberships'], sum(len(p['categories']) for p in self.catalog['projects']))
        self.assertEqual(self.catalog['category_memberships'], sum(c['count'] for c in self.catalog['categories']))
        self.assertFalse(any(node.has_class('collection-band') for node in self.page.elements))
        nav = [node for node in self.page.nodes('nav') if node.has_class('category-nav')][0]
        self.assertEqual(len(nav.descendants('a')), len(self.catalog['categories']) + 1)
        for category, link in zip(self.catalog['categories'], nav.descendants('a')[1:]):
            self.assertEqual(link.attrs['data-category'], category['id'])
            self.assertIn(category['name'], link.text)
            self.assertTrue(link.attrs['href'].endswith('/README.source.md#' + category['id']))
        methods = [node for node in self.page.elements if node.has_class('colophon')][0]
        for qualification in ('Detected licenses: verify against current official terms',
                              'Repository dates refer to GitHub activity',
                              'HN charts: matched stories / 2 years, shared square-root scale',
                              'Specimen illustrations are original artwork'):
            self.assertIn(qualification, methods.text)
        self.assertIn('<title>Awesome Open* Catalog</title>', self.html)
        self.assertIn('href="#about">About</a>', self.html)
        self.assertEqual(self.page.by_id['about'].tag, 'footer')
        self.assertIn('href="spotlight/">Spotlight</a>', self.html)
        record = next((self.output / 'records').glob('*.html')).read_text()
        self.assertIn('href="spotlight/"', record)
        for document in (self.html, record):
            self.assertNotIn('href="draws/"', document)
            self.assertNotIn('awesome-open/draws/', document)
        self.assertTrue((self.output / 'spotlight/index.html').is_file())
        self.assertTrue((self.output / 'spotlight/draws.json').is_file())

        self.assertIn('href="https://github.com/awesomeopen/awesome-open">GitHub</a><a href="#catalog">Top</a>', self.html)
        self.assertIn('shared square-root scale</li><li>GitHub stars / past 2y: Stars per month that remained at last successful fetch.</li>', self.html)

    def test_ledger_starts_without_cover_and_retains_plain_controls(self):
        page = Page((self.output / 'index.html').read_text())
        self.assertFalse(any(node.has_class(c) for node in page.elements for c in ('hero', 'reading-room', 'collection-band')))
        self.assertEqual(page.by_id['page-title'].tag, 'h1')
        self.assertIn('Projects', page.by_id['page-title'].text)
        self.assertEqual(page.by_id['method'].tag, 'details')
        self.assertEqual(page.by_id['clear-filters'].text.strip(), 'Reset filters ↺')

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
        self.assertEqual(len(scripts), len(RUNTIME_SCRIPTS) + 1)
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
        self.assertEqual(json.loads(self.page.by_id['catalog-data'].text), search_index(self.catalog))
        for name in RUNTIME_SCRIPTS:
            name = name.split('?')[0]
            self.assertEqual((self.output / name).read_bytes(), (ROOT / 'site' / name).read_bytes())

    def test_search_index_contains_only_runtime_fields_without_mutating_catalog(self):
        original = copy.deepcopy(self.catalog)
        index = search_index(self.catalog)
        self.assertEqual(self.catalog, original)
        self.assertEqual(set(index), {'metrics_as_of', 'categories', 'projects'})
        self.assertEqual(index['metrics_as_of'], self.catalog['metrics_as_of'])
        for category, full in zip(index['categories'], self.catalog['categories']):
            self.assertEqual(category, {key: full[key] for key in ('id', 'name')})
        self.assertEqual(len(index['projects']), len(self.catalog['projects']))
        for item, full in zip(index['projects'], self.catalog['projects']):
            self.assertEqual(set(item), {'id', 'name', 'description', 'categories',
                                        'leader_categories', 'github', 'alternatives', 'deployment'} | ({'aliases'} if full.get('aliases') else set()))
            for key in ('id', 'name', 'description', 'categories', 'leader_categories'):
                self.assertEqual(item[key], full[key])
            if full['github'] is None:
                self.assertIsNone(item['github'])
            else:
                self.assertEqual(item['github'], {key: full['github'].get(key)
                                                  for key in ('license', 'stars', 'pushed_at', 'status', 'last_success_at')})
            if full.get('aliases'):
                self.assertEqual(item['aliases'], [{'name': a['name']} for a in full['aliases']])
            self.assertEqual(item['alternatives'], [{'name': a['name']} for a in full['alternatives']])
            self.assertEqual(item['deployment'], {
                field: [{'value': fact['value']} for fact in full.get('deployment', {}).get(field, [])]
                for field in ('run_modes', 'install_methods')})
        # Guard against accidentally embedding evidence payloads again. This is
        # a ratio rather than a fragile byte count tied to today's catalog.
        self.assertLess(len(json_for_html(index)), len(json_for_html(self.catalog)) * 0.5)

    @unittest.skipUnless(shutil.which('node'), 'Node is optional for JS helper tests')
    def test_compact_index_preserves_runtime_filter_and_sort_results(self):
        catalog = copy.deepcopy(self.catalog)
        # Include edge cases even if the current evidence snapshot lacks them.
        for github in (None, {}, {'license': 'UNKNOWN', 'stars': None, 'pushed_at': None},
                       {'license': 'NOASSERTION', 'stars': 0, 'pushed_at': '2024-02-29T00:00:00Z'},
                       {'license': 'OTHER', 'stars': -1, 'pushed_at': 'invalid'}):
            project = copy.deepcopy(catalog['projects'][0])
            project.update(id='edge-' + str(len(catalog['projects'])), github=github,
                           name='Opén </script> \u2028', description='Mixed CASE & punctuation',
                           alternatives=[{'name': 'Café & tools'}])
            catalog['projects'].append(project)
        result = subprocess.run(['node', '-e', r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const api = require('./site/catalog.js');
const [full, compact] = JSON.parse(fs.readFileSync(0, 'utf8'));
const inputs = [{}, {q: 'OPEN'}, {q: 'cafe tools'}, {q: '</script>'},
  {q: 'no such project'}, {category: 'invalid'}, {license: 'invalid'},
  {run_mode: 'invalid'}, {install_method: 'invalid'}, {stars: 'invalid'},
  {pushed: '2024-02-30'}];
for (const key of ['license', 'window', 'metrics', 'run_mode', 'install_method']) {
  const values = key === 'license' ? ['all', 'known', 'unknown']
    : key === 'window' ? ['all', 'recent', 'older', 'unknown']
    : key === 'metrics' ? ['all', 'present', 'missing'] : ['', 'unknown'];
  for (const value of values) inputs.push({[key]: value});
}
for (const stars of [0, 1, 100, 10000, Number.MAX_SAFE_INTEGER]) inputs.push({stars});
for (const pushed of ['1900-01-01', '2024-02-29', full.metrics_as_of, '2099-01-01']) inputs.push({pushed});
for (const category of full.categories) inputs.push({category: category.id});
for (const alternative of api.alternativeNames(full.projects)) inputs.push({alternative});
for (const project of full.projects) {
  inputs.push({q: project.name}, {q: project.description});
  for (const alias of project.aliases || []) inputs.push({q: alias.name});
  if (project.github) inputs.push({license: project.github.license});
  for (const [key, field] of [['run_mode', 'run_modes'], ['install_method', 'install_methods']]) {
    for (const fact of (project.deployment || {})[field] || []) inputs.push({[key]: fact.value});
  }
  inputs.push({q: project.name, category: project.categories[0], license: api.licenseOf(project) || 'unknown',
    stars: api.starsOf(project), metrics: api.metricsPresent(project) ? 'present' : 'missing',
    window: api.pushWindowOf(project, full) || 'all',
    alternative: (project.alternatives[0] || {}).name || ''});
}
assert.deepEqual(api.diagnosticCounts(compact.projects, compact), api.diagnosticCounts(full.projects, full));
assert.deepEqual(api.alternativeNames(compact.projects), api.alternativeNames(full.projects));
for (const input of inputs) {
  const expected = api.normalizeState(input, full);
  assert.deepEqual(api.normalizeState(input, compact), expected);
  for (const sort of ['name', 'stars', 'pushed']) {
    const state = {...expected, sort};
    const ids = data => api.selectProjects(data.projects, state, data).map(project => project.id);
    assert.deepEqual(ids(compact), ids(full), JSON.stringify(state));
  }
}
"""], cwd=ROOT, input=json.dumps([catalog, search_index(catalog)]), text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_local_assets_evidence_and_portable_paths(self):
        self.assertTrue((self.output / 'styles.css').is_file())
        self.assertTrue((self.output / 'catalog.js').is_file())
        self.assertTrue((self.output / '.nojekyll').is_file())
        published = (self.output / 'catalog.json').read_text()
        self.assertEqual(published.count('\n'), 1, 'catalog.json is written without indentation')
        self.assertFalse(any('last_good' in (p.get('star_history') or {}) for p in json.loads(published)['projects']))
        self.assertEqual(load_site_catalog(self.output), self.catalog)
        for name in ('hn_evidence.json', 'alternatives.json', 'star_history.json'):
            copy = (self.output / 'data' / name).read_text()
            self.assertEqual(copy.count('\n'), 1, name + ' is written without indentation')
            self.assertEqual(json.loads(copy), json.loads((ROOT / 'data' / name).read_text()))
        for image in self.page.images:
            self.assertIsInstance(image['alt'], str)
            self.assertFalse(image['src'].startswith('/'))
            self.assertTrue((self.output / image['src']).is_file())
        for href in self.page.links:
            if href.startswith('#'):
                self.assertIn(href[1:], self.page.ids)
            elif not href.startswith(('https://', 'http://')) and href != './':
                target = self.output / href
                self.assertTrue((target / 'index.html').is_file() if href.endswith('/') else target.is_file(), href)
        for resource in self.page.nodes('link'):
            href = resource.attrs['href']
            self.assertFalse(href.startswith(('/', 'http:', 'https:')))
            self.assertTrue((self.output / href.split('?', 1)[0]).is_file(), href)
        self.assertTrue((self.output / 'vendor/FONT-LICENSE.txt').is_file())
        self.assertTrue((self.output / 'vendor/FONT-PROVENANCE.json').is_file())

    def test_build_writes_no_standalone_download_and_links_to_none(self):
        self.assertFalse((self.output / 'standalone.html').exists())
        self.assertFalse((self.output / 'observatory/report.html').exists())
        pages = [self.output / 'index.html', *(self.output / 'records').glob('*.html'),
                 self.output / 'observatory/index.html', self.output / 'spotlight/index.html']
        for page in pages:
            html = page.read_text()
            self.assertNotIn('standalone.html', html, page)
            self.assertNotIn('report.html', html, page)
        footer = Page(self.html).by_id['about']
        self.assertEqual([link.attrs['href'] for link in footer.descendants('a') if link.attrs.get('href') in ('catalog.json', 'data/hn_evidence.json')],
                         ['data/hn_evidence.json', 'catalog.json'])

    def test_footer_pattern_is_copied_and_not_rotating_art(self):
        pattern = 'patterns/navypattern2.png'
        original = (ROOT / 'site' / pattern).read_bytes()
        self.assertEqual((self.output / pattern).read_bytes(), original)
        css = (self.output / 'styles.css').read_text()
        self.assertIn(f'url({pattern})', css)
        self.assertNotIn('url(site/footer-backgrounds/', css)
        self.assertEqual(self.catalog['footer_backgrounds'], sorted(
            str(p.relative_to(ROOT / 'site')) for p in (ROOT / 'site/footer-backgrounds').glob('*')
            if p.is_file() and not p.name.startswith('.') and p.suffix.lower() in {'.png', '.webp'}))
        self.assertNotIn(pattern, self.catalog['footer_backgrounds'])
        footer = next(image for image in self.page.images if 'data-footer-background' in image)
        self.assertEqual(json.loads(footer['data-backgrounds']), self.catalog['footer_backgrounds'])
        self.assertNotEqual(footer['src'], pattern)

    def test_supplied_brand_assets_are_sized_transparent_and_copied_unchanged(self):
        for name in BRAND_ASSETS:
            self.assertEqual((self.output / 'brand' / name).read_bytes(), (ROOT / 'site/brand' / name).read_bytes())
        for name, size in (('fruit-16.png', 16), ('fruit-32.png', 32), ('fruit-96.png', 96), ('awesome-open-logo.png', 512)):
            data = (self.output / 'brand' / name).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            width, height, depth, color = struct.unpack('>IIBB', data[16:26])
            self.assertEqual((width, height, depth, color), (size, size, 8, 6))
        icon = (self.output / 'brand/favicon.ico').read_bytes()
        self.assertEqual(struct.unpack('<HHH', icon[:6]), (0, 1, 3))
        self.assertEqual([(icon[6 + 16*i], icon[7 + 16*i]) for i in range(3)], [(16, 16), (32, 32), (48, 48)])
        brand = [node for node in self.page.nodes('a') if node.has_class('brand')][0]
        self.assertEqual(brand.attrs['aria-label'], 'Awesome Open home')
        self.assertEqual(brand.descendants('img')[0].attrs['alt'], '')

    def test_stylesheet_content_hash_prevents_stale_branding_on_return_visits(self):
        expected = 'href="' + font_asset_url('styles.css') + '"'
        self.assertIn(expected, self.html)
        # The token follows the stylesheet's bytes, not the source revision.
        local = copy.deepcopy(self.catalog)
        local['source_sha'] = None
        self.assertIn(expected, render_html(local))

    def test_every_same_origin_runtime_url_is_content_versioned(self):
        pages = [self.output / 'index.html', next((self.output / 'records').glob('*.html')),
                 self.output / 'observatory/index.html', self.output / 'spotlight/index.html']
        for page in pages:
            html = page.read_text()
            urls = re.findall(r'<link rel="stylesheet" href="([^"]+)"|<script src="([^"]+)"', html)
            urls = [a or b for a, b in urls if not (a or b).startswith(('data:', 'http'))]
            self.assertTrue(urls, page)
            for url in urls:
                self.assertRegex(url, r'\?v=[0-9a-f]{16,64}$', f'{page.name}: {url}')

    def test_animation_dependencies_removed_and_reduced_motion_supported(self):
        self.assertNotIn('gsap', self.html)
        self.assertFalse((self.output / 'motion.js').exists())
        self.assertFalse((self.output / 'vendor/gsap.min.js').exists())
        css = (self.output / 'styles.css').read_text()
        self.assertIn('(prefers-reduced-motion:reduce)', css)
        self.assertIn('scroll-behavior:auto', css)
        self.assertIn('transition:none!important', css)

    def test_specimen_art_is_optional_and_portable(self):
        illustrated = [p for p in self.catalog['projects'] if p.get('artwork')]
        manifest = json.loads((ROOT / 'data/specimen_art.json').read_text())
        catalog_ids = {p['id'] for p in self.catalog['projects']}
        approved_ids = {project_id for project_id, artwork in manifest['artworks'].items()
                        if artwork.get('review_status') == 'approved' and project_id in catalog_ids}
        self.assertEqual({p['id'] for p in illustrated}, approved_ids)
        self.assertTrue({'OpenTofu', 'OpenRefine', 'OpenSCAD', 'OpenObserve', 'OpenResty', 'OpenSSL', 'OpenSearch'}
                        <= {p['name'] for p in illustrated})
        for project in self.catalog['projects']:
            card = self.records[project['id']].by_id['project-' + project['id']]
            figures = [n for n in card.descendants('figure') if n.has_class('specimen-art')]
            self.assertEqual(len(figures), 1 if project.get('artwork') else 0)
            if figures:
                image = figures[0].descendants('img')[0]
                # Plates show the transparent derivative while it matches its source; otherwise the original.
                self.assertIn(image.attrs['src'], (project['artwork']['path'], f'specimens/cutouts/{project["id"]}.webp'))
                self.assertTrue((self.output / image.attrs['src']).is_file())
                self.assertEqual(image.attrs['alt'], project['artwork']['alt'])

    def test_output_deterministic_and_revision_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            output = copy_site_fixture(self.output, Path(temp) / 'site')
            before = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            build(output, source_sha='a' * 40)
            after = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob('*') if p.is_file()}
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
        self.assertEqual(json.loads(Page(document).by_id['catalog-data'].text), search_index(catalog))

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
        self.assertEqual(json.loads(page.by_id['catalog-data'].text), search_index(catalog))
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

