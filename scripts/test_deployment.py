"""Offline contract and rendering tests for optional reviewed setup evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_catalog import canonical_url
from build_site import build
import deployment
from site_test_fixtures import baseline_site

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://example.org/OpenPilot'
PID = hashlib.sha256(URL.encode()).hexdigest()


def fixture():
    return {'schema_version': 1, 'projects': {PID: {
        'project_url': URL, 'review_status': 'approved', 'checked_at': '2026-10-13',
        'reviewed_by': 'Test reviewer', 'review_note': 'Source review, not installation testing.',
        'sources': {'install': {'url': 'https://example.org/install', 'title': 'Official setup', 'kind': 'upstream_docs'}},
        'run_modes': [{'value': v, 'scope': 'Documented setup', 'source_ids': ['install']} for v in ('desktop', 'cli')],
        'install_methods': [{'value': 'binary', 'scope': 'Release archive', 'source_ids': ['install']}],
        'requirements': [{'kind': 'recommended', 'note': 'Example only', 'scope': 'Single user', 'source_ids': ['install']}],
    }}}


class DeploymentTests(unittest.TestCase):
    def attach(self, doc):
        projects = {URL: {'id': PID, 'url': URL}}
        deployment.attach(projects, doc, canonical_url)
        return projects[URL]

    def test_non_github_identity_optional_input_and_review_gating(self):
        self.assertNotIn('deployment', self.attach(None))
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(deployment.load_optional(Path(folder) / 'absent.json'))
        for status in ('pending', 'rejected'):
            doc = fixture(); doc['projects'][PID]['review_status'] = status
            self.assertNotIn('deployment', self.attach(doc))
        doc = fixture(); project = self.attach(doc)
        self.assertEqual(len(project['deployment']['run_modes']), 2)
        project['deployment']['run_modes'][0]['scope'] = 'Changed'
        self.assertEqual(doc['projects'][PID]['run_modes'][0]['scope'], 'Documented setup')

    def test_malformed_evidence_fails_before_display(self):
        changes = [
            lambda e: e.update(project_url='https://example.org/other'),
            lambda e: e.update(checked_at='2026-02-30'),
            lambda e: e.update(review_status='fresh'),
            lambda e: e.update(review_status=[]),
            lambda e: e.update(supported=True),
            lambda e: e.update(run_modes=[]),
            lambda e: e['run_modes'][0].update(value='online-only'),
            lambda e: e['run_modes'].append(deepcopy(e['run_modes'][0])),
            lambda e: e['run_modes'][0].update(source_ids=['missing']),
            lambda e: e['run_modes'][0].update(scope='bad\x00text'),
            lambda e: e['sources']['install'].update(url='javascript:alert(1)'),
            lambda e: e['sources']['install'].update(revision='short'),
            lambda e: e['sources']['install'].update(revision=1111111111111111111111111111111111111111),
            lambda e: e['requirements'][0].update(kind='benchmark'),
        ]
        for change in changes:
            with self.subTest(change=change):
                doc = fixture(); change(doc['projects'][PID])
                with self.assertRaises(ValueError): self.attach(doc)
        doc = fixture(); doc['projects']['not-full-id'] = doc['projects'].pop(PID)
        with self.assertRaises(ValueError): self.attach(doc)

    def test_package_scope_channel_relationship_and_service_qualification(self):
        doc = fixture(); entry = doc['projects'][PID]
        entry['packages'] = [{'ecosystem': 'Example registry', 'coordinate': 'org/pkg', 'channel': 'stable',
                              'status': 'documented', 'upstream_relationship': 'community',
                              'scope': 'Community package, no live availability claim', 'source_ids': ['install']}]
        entry['external_services'] = [{'name': 'Model API', 'requirement': 'configuration-dependent',
                                      'scope': 'Only API configurations', 'source_ids': ['install']}]
        self.assertIn('community', deployment.render(self.attach(doc)))
        for key, value in (('coordinate', ''), ('channel', ''), ('status', True), ('upstream_relationship', 'official-ish')):
            changed = deepcopy(doc); changed['projects'][PID]['packages'][0][key] = value
            with self.assertRaises(ValueError): self.attach(changed)
        entry['packages'].append(deepcopy(entry['packages'][0]))
        with self.assertRaises(ValueError): self.attach(doc)

    def test_plain_text_escaping(self):
        doc = fixture(); doc['projects'][PID]['run_modes'][0]['scope'] = '<script>alert("x")</script>'
        rendered = deployment.render(self.attach(doc))
        self.assertIn('Test reviewer · Approved evidence record</p><p><strong>Run:</strong>', rendered)
        self.assertEqual(rendered.count('Approved evidence record'), 1)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertEqual(deployment.render({'id': PID}), '')

    def test_full_site_without_optional_evidence_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'source'; root.mkdir()
            (root / 'data').mkdir()
            (root / 'README.source.md').symlink_to(ROOT / 'README.source.md')
            (root / 'site').symlink_to(ROOT / 'site', target_is_directory=True)
            for path in (ROOT / 'data').iterdir():
                if path.name != 'deployment_evidence.json' and path.is_file():
                    (root / 'data' / path.name).symlink_to(path)
            with patch('socket.create_connection', side_effect=AssertionError('Offline build attempted network')):
                catalog = build(Path(folder) / 'output', root=root)
            self.assertTrue(catalog['projects'])
            self.assertFalse(any('deployment' in p for p in catalog['projects']))
            self.assertNotIn('class="deployment-evidence"', (Path(folder) / 'output/index.html').read_text())

    def test_pilot_offline_build_and_unchanged_core_metadata(self):
        document = deployment.load_optional(ROOT / 'data/deployment_evidence.json')
        self.assertEqual(len(document['projects']), 8)
        with patch('socket.create_connection', side_effect=AssertionError('Offline build attempted network')):
            output, catalog = baseline_site()
            if catalog is None: catalog = json.loads((output / 'catalog.json').read_text())
            reviewed = [p for p in catalog['projects'] if p.get('deployment')]
            self.assertEqual(len(reviewed), 8)
            expected_function_urls = {'https://github.com/opentofu/opentofu', 'https://github.com/openrefine/openrefine', 'https://github.com/openscad/openscad'}
            self.assertTrue(expected_function_urls <= {p['url'] for p in reviewed if p.get('function_summary')})
            self.assertTrue(all(p['deployment']['review_status'] == 'approved' for p in reviewed))
            from build_catalog import build_catalog
            base = build_catalog((ROOT / 'README.source.md').read_text(),
                                 json.loads((ROOT / 'data/github_metrics.json').read_text()),
                                 json.loads((ROOT / 'data/alternatives.json').read_text()),
                                 json.loads((ROOT / 'data/hn_evidence.json').read_text()))
            by_id = {p['id']: p for p in base['projects']}
            for project in catalog['projects']:
                for key in ('name', 'url', 'description', 'categories', 'github', 'alternatives', 'hn'):
                    self.assertEqual(project[key], by_id[project['id']][key])
            page = (output / 'index.html').read_text()
            self.assertEqual(page.count('class="deployment-evidence"'), 0)
            records = ''.join(record.read_text() for record in (output / 'records').glob('*.html'))
            # Setup facts live in the plate's Where it runs box and its popup.
            self.assertEqual(records.count('<dl class="pg-kit">'), 8)
            self.assertEqual(records.count('class="deployment-evidence"'), 0)
            self.assertIn('id="run-mode-filter"', page)
            self.assertIn('id="install-method-filter"', page)
            self.assertIn('<summary aria-label="Details: Where it runs">i</summary>', records)
            self.assertIn('<h5>Install methods</h5>', records)


if __name__ == '__main__': unittest.main()
