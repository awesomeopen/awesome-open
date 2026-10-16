"""Literal count wording, canonical identity reuse and offline badge output."""

import json
from pathlib import Path
import unittest
from xml.etree import ElementTree

import build_catalog
import readme_badges as badges


class BadgeTests(unittest.TestCase):
    def test_counts_unique_identities_including_non_github_projects(self):
        source = """## One

| Project | Description |
| --- | --- |
| [Open One](https://github.com/Example/Open/) | A tool. |
| [Open Web](https://EXAMPLE.org/) | A service. |
| [Open Case](https://example.org/Tool) | Another tool. |

## Two

| Project | Description |
| --- | --- |
| [Open One](https://github.com/example/open) | A tool. |
| [Open Web](https://example.org) | A service. |
| [Open Case](https://example.org/tool) | A distinct path. |
"""
        self.assertEqual(badges.specimen_count(source), 4)
        self.assertIn('4 specimen', badges.count_badge(source))

    def test_count_matches_the_current_catalog(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'README.source.md').read_text()
        inputs = [json.loads((root / 'data' / filename).read_text()) for filename in
                  ('github_metrics.json', 'alternatives.json', 'hn_evidence.json')]
        catalog = build_catalog.build_catalog(source, *inputs)
        self.assertEqual(badges.specimen_count(source), len(catalog['projects']))

    def test_badge_is_accessible_flat_and_deterministic(self):
        for count in (0, 1, 511, 10000):
            label = f'{count} specimen'
            svg = badges.flat_badge(label)
            self.assertEqual(svg, badges.flat_badge(label))
            root = ElementTree.fromstring(svg)
            self.assertEqual(root.attrib['aria-label'], label)
            self.assertEqual(root.attrib['height'], '20')
            rect = root.find('{http://www.w3.org/2000/svg}rect')
            self.assertEqual(rect.attrib['fill'], '#0B2546')
            self.assertNotIn('rx', rect.attrib)
            self.assertNotIn('specimens', svg)

    def test_label_is_xml_escaped(self):
        svg = ElementTree.fromstring(badges.flat_badge('<label & "value">'))
        self.assertEqual(svg.attrib['aria-label'], '<label & "value">')


if __name__ == '__main__':
    unittest.main()
