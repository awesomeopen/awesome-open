import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_webmcplet_list as adapter  # noqa: E402

URLS = ['https://www.GitHub.com/Owner/Repo.git/', 'http://example.org/a/?q=1', 'https://Codeberg.org/x/y/',
        'https://gitlab.com/group/sub/project']


def project(pid, name, stars=None, license=None, **extra):
    return {'id': pid * 64, 'name': name, 'url': f'https://github.com/o/{name.lower().replace(" ", "-")}',
            'description': f'{name} description.', 'categories': ['tools'],
            'github': {'stars': stars, 'license': license, 'pushed_at': '2026-11-01T00:00:00Z'}, **extra}


CATALOG = {
    'source_sha': 'f' * 40, 'metrics_as_of': '2026-11-09',
    'categories': [{'id': 'tools', 'name': 'Tools'}],
    'projects': [
        project('a', 'Open Zeta', stars=0, license='NOASSERTION'),
        project('b', 'Open Alpha', license='MIT', aliases=[{'name': 'OA'}],
                deployment={'run_modes': [{'value': 'server'}]},
                function_summary={'text': 'Runs at home.', 'features': [{'title': 'Sync', 'text': 'Syncs files.'}]}),
        project('c', 'Open Beta', stars=40, alternatives=[{'name': 'Dropbox'}]),
    ],
}


class WebMCPletTest(unittest.TestCase):
    def test_javascript_suites(self):
        result = subprocess.run(['node', '--test', *sorted(map(str, (ROOT / 'webmcplet/test').glob('*.test.js')))],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_url_identity_matches_the_script(self):
        script = 'const W=require("./webmcplet/webmcplet.js");console.log(JSON.stringify(%s.map(W.normalizeUrl)))'
        result = subprocess.run(['node', '-e', script % json.dumps(URLS)], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [adapter.normalize_url(url) for url in URLS])

    def test_adapter_keeps_catalog_order_and_unknowns(self):
        document = adapter.build(CATALOG, 'https://example.org/list/')
        self.assertEqual([item['name'] for item in document['items']], ['Open Beta', 'Open Zeta', 'Open Alpha'])
        beta, zeta, alpha = document['items']
        self.assertEqual(zeta['fields'], {'github_stars': 0, 'pushed_at': '2026-11-01T00:00:00Z'})
        self.assertEqual(alpha['fields']['run_modes'], ['server'])
        self.assertEqual(alpha['fields']['feature_notes'], ['Sync Syncs files.'])
        self.assertEqual(alpha['aliases'], ['OA'])
        self.assertEqual(beta['fields']['alternatives'], ['Dropbox'])
        self.assertEqual(beta['link'], 'https://example.org/list/records/' + 'c' * 64 + '.html')
        self.assertEqual(document['fields']['github_stars']['observed_at'], '2026-11-09')

    def test_adapter_output_passes_the_schema_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'list.json'
            path.write_text(json.dumps(adapter.build(CATALOG, 'https://example.org/list/')), encoding='utf-8')
            result = subprocess.run(['node', 'webmcplet/build.cjs', 'check', str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
