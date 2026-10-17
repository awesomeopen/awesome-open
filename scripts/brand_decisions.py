#!/usr/bin/env python3
"""Validate brand decisions offline and build an untracked, deterministic overview."""
import argparse
from dataclasses import dataclass
from datetime import date
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = 'brand/decisions.md'
RECORD_DIR = 'brand/decisions'
ID_RE = re.compile(r'B-PR([1-9][0-9]*)-([0-9]{2,})\Z')
MENTION_RE = re.compile(r'(?<![\w#])(?:B-PR[0-9]+-[0-9]+|B[0-9]+)(?!\w)')
LINK_RE = re.compile(r'''!?\[([^\]\n]*)\]\(<?((?:[^\s()<>]|\([^\s()<>]*\))+)>?(?:\s+(?:"[^"\n]*"|'[^'\n]*'|\([^\n)]*\)))?\)''')
REFERENCE_LINK_RE = re.compile(r'^ {0,3}\[([^\]\n]+)\]:\s*<?([^\s>]+)>?', re.MULTILINE)
STATUSES = {'proposed', 'accepted', 'implemented', 'rejected', 'unresolved'}
TYPES = {'design', 'artwork', 'content', 'evidence', 'workflow'}
FIELDS = {'id', 'title', 'date', 'status', 'type', 'supersedes'}
EXCLUDED_DOCS = {'site/DESIGN.md', 'site/design_plan.md'}


@dataclass(frozen=True)
class Decision:
    id: str
    title: str
    date: str
    status: str
    type: str
    supersedes: tuple
    path: str
    body: str = ''


def id_key(identifier):
    match = ID_RE.fullmatch(identifier)
    if match:
        return (1, int(match[1]), int(match[2]))
    return (0, int(identifier[1:]), 0)


def valid_id(identifier):
    match = ID_RE.fullmatch(identifier) if isinstance(identifier, str) else None
    return bool(match and int(match[2]) > 0 and match[2] == f'{int(match[2]):02d}')


def safe_file(root, relative):
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Unsafe decision/document path: {relative}')
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate metadata key: {key}')
        result[key] = value
    return result


def parse_record(text, path):
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError(f'{path}: expected JSON front matter between --- lines')
    front, body = text[4:].split('\n---\n', 1)
    metadata = json.loads(front, object_pairs_hook=unique_object)
    if not isinstance(metadata, dict) or metadata.keys() != FIELDS:
        raise ValueError(f'{path}: metadata must have exactly {sorted(FIELDS)}')
    for field in FIELDS - {'supersedes'}:
        if not isinstance(metadata[field], str) or not metadata[field].strip():
            raise ValueError(f'{path}: {field} must be a nonempty string')
        if '\n' in metadata[field] or '\r' in metadata[field]:
            raise ValueError(f'{path}: {field} must fit on one line')
    identifier = metadata['id']
    if not valid_id(identifier) or Path(path).name != identifier + '.md':
        raise ValueError(f'{path}: invalid ID or filename/ID mismatch: {identifier}')
    if date.fromisoformat(metadata['date']).isoformat() != metadata['date']:
        raise ValueError(f'{path}: date must be YYYY-MM-DD')
    if metadata['status'] not in STATUSES or metadata['type'] not in TYPES:
        raise ValueError(f'{path}: unsupported status or type')
    supersedes = metadata['supersedes']
    if (not isinstance(supersedes, list) or
            any(not isinstance(item, str) for item in supersedes) or
            len(set(supersedes)) != len(supersedes)):
        raise ValueError(f'{path}: supersedes must be a list of distinct ID strings')
    if not body.strip():
        raise ValueError(f'{path}: decision rationale and evidence are required')
    return Decision(**{**metadata, 'supersedes': tuple(supersedes)}, path=path, body=body)


def load_decisions(root):
    legacy = safe_file(root, LEGACY_PATH).read_bytes()
    decisions = {}
    for line in legacy.decode('utf-8').splitlines():
        if not re.match(r'^\s*\|?\s*`?(?:B[0-9]+|B-PR[0-9]+-[0-9]+)`?\s*\|', line):
            continue
        fields = line.strip().strip('|').split('|', 3)
        if len(fields) != 4:
            raise ValueError('Malformed legacy decision row')
        identifier, day, status, body = (field.strip() for field in fields)
        identifier = identifier.strip('`')
        if identifier in decisions:
            raise ValueError(f'Duplicate decision ID: {identifier}')
        decisions[identifier] = Decision(identifier, body, day, status, 'legacy', (), LEGACY_PATH)
    if set(decisions) != {f'B{number:02d}' for number in range(1, 45)}:
        raise ValueError('Legacy register must contain exactly B01–B44; use PR-scoped IDs for additions')
    directory = safe_file(root, RECORD_DIR)
    if not directory.is_dir():
        raise ValueError(f'Missing decision directory: {RECORD_DIR}')
    for path in sorted(directory.iterdir()):
        relative = path.relative_to(root).as_posix()
        safe_file(root, relative)
        if not path.is_file() or path.suffix != '.md':
            raise ValueError(f'Unexpected decision path: {relative}')
        decision = parse_record(path.read_text(encoding='utf-8'), relative)
        if decision.id in decisions:
            raise ValueError(f'Duplicate decision ID: {decision.id}')
        decisions[decision.id] = decision
    return decisions


def without_fences(text):
    # Examples in fenced blocks are not live citations. Inline code still is.
    output, fence = [], None
    for line in text.splitlines():
        match = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            output.append('')
        elif fence is None:
            output.append(line)
    return '\n'.join(output)


def anchors(text):
    result = set()
    text = without_comments(without_fences(text))
    if text.startswith('---\n') and '\n---\n' in text[4:]:
        text = text[4:].split('\n---\n', 1)[1]
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r'^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$', line)
        title = match[1] if match else None
        if (not match and index and lines[index - 1].strip() and
                re.fullmatch(r' {0,3}(?:=+|-+)\s*', line)):
            title = lines[index - 1].strip()
        if title is not None:
            title = LINK_RE.sub(lambda item: item[1], title)
            title = html.unescape(re.sub(r'<[^>]*>', '', title)).lower()
            slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
            candidate, count = slug, 0
            while candidate in result:
                count += 1
                candidate = f'{slug}-{count}'
            result.add(candidate)
    actual_html = re.sub(r'(`+)(.*?)\1', '', text)

    class AnchorParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            result.update(value for key, value in attrs if value is not None and
                          (key == 'id' or tag == 'a' and key == 'name'))

    AnchorParser().feed(actual_html)
    return result


def without_comments(text):
    # Preserve comment-looking text that is visibly quoted as inline code.
    return re.sub(r'(`+)(.*?)\1|<!--.*?-->',
                  lambda match: match[0] if match[1] else '', text, flags=re.DOTALL)


def authored_docs(root):
    paths = {root / 'AGENTS.md', root / 'CONTRIBUTING.md', root / '.github/pull_request_template.md'}
    for directory in ('brand', 'site', '.agents/skills/awesome-open-brand'):
        paths.update((root / directory).rglob('*.md'))
    return sorted(path for path in paths if path.is_file() and
                  path.relative_to(root).as_posix() not in EXCLUDED_DOCS and
                  not path.relative_to(root).as_posix().startswith('brand/archive/'))


def reference_errors(root, decisions):
    errors = []
    for path in authored_docs(root):
        relative = path.relative_to(root).as_posix()
        safe_file(root, relative)
        text = without_fences(path.read_text(encoding='utf-8'))
        if relative.startswith(RECORD_DIR + '/'):
            text = without_fences(decisions[path.stem].body)
        text = without_comments(text)
        # Inline code may demonstrate Markdown syntax; it is not a rendered link.
        link_text = re.sub(r'(`+)(.*?)\1', '', text)
        for match in list(LINK_RE.finditer(link_text)) + list(REFERENCE_LINK_RE.finditer(link_text)):
            target = urlsplit(match[2])
            if target.scheme or target.netloc:
                continue
            local = unquote(target.path)
            linked = path.parent / local if local else path
            if local.startswith('/'):
                linked = root / local.lstrip('/')
            if not linked.resolve().is_relative_to(root.resolve()) or not linked.exists():
                errors.append(f'{relative}: broken local link: {match[2]}')
            elif target.fragment and linked.suffix.lower() in {'.md', '.html'}:
                if unquote(target.fragment) not in anchors(linked.read_text(encoding='utf-8')):
                    errors.append(f'{relative}: missing local anchor: {match[2]}')
        # Check live prose/inline code but not destinations or raw external URLs.
        prose = LINK_RE.sub(lambda match: match[1], text)
        prose = REFERENCE_LINK_RE.sub(lambda match: match[1], prose)
        prose = re.sub(r'(?:https?://|mailto:)\S+', '', prose)
        for identifier in sorted(set(MENTION_RE.findall(prose))):
            if identifier not in decisions:
                errors.append(f'{relative}: unknown decision reference: {identifier}')
    return errors


def supersession_errors(decisions):
    errors = []
    for decision in decisions.values():
        for target in decision.supersedes:
            if target not in decisions:
                errors.append(f'{decision.id}: unknown supersedes target: {target}')
            elif target == decision.id:
                errors.append(f'{decision.id}: cannot supersede itself')
    visiting, visited = set(), set()

    def visit(identifier):
        if identifier in visiting:
            errors.append(f'Supersession cycle at {identifier}')
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        for target in decisions[identifier].supersedes:
            if target in decisions:
                visit(target)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in decisions:
        visit(identifier)
    return errors


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def history_errors(root, decisions, base, pr_number=None):
    # Resolve first: user-supplied refs never become Git options or pathspecs.
    sha = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}')
    files = git(root, 'ls-tree', '-r', '--name-only', sha, '--', RECORD_DIR).splitlines()
    errors, existing = [], set()
    prior_legacy = git(root, 'show', f'{sha}:{LEGACY_PATH}')
    current_legacy = safe_file(root, LEGACY_PATH).read_text(encoding='utf-8')
    for anchor in sorted(anchors(prior_legacy) - anchors(current_legacy)):
        errors.append(f'Existing legacy heading anchor cannot be removed: #{anchor}')
    for path in files:
        prior = parse_record(git(root, 'show', f'{sha}:{path}') + '\n', path)
        existing.add(prior.id)
        current = decisions.get(prior.id)
        if current is None or current.path != path:
            errors.append(f'Existing decision ID/path cannot be removed or renamed: {prior.id} ({path})')
    if pr_number is not None:
        for decision in decisions.values():
            if decision.type != 'legacy' and decision.id not in existing:
                if int(ID_RE.fullmatch(decision.id)[1]) != pr_number:
                    errors.append(f'{decision.id}: new record must use this PR number ({pr_number})')
    return errors


def validate(root=ROOT, base=None, pr_number=None):
    decisions = load_decisions(root)
    errors = supersession_errors(decisions) + reference_errors(root, decisions)
    if pr_number is not None and (type(pr_number) is not int or pr_number <= 0 or base is None):
        errors.append('A positive PR number requires an actual base revision')
    elif base:
        errors.extend(history_errors(root, decisions, base, pr_number))
    if errors:
        raise ValueError('\n'.join(errors))
    return decisions


def render(decisions, source_ref):
    if not re.fullmatch(r'[0-9a-f]{40}', source_ref):
        raise ValueError('Overview source ref must be a full commit SHA')
    prefix = f'https://github.com/awesomeopen/awesome-open/blob/{source_ref}/'
    lines = ['# Brand decision overview', '',
             'Generated from the legacy register and individual records. Do not edit or commit this output.',
             f'Source revision: `{source_ref}`. Status is recorded evidence, not inferred approval.', '',
             '| ID | Date | Status | Type | Decision | Supersession declared by |',
             '| --- | --- | --- | --- | --- | --- |']
    for identifier in sorted(decisions, key=id_key):
        decision = decisions[identifier]
        title = decision.title
        if decision.type == 'legacy':
            def absolute(match):
                target = urlsplit(match[2])
                if target.scheme or target.netloc:
                    return match[0]
                # Legacy links are relative to brand/decisions.md.
                import posixpath
                path = posixpath.normpath(posixpath.join('brand', target.path))
                return f'[{match[1]}]({prefix}{path}' + (f'#{target.fragment}' if target.fragment else '') + ')'
            title = LINK_RE.sub(absolute, title)
        title = title.replace('|', '&#124;').replace('\n', ' ')
        replacements = [item for item in decisions.values() if identifier in item.supersedes]
        links = ', '.join(f'[{item.id}]({prefix}{item.path}) ({item.status})'
                          for item in sorted(replacements, key=lambda item: id_key(item.id))) or '—'
        lines.append(f'| [{identifier}]({prefix}{decision.path}) | {decision.date} | '
                     f'{decision.status} | {decision.type} | {title} | {links} |')
    lines += ['', 'Supersession declarations retain the replacement record’s status. A proposed',
              'replacement does not automatically retire its target; competing replacements need review.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Verified PR base for stable-ID history checks')
    parser.add_argument('--pr-number', type=int, help='Namespace for records new to this PR (requires --base)')
    parser.add_argument('--output', type=Path, help='Generate an overview under ignored tmp/')
    parser.add_argument('--source-ref', help='Full commit SHA for portable overview links; defaults to HEAD')
    parser.add_argument('--check', action='store_true', help='Check output bytes without writing (requires --output)')
    args = parser.parse_args(argv)
    decisions = validate(ROOT, args.base, args.pr_number)
    if args.check and args.output is None:
        raise ValueError('--check requires --output')
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        temporary = ROOT / 'tmp'
        if (temporary.is_symlink() or not temporary.resolve().is_relative_to(ROOT.resolve()) or
                not output.resolve().is_relative_to(temporary.resolve()) or output.is_symlink()):
            raise ValueError('Generated overview must stay under ignored tmp/')
        content = render(decisions, args.source_ref or git(ROOT, 'rev-parse', 'HEAD'))
        if args.check:
            if not output.is_file() or output.read_text(encoding='utf-8') != content:
                raise ValueError(f'Missing or stale generated overview: {args.output}')
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding='utf-8')
    print(f'Brand decisions OK: {len(decisions)} records (44 legacy).')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Brand decisions failed: {exc}', file=sys.stderr)
        sys.exit(1)
