"""Shared search and Cabinet state contracts, exercised in the normal offline suite."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CabinetTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable')
    def test_search_contract(self):
        subprocess.run(['node', '--test', 'site/test_search.js'], cwd=ROOT,
                       check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which('node'), 'Node unavailable')
    def test_state_contract(self):
        subprocess.run(['node', '--test', 'site/test_cabinet.js'], cwd=ROOT,
                       check=True, capture_output=True, text=True)
