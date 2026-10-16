"""Process-local, read-only builds of the unchanged checkout for integration tests.

Only baseline readers belong here. Tests changing sources, mocking build inputs,
adding a hero, or removing/corrupting output must call build_site.build directly.
Rebuild checks first copy the baseline to a private writable directory. Nothing
is loaded from a previous test process or persisted after this process exits.
"""
import atexit
from copy import deepcopy
from pathlib import Path
import shutil
import stat
import tempfile
from unittest.mock import patch

import build_site


_fixtures = {}


def baseline_site(source_sha=None):
    """Return a read-only output path and a detached catalog for this checkout.

    ROOT is intentionally not an argument: changed-root/data tests need fresh
    builds, not cached fixtures. The resolved root and exact source_sha identify
    each baseline within this test process's unchanged source snapshot.
    """
    root = build_site.ROOT.resolve()
    key = (root, source_sha)
    if key not in _fixtures:
        temporary = tempfile.TemporaryDirectory(prefix='site-test-baseline-')
        output = Path(temporary.name) / 'site'
        try:
            # These guards surround the actual first build regardless of which
            # test class requests it first. A cache hit cannot bypass the check.
            with patch('urllib.request.urlopen', side_effect=AssertionError('Offline build attempted network')), \
                    patch('socket.create_connection', side_effect=AssertionError('Offline build attempted network')):
                catalog = build_site.build(output, source_sha=source_sha, root=root)
            for path in [output, *output.rglob('*')]:
                path.chmod(path.stat().st_mode & ~0o222)
        except BaseException:
            temporary.cleanup()
            raise
        _fixtures[key] = (temporary, output, catalog)
    _, output, catalog = _fixtures[key]
    return output, deepcopy(catalog)


def copy_site_fixture(source, destination):
    """Copy a baseline to a new, writable output for an isolated real rebuild."""
    destination = Path(destination)
    shutil.copytree(source, destination)
    for path in [destination, *destination.rglob('*')]:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    return destination


def _cleanup():
    for temporary, _, _ in _fixtures.values():
        temporary.cleanup()
    _fixtures.clear()


atexit.register(_cleanup)
