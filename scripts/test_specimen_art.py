"""Optional artwork identity and README/site ranking parity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import warnings

from build_site import ROOT, attach_specimen_art
from build_catalog import build_catalog
import update_stats as stats


class ArtTests(unittest.TestCase):
    def test_missing_pending_and_invalid_art(self):
        pid = 'a' * 64
        project = {'id': pid, 'url': 'https://github.com/example/open'}
        entry = {'project_url': project['url'], 'path': f'specimens/{pid}.webp',
                 'alt': 'A seed-shaped tool.', 'width': 100, 'height': 100, 'review_status': 'approved'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            (root / 'site/specimens').mkdir(parents=True)
            manifest = root / 'data/specimen_art.json'
            def run(record):
                manifest.write_text(json.dumps({'schema_version': 1, 'artworks': {pid: record}}))
                catalog = {'projects': [copy.deepcopy(project)]}
                attach_specimen_art(catalog, root)
                return catalog['projects'][0]
            with warnings.catch_warnings(record=True) as caught:
                self.assertNotIn('artwork', run(entry))
                self.assertTrue(caught)
            self.assertNotIn('artwork', run({**entry, 'review_status': 'pending'}))
            for changes in ({'path': '../secret.webp'}, {'project_url': 'https://wrong.example'}, {'alt': ''}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    run({**entry, **changes})
            (root / 'site' / entry['path']).write_bytes(b'not an image')
            with self.assertRaises(ValueError):
                run(entry)

    def test_category_leaders_match_readme_with_cross_listing_and_ties(self):
        source = '## One\n' + ''.join(f'| [Open{n}](https://github.com/example/{n}) | Tool. |\n' for n in 'abcd')
        source += '## Two\n| [Opend](https://github.com/example/d) | Tool. |\n'
        record = {'created_at': '2020-01-01T00:00:00Z', 'pushed_at': None, 'license': None, 'stargazers_count': 10}
        snapshot = {'schema_version': 1, 'as_of': '2026-10-12', 'repositories': {f'example/{n}': record for n in 'abcd'}}
        catalog = build_catalog(source, snapshot, {'schema_version': 1, 'projects': []}, {'schema_version': 1, 'projects': []})
        expected = stats.category_leaders(source, snapshot['repositories'])
        for index, category in enumerate(catalog['categories'], 1):
            actual = {p['github']['repo'] for p in catalog['projects'] if category['id'] in p['leader_categories']}
            self.assertEqual(actual, expected[index])
        d = next(p for p in catalog['projects'] if p['name'] == 'Opend')
        self.assertEqual(d['leader_categories'], ['two'])
        self.assertEqual(d['categories'], ['one', 'two'])
