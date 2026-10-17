"""Hero payload contract without requiring an image library in ordinary builds."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest

from build_jar_preview import build as build_hero, DISPLAY, responsive_image
from build_site import ROOT, build


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class HeroImageTests(unittest.TestCase):
    def test_manifest_matches_originals_and_derivatives(self):
        manifest = json.loads((ROOT / 'site/jars/responsive.json').read_text())
        self.assertEqual(len(manifest['sources']), 14)
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
            build_hero(output, production=True)
            html = (output / 'index.html').read_text()
            tags = Tags(html).tags
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
