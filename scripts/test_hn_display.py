"""Display policy is independent of immutable HN collection qualification."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import chart_observations
import render_readme
import update_hn as hn

ROOT = Path(__file__).resolve().parents[1]


def project(name, counts, eligible=False):
    return dict(name=name, slug=name.lower(), readme_url='https://example.org/' + name,
                story_count=sum(counts), monthly_counts=counts, eligible=eligible,
                search_url='https://hn.algolia.com/?q=' + name + '&type=story')


class DisplayTests(unittest.TestCase):
    def test_any_positive_count_displays_independent_of_historical_flag(self):
        for count in (0, 1, 5, 6, 20):
            for eligible in (False, True):
                with self.subTest(count=count, eligible=eligible):
                    self.assertEqual(hn.chart_displayable(dict(story_count=count, eligible=eligible)), count > 0)
        for count in (None, True, -1, '1', 1.0):
            with self.subTest(invalid=count), self.assertRaises(ValueError):
                hn.chart_displayable(dict(story_count=count))

    def test_shared_scale_includes_large_single_month_and_preserves_source(self):
        evidence = dict(projects=[project('Sparse', [40] + [0] * 23),
                                  project('Old', [2, 2, 2] + [0] * 21, True)],
                        shared_monthly_maximum=2, eligibility=dict(minimum_stories=6, minimum_active_months=3))
        before = deepcopy(evidence)
        display = hn.display_evidence(evidence)
        self.assertEqual(display['shared_monthly_maximum'], 40)
        self.assertEqual(display['eligibility'], evidence['eligibility'])
        self.assertFalse(display['projects'][0]['eligible'])
        bars = ET.fromstring(hn.svg(display['projects'][0], dict(display, months=['2024-10'] * 24)))
        self.assertEqual(bars.findall('{http://www.w3.org/2000/svg}rect')[0].attrib['height'], '20.000')
        self.assertEqual(evidence, before)

    def test_missing_invalid_or_inconsistent_counts_fail(self):
        for counts in (None, [1], [True] + [0] * 23, [-1] + [0] * 23, [0] * 24):
            p = dict(story_count=1, monthly_counts=counts)
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                hn.display_evidence(dict(projects=[p]))

    def test_zero_only_has_no_charts_and_safe_scale(self):
        evidence = dict(projects=[project('Zero', [0] * 24)], shared_monthly_maximum=0)
        self.assertEqual(hn.display_evidence(evidence)['shared_monthly_maximum'], 1)
        with tempfile.TemporaryDirectory() as folder:
            hn.render(evidence, Path(folder))
            self.assertEqual(list(Path(folder).glob('*.svg')), [])
        self.assertEqual(hn.display_evidence(dict(projects=[]))['shared_monthly_maximum'], 1)

    def test_single_and_multiple_story_charts_keep_search_links(self):
        projects = [project('Single', [1] + [0] * 23), project('Several', [3] + [0] * 23),
                    project('Zero', [0] * 24)]
        evidence = dict(projects=projects, months=hn.window()[2], shared_monthly_maximum=1)
        source = '\n'.join('| [{name}]({readme_url}) | Description. |'.format(**p) for p in projects)
        rendered = hn.decorate_readme(source, evidence)
        self.assertEqual(rendered.count('HN:START'), 2)
        for p in projects[:2]:
            self.assertIn('](' + p['search_url'] + ')', rendered)
        self.assertNotIn('news.ycombinator.com/item', rendered)
        with tempfile.TemporaryDirectory() as folder:
            hn.render(evidence, Path(folder))
            self.assertEqual({p.name for p in Path(folder).glob('*.svg')}, {'single.svg', 'several.svg'})
            self.assertIn('0–3 stories/month', (Path(folder) / 'single.svg').read_text())

    def test_current_cache_queue_and_archive_remain_valid_and_unchanged(self):
        evidence = json.loads((ROOT / 'data/hn_evidence.json').read_text())
        archive = json.loads((ROOT / 'data/chart_observations.json').read_text())
        before = deepcopy((evidence, archive))
        hn.validate_queue(evidence)
        chart_observations.validate(archive)
        display = render_readme.display_hn_evidence((ROOT / 'README.source.md').read_text(), evidence)
        self.assertEqual(display['queue'], evidence['queue'])
        self.assertEqual(sum(hn.chart_displayable(p) for p in display['projects']),
                         sum(p['story_count'] > 0 for p in evidence['projects']))
        self.assertEqual((evidence, archive), before)
        hn.validate_queue(evidence)
        chart_observations.validate(archive)
