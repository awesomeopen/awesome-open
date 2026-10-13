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
            hero = [attrs for tag, attrs in tags if tag == 'img' and attrs.get('class') in
                    ('jar-photo', 'jar-reflection', 'jar-lid', 'specimen-print')]
            self.assertEqual(len(hero), 24)
            prints = [attrs for tag, attrs in tags if tag == 'source' and attrs.get('media') == 'print']
            self.assertEqual(len(prints), len(hero))
            for img in hero:
                self.assertTrue(img['src'].startswith('jars/responsive/'))
                self.assertIn('srcset', img)
                self.assertIn('sizes', img)
                self.assertNotEqual(img.get('loading'), 'lazy')
                self.assertTrue((output / img['src']).exists())
            for source in prints:
                self.assertNotIn('responsive/', source['srcset'])
                self.assertEqual((output / source['srcset']).read_bytes(), (ROOT / 'site' / source['srcset']).read_bytes())
            for project in catalog['projects']:
                if project.get('artwork'):
                    self.assertIn(f'src="{project["artwork"]["path"]}"', html)
            self.assertEqual((output / 'standalone.html').read_bytes(), standalone)
            self.assertNotIn(b'jars/responsive/', standalone)
