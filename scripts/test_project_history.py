"""Reviewed occurrence dates remain distinct from discovery and source milestones."""
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

from build_catalog import canonical_url, build_catalog
import history_view
import project_history as history
from test_specimen_plate import PROJECT, render

ROOT = Path(__file__).resolve().parents[1]


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / history.PATH).read_text())
        self.event = deepcopy(self.document['events'][0])
        self.event['project_url'] = PROJECT['url']
        self.projects = {canonical_url(PROJECT['url']): deepcopy(PROJECT)}

    def attach(self, event=None):
        history.attach(self.projects, {'schema_version': 1, 'events': [event or self.event]}, canonical_url)
        return self.projects[canonical_url(PROJECT['url'])]['history']

    def test_seed_evidence_and_date_bases(self):
        projects = {canonical_url(e['project_url']): {} for e in self.document['events']}
        before = deepcopy(self.document)
        history.attach(projects, self.document, canonical_url)
        self.assertEqual(self.document, before)
        self.assertEqual([e['occurred']['basis'] for e in self.document['events']], ['announcement', 'implementation'])
        self.assertEqual(self.document['events'][1]['sources'][-1]['date'], '2024-08-23')
        self.assertEqual(len(history.exact_events(self.document['events'])), 2)

    def test_optional_source_does_not_change_projects(self):
        before = deepcopy(self.projects)
        history.attach(self.projects, None, canonical_url)
        self.assertEqual(self.projects, before)

    def test_invalid_records_fail(self):
        for field, value in [('kind', 'fork'), ('project_url', 'https://example.org/unlisted'),
                             ('checked_at', '2026-02-30'), ('first_observed_at', '2027-01-01'),
                             ('new_name', self.event['old_name']), ('id', '<script>'),
                             ('note', '<script>alert(1)</script>')]:
            with self.subTest(field=field):
                event = deepcopy(self.event); event[field] = value
                with self.assertRaises(ValueError): self.attach(event)

    def test_duplicate_event_and_fact_fail(self):
        for changed in (False, True):
            other = deepcopy(self.event)
            if changed: other['id'] += '-duplicate'
            with self.assertRaises(ValueError):
                history.attach(self.projects, {'schema_version': 1, 'events': [self.event, other]}, canonical_url)

    def test_invalid_occurrences_fail(self):
        for field, value in [('value', '2023-13-20'), ('value', '2027-01-01'), ('value', '2023-09-21'),
                             ('precision', 'week'), ('basis', 'discovered'),
                             ('source_url', 'https://example.org/unreviewed'),
                             ('source_url', self.event['sources'][1]['url'])]:
            event = deepcopy(self.event); event['occurred'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): self.attach(event)

    def test_unknown_and_coarse_dates_are_evidence_only(self):
        for occurrence in (None, {**self.event['occurred'], 'value': '2023-09', 'precision': 'month'},
                           {**self.event['occurred'], 'value': '2023', 'precision': 'year'}):
            event = deepcopy(self.event); event['occurred'] = occurrence
            event['first_observed_at'] = '2026-10-19'
            events = self.attach(event)
            self.assertEqual(history.exact_events(events), [])
            plotted = history_view.timeline(None, None, None, events, 'abc')
            self.assertEqual(plotted, '')
            evidence = history_view.evidence(events)
            self.assertIn('First observed 2026-10-19', evidence)
            self.assertNotIn('<time', evidence)
            self.assertIn('Rename date unknown' if occurrence is None else 'not plotted', evidence)
            self.projects[canonical_url(PROJECT['url'])].pop('history')

    def test_literal_same_day_and_nearby_markers_use_separate_lanes(self):
        first = deepcopy(self.event); second = deepcopy(self.event)
        second.update(id='second', old_name='OpenTofu', new_name='OpenTofu Next')
        line = history_view.timeline('2023-09-20', ('2023-09-20', 'v1'), '2023-09-21', [first, second], 'abc')
        positions = re.findall(r'style="left:([\d.]+)%;top:([\d.]+)rem;', line)
        self.assertEqual(len(positions), 5)
        self.assertEqual(len({x for x, y in positions}), 2)
        self.assertEqual(len({y for x, y in positions}), 5)
        self.assertEqual(line.count('<li id='), 5)
        self.assertIn('OpenTF → OpenTofu (announced)', line)

    def test_event_ids_cannot_collide_with_repository_milestones(self):
        event = deepcopy(self.event); event['id'] = 'created'
        line = history_view.timeline('2023-09-20', None, None, [event], 'abc')
        ids = re.findall(r'<li id="([^"]+)"', line)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('history-abc-event-created', ids)
        self.assertIn('history-abc-repository-created', ids)

    def test_pre_repository_and_missing_creation(self):
        for created in (None, 'Unknown', '2025-01-01'):
            line = history_view.timeline(created, None, None, [self.event], 'abc')
            self.assertIn('2023-09-20', line)
            self.assertNotIn('left:-', line)
            if created != '2025-01-01': self.assertNotIn('history-repository-span', line)

    def test_shared_record_uses_history_and_evidence(self):
        events = self.attach()
        project = deepcopy(PROJECT); project['history'] = events
        page = render(project)
        self.assertIn('history-timeline', page)
        self.assertIn('Name-change evidence', page)
        self.assertIn('Reviewed 2026-10-19', page)
        self.assertNotIn('2026-10-19</time>', page)
        project['github'] = None
        self.assertIn('OpenTF → OpenTofu', render(project))

    def test_existing_timeline_unchanged_without_history(self):
        self.assertIn('class="timeline"', render(PROJECT))
        self.assertNotIn('Name-change evidence', render(PROJECT))


if __name__ == '__main__': unittest.main()


class HistoryOutputTests(unittest.TestCase):
    def test_full_record_and_offline_share_evidence(self):
        from site_test_fixtures import baseline_site
        output, catalog = baseline_site()
        projects = [p for p in catalog['projects'] if p.get('history')]
        self.assertEqual(len(projects), 2)
        standalone = (output / 'standalone.html').read_text()
        for project in projects:
            pid = project['id']
            record = (output / 'records' / (pid + '.html')).read_text()
            self.assertIn(f'href="records/{pid}.html#history-{pid}-', record)
            self.assertIn(f'href="#history-{pid}-', standalone)
            self.assertIn(history_view.event_title(project['history'][0]), record)
            self.assertIn(history_view.event_title(project['history'][0]), standalone)
        self.assertTrue((output / history.PATH).exists())
        exported = json.loads((output / 'catalog.json').read_text())
        self.assertEqual(sum(len(p.get('history', [])) for p in exported['projects']), 2)
        self.assertFalse(any(p.get('history') for p in exported['projects'] if p['name'] not in {'OpenHands', 'OpenTofu'}))
