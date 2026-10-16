"""Category artwork identity, responsive delivery and offline integrity."""
import base64
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from build_site import ROOT, search_index
from category_art import attach_category_art, category_image, webp_dimensions
from site_test_fixtures import baseline_site


class Images(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.images = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img' and attrs.get('class') == 'category-art':
            self.images.append(attrs)


class CategoryArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output, cls.catalog = baseline_site(source_sha='a' * 40)
        cls.manifest = json.loads((ROOT / 'site/domains/provenance.json').read_text())

    def test_complete_category_ids_and_source_filename_mapping(self):
        categories = self.manifest['categories']
        self.assertTrue(set(categories).issubset({c['id'] for c in self.catalog['categories']}))
        self.assertEqual(len(categories), 21)
        self.assertEqual(len({a['source_filename'] for a in categories.values()}), 21)
        self.assertEqual(categories['ai--language-models']['source_filename'],
                         'Coral-throated open source songbird.png')
        self.assertEqual(categories['security--privacy']['source_filename'],
                         'Violet-seamed armored burrower.png')
        self.assertIsNone(self.manifest['source']['original_sha256'])
        self.assertIsNone(self.manifest['recipe']['source_encoder_versions'])

    def test_all_variant_bytes_dimensions_and_brand_inventory(self):
        inventory = json.loads((ROOT / 'brand/assets.lock.json').read_text())['files']
        for category in self.catalog['categories']:
            variants = category['artwork']['variants']
            self.assertEqual([variants[s]['width'] for s in ('s', 'm', 'l')], [104, 207, 414])
            for variant in variants.values():
                with self.subTest(path=variant['path']):
                    data = (ROOT / 'site' / variant['path']).read_bytes()
                    self.assertEqual(webp_dimensions(data), (variant['width'], variant['height']))
                    self.assertEqual(len(data), variant['bytes'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), variant['sha256'])
                    self.assertEqual(inventory['site/' + variant['path']],
                                     {'bytes': len(data), 'sha256': variant['sha256']})
                    self.assertEqual((self.output / variant['path']).read_bytes(), data)
        self.assertEqual(len(list((self.output / 'domains').glob('*.webp'))), 63)
        self.assertEqual(json.loads((self.output / 'domains/provenance.json').read_text()), self.manifest)

    def test_responsive_markup_and_small_payload(self):
        images = Images((self.output / 'index.html').read_text()).images
        self.assertEqual(len(images), 21)
        for image in images:
            self.assertTrue(image['src'].endswith('-s.webp'))
            self.assertTrue(image['data-end-src'].endswith('-m.webp'))
            self.assertEqual(image['data-end-width'], '207')
            self.assertEqual(image['sizes'], '48px')
            self.assertEqual((image['width'], image['height']), ('104', '104'))
            self.assertEqual(image['alt'], '')
            self.assertEqual(image['aria-hidden'], 'true')
            self.assertEqual(image['loading'], 'lazy')
            self.assertEqual(image['decoding'], 'async')
            self.assertEqual(image['fetchpriority'], 'low')
            self.assertEqual([candidate.split()[-1] for candidate in image['srcset'].split(',')],
                             ['104w', '207w', '414w'])
        self.assertLess(sum(c['artwork']['variants']['s']['bytes'] for c in self.catalog['categories']), 160_000)
        self.assertTrue(all('artwork' not in c for c in search_index(self.catalog)['categories']))

    def test_standalone_embeds_small_bytes_without_external_candidates(self):
        images = Images((self.output / 'standalone.html').read_text()).images
        self.assertEqual(len(images), 21)
        for category, image in zip(self.catalog['categories'], images):
            self.assertEqual(base64.b64decode(image['data-end-src'].split(',', 1)[1]),
                             (ROOT / 'site' / category['artwork']['variants']['m']['path']).read_bytes())
            self.assertNotIn('srcset', image)
            self.assertNotIn('sizes', image)
            self.assertTrue(image['src'].startswith('data:image/webp;base64,'))
            self.assertEqual(base64.b64decode(image['src'].split(',', 1)[1]),
                             (ROOT / 'site' / category['artwork']['variants']['s']['path']).read_bytes())

    def test_unknown_missing_and_corrupt_art_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'site/domains', root / 'site/domains')
            path = root / 'site/domains/provenance.json'
            for change in ('unknown', 'path', 'hash', 'dimensions', 'missing_variant', 'unreviewed'):
                manifest = copy.deepcopy(self.manifest)
                record = manifest['categories']['ai--language-models']
                if change == 'unknown':
                    manifest['categories']['unknown'] = record
                elif change == 'path':
                    record['variants']['s']['path'] = '../outside.webp'
                elif change == 'hash':
                    record['variants']['s']['sha256'] = '0' * 64
                elif change == 'dimensions':
                    record['variants']['s']['width'] = 105
                elif change == 'missing_variant':
                    del record['variants']['l']
                else:
                    record['review_status'] = 'pending'
                path.write_text(json.dumps(manifest))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    attach_category_art(copy.deepcopy(self.catalog), root)

    def test_absent_art_renders_no_placeholder(self):
        self.assertEqual(category_image({'id': 'new-category'}), '')
        with tempfile.TemporaryDirectory() as directory:
            catalog = {'categories': [{'id': 'new-category'}]}
            attach_category_art(catalog, directory)
            self.assertNotIn('artwork', catalog['categories'][0])


if __name__ == '__main__':
    unittest.main()
