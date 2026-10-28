"""Run the browser-readiness unit checks without launching Chromium."""
from pathlib import Path
import shutil
import subprocess
import unittest


class SpecimenLayoutTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for JavaScript tests')
    def test_readiness_and_geometry_regressions(self):
        root = Path(__file__).resolve().parent.parent
        result = subprocess.run(['node', '--test', 'scripts/test_specimen_layout.cjs'],
                                cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
