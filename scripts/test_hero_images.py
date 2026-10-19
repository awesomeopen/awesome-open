"""Hero payload contract without requiring an image library in ordinary builds."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_jar_preview import build as build_hero, DISPLAY, responsive_image, jar_stylesheet_href
from build_site import ROOT, build


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class HeroImageTests(unittest.TestCase):
    def test_stylesheet_version_depends_only_on_exact_css_bytes(self):
        css = (ROOT / 'site/jars.css').read_bytes()
        expected = 'jars.css?v=' + hashlib.sha256(css).hexdigest()
        self.assertEqual(jar_stylesheet_href(css), expected)
        self.assertEqual(jar_stylesheet_href(bytes(bytearray(css))), expected)
        self.assertNotEqual(jar_stylesheet_href(css + b'\n'), expected)

    def test_comparison_stylesheet_accepts_old_and_versioned_links(self):
        from build_specimen_bounds_control import strip_jar_stylesheet, comparison_stylesheet
        base_css = b'/* base bytes differ from current CSS */'
        for suffix in ('', '?v=old', '?v=current'):
            link = f'<link rel="stylesheet" href="jars.css{suffix}">'
            other = '<link rel="stylesheet" href="styles.css?v=keep">'
            self.assertEqual(strip_jar_stylesheet(other + link), other)
            rewritten = comparison_stylesheet(link, base_css)
            self.assertEqual(rewritten, '<link rel="stylesheet" href="jars-before/' +
                             jar_stylesheet_href(base_css) + '">')

    def test_manifest_matches_originals_and_derivatives(self):
        manifest = json.loads((ROOT / 'site/jars/responsive.json').read_text())
        self.assertEqual(len(manifest['sources']), 17)
        cutouts = {source for source in manifest['sources'] if '/cutouts/' in source}
        self.assertEqual({Path(source).stem for source in cutouts}, {
            '73a5f910365e4bae9875aec5d471bb7fceb3f2fccb72a97789dd1370fba7e6bf',
            '79c63bf03f65fab31691d3f9dd0a884196d15614867c17dbc8d81956b648695c',
            'e30c092e43a54d5e7f675e251625a0bcfb59e18c106e9441d5f7cbf3f3842e83'})
        for source, record in manifest['sources'].items():
            with self.subTest(source=source):
                self.assertEqual(hashlib.sha256((ROOT / 'site' / source).read_bytes()).hexdigest(), record['sha256'])
                self.assertEqual([v['width'] for v in record['variants']], [256, 512, 768])
                for variant in record['variants']:
                    data = (ROOT / 'site' / variant['path']).read_bytes()
                    self.assertEqual(len(data), variant['bytes'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), variant['sha256'])
                    self.assertEqual(data[:4], b'RIFF')
                    self.assertEqual(data[8:12], b'WEBP')
                    self.assertEqual(variant['height'], round(record['height'] * variant['width'] / record['width']))

    def test_image_and_mask_candidates_share_resolution(self):
        manifest = json.loads((ROOT / 'site/jars/responsive.json').read_text())
        for source, record in manifest['sources'].items():
            attrs, mask = responsive_image(source, 241.5, manifest)
            self.assertIn('sizes="242px"', attrs)
            for variant in record['variants']:
                self.assertIn(f"{variant['path']} {variant['width']}w", attrs)
                self.assertIn(f"url('{variant['path']}') {variant['width']/242:.6f}x", mask)
            self.assertIn(f"{source} {record['width']}w", attrs)

    def test_production_hero_preserves_full_detail_and_offline_art(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            catalog = build(output)
            standalone = (output / 'standalone.html').read_bytes()
            original_page = (output / 'index.html').read_text()
            build_hero(output)
            self.assertIn('href="' + jar_stylesheet_href((output / 'jars.css').read_bytes()) + '"',
                          (output / 'jars.html').read_text())
            build_hero(output, production=True)
            html = (output / 'index.html').read_text()
            tags = Tags(html).tags
            stylesheet = jar_stylesheet_href((output / 'jars.css').read_bytes())
            self.assertEqual([attrs['href'] for tag, attrs in tags
                              if tag == 'link' and attrs.get('href', '').startswith('jars.css')],
                             [stylesheet])
            self.assertNotIn('href="jars.css"', html)
            build_hero(output)
            preview = (output / 'jars.html').read_text()
            self.assertIn(f'href="{stylesheet}"', preview)
            self.assertNotIn('href="jars.css"', preview)
            for tag, attrs in tags:
                if tag == 'article' and 'jar-exhibit' in attrs.get('class', ''):
                    self.assertRegex(attrs['style'], r'--display-height:[1-9][0-9]*px')
                    self.assertRegex(attrs['style'], r'--display-width:[1-9][0-9]*px')
                    self.assertRegex(attrs['style'], r'--display-foot:[0-9]+px')
            self.assertNotIn('glass-displacement', html)
            hero = [attrs for tag, attrs in tags if tag == 'img' and attrs.get('class') in
                    ('jar-photo', 'jar-reflection', 'jar-lid', 'jar-sticker', 'jar-cork', 'specimen-print')]
            self.assertEqual(len(hero), 27)
            prints = [attrs for tag, attrs in tags if tag == 'source' and attrs.get('media') == 'print']
            self.assertEqual(len(prints), len(hero))
            for img in hero:
                if img['class'] != 'specimen-print':
                    self.assertTrue(img['src'].startswith('jars/responsive/'))
                else:
                    self.assertTrue(img['src'].startswith(('jars/responsive/', 'specimens/')))
                self.assertIn('srcset', img)
                self.assertIn('sizes', img)
                self.assertNotEqual(img.get('loading'), 'lazy')
                self.assertTrue((output / img['src']).exists())
            glass = {img['src']: img for img in hero if img['class'] == 'jar-photo'}
            for img in hero:
                if img['class'] in ('jar-sticker', 'jar-cork'):
                    for attr in ('srcset', 'sizes', 'width', 'height'):
                        self.assertEqual(img[attr], glass[img['src']][attr])
            for source in prints:
                self.assertNotIn('responsive/', source['srcset'])
                self.assertEqual((output / source['srcset']).read_bytes(), (ROOT / 'site' / source['srcset']).read_bytes())
            for project in catalog['projects']:
                if project.get('artwork'):
                    cutout = f'specimens/cutouts/{project["id"]}.webp'
                    record = (output / 'records' / (project['id'] + '.html')).read_text()
                    self.assertTrue(f'src="{cutout}"' in record or f'src="{project["artwork"]["path"]}"' in record)
                self.assertIn(f'data-detail-url="records/{project["id"]}.html"', html)
            self.assertEqual((output / 'standalone.html').read_bytes(), standalone)
            self.assertNotIn(b'jars/responsive/', standalone)
            self.assertNotIn(b'jars.css', standalone)
            self.assertNotIn(b'jars.js', standalone)
            self.assertNotIn(b'class="jar-hall"', standalone)
            # Simulate a CSS-only rebuild without touching approved source files.
            css_path = ROOT / 'site/jars.css'
            changed_css = css_path.read_bytes() + b'\n/* cache regression */\n'
            read_bytes = Path.read_bytes
            with patch.object(Path, 'read_bytes', lambda path:
                              changed_css if path == css_path else read_bytes(path)):
                build_hero(output, production=True)
            changed_href = jar_stylesheet_href(changed_css)
            self.assertNotEqual(changed_href, stylesheet)
            self.assertIn(f'href="{changed_href}"', (output / 'index.html').read_text())
            self.assertEqual((output / 'jars.css').read_bytes(), changed_css)
            # Catalog source revision alone must not invalidate unchanged CSS.
            catalog['source_sha'] = 'f' * 40
            (output / 'catalog.json').write_text(json.dumps(catalog))
            (output / 'index.html').write_text(original_page)
            build_hero(output, production=True)
            self.assertIn(f'href="{stylesheet}"', (output / 'index.html').read_text())
            self.assertEqual((output / 'jars.css').read_bytes(), css_path.read_bytes())

    def test_weekly_hero_uses_saved_membership_and_fits_subjects(self):
        from datetime import date
        import weekly_draw
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            catalog = build(output)
            state = weekly_draw.advance(weekly_draw.empty(), catalog, date(2026, 10, 12))
            state = weekly_draw.advance(state, catalog, date(2026, 10, 19))
            catalog['weekly_draws'] = state
            (output / 'catalog.json').write_text(json.dumps(catalog))
            result = build_hero(output, production=True)
            tags = Tags((output / 'index.html').read_text()).tags
            occupants = {attrs['data-project'] for tag, attrs in tags
                         if tag == 'article' and 'jar-exhibit' in attrs.get('class', '')}
            self.assertEqual(occupants, {p['id'] for p in state['editions'][0]['projects']})
            self.assertEqual(result['display_week'], '2026-10-19')
            images = [attrs for tag, attrs in tags if tag == 'img' and attrs.get('class') == 'specimen-print']
            self.assertEqual(len(images), 7)
            for img in images:
                self.assertTrue((output / img['src']).is_file())
                self.assertIn('transform:translate(', img['style'])
            self.assertNotIn('class="jar-draw-link"', (output / 'index.html').read_text())
            self.assertIn('href="draws/"', (output / 'index.html').read_text())
