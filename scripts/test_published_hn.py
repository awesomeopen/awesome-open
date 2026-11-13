"""Published references preserve every collector field and distinct snapshot."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import published_hn as export


def fixture():
    project = {'readme_url': 'https://github.com/example/open', 'stories': [{'id': 1}],
               'excluded_candidates': [{'id': 2}], 'monthly_counts': [1]}
    return {'schema_version': 2, 'projects': [project], 'queue': {
        project['readme_url']: {'status': 'failed', 'pending': {'page': 2}, 'last_good': {
            'project': deepcopy(project), 'months': ['2026-10'], 'collected_at': None,
            'identity_key': 'original'}}}, 'budget': {'spent': 3}}


class PublishedHNTests(unittest.TestCase):
    def test_live_round_trip(self):
        source = json.loads((Path(__file__).resolve().parents[1] / 'data/hn_evidence.json').read_text())
        before = deepcopy(source)
        published = export.publish(source)
        self.assertEqual(published['projects'], source['projects'])
        self.assertEqual(export.materialize(json.loads(json.dumps(published))), source)
        self.assertEqual(source, before)
        self.assertLess(len(json.dumps(published)), len(json.dumps(source)))

    def test_recovery_metadata_and_independent_objects(self):
        source = fixture()
        published = export.publish(source)
        good = next(iter(published['queue'].values()))['last_good']
        self.assertEqual(good['project_ref'], 0)
        self.assertNotIn('project', good)
        restored = export.materialize(published)
        self.assertEqual(restored, source)
        next(iter(restored['queue'].values()))['last_good']['project']['stories'].clear()
        self.assertEqual(restored['projects'][0]['stories'], [{'id': 1}])
        self.assertEqual(export.materialize(published), source)

    def test_distinct_snapshots_and_absent_current_project(self):
        for change in ('story', 'excluded', 'type', 'removed'):
            source = fixture()
            good = next(iter(source['queue'].values()))['last_good']
            if change == 'story': good['project']['stories'].append({'id': 3})
            elif change == 'excluded': good['project']['excluded_candidates'] = []
            elif change == 'type': good['project']['monthly_counts'] = [True]
            else: source['projects'] = []
            published = export.publish(source)
            self.assertEqual(next(iter(published['queue'].values()))['last_good'], good)
            self.assertEqual(export.materialize(published), source)

    def test_legacy_and_missing_results(self):
        for version in (1, 2):
            for queue in ({}, {'new': {'last_good': None}}, {'new': {'status': 'pending'}}):
                source = {'schema_version': version, 'projects': [], 'queue': queue}
                self.assertEqual(export.materialize(source), source)
                self.assertEqual(export.materialize(export.publish(source)), source)
        source = {'schema_version': 1, 'projects': []}
        self.assertEqual(export.materialize(export.publish(source)), source)

    def test_malformed_references(self):
        for ref in (-1, 1, True, '0', None, {}, []):
            document = export.publish(fixture())
            next(iter(document['queue'].values()))['last_good']['project_ref'] = ref
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                export.materialize(document)
        for change in ('both', 'missing', 'identity', 'duplicate', 'version', 'source', 'legacy-ref'):
            document = export.publish(fixture())
            good = next(iter(document['queue'].values()))['last_good']
            if change == 'both': good['project'] = {}
            elif change == 'missing': del good['project_ref']
            elif change == 'identity': document['projects'][0]['readme_url'] += '-other'
            elif change == 'duplicate': document['projects'].append(deepcopy(document['projects'][0]))
            elif change == 'version': document['schema_version'] = 99
            elif change == 'source': document['source_schema_version'] = True
            else:
                document['schema_version'] = 2
                del document['source_schema_version']
            with self.subTest(change=change), self.assertRaises(ValueError):
                export.materialize(document)


if __name__ == '__main__':
    unittest.main()
