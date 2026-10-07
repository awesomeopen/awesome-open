#!/usr/bin/env python3
"""Collect, validate, and publish generated README files from current main.

Every attempt uses a disposable, detached worktree of freshly fetched main.
Nothing is rebased onto a stale generated README: if main advances, collection
and rendering start again from its new source. The final ordinary Git push is
an additional compare-and-swap guard against a race after the last fetch.
The invoking checkout (including any local curated edits) is never reset.
"""

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
GENERATED_FILES = frozenset({
    "README.md", "data/github_metrics.json", "data/hn_evidence.json",
})


def run(root, *command, check=True):
    result = subprocess.run(command, cwd=root, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result


def git(root, *arguments, check=True):
    return run(root, "git", *arguments, check=check)


def latest_main(root):
    git(root, "fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    return git(root, "rev-parse", "refs/remotes/origin/main").stdout.strip()


def allowed_path(name):
    path = PurePosixPath(name)
    return name in GENERATED_FILES or (
        path.parent == PurePosixPath("assets/hn") and path.suffix == ".svg"
    )


def changed_paths(root):
    tracked = git(root, "diff", "--no-renames", "--name-only", "-z", "HEAD").stdout
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    return set(filter(None, (tracked + untracked).split("\0")))


def assert_generated_only(root):
    changed = changed_paths(root)
    unexpected = sorted(name for name in changed if not allowed_path(name))
    if unexpected:
        raise RuntimeError("Refusing to publish changes outside generated paths: " + ", ".join(unexpected))
    return changed


def collect_and_render(root):
    # Collectors own only their snapshots. The offline renderer owns all output.
    run(root, sys.executable, "scripts/update_stats.py")
    run(root, sys.executable, "scripts/update_hn.py")
    run(root, sys.executable, "scripts/render_readme.py", "--strict-metrics")


def validate(root):
    # Publish validates its own newly collected state. It must not depend on a
    # second workflow being triggered by a GITHUB_TOKEN-authored commit.
    run(root, sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py")
    with tempfile.TemporaryDirectory(prefix="readme-validation-") as directory:
        output = Path(directory) / "README.md"
        run(root, sys.executable, "scripts/render_readme.py", "--strict-metrics", "--output", str(output))
        if output.read_bytes() != (root / "README.md").read_bytes():
            raise RuntimeError("The offline README render is not reproducible")
        expected = {path.name: path.read_bytes() for path in (output.parent / "assets/hn").glob("*.svg")}
        actual = {path.name: path.read_bytes() for path in (root / "assets/hn").glob("*.svg")}
        if actual != expected:
            raise RuntimeError("The offline HN assets are not reproducible")
    return assert_generated_only(root)


def publish(root=ROOT, max_attempts=5):
    root = Path(root).resolve()
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    for attempt in range(1, max_attempts + 1):
        base = latest_main(root)
        print(f"Publishing attempt {attempt}/{max_attempts} from main {base}", flush=True)
        with tempfile.TemporaryDirectory(prefix="readme-publisher-") as directory:
            worktree = Path(directory) / "checkout"
            git(root, "worktree", "add", "--detach", str(worktree), base)
            try:
                try:
                    collect_and_render(worktree)
                    changed = validate(worktree)
                except (RuntimeError, OSError):
                    # A stale input may itself cause collection to fail (for
                    # example, a repository removed by a concurrent edit).
                    if latest_main(root) != base:
                        print("Main advanced while generation or validation failed; retrying its latest source.", flush=True)
                        continue
                    raise
                # Even a no-op render must be based on the latest source.
                if latest_main(root) != base:
                    print("Main advanced during collection; regenerating from its latest source.", flush=True)
                    continue
                if not changed:
                    print("README and snapshots are already current.", flush=True)
                    return None
                git(worktree, "--literal-pathspecs", "add", "--all", "--", *sorted(changed))
                # Set identity only for this commit, without changing the user's
                # repository or global Git configuration.
                git(worktree, "-c", "user.name=github-actions[bot]",
                    "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                    "commit", "-m", "chore: publish generated README and snapshots")
                commit = git(worktree, "rev-parse", "HEAD").stdout.strip()
                pushed = git(worktree, "push", "origin", "HEAD:refs/heads/main", check=False)
                if pushed.returncode == 0:
                    print(f"Published {commit}", flush=True)
                    return commit
                current = latest_main(root)
                # A transport error may be reported after the server accepted
                # the push. Verify before retrying or reporting failure.
                accepted = git(root, "merge-base", "--is-ancestor", commit, current, check=False)
                if accepted.returncode == 0:
                    print(f"Verified published commit {commit} on main.", flush=True)
                    return commit
                if current == base:
                    raise RuntimeError("Push failed while main was unchanged; check repository write permissions or branch rules")
                print("Main advanced before push; regenerating from its latest source.", flush=True)
            finally:
                # This is only our disposable generated worktree, never the
                # caller's checkout or any contributor branch.
                git(root, "worktree", "remove", "--force", str(worktree))
    raise RuntimeError(f"Main kept advancing across {max_attempts} attempts; no stale output was pushed. Rerun the publisher.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attempts", type=int, default=5)
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be positive")
    try:
        publish(max_attempts=args.max_attempts)
    except (RuntimeError, OSError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
