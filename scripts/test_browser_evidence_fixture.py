"""Fixed evidence passes through the production renderers without reading caches."""
from pathlib import Path
import unittest
from unittest.mock import patch
import browser_evidence_fixture as fixture


class BrowserEvidenceTests(unittest.TestCase):
    def test_complete_evidence_and_real_chart_assets(self):
        read_text = Path.read_text
        def read(path, *args, **kwargs):
            self.assertNotIn('data', path.parts, 'Fixture must not read mutable evidence caches')
            return read_text(path, *args, **kwargs)
        with patch('urllib.request.urlopen', side_effect=AssertionError('offline')), patch.object(Path, 'read_text', read):
            result = fixture.fixture()
        project = next(p for p in result['data']['projects'] if p['name'] == 'OpenTofu')
        self.assertTrue(project['function_summary'] and project['deployment'] and project['artwork'])
        for chart in (project['hn'], project['star_history']):
            self.assertIn('<svg', result['responses'][chart['chart_url']])
        self.assertEqual(result, fixture.fixture())

    def test_missing_and_partial_evidence_keeps_honest_states(self):
        for state in ('empty', 'partial', 'unavailable', 'rollover'):
            with self.subTest(state=state):
                result = fixture.fixture(state)
                project = next(p for p in result['data']['projects'] if p['name'] == 'OpenTofu')
                self.assertEqual(bool(project['hn']), state == 'partial')
                self.assertFalse((project.get('star_history') or {}).get('chart_url'))
                self.assertFalse(any(path.startswith('assets/stars/') for path in result['responses']))
                record = result['responses']['records/'+project['id']+'.html']
                expected = 'Not recorded' if state == 'empty' else 'withheld until aligned' if state == 'rollover' else 'no zero values inferred'
                self.assertIn(expected, record)
