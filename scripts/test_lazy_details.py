"""Initial-memory budget and native fallback contracts, without network or a browser."""
from font_assets import font_asset_url
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import json
import hashlib
import tempfile
import unittest

from build_site import ROOT, attach_specimen_cutouts, build, catalog_script_url, render_html
from site_test_fixtures import baseline_site, copy_site_fixture
from test_build_site import Page


class LazyDetailSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output, cls.catalog = baseline_site(source_sha='a' * 40)
        cls.initial = (cls.output / 'index.html').read_text()
        cls.page = Page(cls.initial)

    def test_generated_routes_share_content_versioned_drawer_runtime(self):
        code = (self.output / 'catalog.js').read_bytes()
        expected = 'catalog.js?v=' + hashlib.sha256(code).hexdigest()
        self.assertEqual(catalog_script_url(code.decode('utf-8')), expected)
        self.assertNotEqual(catalog_script_url(code.decode('utf-8') + '\n// changed'), expected)
        for path in [self.output / 'index.html', *sorted((self.output / 'records').glob('*.html'))]:
            page = Page(path.read_text())
            scripts = [node.attrs['src'] for node in page.nodes('script') if 'src' in node.attrs]
            self.assertEqual(scripts, [font_asset_url("serif-preview.js"), expected], path.name)
        # A metadata-only revision keeps the same runtime identity; raw renderer
        # callers remain compatible with historical preview tooling.
        for revision in ('b' * 40, 'c' * 40):
            catalog = {**self.catalog, 'source_sha': revision}
            page = Page(render_html(catalog, deferred=True, script_url=expected))
            self.assertEqual(page.nodes('script')[1].attrs['src'], expected)
        self.assertEqual(Page(render_html(self.catalog)).nodes('script')[1].attrs['src'], 'catalog.js')

    def test_exhibition_uses_runtime_from_its_output_bundle(self):
        from build_exhibition_preview import build as build_exhibition
        with tempfile.TemporaryDirectory() as directory:
            output = copy_site_fixture(self.output, Path(directory) / 'site')
            runtime = (output / 'catalog.js').read_text() + '\n// fixture revision'
            (output / 'catalog.js').write_text(runtime)
            build_exhibition(output)
            page = Page((output / 'exhibition.html').read_text())
            self.assertEqual(page.nodes('script')[0].attrs['src'], catalog_script_url(runtime))

    def test_initial_entry_has_all_rows_but_no_detail_subtrees(self):
        ids = {p['id'] for p in self.catalog['projects']}
        self.assertEqual(set(self.page.cards), ids)
        self.assertEqual(len(self.page.cards), len(ids))
        self.assertFalse(any(n.has_class('specimen-plate') for n in self.page.elements))
        self.assertNotIn('<template', self.initial)
        self.assertFalse(any('/records/' in n.attrs.get('src', '') for n in self.page.nodes('script')))
        hosts = [n for n in self.page.elements if n.has_class('specimen-detail-host')]
        self.assertEqual(len(hosts), len(ids))
        for host in hosts:
            pid = host.attrs['data-project-id']
            self.assertIn(pid, ids)
            path = f'records/{pid}.html'
            self.assertEqual(host.attrs['data-detail-url'], path)
            self.assertEqual([a.attrs['href'] for a in host.descendants('a')], [path])
            self.assertTrue((self.output / path).is_file())
        # Structural regression budget, not an assertion about process RAM.
        full = Page(render_html(self.catalog, attach_specimen_cutouts(self.catalog, ROOT)))
        self.assertLess(len(self.page.elements), len(full.elements) * .25)
        self.assertLess(len(self.initial), len(render_html(self.catalog)) * .4)

    def test_static_records_preserve_every_plate_identity_evidence_and_local_asset(self):
        categories = {c['id']: c['name'] for c in self.catalog['categories']}
        from build_site import project_html
        cutouts = attach_specimen_cutouts(self.catalog, ROOT)
        for folio, project in enumerate(self.catalog['projects'], 1):
            pid = project['id']
            text = (self.output / 'records' / f'{pid}.html').read_text()
            page = Page(text)
            self.assertEqual(page.cards, [pid])
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertEqual(page.nodes('base')[0].attrs['href'], '../')
            self.assertEqual(len(page.nodes('h1')), 1)
            self.assertEqual(len(page.nodes('main')), 1)
            self.assertTrue(any(n.has_class('obs-header') for n in page.elements))
            self.assertTrue(any(n.has_class('obs-footer') for n in page.elements))
            self.assertEqual(len([n for n in page.elements if n.has_class('specimen-plate')]), 1)
            self.assertIn('name-' + pid, page.by_id)
            drawer = next(n for n in page.nodes('details') if n.has_class('specimen-drawer'))
            self.assertIn('open', drawer.attrs)
            expected = project_html(project, categories, self.catalog, folio, cutouts, position=1)
            expected = expected.replace('<details class="specimen-drawer">', '<details class="specimen-drawer" open>', 1)
            expected = expected.replace(f'href="#history-{pid}-',
                                        f'href="records/{pid}.html#history-{pid}-')
            self.assertIn(expected, text)
            self.assertIn(project['url'], page.links)
            self.assertIn(f'#project-{pid}', page.links)
            self.assertIn('Source revision:', text)
            for node in page.elements:
                for attr in ('src', 'href'):
                    value = node.attrs.get(attr)
                    if not value or node.tag == 'base' or value.startswith(('https:', 'http:', 'mailto:', '#')):
                        continue
                    relative = urlsplit(value).path
                    target = self.output / relative
                    self.assertTrue(target.is_file() or target.is_dir(), (pid, value))
                for attr in ('aria-labelledby', 'aria-describedby'):
                    for reference in node.attrs.get(attr, '').split():
                        self.assertIn(reference, page.ids)
            for image in page.images:
                if '/specimens/' in '/' + image['src'] or '/cutouts/' in '/' + image['src']:
                    self.assertEqual(image.get('loading'), 'lazy')

    def test_standalone_has_full_details_and_no_fetch_hosts(self):
        text = (self.output / 'standalone.html').read_text()
        self.assertEqual(text.count('class="specimen-interior specimen-plate'), len(self.catalog['projects']))
        self.assertNotIn('data-detail-url=', text)
        self.assertNotIn('class="detail-fallback"', text)
        self.assertNotIn('<base', text)
        self.assertIn('data:image/webp;base64,', text)

    def test_rebuild_discards_stale_record_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = copy_site_fixture(self.output, Path(directory) / 'site')
            stale = output / 'records' / ('0' * 64 + '.html')
            stale.write_text('obsolete')
            build(output)
            self.assertFalse(stale.exists())
            self.assertEqual(len(list((output / 'records').glob('*.html'))), len(self.catalog['projects']))


if __name__ == '__main__':
    unittest.main()
