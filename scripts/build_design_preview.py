#!/usr/bin/env python3
"""Build a private design-review bundle from a clean, identified Git revision."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='tmp/design-preview')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    # Never allow a build destination to overwrite tracked source directories.
    protected = [ROOT / p for p in ('site', 'scripts', 'data', '.git', '.github')]
    if output == ROOT or ROOT.is_relative_to(output) or any(output == p or p in output.parents for p in protected):
        parser.error('Choose an output outside source directories, such as tmp/design-preview.')
    if output.exists() and any(output.iterdir()):
        parser.error('Use an empty output directory so stale files cannot enter the preview.')
    if git('status', '--porcelain', '--untracked-files=normal'):
        parser.error('Commit or set aside source changes first; the preview must match its Git SHA.')
    sha = git('rev-parse', 'HEAD')
    subprocess.run(['python3', str(ROOT / 'scripts/build_site.py'), '--output', str(output), '--source-sha', sha, '--production'], cwd=ROOT, check=True)
    from build_exhibition_preview import build as build_exhibition
    build_exhibition(output)
    from build_jar_preview import build as build_jars
    build_jars(output)
    design = output / 'design'
    shutil.copytree(ROOT / 'site/design', design, dirs_exist_ok=True)
    shutil.copyfile(ROOT / 'site/FUNCTION-SUMMARIES.md', design / 'FUNCTION-SUMMARIES.md')
    guide = (ROOT / 'site/RETRO-SCRAPERISM.md').read_text()
    guide = guide.replace('(design/index.html)', '(index.html)').replace('(design/tokens.css)', '(tokens.css)')
    guide = guide.replace('(PREVIEW.md)', f'(https://github.com/awesomeopen/awesome-open/blob/{sha}/site/PREVIEW.md)')
    (design / 'style-guide.md').write_text(guide, encoding='utf-8')
    index = design / 'index.html'
    index.write_text(index.read_text().replace('__SOURCE_SHA__', sha), encoding='utf-8')
    metadata = {'repository': 'awesomeopen/awesome-open', 'source_sha': sha, 'design_system': 'Retro-Scraperism', 'design_system_version': '0.1', 'status': 'proposal'}
    (output / 'preview.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(f'Design preview: {output}/design/\nGitHub source: {sha}')


if __name__ == '__main__':
    main()
