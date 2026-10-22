"""Offline mixed-cache regressions across catalog and both downloadable views."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_catalog
import build_site
import build_observatory as obs
from site_test_fixtures import baseline_site
from test_observatory import fixture


class MetricsFreshnessTests(unittest.TestCase):
    def test_catalog_preserves_unavailable_and_stale_provenance(self):
        attempt = dict(at='2026-10-14T01:00:00Z', status='unavailable', http_status=404, reason='repository_unavailable')
        for status, stars, observed in [('stale', 0, '2026-10-07'), ('unavailable', None, None)]:
            record = dict(created_at=None, pushed_at=None, license=None, archived=None,
                          stargazers_count=stars, status=status, last_success_at=observed, last_attempt=attempt)
            snapshot = dict(as_of='2026-10-14', repositories={'example/open': record})
            metadata = build_catalog._github_metadata('https://github.com/example/open', snapshot)
            self.assertEqual(metadata['stars'], stars)
            self.assertEqual(metadata['status'], status)
            self.assertEqual(metadata['last_success_at'], observed)
            self.assertEqual(metadata['last_attempt'], attempt)

    def test_observatory_unknown_total_differs_from_observed_zero(self):
        catalog = fixture()
        catalog['projects'] = catalog['projects'][:1]
        github = catalog['projects'][0]['github']
        github.update(status='unavailable', stars=None, created_at=None, last_success_at=None)
        index = obs.project_index(catalog)
        self.assertIsNone(obs.aggregate(index)['stars'])
        self.assertEqual(obs.aggregate(index)['mapped'], 0)
        html = obs.render(index, obs.aggregate(index), obs.coverage(catalog, {}))
        self.assertIn('data-metric="stars">Unknown</span>', html)
        github.update(status='stale', stars=0, last_success_at='2026-10-07')
        index = obs.project_index(catalog)
        self.assertEqual(obs.aggregate(index)['stars'], 0)
        self.assertIn('metrics_last_success_at', obs.csv_text(index))
        self.assertIn('2026-10-07', obs.csv_text(index))

    def test_comparison_plates_date_cached_metrics(self):
        catalog = fixture()
        for p in catalog['projects']:
            p['name'] = 'Open'
        catalog['projects'][0]['github'].update(status='stale', last_success_at='2026-10-07')
        index = obs.project_index(catalog)
        html = obs.render(index, obs.aggregate(index), obs.coverage(catalog, {}))
        self.assertIn('<dt>Metrics cache</dt><dd>stale · observed 2026-10-07 UTC</dd>', html)
        self.assertIn('<dt>GitHub stars</dt><dd>0</dd>', html)

    def test_mixed_cache_normal_standalone_and_observatory_outputs(self):
        # Use real catalog shape/assets while replacing only repository measurements.
        with tempfile.TemporaryDirectory() as temp:
            _, original = baseline_site()
            catalog = deepcopy(original)
            projects = [p for p in catalog['projects'] if p['github']][:3]
            stale, unavailable, fresh = projects
            attempt = dict(at='2026-10-14T01:00:00Z', status='unavailable', http_status=404, reason='repository_unavailable')
            stale['github'].update(status='stale', stars=0, last_success_at='2026-10-07', last_attempt=attempt)
            unavailable['github'].update(status='unavailable', stars=None, license=None, created_at=None,
                                         pushed_at=None, archived=None, last_success_at=None, last_attempt=attempt)
            fresh['github'].update(status='fresh', last_success_at='2026-10-14T01:00:00Z')
            output = Path(temp) / 'mixed'
            with patch.object(build_site, 'build_catalog', return_value=catalog):
                build_site.build(output)
            records = ''.join(path.read_text() for path in (output / 'records').glob('*.html'))
            for text in (records, (output / 'standalone.html').read_text()):
                self.assertIn('Stale GitHub metrics; last successful observation: 2026-10-07 UTC', text)
                self.assertIn('GitHub metrics unavailable; no successful observation.', text)
                self.assertNotIn('GitHub metrics observed:', text)
                self.assertIn('<dt>GitHub stars</dt><dd>Unknown</dd>', text)
                self.assertIn('<dt>GitHub stars</dt><dd>0</dd>', text)
            for name in ('index.html', 'report.html'):
                text = (output / 'observatory' / name).read_text()
                self.assertIn('Last success: 2026-10-07', text)
                self.assertIn('unavailable<br>Last success: Unknown', text)
                self.assertIn('Cached measurements may be stale', text)
                self.assertIn('Top 10 specimen by GitHub stars.', text)
                self.assertNotIn('Observed counts may include dated stale cache.', text)
                self.assertIn('unavailable · HTTP 404 · repository_unavailable', text)
            index = obs.project_index(catalog)
            row = next(p for p in index['projects'] if p['id'] == stale['id'])
            self.assertEqual(row['metrics_attempt_http_status'], 404)
            self.assertEqual(row['metrics_attempt_reason'], 'repository_unavailable')
            self.assertIn('repository_unavailable', obs.csv_text(index))
