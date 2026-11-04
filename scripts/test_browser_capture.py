"""Capture policy preserves failures and fixed layouts without a browser launch."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which('node'), 'Node required')
class CapturePolicyTests(unittest.TestCase):
    def test_full_default_and_selected_capture_contract(self):
        script = r"""
const assert = require('node:assert/strict');
const policy = require('./scripts/browser_capture.cjs');
assert.equal(policy.artwork('selected'), true);
assert.equal(policy.artwork('unchanged'), !policy.plan);
for (const name of ['footer-mobile.png', 'footer-production-1440.png', 'hero-desktop-1x-responsive.png', 'sheet-full-390.png', 'footer-failure.png', 'jars-failure.png']) assert.equal(policy.review(name), true);
for (const name of ['footer-background-1.png', 'footer-production-2560.png', 'hero-mobile-3x-original.png']) assert.equal(policy.review(name), !policy.plan);
"""
        env = {k: v for k, v in os.environ.items() if k != 'BROWSER_CAPTURE_PLAN'}
        subprocess.run(['node', '-e', script], cwd=ROOT, env=env, check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'plan.json'
            file.write_text(json.dumps(dict(mode='selective', sourceSha='revision', captureIds=['selected'])))
            env.update(BROWSER_CAPTURE_PLAN=str(file), SITE_SOURCE_SHA='revision')
            subprocess.run(['node', '-e', script], cwd=ROOT, env=env, check=True, capture_output=True)
            env['SITE_SOURCE_SHA'] = 'wrong'
            result = subprocess.run(['node', '-e', script], cwd=ROOT, env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Capture plan source/mode mismatch', result.stderr)


if __name__ == '__main__':
    unittest.main()
