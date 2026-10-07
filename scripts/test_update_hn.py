import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import update_hn as hn


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.project = {'name': 'OpenThing', 'slug': 'openthing', 'domains': ['openthing.org'], 'repositories': ['org/openthing'], 'title_aliases': ['OpenThing'], 'readme_url': 'https://github.com/org/openthing', 'eligible': True, 'monthly_counts': [0, 3] + [0] * 22, 'search_url': 'https://hn.algolia.com/?q=OpenThing&type=story'}
        self.evidence = {'projects': [self.project], 'months': hn.window(datetime(2026, 10, 3, tzinfo=timezone.utc))[2], 'shared_monthly_maximum': 6}

    def test_completed_month_window(self):
        start, end, months = hn.window(datetime(2026, 10, 3, tzinfo=timezone.utc))
        self.assertEqual(start.isoformat(), '2024-10-01T00:00:00+00:00')
        self.assertEqual(end.isoformat(), '2026-10-01T00:00:00+00:00')
        self.assertEqual((len(months), months[0], months[-1]), (24, '2024-10', '2026-09'))
        self.assertEqual(hn.window(datetime(2026, 1, 1, tzinfo=timezone.utc))[2][-1], '2025-12')

    def test_identity_boundaries(self):
        for url in ['https://openthing.org/docs', 'https://docs.openthing.org/x', 'https://github.com/org/openthing/issues/2']:
            self.assertTrue(hn.identity_reason({'url': url}, self.project))
        for url in ['https://evilopenthing.org', 'https://openthing.org.evil.com', 'https://github.com/org/openthing-other', 'https://evil.com/openthing.org']:
            self.assertIsNone(hn.identity_reason({'url': url}, self.project))
        self.assertIsNone(hn.identity_reason({'title': 'OpenThings'}, self.project))
        self.assertTrue(hn.identity_reason({'title': 'New OpenThing release'}, self.project))

    def test_ambiguous_title_requires_context(self):
        project = dict(self.project, title_context_pattern=r'\bAI\b')
        self.assertIsNone(hn.identity_reason({'title': 'OpenThing conference'}, project))
        self.assertTrue(hn.identity_reason({'title': 'OpenThing AI agent'}, project))

    def test_opencode_collision_excluded(self):
        projects = json.loads(hn.PROJECTS_PATH.read_text())['projects']
        project = next(p for p in projects if p['name'] == 'OpenCode')
        self.assertIsNone(hn.identity_reason({'title': 'OpenCode AI coding agent', 'url': 'https://github.com/opencode-ai/opencode'}, project))
        self.assertIsNone(hn.identity_reason({'title': 'OpenCode AI coding agent', 'url': 'https://example.com'}, project))
        self.assertTrue(hn.identity_reason({'title': 'OpenCode', 'url': 'https://github.com/sst/opencode'}, project))
        self.assertTrue(hn.identity_reason({'title': 'OpenCode by SST', 'url': 'https://example.com'}, project))

    def test_official_domain_changes_and_shared_host_siblings(self):
        projects = {p['name']: p for p in json.loads(hn.PROJECTS_PATH.read_text())['projects']}
        self.assertTrue(hn.identity_reason({'title': 'Post-Quantum Cryptography', 'url': 'https://www.openssh.org/pq.html'}, projects['OpenSSH']))
        self.assertTrue(hn.identity_reason({'title': 'CVE-2025-4575', 'url': 'https://openssl-library.org/news/secadv/20250522.txt'}, projects['OpenSSL']))
        sibling = {'title': 'LibreSSL 4.0.0', 'url': 'https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-4.0.0-relnotes.txt'}
        self.assertIsNone(hn.identity_reason(sibling, projects['OpenBSD']))
        self.assertTrue(hn.identity_reason(dict(sibling, title='OpenBSD updates LibreSSL'), projects['OpenBSD']))
        self.assertTrue(hn.identity_reason({'title': 'Calendar(1)', 'url': 'https://man.openbsd.org/calendar'}, projects['OpenBSD']))

    def test_pages_and_overflow_split(self):
        calls = []
        def getter(url):
            query = parse_qs(urlsplit(url).query)
            calls.append(query)
            page = int(query['page'][0])
            return {'hits': [{'objectID': str(page)}], 'nbPages': 3, 'nbHits': 201}
        hits, sources = hn.fetch_query('OpenThing', 0, 100, getter)
        self.assertEqual(len(hits), 3)
        self.assertEqual(len(sources), 3)
        def crowded(url):
            filters = parse_qs(urlsplit(url).query)['numericFilters'][0]
            return {'hits': [], 'nbPages': 10, 'nbHits': 1000} if filters == 'created_at_i>=0,created_at_i<100' else {'hits': [{'objectID': filters}], 'nbPages': 1, 'nbHits': 1}
        hits, sources = hn.fetch_query('OpenThing', 0, 100, crowded)
        self.assertEqual(len(hits), 2)
        self.assertEqual(len(sources), 3)

    def test_collection_deduplicates_and_excludes_current_month(self):
        start, end, months = hn.window(datetime(2026, 10, 3, tzinfo=timezone.utc))
        project = dict(self.project, queries=['OpenThing', 'openthing.org'])
        hits = [
            {'objectID': '123', 'title': 'OpenThing release', 'url': '', 'created_at_i': int(start.timestamp())},
            {'objectID': '124', 'title': 'OpenThing today', 'url': '', 'created_at_i': int(end.timestamp())},
            {'objectID': '125', 'title': 'Unrelated', 'url': '', 'created_at_i': int(start.timestamp())},
        ]
        with patch.object(hn, 'fetch_query', return_value=(hits, ['https://example.org/query'])):
            result = hn.collect_project(project, start, end, months)
        self.assertEqual(result['story_count'], 1)
        self.assertEqual(result['monthly_counts'], [1] + [0] * 23)
        self.assertFalse(result['eligible'])
        self.assertEqual(len(result['excluded_candidates']), 1)

    def test_svg_safe_and_shared_scale(self):
        project = dict(self.project, name='Open <script> & Thing')
        root = ET.fromstring(hn.svg(project, self.evidence))
        rectangles = root.findall('{http://www.w3.org/2000/svg}rect')
        self.assertEqual(len(rectangles), 24)
        self.assertEqual(rectangles[1].attrib['height'], '14.142')
        self.assertIn('Shared square-root scale: 0–6 stories/month.', hn.svg(project, self.evidence))
        self.assertNotIn('<script>', hn.svg(project, self.evidence))
        self.assertNotIn('href=', hn.svg(project, self.evidence))

    def test_square_root_scale_preserves_shared_heights_and_baseline(self):
        evidence = dict(self.evidence, shared_monthly_maximum=20)
        counts = [0, 1, 2, 5, 10, 20] + [0] * 18
        project = dict(self.project, monthly_counts=counts)
        rectangles = ET.fromstring(hn.svg(project, evidence)).findall('{http://www.w3.org/2000/svg}rect')
        heights = [float(rect.attrib['height']) for rect in rectangles]
        self.assertEqual(heights[:6], [0, 4.472, 6.325, 10, 14.142, 20])
        for rect in rectangles:
            self.assertAlmostEqual(float(rect.attrib['y']) + float(rect.attrib['height']), 22)
        # A lower-activity project keeps the same heights, not its own maximum.
        smaller = dict(project, monthly_counts=[0, 1, 2] + [0] * 21)
        small_rectangles = ET.fromstring(hn.svg(smaller, evidence)).findall('{http://www.w3.org/2000/svg}rect')
        self.assertEqual([r.attrib['height'] for r in small_rectangles[:3]],
                         [r.attrib['height'] for r in rectangles[:3]])

    def test_square_root_scale_handles_all_zero_counts(self):
        project = dict(self.project, monthly_counts=[0] * 24)
        evidence = dict(self.evidence, shared_monthly_maximum=0)
        rectangles = ET.fromstring(hn.svg(project, evidence)).findall('{http://www.w3.org/2000/svg}rect')
        self.assertTrue(all(r.attrib['height'] == '0.000' and r.attrib['y'] == '22.000' for r in rectangles))

    def test_decorator_idempotent_duplicates_and_stale(self):
        row = '| [OpenThing](https://github.com/org/openthing) | Description. |\n'
        source = row + row + '| [Other](https://example.org) | Description. |\n'
        result = hn.decorate_readme(source, self.evidence)
        self.assertEqual(result.count('![HN discussions / 2y]'), 2)
        image = f'[![HN discussions / 2y](assets/hn/{self.project["slug"]}.svg "HN discussions / 2y")]({self.project["search_url"]})'
        self.assertEqual(result.count(image), 2)
        self.assertEqual(result.count('<br>'), 2)
        self.assertEqual(hn.decorate_readme(result, self.evidence), result)
        bold = row.replace('[OpenThing](https://github.com/org/openthing)', '**[OpenThing](https://github.com/org/openthing)**')
        self.assertIn('**<br><!-- HN:START -->', hn.decorate_readme(bold, self.evidence))
        empty = dict(self.evidence, projects=[])
        self.assertEqual(hn.decorate_readme(result, empty), source)

    def test_checked_in_evidence_invariants(self):
        if not hn.EVIDENCE_PATH.exists():
            self.skipTest('No committed evidence yet')
        evidence = json.loads(hn.EVIDENCE_PATH.read_text())
        self.assertEqual(len(evidence['months']), 24)
        eligible_max = 1
        for project in evidence['projects']:
            # Validate the identity embedded in cached evidence. A mapping-only
            # PR takes effect after the publisher collects replacement evidence.
            stories = project['stories']
            self.assertEqual(len({s['id'] for s in stories}), len(stories))
            self.assertTrue(all(hn.identity_reason(s, project) for s in stories))
            expected = [sum(s['month'] == month for s in stories) for month in evidence['months']]
            self.assertEqual(project['monthly_counts'], expected)
            self.assertEqual(project['story_count'], len(stories))
            self.assertEqual(project['eligible'], len(stories) >= hn.MIN_STORIES and sum(n > 0 for n in expected) >= hn.MIN_MONTHS)
            if project['eligible']:
                eligible_max = max(eligible_max, max(expected))
                # Source/evidence-only PRs intentionally leave tracked SVGs
                # stale. Check the rendered preview, not published artifacts.
                rendered = ET.fromstring(hn.svg(project, evidence))
                self.assertEqual(len(rendered.findall('{http://www.w3.org/2000/svg}rect')), 24)
        self.assertEqual(evidence['shared_monthly_maximum'], eligible_max)

    def test_identity_mapping_has_complete_unique_projects(self):
        projects = json.loads(hn.PROJECTS_PATH.read_text())['projects']
        self.assertEqual(len({p['slug'] for p in projects}), len(projects))
        for project in projects:
            for key in ['name', 'slug', 'readme_url']:
                self.assertIsInstance(project[key], str)
                self.assertTrue(project[key])
            for key in ['domains', 'repositories', 'title_aliases', 'queries']:
                self.assertIsInstance(project[key], list)
                self.assertTrue(all(isinstance(value, str) and value for value in project[key]))
            self.assertTrue(project['queries'])
            self.assertTrue(project['title_aliases'])

    def test_collector_refreshes_removed_identity_field_without_rendering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_path = root / 'evidence.json'
            identities_path = root / 'projects.json'
            evidence = dict(self.evidence, projects=[dict(self.project, title_context_pattern='AI')])
            identity = {key: value for key, value in self.project.items() if key not in hn.COLLECTED_KEYS}
            evidence_path.write_text(json.dumps(evidence))
            identities_path.write_text(json.dumps({'projects': [identity]}))
            with patch.object(hn, 'EVIDENCE_PATH', evidence_path), \
                    patch.object(hn, 'PROJECTS_PATH', identities_path), \
                    patch.object(hn, 'window', return_value=(None, None, self.evidence['months'])), \
                    patch.object(hn, 'refresh', return_value=self.evidence) as refresh, \
                    patch.object(hn, 'render', side_effect=AssertionError('Collector must not render')), \
                    patch('sys.argv', ['update_hn.py']):
                hn.main()
            refresh.assert_called_once_with()
            self.assertEqual(json.loads(evidence_path.read_text()), self.evidence)


if __name__ == '__main__':
    unittest.main()
