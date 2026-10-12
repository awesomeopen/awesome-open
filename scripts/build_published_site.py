#!/usr/bin/env python3
"""Build the website from an accepted main revision in a fresh detached worktree."""

import argparse
from pathlib import Path
import re
import sys
import tempfile

from publish_readme import ROOT, git, latest_main, run


def build_published_site(source_sha, output, root=ROOT):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source_sha must be a full lowercase Git commit SHA")
    # Fetch to resolve newly published commits and verify they were accepted.
    current = latest_main(root)
    if git(root, "merge-base", "--is-ancestor", source_sha, current, check=False).returncode:
        raise RuntimeError("Refusing to build a revision that is not on main")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Site output directory must be empty to prevent stale artifacts")
    with tempfile.TemporaryDirectory(prefix="pages-build-") as directory:
        worktree = Path(directory) / "checkout"
        git(root, "worktree", "add", "--detach", str(worktree), source_sha)
        try:
            if git(worktree, "rev-parse", "HEAD").stdout.strip() != source_sha:
                raise RuntimeError("Site checkout does not match the published revision")
            run(worktree, sys.executable, "scripts/build_site.py", "--output", str(output),
                "--source-sha", source_sha)
            if not (output / "index.html").is_file() or not (output / "catalog.json").is_file():
                raise RuntimeError("Published site build did not produce the required files")
        finally:
            git(root, "worktree", "remove", "--force", str(worktree))
    print(f"Built website from published revision {source_sha}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        build_published_site(args.source_sha, args.output)
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
