"""Run independent browser suites and exhaustive bounded artwork chunks.

The caller serves tmp/site on loopback. Every suite runs even after another fails;
logs, per-suite limits/timings and exact artwork coverage remain in tmp/site-qa.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
CHUNK_SIZE = 32


def make_plan(catalog):
    ids = sorted(p['id'] for p in catalog['projects'] if p.get('artwork'))
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate illustrated canonical IDs')
    suites = [dict(name='core', script='check_site_browser.cjs', seconds=180),
              dict(name='fonts', script='check_fonts_browser.cjs', seconds=90),
              dict(name='observatory', script='check_observatory_browser.cjs', seconds=90),
              dict(name='exhibition', script='check_exhibition_browser.cjs', seconds=90),
              dict(name='jars', script='check_jar_browser.cjs', seconds=90)]
    for index, start in enumerate(range(0, len(ids), CHUNK_SIZE)):
        suites.append(dict(name=f'artwork-{index}', script='check_artwork_browser.cjs',
                           args=[str(index)], seconds=60, ids=ids[start:start + CHUNK_SIZE]))
    # Includes process-group cleanup and report writes after every potential timeout.
    minutes = math.ceil(sum(s['seconds'] + 5 for s in suites) / 60) + 1
    return dict(sourceSha=catalog['source_sha'], artworkIds=ids, suites=suites,
                timeout_minutes=minutes)


def run_suite(suite, output, command=None, cwd=ROOT):
    started = time.monotonic()
    result = dict(name=suite['name'], limitSeconds=suite['seconds'], status='failed')
    argv = command or ['node', str(ROOT / 'scripts' / suite['script']), *suite.get('args', [])]
    env = dict(os.environ, JAR_PAGE='index.html')
    with (output / (suite['name'] + '.log')).open('w') as log:
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=suite['seconds'])
                result.update(status='passed' if code == 0 else 'failed', exitCode=code)
            except subprocess.TimeoutExpired:
                result.update(status='timed_out', exitCode=None)
            finally:
                # Chromium descendants must not survive a timed-out or crashed parent.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        except OSError as error:
            result.update(status='unavailable', error=str(error), exitCode=None)
    result['elapsedSeconds'] = round(time.monotonic() - started, 3)
    return result


def execute(plan, output, runner=run_suite):
    output.mkdir(parents=True, exist_ok=True)
    # A prior successful local run cannot satisfy this run's coverage checks.
    for suite in plan['suites']:
        if 'ids' in suite:
            (output / (suite['name'] + '.json')).unlink(missing_ok=True)
            for project_id in suite['ids']:
                (output / f'specimen-{project_id}.png').unlink(missing_ok=True)
    report = dict(status='running', sourceSha=plan['sourceSha'],
                  prHeadSha=os.environ.get('PR_HEAD_SHA'), expectedArtworkIds=plan['artworkIds'], suites=[])
    def save():
        (output / 'browser-suites.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    for suite in plan['suites']:
        print(f"Browser suite {suite['name']} (limit {suite['seconds']}s)", flush=True)
        try:
            result = runner(suite, output)
        except (KeyboardInterrupt, SystemExit):
            report['status'] = 'cancelled'
            report['suites'].append(dict(name=suite['name'], status='cancelled'))
            save()
            raise
        if result['status'] == 'passed' and 'ids' in suite:
            try:
                capture = json.loads((output / (suite['name'] + '.json')).read_text())
                if (capture['status'] != 'passed' or capture['sourceSha'] != plan['sourceSha']
                        or capture['expectedIds'] != suite['ids']
                        or [p['id'] for p in capture['projects']] != suite['ids']
                        or [s['file'] for s in capture['screenshots']] != [f'specimen-{i}.png' for i in suite['ids']]
                        or not all((output / f'specimen-{i}.png').is_file() for i in suite['ids'])):
                    raise ValueError('Artwork coverage or source revision mismatch')
            except (OSError, ValueError, KeyError, TypeError) as error:
                result.update(status='failed', error=str(error))
        report['suites'].append(result)
        save()
        print(f"  {result['status']} after {result.get('elapsedSeconds', 0)}s", flush=True)
    report['status'] = 'passed' if all(s['status'] == 'passed' for s in report['suites']) else 'failed'
    save()
    return report


def main():
    # Let run_suite's finally terminate the detached Chromium process group.
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', help='Write the workflow step budget without launching browsers')
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'tmp/site/catalog.json').read_text())
    plan = make_plan(catalog)
    expected = os.environ.get('SITE_SOURCE_SHA')
    if expected and expected != plan['sourceSha']:
        raise SystemExit('Generated catalog revision differs from SITE_SOURCE_SHA')
    if args.plan:
        print(json.dumps(plan, indent=2))
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
                out.write(f"timeout_minutes={plan['timeout_minutes']}\n")
        return 0
    report = execute(plan, ROOT / 'tmp/site-qa')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write('\n## Browser suites\n\n' + report['status'] + '\n\n')
            for suite in report['suites']:
                out.write(f"- {suite['name']}: {suite['status']} ({suite['elapsedSeconds']}s)\n")
            out.write(f"\nExpected artwork coverage: {len(plan['artworkIds'])} canonical projects. See browser-suites.json and per-chunk manifests.\n")
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
