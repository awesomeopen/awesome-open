"""Regression coverage for historical renderer asset-root compatibility."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_specimen_bounds_control as control


class ComparisonRendererRootTests(unittest.TestCase):
    def build_with_renderer(self, render_function):
        renderer = ('from pathlib import Path\n'
                    'ROOT = Path(__file__).resolve().parents[1]\n'
                    'def attach_specimen_cutouts(catalog, root): return {}\n' + render_function)

        def git_output(command, **kwargs):
            if command[1] == 'rev-parse':
                return 'abc123\n'
            source = command[-1].split(':', 1)[1]
            if source == 'scripts/build_site.py':
                return renderer
            if source == 'scripts/build_jar_preview.py':
                return 'def build(output, production=False): pass\n'
            return '/* historical asset */'

        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / 'catalog.json').write_text(json.dumps({
                'categories': [], 'projects': [
                    {'id': 'openbb', 'name': 'OpenBB', 'artwork': {'width': 100, 'height': 100}}]}))
            (site / 'index.html').write_text('<head></head>')
            with patch.object(control.subprocess, 'check_output', side_effect=git_output):
                control.build('base', site)
            return (site / 'bounds-before/openbb.html').read_text()

    def test_current_renderer_reads_fonts_from_repository_not_temporary_module(self):
        html = self.build_with_renderer(
            'def render_record(project, categories, catalog, number, cutouts=None, root=ROOT):\n'
            '    assert (root / "site/vendor/fonts.css").read_bytes()\n'
            '    return str(root)\n')
        self.assertEqual(html, str(Path(control.__file__).resolve().parents[1]))

    def test_older_renderer_without_root_keyword_remains_supported(self):
        html = self.build_with_renderer(
            'def render_record(project, categories, catalog, number, cutouts=None):\n'
            '    return "historical renderer"\n')
        self.assertEqual(html, 'historical renderer')


if __name__ == '__main__':
    unittest.main()
