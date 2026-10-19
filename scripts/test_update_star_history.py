import io
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request
from unittest.mock import patch

import update_star_history as stars


NOW = datetime(2026, 10, 13, 2, tzinfo=timezone.utc)
SHA = 'a' * 40
PROJECT = {'name': 'Example', 'repo': 'org/example', 'readme_url': 'https://github.com/org/example'}
OPENREMOTE = {'name': 'OpenRemote', 'repo': 'openremote/openremote',
              'readme_url': 'https://github.com/openremote/openremote'}

OPENOMSI = {'name': 'openOMSI', 'repo': 'openomsi-project/openomsi',
            'readme_url': 'https://github.com/openomsi-project/openomsi'}

OPENBRENDER = {'name': 'OpenBRender', 'repo': 'gptchatly/openbrender',
               'readme_url': 'https://github.com/gptchatly/openbrender'}
OPENNEX = {'name': 'OpenNex', 'repo': 'sophontrace/opennex',
           'readme_url': 'https://github.com/sophontrace/opennex'}

def weekly_series(count=108, offset=0):
    newest = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp()) + offset
    return [{'week': newest - i * stars.WEEK, 'total': 7, 'days': [1] * 7} for i in range(count)]


def pager(rows, calls=None):
    def get(url):
        if calls is not None:
            calls.append(url)
        query = parse_qs(urlsplit(url).query)
        page = int(query['page'][0])
        return deepcopy(rows[(page - 1) * 30:page * 30])
    return get


class Response(io.BytesIO):
    def __init__(self, payload, remaining=100):
        super().__init__(json.dumps(payload).encode())
        self.headers = {'X-RateLimit-Remaining': str(remaining)}


class CollectorTests(unittest.TestCase):
    def collect(self, **kwargs):
        return stars.collect_repository('org/example', NOW, source_sha=SHA, **kwargs)

    def refresh(self, **kwargs):
        return stars.refresh([PROJECT], now=NOW, source_sha=SHA, **kwargs)

    def test_four_pages_cover_24_complete_months(self):
        calls, budget = [], stars.RequestBudget()
        good = self.collect(getter=pager(weekly_series(), calls), budget=budget)
        self.assertEqual(len(calls), 4)
        self.assertEqual(budget.used, 4)
        self.assertEqual(good['months'][0], '2024-10')
        self.assertEqual(good['months'][-1], '2026-09')
        self.assertEqual(len(good['monthly_counts']), 24)
        self.assertEqual(good['monthly_counts'][0], 31)
        self.assertEqual(good['monthly_counts'][-1], 30)
        self.assertEqual(sum(good['monthly_counts']), 730)
        self.assertEqual(good['source_sha'], SHA)
        self.assertTrue(all('/stargazers/history?' in url for url in calls))
        self.assertNotIn('login', json.dumps(good))

    def test_reviewed_rename_only_changes_history_endpoint(self):
        calls = []
        cache = stars.refresh([OPENREMOTE], now=NOW, source_sha=SHA,
                              getter=pager(weekly_series(), calls))
        record = cache['repositories'][OPENREMOTE['repo']]
        for key, value in OPENREMOTE.items():
            self.assertEqual(record[key], value)
        expected = stars.API + 'openremote/core/stargazers/history'
        self.assertEqual(record['source_url'], expected)
        self.assertEqual(record['last_good']['source_urls'], calls)
        self.assertEqual(calls, [expected + f'?per_page=30&page={page}' for page in range(1, 5)])
        self.assertEqual(stars.history_source_url('unknown/renamed'), stars.API + 'unknown/renamed/stargazers/history')
        self.assertEqual(stars.history_source_url('openremote/core'), expected)
        source = '| [OpenRemote](https://github.com/openremote/openremote) | IoT platform. |\n'
        self.assertEqual(stars.load_projects({'schema_version': 2, 'scope': 'catalog_github'}, source), [OPENREMOTE])

    def test_rename_retains_old_evidence_urls_and_archive_observations(self):
        import chart_observations as observations
        with patch.dict(stars.REVIEWED_REPOSITORY_RENAMES, {}, clear=True):
            original = stars.refresh([OPENREMOTE], now=NOW, source_sha=SHA, getter=pager(weekly_series()))
        before = deepcopy(original)
        archive = observations.add_stars(observations.empty(), original)
        prior_observations = deepcopy(archive['observations'])
        def unavailable(url):
            raise stars.HistoryError('GitHub history HTTP 503', 'unavailable')
        failed = stars.refresh([OPENREMOTE], existing=original, now=NOW + timedelta(days=1),
                               source_sha=SHA, getter=unavailable, force=True)
        old = original['repositories'][OPENREMOTE['repo']]
        retained = failed['repositories'][OPENREMOTE['repo']]
        self.assertEqual(retained['last_good'], old['last_good'])
        self.assertEqual(retained['source_url'], old['source_url'])
        observations.add_stars(archive, failed)
        self.assertEqual(archive['observations'], prior_observations)
        current = stars.refresh([OPENREMOTE], existing=failed, now=NOW + timedelta(days=2),
                                source_sha=SHA, getter=pager(weekly_series()), force=True)
        observations.add_stars(archive, current)
        observations.validate(archive)
        self.assertEqual(len(archive['observations']), 2)
        for key, value in prior_observations.items():
            self.assertEqual(archive['observations'][key], value)
        self.assertEqual(original, before)

    def test_rename_cannot_remap_other_repos_or_mix_pagination_identities(self):
        cache = stars.refresh([OPENREMOTE], now=NOW, getter=pager(weekly_series()))
        for mutation in ['unreviewed', 'mixed_pages', 'mismatched_source', 'reverse']:
            bad = deepcopy(cache)
            record = bad['repositories'][OPENREMOTE['repo']]
            if mutation == 'unreviewed':
                record['source_url'] = stars.API + 'openremote/other/stargazers/history'
            elif mutation == 'mixed_pages':
                record['last_good']['source_urls'][1] = record['last_good']['source_urls'][1].replace('/core/', '/openremote/')
            elif mutation == 'mismatched_source':
                record['source_url'] = stars.API + 'openremote/openremote/stargazers/history'
            else:
                bad['repositories'] = {'openremote/core': record}
                record.update(repo='openremote/core', readme_url='https://github.com/openremote/core',
                              source_url=stars.API + 'openremote/openremote/stargazers/history')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                stars.validate_cache(bad)

    def test_openomsi_reviewed_rename_only_changes_history_endpoint(self):
        calls = []
        cache = stars.refresh([OPENOMSI], now=NOW, source_sha=SHA,
                              getter=pager(weekly_series(), calls))
        record = cache['repositories'][OPENOMSI['repo']]
        for key, value in OPENOMSI.items():
            self.assertEqual(record[key], value)
        expected = stars.API + 'openomsi-org/openomsi/stargazers/history'
        self.assertEqual(record['source_url'], expected)
        self.assertEqual(record['last_good']['source_urls'], calls)
        self.assertEqual(calls, [expected + f'?per_page=30&page={page}' for page in range(1, 5)])
        self.assertEqual(stars.history_source_url('unknown/renamed'), stars.API + 'unknown/renamed/stargazers/history')
        self.assertEqual(stars.history_source_url('openomsi-org/openomsi'), expected)
        source = '| [openOMSI](https://github.com/openomsi-project/openomsi) | Bus simulator. |\n'
        self.assertEqual(stars.load_projects({'schema_version': 2, 'scope': 'catalog_github'}, source), [OPENOMSI])

    def test_openomsi_rename_retains_old_evidence_urls_and_archive_observations(self):
        import chart_observations as observations
        with patch.dict(stars.REVIEWED_REPOSITORY_RENAMES, {}, clear=True):
            original = stars.refresh([OPENOMSI], now=NOW, source_sha=SHA, getter=pager(weekly_series()))
        before = deepcopy(original)
        archive = observations.add_stars(observations.empty(), original)
        prior_observations = deepcopy(archive['observations'])
        def unavailable(url):
            raise stars.HistoryError('GitHub history HTTP 503', 'unavailable')
        failed = stars.refresh([OPENOMSI], existing=original, now=NOW + timedelta(days=1),
                               source_sha=SHA, getter=unavailable, force=True)
        old = original['repositories'][OPENOMSI['repo']]
        retained = failed['repositories'][OPENOMSI['repo']]
        self.assertEqual(retained['last_good'], old['last_good'])
        self.assertEqual(retained['source_url'], old['source_url'])
        observations.add_stars(archive, failed)
        self.assertEqual(archive['observations'], prior_observations)
        current = stars.refresh([OPENOMSI], existing=failed, now=NOW + timedelta(days=2),
                                source_sha=SHA, getter=pager(weekly_series()), force=True)
        observations.add_stars(archive, current)
        observations.validate(archive)
        self.assertEqual(len(archive['observations']), 2)
        for key, value in prior_observations.items():
            self.assertEqual(archive['observations'][key], value)
        self.assertEqual(original, before)

    def test_openomsi_rename_cannot_remap_other_repos_or_mix_pagination_identities(self):
        cache = stars.refresh([OPENOMSI], now=NOW, getter=pager(weekly_series()))
        for mutation in ['unreviewed', 'mixed_pages', 'mismatched_source', 'reverse']:
            bad = deepcopy(cache)
            record = bad['repositories'][OPENOMSI['repo']]
            if mutation == 'unreviewed':
                record['source_url'] = stars.API + 'openomsi-org/other/stargazers/history'
            elif mutation == 'mixed_pages':
                record['last_good']['source_urls'][1] = record['last_good']['source_urls'][1].replace('/openomsi-org/', '/openomsi-project/')
            elif mutation == 'mismatched_source':
                record['source_url'] = stars.API + 'openomsi-project/openomsi/stargazers/history'
            else:
                bad['repositories'] = {'openomsi-org/openomsi': record}
                record.update(repo='openomsi-org/openomsi', readme_url='https://github.com/openomsi-org/openomsi',
                              source_url=stars.API + 'openomsi-project/openomsi/stargazers/history')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                stars.validate_cache(bad)

    def test_openbrender_reviewed_rename_only_changes_history_endpoint(self):
        calls = []
        cache = stars.refresh([OPENBRENDER], now=NOW, source_sha=SHA,
                              getter=pager(weekly_series(), calls))
        record = cache['repositories'][OPENBRENDER['repo']]
        for key, value in OPENBRENDER.items():
            self.assertEqual(record[key], value)
        expected = stars.API + 'gptchatly/drawplotia/stargazers/history'
        self.assertEqual(record['source_url'], expected)
        self.assertEqual(record['last_good']['source_urls'], calls)
        self.assertEqual(calls, [expected + f'?per_page=30&page={page}' for page in range(1, 5)])
        self.assertEqual(stars.history_source_url('unknown/renamed'), stars.API + 'unknown/renamed/stargazers/history')
        self.assertEqual(stars.history_source_url('gptchatly/drawplotia'), expected)
        source = '| [OpenBRender](https://github.com/gptchatly/openbrender) | Scientific figure editor. |\n'
        self.assertEqual(stars.load_projects({'schema_version': 2, 'scope': 'catalog_github'}, source), [OPENBRENDER])

    def test_openbrender_rename_retains_old_evidence_urls_and_archive_observations(self):
        import chart_observations as observations
        with patch.dict(stars.REVIEWED_REPOSITORY_RENAMES, {}, clear=True):
            original = stars.refresh([OPENBRENDER], now=NOW, source_sha=SHA, getter=pager(weekly_series()))
        before = deepcopy(original)
        archive = observations.add_stars(observations.empty(), original)
        prior_observations = deepcopy(archive['observations'])
        def unavailable(url):
            raise stars.HistoryError('GitHub history HTTP 503', 'unavailable')
        failed = stars.refresh([OPENBRENDER], existing=original, now=NOW + timedelta(days=1),
                               source_sha=SHA, getter=unavailable, force=True)
        old = original['repositories'][OPENBRENDER['repo']]
        retained = failed['repositories'][OPENBRENDER['repo']]
        self.assertEqual(retained['last_good'], old['last_good'])
        self.assertEqual(retained['source_url'], old['source_url'])
        observations.add_stars(archive, failed)
        self.assertEqual(archive['observations'], prior_observations)
        current = stars.refresh([OPENBRENDER], existing=failed, now=NOW + timedelta(days=2),
                                source_sha=SHA, getter=pager(weekly_series()), force=True)
        observations.add_stars(archive, current)
        observations.validate(archive)
        self.assertEqual(len(archive['observations']), 2)
        for key, value in prior_observations.items():
            self.assertEqual(archive['observations'][key], value)
        self.assertEqual(original, before)

    def test_openbrender_rename_cannot_remap_other_repos_or_mix_pagination_identities(self):
        cache = stars.refresh([OPENBRENDER], now=NOW, getter=pager(weekly_series()))
        for mutation in ['unreviewed', 'mixed_pages', 'mismatched_source', 'reverse']:
            bad = deepcopy(cache)
            record = bad['repositories'][OPENBRENDER['repo']]
            if mutation == 'unreviewed':
                record['source_url'] = stars.API + 'gptchatly/other/stargazers/history'
            elif mutation == 'mixed_pages':
                record['last_good']['source_urls'][1] = record['last_good']['source_urls'][1].replace('/drawplotia/', '/openbrender/')
            elif mutation == 'mismatched_source':
                record['source_url'] = stars.API + 'gptchatly/openbrender/stargazers/history'
            else:
                bad['repositories'] = {'gptchatly/drawplotia': record}
                record.update(repo='gptchatly/drawplotia', readme_url='https://github.com/gptchatly/drawplotia',
                              source_url=stars.API + 'gptchatly/openbrender/stargazers/history')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                stars.validate_cache(bad)

    def test_opennex_reviewed_rename_only_changes_history_endpoint(self):
        calls = []
        cache = stars.refresh([OPENNEX], now=NOW, source_sha=SHA,
                              getter=pager(weekly_series(), calls))
        record = cache['repositories'][OPENNEX['repo']]
        for key, value in OPENNEX.items():
            self.assertEqual(record[key], value)
        expected = stars.API + 'sophontrace/openlnku/stargazers/history'
        self.assertEqual(record['source_url'], expected)
        self.assertEqual(record['last_good']['source_urls'], calls)
        self.assertEqual(calls, [expected + f'?per_page=30&page={page}' for page in range(1, 5)])
        self.assertEqual(stars.history_source_url('unknown/renamed'), stars.API + 'unknown/renamed/stargazers/history')
        self.assertEqual(stars.history_source_url('sophontrace/openlnku'), expected)
        source = '| [OpenNex](https://github.com/SophonTrace/OpenNex) | Network authentication client. |\n'
        self.assertEqual(stars.load_projects({'schema_version': 2, 'scope': 'catalog_github'}, source), [OPENNEX])

    def test_opennex_rename_retains_old_evidence_urls_and_archive_observations(self):
        import chart_observations as observations
        with patch.dict(stars.REVIEWED_REPOSITORY_RENAMES, {}, clear=True):
            original = stars.refresh([OPENNEX], now=NOW, source_sha=SHA, getter=pager(weekly_series()))
        before = deepcopy(original)
        archive = observations.add_stars(observations.empty(), original)
        prior_observations = deepcopy(archive['observations'])
        def unavailable(url):
            raise stars.HistoryError('GitHub history HTTP 503', 'unavailable')
        failed = stars.refresh([OPENNEX], existing=original, now=NOW + timedelta(days=1),
                               source_sha=SHA, getter=unavailable, force=True)
        old = original['repositories'][OPENNEX['repo']]
        retained = failed['repositories'][OPENNEX['repo']]
        self.assertEqual(retained['last_good'], old['last_good'])
        self.assertEqual(retained['source_url'], old['source_url'])
        observations.add_stars(archive, failed)
        self.assertEqual(archive['observations'], prior_observations)
        current = stars.refresh([OPENNEX], existing=failed, now=NOW + timedelta(days=2),
                                source_sha=SHA, getter=pager(weekly_series()), force=True)
        observations.add_stars(archive, current)
        observations.validate(archive)
        self.assertEqual(len(archive['observations']), 2)
        for key, value in prior_observations.items():
            self.assertEqual(archive['observations'][key], value)
        self.assertEqual(original, before)

    def test_opennex_rename_cannot_remap_other_repos_or_mix_pagination_identities(self):
        cache = stars.refresh([OPENNEX], now=NOW, getter=pager(weekly_series()))
        for mutation in ['unreviewed', 'mixed_pages', 'mismatched_source', 'reverse']:
            bad = deepcopy(cache)
            record = bad['repositories'][OPENNEX['repo']]
            if mutation == 'unreviewed':
                record['source_url'] = stars.API + 'sophontrace/other/stargazers/history'
            elif mutation == 'mixed_pages':
                record['last_good']['source_urls'][1] = record['last_good']['source_urls'][1].replace('/openlnku/', '/opennex/')
            elif mutation == 'mismatched_source':
                record['source_url'] = stars.API + 'sophontrace/opennex/stargazers/history'
            else:
                bad['repositories'] = {'sophontrace/openlnku': record}
                record.update(repo='sophontrace/openlnku', readme_url='https://github.com/sophontrace/openlnku',
                              source_url=stars.API + 'sophontrace/opennex/stargazers/history')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                stars.validate_cache(bad)

    def test_month_assignment_excludes_current_and_older_month(self):
        rows = [
            {'week': int(datetime(2026, 9, 27, tzinfo=timezone.utc).timestamp()), 'total': 28, 'days': [1, 2, 3, 4, 5, 6, 7]},
            {'week': int(datetime(2024, 9, 29, tzinfo=timezone.utc).timestamp()), 'total': 28, 'days': [1, 2, 3, 4, 5, 6, 7]},
        ]
        counts = stars.monthly_counts(rows, stars.window(NOW)[2])
        self.assertEqual(counts[-1], 10)
        self.assertEqual(counts[0], 25)
        self.assertEqual(sum(counts), 35)

    def test_non_utc_source_boundary_preserved_and_disclosed(self):
        good = self.collect(getter=pager(weekly_series(offset=8 * 3600)))
        self.assertEqual(good['weeks'][0]['week'] % stars.DAY, 8 * 3600)
        self.assertIn('may differ from UTC', good['source_boundary_note'])
        self.assertIn('approximate', good['source_boundary_note'])
        rows = weekly_series(3)
        rows[1]['week'] -= 3600
        rows[2]['week'] -= 3600
        self.assertEqual(len(stars.validate_weeks(rows)), 3)

    def test_invalid_week_shape_totals_and_values_rejected(self):
        for mutation in [
            {'total': 8}, {'days': [1] * 6}, {'days': [-1] + [1] * 6, 'total': 5},
            {'days': [True] + [1] * 6}, {'week': True}, {'total': 7.0},
            {'week': int(NOW.timestamp()) + stars.WEEK},
        ]:
            with self.subTest(mutation=mutation):
                row = {**weekly_series(1)[0], **mutation}
                with self.assertRaises(stars.HistoryError):
                    stars.validate_weeks([row], now=NOW)
        for payload in [{}, None, 'bad', [1], weekly_series(31)]:
            with self.subTest(payload=type(payload)):
                with self.assertRaises(stars.HistoryError):
                    stars.validate_weeks(payload)

    def test_duplicate_gap_and_order_rejected_within_and_across_pages(self):
        for index, delta in [(1, stars.WEEK), (1, -stars.WEEK), (30, stars.WEEK), (30, -stars.WEEK)]:
            rows = weekly_series()
            rows[index]['week'] += delta
            with self.subTest(index=index, delta=delta):
                with self.assertRaises(stars.HistoryError):
                    self.collect(getter=pager(rows))
        rows = weekly_series()
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(stars.HistoryError):
            self.collect(getter=pager(rows))

    def test_known_creation_week_allows_prior_month_zeros(self):
        good = self.collect(getter=pager(weekly_series(10)), created_at='2026-08-10T12:00:00Z')
        self.assertTrue(good['coverage']['creation_week_reached'])
        self.assertEqual(good['monthly_counts'][:-2], [0] * 22)
        self.assertGreater(good['monthly_counts'][-2], 0)
        self.assertEqual(good['coverage']['terminal_page'], 1)

    def test_terminal_without_metadata_does_not_invent_creation_boundary(self):
        with self.assertRaises(stars.HistoryError):
            self.collect(getter=pager(weekly_series(10)))

    def test_truncated_terminal_contradicting_metadata_is_partial(self):
        with self.assertRaisesRegex(stars.HistoryError, 'before the known'):
            self.collect(getter=pager(weekly_series(10)), created_at='2020-01-01T00:00:00Z')

    def test_empty_first_page_never_invents_old_repository_zeros(self):
        for created in [None, '2020-01-01T00:00:00Z', '2026-09-01T00:00:00Z']:
            with self.subTest(created=created):
                with self.assertRaisesRegex(stars.HistoryError, 'Empty history'):
                    self.collect(getter=lambda _: [], created_at=created)
        good = self.collect(getter=lambda _: [], created_at='2026-10-04T00:00:00Z')
        self.assertEqual(good['monthly_counts'], [0] * 24)
        self.assertTrue(good['coverage']['creation_week_reached'])

    def test_empty_terminal_after_full_page_requires_creation_boundary(self):
        good = self.collect(getter=pager(weekly_series(30)), created_at='2026-03-23T01:00:00Z')
        self.assertEqual(good['coverage']['terminal_page'], 2)
        with self.assertRaises(stars.HistoryError):
            self.collect(getter=pager(weekly_series(30)), created_at='2020-01-01T00:00:00Z')

    def test_stale_recent_edge_is_not_zero_padded(self):
        rows = weekly_series()[5:]
        with self.assertRaisesRegex(stars.HistoryError, 'end of the requested window'):
            self.collect(getter=pager(rows))

    def test_exhausted_budget_discards_partial_window(self):
        budget = stars.RequestBudget(2)
        with self.assertRaises(stars.BudgetExhausted):
            self.collect(getter=pager(weekly_series()), budget=budget)
        self.assertEqual(budget.used, 2)

    def test_repository_url_validation_rejects_non_github_and_mismatch(self):
        for url in ['https://example.com/org/example', 'https://github.com.evil/org/example',
                    'https://github.com/org/other', 'https://github.com/org/example/issues',
                    'https://user@github.com/org/example', 'https://github.com/org/example?x=1',
                    'https://github.com//org/example', 'https://github.com/org/example//']:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    stars.validate_projects({'schema_version': 1, 'projects': [{**PROJECT, 'readme_url': url}]})
        valid = stars.validate_projects({'schema_version': 1, 'projects': [{**PROJECT, 'repo': 'ORG/Example', 'readme_url': 'https://github.com/ORG/Example/'}]})
        self.assertEqual(valid[0]['repo'], 'org/example')
        with self.assertRaises(ValueError):
            stars.validate_projects({'schema_version': 1, 'projects': [PROJECT, PROJECT]})

    def test_failure_retains_last_good_and_explicit_status(self):
        cache = self.refresh(getter=pager(weekly_series()))
        old_good = deepcopy(cache['repositories']['org/example']['last_good'])
        def unavailable(url):
            raise stars.HistoryError('GitHub history HTTP 503', 'unavailable')
        failed = self.refresh(existing=cache, getter=unavailable, force=True)
        record = failed['repositories']['org/example']
        self.assertEqual(record['status'], 'unavailable')
        self.assertEqual(record['last_good'], old_good)
        self.assertEqual(cache['repositories']['org/example']['status'], 'ok')
        self.assertNotIn('error', cache['repositories']['org/example'])

    def test_first_partial_has_no_last_good_or_fabricated_chart_counts(self):
        cache = self.refresh(getter=pager(weekly_series()), request_budget=1)
        record = cache['repositories']['org/example']
        self.assertEqual(record['status'], 'deferred')
        self.assertNotIn('last_good', record)
        self.assertNotIn('monthly_counts', record)

    def test_budget_persists_same_day_and_resets_next_day(self):
        cache = self.refresh(getter=pager(weekly_series()), request_budget=4)
        calls = []
        unchanged = self.refresh(existing=cache, getter=pager(weekly_series(), calls), force=True, request_budget=4)
        self.assertEqual(calls, [])
        self.assertEqual(unchanged['budget']['requests_used'], 4)
        tomorrow = stars.refresh([PROJECT], existing=cache, now=NOW + timedelta(days=1), getter=pager(weekly_series(), calls), force=True, request_budget=4)
        self.assertEqual(len(calls), 4)
        self.assertEqual(tomorrow['budget']['requests_used'], 4)

    def test_refresh_interval_and_month_rollover(self):
        cache = self.refresh(getter=pager(weekly_series()))
        record = cache['repositories']['org/example']
        self.assertFalse(stars.needs_refresh(record, NOW + timedelta(days=13), stars.window(NOW)[2]))
        self.assertTrue(stars.needs_refresh(record, NOW + timedelta(days=14), stars.window(NOW)[2]))
        october_end = datetime(2026, 10, 31, tzinfo=timezone.utc)
        record['last_good']['fetched_at'] = october_end.isoformat()
        november = october_end + timedelta(days=1)
        self.assertTrue(stars.needs_refresh(record, november, stars.window(november)[2]))
        record['status'] = 'partial'
        self.assertFalse(stars.needs_refresh(record, NOW, stars.window(NOW)[2]))

    def test_oldest_attempt_rotation_and_repository_limit(self):
        projects = [{**PROJECT, 'repo': 'org/' + name, 'readme_url': 'https://github.com/org/' + name} for name in ['a', 'b', 'c']]
        cache = stars.refresh(projects, now=NOW, getter=pager(weekly_series()), max_repositories=1)
        self.assertEqual(set(cache['repositories']), {'org/a'})
        cache = stars.refresh(projects, existing=cache, now=NOW, getter=pager(weekly_series()), max_repositories=1)
        self.assertEqual(set(cache['repositories']), {'org/a', 'org/b'})

    def test_cache_month_count_identity_and_partial_coverage_validation(self):
        cache = self.refresh(getter=pager(weekly_series()))
        for mutation in ['months', 'counts', 'identity', 'coverage', 'source_urls', 'end']:
            bad = deepcopy(cache)
            record = bad['repositories']['org/example']
            good = record['last_good']
            if mutation == 'months':
                good['months'][-1] = '2026-10'
            elif mutation == 'counts':
                good['monthly_counts'][0] += 1
            elif mutation == 'identity':
                record['readme_url'] = 'https://github.com/org/other'
            elif mutation == 'coverage':
                good['weeks'] = good['weeks'][:30]
                good['monthly_counts'] = stars.monthly_counts(good['weeks'], good['months'])
                good['coverage']['oldest_week'] = good['weeks'][-1]['week']
            elif mutation == 'end':
                good['window_end_exclusive'] = '2026-10-02T00:00:00+00:00'
            else:
                good['source_urls'][0] = 'https://github.com/org/other'
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    stars.validate_cache(bad)

    def test_atomic_cache_write_and_read_roundtrip(self):
        cache = self.refresh(getter=pager(weekly_series()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.json'
            stars.write_cache(path, cache)
            self.assertEqual(stars.validate_cache(json.loads(path.read_text())), cache)
            before = path.read_bytes()
            bad = deepcopy(cache)
            bad['schema_version'] = 2
            with self.assertRaises(ValueError):
                stars.write_cache(path, bad)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_catalog_eligibility_deduplicates_and_preserves_unknowns(self):
        config = json.loads(stars.PROJECTS_PATH.read_text())
        source = (stars.ROOT / 'README.source.md').read_text()
        projects = stars.load_projects(config, source)
        from render_readme import validate_source
        self.assertEqual({p['repo'] for p in projects}, set(validate_source(source)))
        self.assertEqual(len(projects), len({p['repo'] for p in projects}))
        fixture = "| [Open A](https://github.com/ORG/A/) | Tool. |\n" * 2
        fixture += "| [Open B](https://elsewhere.example/org/b) | Tool. |\n"
        self.assertEqual(stars.load_projects(config, fixture), [
            {'name': 'Open A', 'repo': 'org/a', 'readme_url': 'https://github.com/org/a'}])
        with self.assertRaises(ValueError):
            stars.load_projects({'schema_version': 2, 'scope': 'anything'}, source)
        with self.assertRaises(ValueError):
            stars.load_projects(config, fixture + "| [Different](https://github.com/org/a) | Tool. |\n")
        self.assertEqual(stars.load_projects({'schema_version': 1, 'projects': [PROJECT]}, ''), [PROJECT])

    def test_popular_unseen_first_then_fair_refresh(self):
        projects = [{**PROJECT, 'repo': 'org/' + name, 'readme_url': 'https://github.com/org/' + name}
                    for name in ['a', 'b', 'c', 'd', 'e']]
        metadata = {'repositories': {'org/a': {'stargazers_count': 0},
                    'org/b': {'stargazers_count': 100}, 'org/c': {'stargazers_count': 100},
                    'org/d': {'stargazers_count': None}}}
        calls = []
        def unavailable(url):
            calls.append(url.split('/repos/')[1].split('/stargazers')[0])
            raise stars.HistoryError('Unavailable', 'unavailable')
        cache = None
        for day in range(6):
            cache = stars.refresh(projects, existing=cache, metadata=metadata,
                now=NOW + timedelta(days=day), getter=unavailable, max_repositories=1)
        self.assertEqual(calls, ['org/b', 'org/c', 'org/a', 'org/d', 'org/e', 'org/b'])
        self.assertEqual(cache['selection_report']['eligible_repositories'], 5)
        self.assertEqual(cache['selection_report']['unattempted_repositories'], 0)
        self.assertEqual(cache['selection_report']['attempted_repositories'], 1)
        self.assertEqual(cache['budget']['limit'], 16)
        self.assertEqual(cache['budget']['requests_used'], 1)

    def test_selection_report_validation_and_offset_order(self):
        cache = self.refresh(getter=pager(weekly_series()))
        for value in [-1, True, '4']:
            bad = deepcopy(cache)
            bad['selection_report']['eligible_repositories'] = value
            with self.assertRaises(ValueError):
                stars.validate_cache(bad)
        bad = deepcopy(cache)
        bad['selection_report']['attempted_repositories'] = 2
        with self.assertRaises(ValueError):
            stars.validate_cache(bad)
        records = {'org/example': {'checked_at': '2026-10-15T01:00:00+02:00'}}
        earlier = stars.priority_key(PROJECT, records, None)
        records['org/example']['checked_at'] = '2026-10-15T00:00:00+00:00'
        self.assertLess(earlier, stars.priority_key(PROJECT, records, None))

    def test_invocation_budget_survives_discarded_worktree_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            budget_file = Path(directory) / 'invocation.json'
            calls = []
            first = self.refresh(getter=pager(weekly_series(), calls), request_budget=4, invocation_budget_file=budget_file)
            self.assertEqual(first['budget']['requests_used'], 4)
            # Simulate a failed publisher push throwing away the first snapshot.
            retried = self.refresh(getter=pager(weekly_series(), calls), request_budget=4, invocation_budget_file=budget_file)
            self.assertEqual(len(calls), 4)
            self.assertEqual(retried['budget']['requests_used'], 4)

    def test_removing_curated_repo_removes_cache_entry(self):
        cache = self.refresh(getter=pager(weekly_series()))
        removed = stars.refresh([], existing=cache, now=NOW)
        self.assertEqual(removed['repositories'], {})

    def test_empty_cached_evidence_requires_proven_creation_after_window(self):
        cache = self.refresh(getter=pager(weekly_series()))
        good = cache['repositories']['org/example']['last_good']
        good['weeks'] = []
        good['monthly_counts'] = [0] * 24
        good['coverage'] = {'oldest_week': None, 'newest_week': None, 'terminal_page': 1,
                            'creation_week_reached': True, 'repository_created_at': '2020-01-01T00:00:00Z'}
        good['source_urls'] = good['source_urls'][:1]
        with self.assertRaises(ValueError):
            stars.validate_cache(cache)
        good['coverage']['repository_created_at'] = '2026-10-02T00:00:00Z'
        stars.validate_cache(cache)


class TransportTests(unittest.TestCase):
    def test_only_aggregate_api_requested_with_supported_version(self):
        seen, budget = [], stars.RequestBudget()
        def opener(request, timeout):
            seen.append(request)
            return Response([])
        stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, opener)
        self.assertEqual(seen[0].get_method(), 'GET')
        self.assertEqual(seen[0].get_header('X-github-api-version'), '2026-03-10')
        self.assertIsNone(seen[0].get_header('Authorization'))
        self.assertEqual(budget.used, 1)

    def test_retry_counted_and_bounded(self):
        calls, budget = [], stars.RequestBudget()
        def opener(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 503, 'Unavailable', {}, None)
            return Response([])
        self.assertEqual(stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, opener, lambda _: None), [])
        self.assertEqual(budget.used, 2)
        budget = stars.RequestBudget(1)
        calls.clear()
        with self.assertRaises(stars.BudgetExhausted):
            stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, opener, lambda _: None)
        self.assertEqual(budget.used, 1)

    def test_redirects_are_rejected_and_transport_cannot_use_legacy_endpoint(self):
        request = Request(stars.API + 'org/example/stargazers/history?per_page=30&page=1')
        self.assertIsNone(stars.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://other.example'))
        with patch.object(stars, 'build_opener') as build:
            build.return_value.open.return_value = Response([])
            stars.request_page(request.full_url, None, stars.RequestBudget())
            build.assert_called_once_with(stars.NoRedirect)
        budget = stars.RequestBudget()
        for url in [stars.API + 'org/example/stargazers', 'https://other.example/stargazers/history']:
            with self.assertRaises(ValueError):
                stars.request_page(url, 'unused', budget)
        self.assertEqual(budget.used, 0)

    def test_rate_errors_halt_without_retry(self):
        for code in [403, 429]:
            calls, budget = [], stars.RequestBudget()
            def opener(request, timeout):
                calls.append(request)
                raise HTTPError(request.full_url, code, 'Limit', {}, None)
            with self.subTest(code=code):
                with self.assertRaises(stars.HistoryError) as raised:
                    stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, opener, lambda _: None)
                self.assertTrue(raised.exception.halt)
                self.assertEqual(budget.used, 1)
                self.assertEqual(budget.remaining, 0)

    def test_rate_reserve_stops_next_request_and_persists(self):
        budget = stars.RequestBudget()
        stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, lambda *a, **k: Response([], remaining=20))
        self.assertEqual(budget.remaining, 0)
        with self.assertRaisesRegex(stars.HistoryError, 'reserve'):
            budget.consume()
        cache = stars.refresh([PROJECT], now=NOW, getter=pager(weekly_series()))
        cache['budget']['paused_reason'] = budget.paused_reason
        calls = []
        stars.refresh([PROJECT], existing=cache, now=NOW, getter=pager(weekly_series(), calls), force=True)
        self.assertEqual(calls, [])

    def test_invalid_json_and_network_failures_are_sanitized(self):
        class BadResponse(Response):
            def read(self, size):
                return b'{bad json secret-content'
        with self.assertRaisesRegex(stars.HistoryError, 'invalid aggregate JSON'):
            stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, stars.RequestBudget(), lambda *a, **k: BadResponse([]))
        def failure(*args, **kwargs):
            raise URLError('sensitive transport detail')
        budget = stars.RequestBudget()
        with self.assertRaises(stars.HistoryError) as raised:
            stars.request_page(stars.API + 'org/example/stargazers/history?per_page=30&page=1', None, budget, failure, lambda _: None)
        self.assertNotIn('sensitive', str(raised.exception))
        self.assertEqual(budget.used, 2)


if __name__ == '__main__':
    unittest.main()
