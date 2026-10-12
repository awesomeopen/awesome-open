"""Offline publisher regression tests using real local Git remotes."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import publish_readme as publisher
import build_published_site as site_publisher


STATS_SCRIPT = '''from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
(root / 'data/github_metrics.json').write_text(json.dumps({'source': (root / 'README.source.md').read_text()}) + '\\n')
'''
HN_SCRIPT = '''from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / 'data/hn_evidence.json').write_text('{"cached": true}\\n')
'''
SIGNALS_SCRIPT = '''import argparse
import json
import os
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source-sha', required=True)
args = parser.parse_args()
assert args.source_sha == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert subprocess.run(['git', 'symbolic-ref', '-q', 'HEAD'], cwd=root, capture_output=True).returncode == 1
source = (root / 'README.source.md').read_text()
assert json.loads((root / 'data/github_metrics.json').read_text())['source'] == source
assert json.loads((root / 'data/hn_evidence.json').read_text())['cached']
output = root / 'data/project_signals.json'
previous = json.loads(output.read_text()) if output.exists() else {}
if os.environ.get('FIXTURE_SIGNALS_UPSTREAM_ERROR'):
    print('Optional upstream unavailable; retaining last-good signals.')
elif previous.get('source') != source:
    output.write_text(json.dumps({'source': source, 'source_sha': args.source_sha}) + '\\n')
'''
RENDER_SCRIPT = '''import argparse
from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', default=str(root / 'README.md'))
parser.add_argument('--strict-metrics', action='store_true')
args = parser.parse_args()
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
source = (root / 'README.source.md').read_text()
assert json.loads((root / 'data/github_metrics.json').read_text())['source'] == source
output.write_text(source + '\\nGenerated from snapshot.\\n')
assets = output.parent / 'assets/hn'
assets.mkdir(parents=True, exist_ok=True)
(assets / 'fixture.svg').write_text('<svg/>\\n')
'''
CHECK_SCRIPT = '''from pathlib import Path
import unittest
class Checks(unittest.TestCase):
    def test_render(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / 'README.md').read_text().startswith((root / 'README.source.md').read_text()))
'''

SITE_SCRIPT = '''import argparse
import json
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source-sha', required=True)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == args.source_sha
assert subprocess.run(['git', 'symbolic-ref', '-q', 'HEAD'], cwd=root, capture_output=True).returncode == 1
args.output.mkdir(parents=True, exist_ok=True)
(args.output / 'index.html').write_text((root / 'README.source.md').read_text())
(args.output / 'catalog.json').write_text(json.dumps({'source_sha': args.source_sha}))
'''


@unittest.skipUnless(shutil.which('git'), 'Git is required for publisher integration tests')
class PublisherGitTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='publisher-test-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.origin = self.root / 'origin.git'
        self.actor = self.root / 'contributor'
        self.checkout = self.root / 'publisher'
        self.git(self.root, 'init', '--bare', '--initial-branch=main', str(self.origin))
        self.git(self.root, 'init', '--initial-branch=main', str(self.actor))
        self.git(self.actor, 'config', 'user.name', 'Test Contributor')
        self.git(self.actor, 'config', 'user.email', 'contributor@example.invalid')
        files = {
            'README.source.md': 'Initial curated row.\n',
            'README.md': 'Old generated output.\n',
            '.gitignore': '__pycache__/\n*.py[cod]\n',
            'data/github_metrics.json': '{}\n',
            'data/hn_evidence.json': '{}\n',
            'assets/hn/fixture.svg': '<svg>old</svg>\n',
            'scripts/update_stats.py': STATS_SCRIPT,
            'scripts/update_hn.py': HN_SCRIPT,
            'scripts/update_signals.py': SIGNALS_SCRIPT,
            'scripts/render_readme.py': RENDER_SCRIPT,
            'scripts/test_fixture.py': CHECK_SCRIPT,
            'scripts/build_site.py': SITE_SCRIPT,
        }
        for name, text in files.items():
            target = self.actor / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        self.git(self.actor, 'add', '.')
        self.git(self.actor, 'commit', '-m', 'Initial fixture')
        self.git(self.actor, 'remote', 'add', 'origin', str(self.origin))
        self.git(self.actor, 'push', '-u', 'origin', 'main')
        self.git(self.root, 'clone', str(self.origin), str(self.checkout))
        self.initial = self.remote_head()
        self.output = io.StringIO()
        self.errors = io.StringIO()
        # Fake repositories contain only test_fixture.py, so running their full
        # suite exercises the production subprocess without recursive tests.
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(contextlib.redirect_stderr(self.errors))

    def git(self, root, *args):
        return subprocess.run(['git', *args], cwd=root, text=True,
                              capture_output=True, check=True).stdout.strip()

    def remote_head(self):
        return self.git(self.origin, 'rev-parse', 'main')

    def remote_file(self, path):
        return self.git(self.origin, 'show', 'main:' + path)

    def advance_source(self, content):
        self.git(self.actor, 'pull', '--ff-only', 'origin', 'main')
        (self.actor / 'README.source.md').write_text(content, encoding='utf-8')
        self.git(self.actor, 'add', 'README.source.md')
        self.git(self.actor, 'commit', '-m', 'Contributor source edit')
        self.git(self.actor, 'push', 'origin', 'main')
        return self.remote_head()

    def assert_worktree_removed(self):
        listed = self.git(self.checkout, 'worktree', 'list', '--porcelain')
        self.assertEqual(listed.count('worktree '), 1)

    def test_publishes_only_generated_files_and_preserves_callers_dirty_index(self):
        (self.checkout / 'README.source.md').write_text('Unpublished local curation.\n')
        self.git(self.checkout, 'add', 'README.source.md')
        (self.checkout / 'personal-note.txt').write_text('Do not touch.\n')
        before = self.git(self.checkout, 'status', '--porcelain')
        commit = publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), commit)
        self.assertEqual(self.git(self.checkout, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual(self.git(self.checkout, 'status', '--porcelain'), before)
        self.assertEqual((self.checkout / 'README.source.md').read_text(), 'Unpublished local curation.\n')
        self.assertEqual(self.remote_file('README.source.md'), 'Initial curated row.')
        self.assertIn('Initial curated row.', self.remote_file('README.md'))
        changed = self.git(self.origin, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        self.assertTrue(changed)
        self.assertIn('data/project_signals.json', changed)
        self.assertTrue(all(publisher.allowed_path(name) for name in changed))
        self.assertEqual(json.loads(self.remote_file('data/project_signals.json'))['source_sha'], self.initial)
        self.assert_worktree_removed()

    def test_regenerates_when_main_advances_during_collection(self):
        original = publisher.collect_and_render
        sources = []
        latest_contributor = []

        def collect(root):
            sources.append((root / 'README.source.md').read_text())
            original(root)
            if len(sources) == 1:
                latest_contributor.append(self.advance_source('Added a new upstream repository.\n'))

        with patch.object(publisher, 'collect_and_render', side_effect=collect):
            commit = publisher.publish(self.checkout)
        self.assertEqual(sources, ['Initial curated row.\n', 'Added a new upstream repository.\n'])
        self.assertEqual(self.git(self.origin, 'rev-parse', commit + '^'), latest_contributor[0])
        self.assertIn('Added a new upstream repository.', self.remote_file('README.md'))
        self.assertEqual(json.loads(self.remote_file('data/github_metrics.json'))['source'], sources[-1])
        signals = json.loads(self.remote_file('data/project_signals.json'))
        self.assertEqual(signals['source'], sources[-1])
        self.assertEqual(signals['source_sha'], latest_contributor[0])
        self.assert_worktree_removed()

    def test_optional_upstream_error_preserves_last_good_while_core_publishes(self):
        publisher.publish(self.checkout)
        previous_signals = self.remote_file('data/project_signals.json')
        source = 'Core catalog changed during an optional upstream outage.\n'
        self.advance_source(source)
        with patch.dict(os.environ, {'FIXTURE_SIGNALS_UPSTREAM_ERROR': '1'}):
            commit = publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), commit)
        self.assertEqual(self.remote_file('data/project_signals.json'), previous_signals)
        self.assertEqual(json.loads(self.remote_file('data/github_metrics.json'))['source'], source)
        self.assertIn(source.strip(), self.remote_file('README.md'))
        self.assertIn('retaining last-good signals', self.output.getvalue())
        self.assert_worktree_removed()

    def test_initial_optional_outage_does_not_require_a_snapshot(self):
        with patch.dict(os.environ, {'FIXTURE_SIGNALS_UPSTREAM_ERROR': '1'}):
            commit = publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), commit)
        self.assertNotIn('data/project_signals.json', self.git(self.origin, 'ls-tree', '-r', '--name-only', 'main'))
        self.assertIn('Initial curated row.', self.remote_file('README.md'))
        self.assert_worktree_removed()

    def test_corrupt_optional_snapshot_fails_without_publishing(self):
        (self.actor / 'data/project_signals.json').write_text('{invalid JSON\n')
        self.git(self.actor, 'add', 'data/project_signals.json')
        self.git(self.actor, 'commit', '-m', 'Corrupt optional snapshot fixture')
        self.git(self.actor, 'push', 'origin', 'main')
        expected = self.remote_head()
        with self.assertRaisesRegex(RuntimeError, 'Command failed .*update_signals.py'):
            publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), expected)
        self.assertEqual(self.remote_file('README.md'), 'Old generated output.')
        self.assertEqual(self.remote_file('data/github_metrics.json'), '{}')
        self.assert_worktree_removed()

    def test_failed_stale_collection_retries_new_main(self):
        original = publisher.collect_and_render
        calls = []

        def collect(root):
            calls.append((root / 'README.source.md').read_text())
            if len(calls) == 1:
                self.advance_source('Removed an unavailable repository.\n')
                raise RuntimeError('The stale source still includes an unavailable repository')
            original(root)

        with patch.object(publisher, 'collect_and_render', side_effect=collect):
            commit = publisher.publish(self.checkout)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.remote_head(), commit)
        self.assertIn('Removed an unavailable repository.', self.remote_file('README.md'))
        self.assert_worktree_removed()

    def test_rejected_push_regenerates_instead_of_rebasing_stale_output(self):
        original = publisher.git
        pushes = []

        def raced_git(root, *arguments, **kwargs):
            if arguments[:2] == ('push', 'origin'):
                pushes.append(arguments)
                if len(pushes) == 1:
                    self.advance_source('Source changed immediately before push.\n')
            return original(root, *arguments, **kwargs)

        with patch.object(publisher, 'git', side_effect=raced_git):
            commit = publisher.publish(self.checkout)
        self.assertEqual(len(pushes), 2)
        self.assertTrue(all(args == ('push', 'origin', 'HEAD:refs/heads/main') for args in pushes))
        self.assertEqual(commit, self.remote_head())
        self.assertIn('Source changed immediately before push.', self.remote_file('README.md'))
        self.assertIn('Main advanced before push', self.output.getvalue())
        self.assert_worktree_removed()

    def test_refuses_unexpected_generated_changes(self):
        original = publisher.collect_and_render

        for unexpected in ['unexpected.txt', 'data/project_signals.json.tmp']:
            with self.subTest(path=unexpected):
                def collect(root):
                    original(root)
                    (root / unexpected).write_text('This must never be committed.\n')

                with patch.object(publisher, 'collect_and_render', side_effect=collect):
                    with self.assertRaisesRegex(RuntimeError, 'outside generated paths') as error:
                        publisher.publish(self.checkout)
                self.assertIn(unexpected, str(error.exception))
                self.assertEqual(self.remote_head(), self.initial)
                self.assert_worktree_removed()

    def test_validation_failure_never_pushes(self):
        (self.actor / 'scripts/test_fixture.py').write_text(CHECK_SCRIPT + '\n    def test_failure(self):\n        self.fail("invalid collected state")\n')
        self.git(self.actor, 'add', 'scripts/test_fixture.py')
        self.git(self.actor, 'commit', '-m', 'Add failing validation')
        self.git(self.actor, 'push', 'origin', 'main')
        expected = self.remote_head()
        with self.assertRaisesRegex(RuntimeError, 'Command failed'):
            publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), expected)
        self.assert_worktree_removed()

    def test_nonreproducible_render_never_pushes(self):
        script = RENDER_SCRIPT + '\nif Path(args.output) != root / "README.md":\n    output.write_text("nonreproducible output")\n'
        (self.actor / 'scripts/render_readme.py').write_text(script)
        self.git(self.actor, 'add', 'scripts/render_readme.py')
        self.git(self.actor, 'commit', '-m', 'Add broken renderer')
        self.git(self.actor, 'push', 'origin', 'main')
        expected = self.remote_head()
        with self.assertRaisesRegex(RuntimeError, 'not reproducible'):
            publisher.publish(self.checkout)
        self.assertEqual(self.remote_head(), expected)
        self.assert_worktree_removed()

    def test_repeated_run_with_unchanged_output_is_noop(self):
        first = publisher.publish(self.checkout)
        self.assertEqual(publisher.publish(self.checkout), first)
        self.assertEqual(self.remote_head(), first)
        self.assert_worktree_removed()

    def test_site_build_uses_accepted_revision_not_dirty_or_newer_checkout(self):
        accepted = publisher.publish(self.checkout)
        self.advance_source('A newer source after accepted publication.\n')
        (self.checkout / 'README.source.md').write_text('Unpublished local work.\n')
        self.git(self.checkout, 'add', 'README.source.md')
        before = self.git(self.checkout, 'status', '--porcelain')
        output = self.root / 'site'
        site_publisher.build_published_site(accepted, output, root=self.checkout)
        self.assertEqual((output / 'index.html').read_text(), 'Initial curated row.\n')
        self.assertEqual(json.loads((output / 'catalog.json').read_text())['source_sha'], accepted)
        self.assertEqual(self.git(self.checkout, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual(self.git(self.checkout, 'status', '--porcelain'), before)
        self.assert_worktree_removed()

    def test_site_build_works_after_noop_publication(self):
        publisher.publish(self.checkout)
        accepted = publisher.publish(self.checkout)
        output = self.root / 'site'
        site_publisher.build_published_site(accepted, output, root=self.checkout)
        self.assertEqual(json.loads((output / 'catalog.json').read_text())['source_sha'], accepted)
        self.assert_worktree_removed()

    def test_site_build_rejects_unpublished_revision(self):
        (self.checkout / 'README.source.md').write_text('Not yet published.\n')
        self.git(self.checkout, 'add', 'README.source.md')
        self.git(self.checkout, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', 'Unpublished fixture')
        sha = self.git(self.checkout, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(RuntimeError, 'not on main'):
            site_publisher.build_published_site(sha, self.root / 'site', root=self.checkout)
        self.assertFalse((self.root / 'site').exists())
        self.assert_worktree_removed()

    def test_site_build_refuses_stale_output_directory(self):
        output = self.root / 'site'
        output.mkdir()
        (output / 'stale.html').write_text('Old artifact')
        with self.assertRaisesRegex(ValueError, 'must be empty'):
            site_publisher.build_published_site(self.initial, output, root=self.checkout)
        self.assertEqual((output / 'stale.html').read_text(), 'Old artifact')
        self.assert_worktree_removed()

    def test_site_build_failure_removes_worktree_and_propagates(self):
        (self.actor / 'scripts/build_site.py').write_text('raise RuntimeError("broken build")\n')
        self.git(self.actor, 'add', 'scripts/build_site.py')
        self.git(self.actor, 'commit', '-m', 'Broken build fixture')
        self.git(self.actor, 'push', 'origin', 'main')
        with self.assertRaisesRegex(RuntimeError, 'Command failed'):
            site_publisher.build_published_site(self.remote_head(), self.root / 'site', root=self.checkout)
        self.assert_worktree_removed()

    def test_continuously_advancing_main_fails_without_stale_push(self):
        original = publisher.collect_and_render
        sources = []

        def collect(root):
            original(root)
            sources.append(str(len(sources)))
            self.advance_source('Upstream source iteration ' + sources[-1] + '\n')

        with patch.object(publisher, 'collect_and_render', side_effect=collect):
            with self.assertRaisesRegex(RuntimeError, 'Main kept advancing across 2 attempts'):
                publisher.publish(self.checkout, max_attempts=2)
        self.assertEqual(len(sources), 2)
        self.assertEqual(self.remote_file('README.md'), 'Old generated output.')
        self.assertEqual(self.git(self.origin, 'log', '-1', '--format=%s'), 'Contributor source edit')
        self.assert_worktree_removed()


class PublisherScopeTests(unittest.TestCase):
    def test_cli_exports_only_successfully_published_sha(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github-output'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), patch.object(sys, 'argv', ['publisher']):
                with patch.object(publisher, 'publish', return_value='a' * 40):
                    publisher.main()
                self.assertEqual(output.read_text(), 'published_sha=' + 'a' * 40 + '\n')
                with patch.object(publisher, 'publish', side_effect=RuntimeError('failed')):
                    with self.assertRaises(SystemExit):
                        publisher.main()
                self.assertEqual(output.read_text(), 'published_sha=' + 'a' * 40 + '\n')

    def test_site_rejects_non_sha_input_before_fetch(self):
        for sha in ['main', '', 'a' * 39, 'A' * 40, '--help']:
            with self.subTest(sha=sha), patch.object(site_publisher, 'latest_main') as fetch:
                with self.assertRaisesRegex(ValueError, 'full lowercase'):
                    site_publisher.build_published_site(sha, '/tmp/not-used')
                fetch.assert_not_called()

    def test_generated_scope_is_explicit(self):
        for name in ['README.md', 'data/github_metrics.json', 'data/hn_evidence.json',
                     'data/project_signals.json', 'assets/hn/project.svg']:
            with self.subTest(name=name):
                self.assertTrue(publisher.allowed_path(name))
        for name in ['README.source.md', 'CONTRIBUTING.md', 'data/hn_projects.json', 'data/alternatives.json',
                     'data/project_signals.json.tmp', 'data/other_signals.json', 'data/nested/project_signals.json',
                     '.github/workflows/update-stats.yml', 'assets/hn/../../secret.svg', 'assets/hn/script.py']:
            with self.subTest(name=name):
                self.assertFalse(publisher.allowed_path(name))

    def test_invalid_attempt_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive'):
            publisher.publish(max_attempts=0)


class WorkflowContractTests(unittest.TestCase):
    def test_pr_preview_is_offline_and_does_not_require_tracked_readme_match(self):
        text = (publisher.ROOT / '.github/workflows/check-updaters.yml').read_text()
        self.assertIn("python3 -m unittest discover -s scripts -p 'test_*.py'", text)
        self.assertIn('scripts/render_readme.py --output tmp/readme-preview/README.md', text)
        self.assertIn('actions/upload-artifact@v4', text)
        self.assertIn('path: tmp/readme-preview/', text)
        self.assertNotIn('git diff --exit-code', text)
        self.assertNotIn('scripts/update_stats.py', text)
        self.assertNotIn('scripts/update_hn.py', text)
        self.assertNotIn('scripts/update_signals.py', text)
        self.assertNotIn('pull_request_target', text)
        self.assertIn('contents: read', text)

    def test_all_publishing_events_share_one_serialized_writer(self):
        text = (publisher.ROOT / '.github/workflows/update-stats.yml').read_text()
        for snippet in ['push:', 'branches: [main]', "'README.source.md'", "'data/**'", "'scripts/**'",
                        "cron: '0 0 * * *'", 'workflow_dispatch:', 'group: publish-readme-main',
                        'cancel-in-progress: false', 'ref: main', 'fetch-depth: 0', 'scripts/publish_readme.py']:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)
        self.assertNotIn('git push', text)
        self.assertNotIn('--force', text)
        self.assertNotIn('scripts/update_stats.py', text)

    def test_pages_build_and_deployment_stay_in_same_serialized_workflow(self):
        text = (publisher.ROOT / '.github/workflows/update-stats.yml').read_text()
        for snippet in ["'site/**'", "'assets/hn/**'", 'id: publish',
                        'steps.publish.outputs.published_sha', 'scripts/build_published_site.py',
                        'actions/upload-pages-artifact@v3', 'path: tmp/site',
                        'name: github-pages-${{ github.run_attempt }}',
                        'artifact_name: github-pages-${{ github.run_attempt }}',
                        'needs: publish-readme', 'actions/deploy-pages@v4',
                        'build_attempt: ${{ steps.publish.outputs.build_attempt }}',
                        'echo "build_attempt=$GITHUB_RUN_ATTEMPT" >> "$GITHUB_OUTPUT"',
                        'BUILD_ATTEMPT: ${{ needs.publish-readme.outputs.build_attempt }}',
                        'if [ "$BUILD_ATTEMPT" != "$GITHUB_RUN_ATTEMPT" ]; then',
                        'Re-run all jobs', 'GITHUB_STEP_SUMMARY',
                        'name: github-pages', "if: github.ref == 'refs/heads/main'"]:
            self.assertIn(snippet, text)
        build, deploy = text.split('  deploy-pages:')
        self.assertNotIn('pages: write', build)
        self.assertNotIn('id-token: write', build)
        self.assertIn('contents: write', build)
        self.assertIn('pages: write', deploy)
        self.assertIn('id-token: write', deploy)
        self.assertNotIn('contents: write', deploy)
        self.assertNotIn('actions/checkout', deploy)
        self.assertNotIn('workflow_run:', text)


if __name__ == '__main__':
    unittest.main()
