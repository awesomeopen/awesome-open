"""Keep PR browser checks tied to local previews and outside production access."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent


class BrowserWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (ROOT / '.github/workflows/check-updaters.yml').read_text()

    def test_browser_uses_this_checkout_and_cleans_up_loopback_server(self):
        text = self.workflow
        build = text.index('scripts/build_site.py --output tmp/site --source-sha "$GITHUB_SHA"')
        browser = text.index('python3 scripts/run_browser_checks.py')
        self.assertLess(build, browser)
        for required in ['SITE_URL: http://127.0.0.1:8000', 'SITE_SOURCE_SHA: ${{ github.sha }}',
                         '--bind 127.0.0.1 --directory tmp/site', 'response.status == 200',
                         'trap \'kill "$server_pid"', 'set -euo pipefail',
                         'python3 scripts/run_browser_checks.py',
                         'fromJSON(steps.browser-plan.outputs.timeout_minutes)' ]:
            self.assertIn(required, text)

    def test_screenshots_are_kept_after_failure_with_bounded_retention(self):
        upload = self.workflow.split('name: Upload desktop and mobile browser screenshots', 1)[1]
        for required in ['if: ${{ always() }}', 'actions/upload-artifact@v4',
                         'name: field-guide-browser-screenshots', 'path: tmp/site-qa/',
                         'retention-days: 14']:
            self.assertIn(required, upload)

    def test_pr_workflow_has_only_read_access_and_no_publisher(self):
        text = self.workflow
        self.assertIn('pull_request:', text)
        self.assertIn('permissions:\n  contents: read', text)
        self.assertIn('persist-credentials: false', text)
        self.assertEqual(len(re.findall(r'^\s*permissions:', text, re.MULTILINE)), 1)
        for forbidden in ['pull_request_target', 'secrets.', ': write', 'deploy-pages',
                          'upload-pages-artifact', 'publish_readme.py', 'build_published_site.py',
                          'environment:', 'awesomeopen.github.io']:
            self.assertNotIn(forbidden, text)

    def test_playwright_and_transitive_dependency_are_locked(self):
        package = json.loads((ROOT / 'package.json').read_text())
        lock = json.loads((ROOT / 'package-lock.json').read_text())
        version = package['devDependencies']['playwright']
        self.assertRegex(version, r'^\d+\.\d+\.\d+$')
        self.assertEqual(lock['packages']['']['devDependencies']['playwright'], version)
        for name in ['playwright', 'playwright-core']:
            entry = lock['packages']['node_modules/' + name]
            self.assertEqual(entry['version'], version)
            self.assertTrue(entry['integrity'].startswith('sha512-'))
        self.assertIn('npm ci --ignore-scripts', self.workflow)
        self.assertIn('npx --no-install playwright install --with-deps chromium', self.workflow)
        self.assertIn('cache-dependency-path: package-lock.json', self.workflow)

    def test_reduced_motion_disables_smooth_scrolling(self):
        css = (ROOT / 'site/styles.css').read_text()
        reduced_motion = css.split('@media(prefers-reduced-motion:reduce)', 1)[1]
        html_rule = reduced_motion.split('html {', 1)[1].split('}', 1)[0]
        self.assertIn('scroll-behavior:auto', html_rule)


if __name__ == '__main__':
    unittest.main()
