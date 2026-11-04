"""Run independent browser suites and exhaustive bounded artwork chunks.

The caller serves tmp/site on loopback. Every suite runs even after another fails;
logs, per-suite limits/timings and exact artwork coverage remain in tmp/site-qa.
"""
import argparse
import json
import hashlib
import struct
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from browser_impact import impact

ROOT = Path(__file__).resolve().parent.parent
CHUNK_SIZE = 32


def make_plan(catalog, comparison=None):
    ids = sorted(p['id'] for p in catalog['projects'] if p.get('artwork'))
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate illustrated canonical IDs')
    comparison = comparison or dict(mode='full', reason='No verified comparison', changedIds=[])
    mode = comparison['mode']
    if mode not in {'selective', 'full'} or not set(comparison['changedIds']).issubset(set(ids)):
        mode = 'full'
    # Named, stable examples supplement all responsive/fixture captures retained
    # by the core suites. Removed/unrendered changed IDs conservatively use full.
    representatives = {'OpenTofu', 'OpenRefine', 'OpenSCAD', 'OpenBB', 'OpenSpec', 'Openpilot', 'OpenRocket'}
    capture_ids = ids if mode == 'full' else sorted(set(comparison['changedIds']) | {
        p['id'] for p in catalog['projects'] if p.get('artwork') and p.get('name') in representatives})
    suites = [dict(name='core', script='check_site_browser.cjs', seconds=120),
              *[dict(name=name, script='check_site_browser.cjs', args=[name], seconds=seconds)
                for name, seconds in [('aliases', 45), ('bounds', 90), ('details', 60), ('footer', 60),
                                      ('deployment', 60), ('star-history', 60), ('plates', 60), ('history', 60)]],
              dict(name='fonts', script='check_fonts_browser.cjs', seconds=90),
              dict(name='observatory', script='check_observatory_browser.cjs', seconds=90),
              dict(name='scoreboard', script='check_scoreboard_browser.cjs', seconds=90),
              dict(name='exhibition', script='check_exhibition_browser.cjs', seconds=90),
              dict(name='jars', script='check_jar_browser.cjs', seconds=90)]
    for index, start in enumerate(range(0, len(ids), CHUNK_SIZE)):
        suites.append(dict(name=f'artwork-{index}', script='check_artwork_browser.cjs',
                           args=[str(index)], seconds=60, ids=ids[start:start + CHUNK_SIZE],
                           captureIds=[i for i in ids[start:start + CHUNK_SIZE] if i in capture_ids]))
    # Includes process-group cleanup and report writes after every potential timeout.
    minutes = math.ceil(sum(s['seconds'] + 5 for s in suites) / 60) + 1
    return dict(sourceSha=catalog['source_sha'], artworkIds=ids, captureIds=capture_ids,
                mode=mode, comparison=comparison, suites=suites,
                timeout_minutes=minutes)


def run_suite(suite, output, command=None, cwd=ROOT):
    started = time.monotonic()
    result = dict(name=suite['name'], limitSeconds=suite['seconds'], status='failed')
    argv = command or ['node', str(ROOT / 'scripts' / suite['script']), *suite.get('args', [])]
    env = dict(os.environ, JAR_PAGE='index.html', BROWSER_SUITE=suite['name'],
               BROWSER_TIMING_FILE=str(output.resolve() / (suite['name'] + '-timings.json')))
    if suite.get('capturePlan'):
        env.update(BROWSER_CAPTURE_PLAN=suite['capturePlan'], SITE_SOURCE_SHA=suite['sourceSha'])
    if command is None:
        argv[1:1] = ['--require', str(ROOT / 'scripts/browser_timings.cjs')]
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


def valid_png(output, capture):
    file = output / capture['file']
    blob = file.read_bytes()
    return (len(blob) >= 24 and blob[:8] == b'\x89PNG\r\n\x1a\n'
            and len(blob) == capture['bytes']
            and hashlib.sha256(blob).hexdigest() == capture['sha256']
            and struct.unpack('>II', blob[16:24]) == (capture['width'], capture['height']))


def execute(plan, output, runner=run_suite):
    output.mkdir(parents=True, exist_ok=True)
    # Entire evidence set belongs to this invocation; server.log is live and
    # owned by the caller. A selective rerun cannot retain old full-run PNGs.
    for artifact in output.iterdir():
        if artifact.is_file() and artifact.suffix in {'.png', '.json', '.log'} and artifact.name != 'server.log':
            artifact.unlink()
    capture_plan = dict(sourceSha=plan['sourceSha'], mode=plan['mode'], captureIds=plan['captureIds'],
                        planId=uuid.uuid4().hex, prHeadSha=os.environ.get('PR_HEAD_SHA'))
    plan_path = output.resolve() / 'capture-plan.json'
    plan_path.write_text(json.dumps(capture_plan, indent=2) + '\n')
    for suite in plan['suites']:
        suite.update(capturePlan=str(plan_path), sourceSha=plan['sourceSha'])
    report = dict(status='running', sourceSha=plan['sourceSha'],
                  prHeadSha=os.environ.get('PR_HEAD_SHA'), expectedArtworkIds=plan['artworkIds'],
                  expectedCaptureIds=plan['captureIds'], mode=plan['mode'], comparison=plan['comparison'], suites=[])
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
                        or capture['planId'] != capture_plan['planId']
                        or capture['prHeadSha'] != capture_plan['prHeadSha']
                        or capture['expectedCaptureIds'] != suite['captureIds']
                        or capture['expectedIds'] != suite['ids']
                        or [p['id'] for p in capture['projects']] != suite['ids']
                        or [s['file'] for s in capture['screenshots']] != [f'specimen-{i}.png' for i in suite['captureIds']]
                        or not all(valid_png(output, image) for image in capture['screenshots'])):
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
    parser.add_argument('--base', default=os.environ.get('BROWSER_BASE_SHA'), help='Exact base commit for conservative capture selection')
    parser.add_argument('--full-capture', action='store_true', help='Retain every review capture')
    parser.add_argument('--suite', action='append', help='Run named groups for diagnosis; report is partial and cannot pass aggregate coverage')
    parser.add_argument('--plan', action='store_true', help='Write the workflow step budget without launching browsers')
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'tmp/site/catalog.json').read_text())
    plan = make_plan(catalog, None if args.full_capture else impact(args.base))
    if args.suite:
        names = {s['name'] for s in plan['suites']}
        if not set(args.suite).issubset(names):
            parser.error('Unknown suite')
        plan['suites'] = [s for s in plan['suites'] if s['name'] in args.suite]
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
    if args.suite:
        report['status'] = 'partial' if report['status'] == 'passed' else report['status']
        (ROOT / 'tmp/site-qa/browser-suites.json').write_text(json.dumps(report, indent=2) + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write('\n## Browser suites\n\n' + report['status'] + '\n\n')
            for suite in report['suites']:
                out.write(f"- {suite['name']}: {suite['status']} ({suite['elapsedSeconds']}s)\n")
            out.write(f"\nExpected artwork coverage: {len(plan['artworkIds'])} canonical projects. See browser-suites.json and per-chunk manifests.\n")
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
