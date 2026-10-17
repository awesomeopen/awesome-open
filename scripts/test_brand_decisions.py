"""Offline decision identity, references, history and generated-artifact checks."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import brand_decisions as decisions


ROOT = Path(__file__).resolve().parents[1]
LEGACY_BYTES = (ROOT / decisions.LEGACY_PATH).read_bytes()
SOURCE_SHA = 'a' * 40


def record_text(identifier='B-PR100-01', body=None, **overrides):
    metadata = {
        'id': identifier,
        'title': 'Keep decision identifiers stable',
        'date': '2026-10-16',
        'status': 'proposed',
        'type': 'workflow',
        'supersedes': [],
    }
    metadata.update(overrides)
    if body is None:
        body = '# Stable decision identifiers\n\nRationale and evidence refer to B44.\n'
    return '---\n' + json.dumps(metadata, indent=2) + '\n---\n' + body


class DecisionFixture(unittest.TestCase):
    """Use the exact legacy capture plus minimal local link destinations."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write(decisions.LEGACY_PATH, LEGACY_BYTES)
        (self.root / decisions.RECORD_DIR).mkdir()
        self.write('AGENTS.md', '# Agent guide\n')
        self.write('CONTRIBUTING.md', '# Contributions\n')
        self.write('brand/README.md', '# Brand reference\n')
        self.write('.github/pull_request_template.md', '# Review\n')
        # Legacy links remain intact; no full site build or remote access is needed.
        for match in decisions.LINK_RE.finditer(LEGACY_BYTES.decode('utf-8')):
            target = urlsplit(match[2])
            if target.scheme or target.netloc or not target.path:
                continue
            path = (self.root / 'brand' / unquote(target.path)).resolve()
            self.assertTrue(path.is_relative_to(self.root))
            if not path.exists():
                self.write(path.relative_to(self.root), '# Fixture source\n')
            if target.fragment:
                with path.open('a', encoding='utf-8') as stream:
                    stream.write(f'\n<a id="{unquote(target.fragment)}"></a>\n')

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding='utf-8')
        return path

    def add_record(self, identifier='B-PR100-01', body=None, **metadata):
        return self.write(f'{decisions.RECORD_DIR}/{identifier}.md',
                          record_text(identifier, body=body, **metadata))

    def all_records(self):
        return decisions.load_decisions(self.root)

    def assert_invalid(self, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            decisions.validate(self.root)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix():
                (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.root.rglob('*') if path.is_file()}

    def prepare_cli(self):
        target = self.root / 'scripts/brand_decisions.py'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'scripts/brand_decisions.py', target)
        return target

    def cli(self, *arguments):
        script = self.root / 'scripts/brand_decisions.py'
        return subprocess.run([sys.executable, '-B', str(script), *arguments],
                              cwd=self.root, capture_output=True, text=True, timeout=20)

    def init_git(self):
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Decision fixture', '-c',
                 'user.email=decision-fixture@example.invalid', 'commit', '-qm', 'Fixture base')
        return self.git('rev-parse', 'HEAD')

    def git(self, *arguments):
        return subprocess.check_output(['git', *arguments], cwd=self.root,
                                       text=True, stderr=subprocess.STDOUT).strip()


class LegacyTests(DecisionFixture):
    def test_exact_legacy_capture_has_all_separated_table_rows(self):
        records = decisions.validate(self.root)
        self.assertEqual(set(records), {f'B{n:02d}' for n in range(1, 45)})
        self.assertEqual((self.root / decisions.LEGACY_PATH).read_bytes(), LEGACY_BYTES)
        self.assertIn('Fraunces', records['B12'].title)
        self.assertIn('/draws/', records['B44'].title)
        self.assertTrue(all(item.type == 'legacy' for item in records.values()))

    def test_duplicate_legacy_id_is_reported_explicitly(self):
        row = next(line for line in LEGACY_BYTES.splitlines() if line.startswith(b'| B01 |'))
        self.write(decisions.LEGACY_PATH, LEGACY_BYTES + b'\n' + row + b'\n')
        self.assert_invalid('Duplicate decision ID: B01')

    def test_legacy_row_formatting_cannot_hide_duplicate_ids(self):
        rows = (
            '|B01|2026-10-16|Proposed|Duplicate record.|',
            '|  B01  | 2026-10-16 | Proposed | Duplicate record. |',
            'B01 | 2026-10-16 | Proposed | Duplicate record.',
            '| `B01` | 2026-10-16 | Proposed | Duplicate record. |',
        )
        for row in rows:
            with self.subTest(row=row):
                self.write(decisions.LEGACY_PATH,
                           LEGACY_BYTES + b'\n' + row.encode('utf-8') + b'\n')
                self.assert_invalid('Duplicate decision ID: B01')

    def test_pr_scoped_records_cannot_be_added_to_shared_legacy_table(self):
        self.write(decisions.LEGACY_PATH, LEGACY_BYTES +
                   b'\n| B-PR101-01 | 2026-10-16 | Proposed | Use an individual file. |\n')
        self.assert_invalid('Legacy register must contain exactly B01')

    def test_missing_legacy_id_is_rejected(self):
        self.write(decisions.LEGACY_PATH,
                   b'\n'.join(line for line in LEGACY_BYTES.splitlines()
                              if not line.startswith(b'| B44 |')) + b'\n')
        self.assert_invalid('exactly B01')

    def test_new_global_legacy_number_is_rejected(self):
        self.write(decisions.LEGACY_PATH, LEGACY_BYTES +
                   b'\n| B45 | 2026-10-16 | Proposed | Do not allocate globally. |\n')
        self.assert_invalid('use PR-scoped IDs')

    def test_legitimate_legacy_evidence_correction_is_allowed(self):
        corrected = LEGACY_BYTES.replace(b'Fixed specimen concept;',
                                        b'Fixed specimen concept (evidence clarified);', 1)
        self.write(decisions.LEGACY_PATH, corrected)
        records = decisions.validate(self.root)
        self.assertIn('(evidence clarified)', records['B01'].title)
        self.assertEqual((self.root / decisions.LEGACY_PATH).read_bytes(), corrected)

    def test_legacy_id_is_not_allowed_as_an_individual_record(self):
        self.add_record('B44')
        self.assert_invalid('invalid ID or filename/ID mismatch')


class RecordTests(DecisionFixture):
    def test_canonical_ids_and_unbounded_numeric_ordinal(self):
        for identifier in ('B-PR1-01', 'B-PR100-02', 'B-PR100-99', 'B-PR100-100'):
            with self.subTest(identifier=identifier):
                self.assertTrue(decisions.valid_id(identifier))
                self.add_record(identifier)
        self.assertEqual(len(decisions.validate(self.root)), 48)

    def test_invalid_ids_padding_case_and_types(self):
        invalid = ('B-PR0-01', 'B-PR01-01', 'B-PR-1-01', 'B-PR1-0', 'B-PR1-00',
                   'B-PR1-1', 'B-PR1-001', 'B-PR1-010', 'B-PR1-0100', 'B-PR1-+1',
                   'B-PR1-01 ', ' B-PR1-01', 'B-PR1-01\n', 'b-pr1-01', 'B-pr1-01',
                   'B–PR1–01', 'B01', '', None, 100, True, ['B-PR1-01'])
        for identifier in invalid:
            with self.subTest(identifier=identifier):
                self.assertFalse(decisions.valid_id(identifier))

    def test_filename_must_match_metadata_id(self):
        self.write('brand/decisions/B-PR100-02.md', record_text('B-PR100-01'))
        self.assert_invalid('filename/ID mismatch')

    def test_metadata_schema_rejects_missing_unknown_and_nondict(self):
        valid = json.loads(record_text().split('---\n')[1])
        cases = [[], None, dict(valid, extra='typo')]
        for key in valid:
            cases.append({name: value for name, value in valid.items() if name != key})
        for metadata in cases:
            with self.subTest(metadata=metadata):
                text = '---\n' + json.dumps(metadata) + '\n---\nRationale.\n'
                with self.assertRaisesRegex(ValueError, 'metadata must have exactly'):
                    decisions.parse_record(text, 'brand/decisions/B-PR100-01.md')

    def test_duplicate_json_metadata_keys_are_rejected(self):
        text = record_text().replace('"id": "B-PR100-01",',
                                     '"id": "B-PR100-01", "id": "B-PR100-01",')
        with self.assertRaisesRegex(ValueError, 'Duplicate metadata key: id'):
            decisions.parse_record(text, 'brand/decisions/B-PR100-01.md')

    def test_scalar_metadata_requires_nonempty_single_line_strings(self):
        for field in ('id', 'title', 'date', 'status', 'type'):
            for value in (None, True, 1, [], {}, '', '  ', 'bad\nvalue', 'bad\rvalue'):
                with self.subTest(field=field, value=value):
                    text = record_text(**{field: value})
                    with self.assertRaises(ValueError):
                        decisions.parse_record(text, 'brand/decisions/B-PR100-01.md')

    def test_dates_are_real_canonical_calendar_dates(self):
        for day in ('2026-02-29', '2026-13-01', '2026-10-32', '20261016',
                    '2026-W42-5', '2026-10-16T00:00:00', '2026-1-1'):
            with self.subTest(day=day), self.assertRaises(ValueError):
                decisions.parse_record(record_text(date=day), 'brand/decisions/B-PR100-01.md')
        decision = decisions.parse_record(record_text(date='2024-02-29'),
                                          'brand/decisions/B-PR100-01.md')
        self.assertEqual(decision.date, '2024-02-29')

    def test_status_and_type_use_documented_vocabulary(self):
        for status in sorted(decisions.STATUSES):
            self.assertEqual(decisions.parse_record(record_text(status=status),
                                                    'brand/decisions/B-PR100-01.md').status, status)
        for kind in sorted(decisions.TYPES):
            self.assertEqual(decisions.parse_record(record_text(type=kind),
                                                    'brand/decisions/B-PR100-01.md').type, kind)
        for override in ({'status': 'approved'}, {'status': 'Proposed'}, {'type': 'legacy'},
                         {'type': 'workflows'}):
            with self.subTest(override=override), self.assertRaisesRegex(ValueError, 'unsupported'):
                decisions.parse_record(record_text(**override), 'brand/decisions/B-PR100-01.md')

    def test_supersedes_requires_distinct_strings_in_a_list(self):
        for value in (None, 'B44', {}, [1], [True], [['B44']], ['B44', 'B44']):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'distinct ID strings'):
                decisions.parse_record(record_text(supersedes=value),
                                       'brand/decisions/B-PR100-01.md')

    def test_front_matter_and_nonempty_rationale_are_required(self):
        for text in ('# Missing metadata\n', '---\n{}\n',
                     record_text().replace('---\n', '--- \n', 1),
                     record_text(body=''), record_text(body=' \n\t')):
            with self.subTest(text=text[:50]), self.assertRaises(ValueError):
                decisions.parse_record(text, 'brand/decisions/B-PR100-01.md')

    def test_unexpected_nested_directory_and_nonmarkdown_files_are_rejected(self):
        for name in ('README.txt', 'B-PR100-01.MD', 'nested/B-PR100-01.md'):
            with self.subTest(name=name):
                path = self.write('brand/decisions/' + name, record_text())
                self.assert_invalid('Unexpected decision path')
                path.unlink()
                if path.parent.name == 'nested':
                    path.parent.rmdir()

    def test_missing_record_directory_is_rejected(self):
        (self.root / decisions.RECORD_DIR).rmdir()
        self.assert_invalid('Missing decision directory')

    def test_record_symlink_is_rejected_even_within_root(self):
        self.write('target.md', record_text())
        (self.root / decisions.RECORD_DIR / 'B-PR100-01.md').symlink_to(self.root / 'target.md')
        self.assert_invalid('Unsafe decision/document path')

    def test_records_directory_symlink_is_rejected(self):
        (self.root / decisions.RECORD_DIR).rmdir()
        (self.root / 'other-records').mkdir()
        (self.root / decisions.RECORD_DIR).symlink_to(self.root / 'other-records',
                                                   target_is_directory=True)
        self.assert_invalid('Unsafe decision/document path')


class ReferenceTests(DecisionFixture):
    def test_current_prose_inline_code_and_link_labels_check_references(self):
        for prose in ('See B999.', 'See `B-PR999-01`.',
                      '[B999](https://example.invalid/anything)', 'B999\'s replacement.'):
            with self.subTest(prose=prose):
                self.write('brand/README.md', prose)
                self.assert_invalid('unknown decision reference')

    def test_known_punctuation_ranges_and_pairs_are_valid(self):
        self.add_record()
        self.write('brand/README.md', 'B01/B02, (B13–B15), B29\'s guide; `B-PR100-01`.')
        decisions.validate(self.root)

    def test_unknown_second_citation_in_slash_pairs_is_rejected(self):
        for prose in ('B01/B999', 'B01/B-PR999-01'):
            with self.subTest(prose=prose):
                self.write('brand/README.md', prose)
                self.assert_invalid('unknown decision reference')

    def test_unknown_range_endpoint_is_rejected(self):
        for prose in ('See B01–B999.', 'See B01-B999.'):
            with self.subTest(prose=prose):
                self.write('brand/README.md', prose)
                self.assert_invalid('unknown decision reference: B999')

    def test_archives_pinned_skills_and_historical_designs_are_not_live_citations(self):
        paths = ('brand/archive/original.md', '.agents/skills/retro-scraperism/SKILL.md',
                 '.agents/skills/speculative-fossoligy/SKILL.md',
                 'site/DESIGN.md', 'site/design_plan.md')
        for path in paths:
            self.write(path, '# Historical B999\n[Missing](never-present.md#absent)\n')
        decisions.validate(self.root)

    def test_project_skill_and_pr_template_are_live_reference_sources(self):
        for path in ('.agents/skills/awesome-open-brand/SKILL.md',
                     '.github/pull_request_template.md', 'AGENTS.md', 'CONTRIBUTING.md'):
            with self.subTest(path=path):
                self.write(path, 'Follow B999.\n')
                self.assert_invalid('unknown decision reference: B999')
                self.write(path, '# Current guide\n')

    def test_external_destinations_raw_urls_colors_and_embedded_strings_are_ignored(self):
        self.write('brand/README.md', '''# Valid references
Use #B62420, #0B2546 and variableB999suffix.
[External](https://example.invalid/B999/B-PR999-01#B888)
https://example.invalid/B777?ref=B-PR777-01
mailto:B666@example.invalid
[Other external](//example.invalid/B555)
[Email](mailto:B444@example.invalid)
The format is B-PR<number>-<ordinal>.
''')
        decisions.validate(self.root)

    def test_fenced_examples_are_ignored_but_inline_code_is_checked(self):
        self.write('brand/README.md', '''# Examples
```markdown
B999 and [missing](missing.md#ghost)
```
~~~markdown
B-PR999-01
~~~
````markdown
```
B888
```
````
See B44.
''')
        decisions.validate(self.root)
        self.write('brand/README.md', '`B999` is still a live citation.\n')
        self.assert_invalid('unknown decision reference: B999')

    def test_unknown_local_file_and_fragment_are_rejected(self):
        for text, error in (('[Guide](missing.md)', 'broken local link'),
                            ('[Guide](../site/OBSERVATORY.md#missing)', 'missing local anchor')):
            with self.subTest(text=text):
                self.write('brand/README.md', text)
                self.assert_invalid(error)

    def test_single_quoted_markdown_link_title_does_not_hide_missing_target(self):
        self.write('brand/README.md', "[Evidence](missing.md 'Evidence title')\n")
        self.assert_invalid('broken local link: missing.md')

    def test_reference_style_local_link_targets_and_fragments_are_checked(self):
        for text, error in (('[Guide][source]\n[source]: missing.md\n', 'broken local link'),
                            ('[Guide][source]\n[source]: ../site/OBSERVATORY.md#ghost\n',
                             'missing local anchor')):
            with self.subTest(text=text):
                self.write('brand/README.md', text)
                self.assert_invalid(error)
        self.write('brand/README.md', '[Guide][source]\n[source]: ../site/OBSERVATORY.md#accounting\n')
        decisions.validate(self.root)

    def test_reference_style_external_urls_are_not_live_decision_citations(self):
        self.write('brand/README.md', '[Evidence][source]\n'
                   '[source]: https://example.invalid/B999/B-PR999-01 "External source"\n')
        decisions.validate(self.root)

    def test_inline_code_markdown_links_are_examples_but_real_links_still_checked(self):
        self.write('brand/README.md', 'Example: `[text](missing.md#ghost)`.\n')
        decisions.validate(self.root)
        self.write('brand/README.md', 'Example: `[text](missing.md#ghost)`. '
                   '[Actual](other-missing.md)\n')
        self.assert_invalid('broken local link: other-missing.md')

    def test_fragment_only_root_relative_percent_encoded_and_html_links(self):
        self.write('site/local guide.md', '# Shared heading\n\n## Shared heading\n')
        self.write('site/local.html', '<section id="real-anchor">Content</section>\n')
        self.write('brand/README.md', '''# Brand reference
[Self](#brand-reference)
[Root](/site/local%20guide.md#shared-heading)
[Duplicate](../site/local%20guide.md#shared-heading-1)
[HTML](../site/local.html#real-anchor)
''')
        decisions.validate(self.root)

    def test_fragment_matching_uses_github_style_heading_slugs(self):
        text = '# A [linked](https://example.invalid/) &amp; `Code`!\n# Same\n# Same\n'
        self.assertTrue({'a-linked--code', 'same', 'same-1'}.issubset(decisions.anchors(text)))

    def test_duplicate_heading_suffixes_do_not_collide_with_literal_heading(self):
        self.assertEqual(decisions.anchors('# Foo\n# Foo\n# Foo-1\n'),
                         {'foo', 'foo-1', 'foo-1-1'})

    def test_setext_heading_supplies_a_real_local_fragment(self):
        self.write('site/example.md', 'Real Heading\n============\n\nSource evidence.\n')
        self.write('brand/README.md', '[Real heading](../site/example.md#real-heading)\n')
        decisions.validate(self.root)

    def test_html_anchor_inside_fence_cannot_satisfy_local_fragment(self):
        self.write('site/example.md', '```html\n<a id="ghost"></a>\n```\n')
        self.write('brand/README.md', '[Absent real heading](../site/example.md#ghost)\n')
        self.assert_invalid('missing local anchor')

    def test_html_anchor_inside_comment_cannot_satisfy_local_fragment(self):
        self.write('site/example.md', '<!-- <a id="ghost"></a> -->\n')
        self.write('brand/README.md', '[Absent real heading](../site/example.md#ghost)\n')
        self.assert_invalid('missing local anchor')

    def test_html_anchor_inside_inline_code_cannot_satisfy_local_fragment(self):
        self.write('site/example.md', '`<a id="ghost"></a>`\n')
        self.write('brand/README.md', '[Absent real heading](../site/example.md#ghost)\n')
        self.assert_invalid('missing local anchor')

    def test_html_anchor_attributes_are_parsed_as_attributes(self):
        self.assertEqual(decisions.anchors(
            '<span data-id="ghost" data-name="other">Example</span>\n'
            '<input name="field">\n<a name = "legacy"></a>\n'
            '<span ID = "actual">Example</span>\n'), {'legacy', 'actual'})

    def test_html_comments_are_not_live_decision_citations_or_local_links(self):
        self.write('brand/README.md', '# Current guide\n'
                   '<!-- B999 and [missing](missing.md) -->\n'
                   '<!--\nB-PR999-01\n[other missing](other-missing.md#ghost)\n-->\n'
                   'See B44.\n')
        decisions.validate(self.root)

    def test_local_link_cannot_escape_repository(self):
        self.write('brand/README.md', '[Outside](../../outside.md)\n')
        self.assert_invalid('broken local link')

    def test_references_in_decision_body_are_validated(self):
        self.add_record(body='# Decision\n\nEvidence depends on B999.\n')
        self.assert_invalid('unknown decision reference: B999')

    def test_decision_reference_before_body_horizontal_rule_is_not_discarded(self):
        self.add_record(body='# Decision\n\nEvidence depends on B999.\n\n---\n\nValid ending.\n')
        self.assert_invalid('unknown decision reference: B999')

    def test_local_link_before_body_horizontal_rule_is_not_discarded(self):
        self.add_record(body='# Decision\n\n[Evidence](missing-evidence.md)\n\n---\n\nValid ending.\n')
        self.assert_invalid('broken local link: missing-evidence.md')


class SupersessionTests(DecisionFixture):
    def test_new_record_can_supersede_legacy_without_rewriting_it(self):
        self.add_record(supersedes=['B44'])
        records = decisions.validate(self.root)
        self.assertEqual(records['B-PR100-01'].supersedes, ('B44',))
        self.assertEqual((self.root / decisions.LEGACY_PATH).read_bytes(), LEGACY_BYTES)
        self.assertEqual(records['B44'].status, 'User-directed; implemented for review')

    def test_unknown_target_self_link_and_multirecord_cycle_are_rejected(self):
        for targets, message in ((['B999'], 'unknown supersedes target'),
                                 (['B-PR100-01'], 'cannot supersede itself')):
            with self.subTest(targets=targets):
                self.add_record(supersedes=targets)
                self.assert_invalid(message)
        self.add_record('B-PR100-01', supersedes=['B-PR100-02'])
        self.add_record('B-PR100-02', supersedes=['B-PR101-01'])
        self.add_record('B-PR101-01', supersedes=['B-PR100-01'])
        self.assert_invalid('Supersession cycle')

    def test_acyclic_chain_and_competing_replacements_are_supported(self):
        self.add_record('B-PR100-01', supersedes=['B44'])
        self.add_record('B-PR101-01', supersedes=['B44'])
        self.add_record('B-PR102-01', supersedes=['B-PR100-01'])
        decisions.validate(self.root)

    def test_proposed_supersession_does_not_change_target_status(self):
        self.add_record(supersedes=['B44'], status='proposed')
        records = decisions.validate(self.root)
        overview = decisions.render(records, SOURCE_SHA)
        row = next(line for line in overview.splitlines() if line.startswith('| [B44]'))
        self.assertIn('| User-directed; implemented for review | legacy |', row)
        self.assertIn('B-PR100-01.md) (proposed)', row)
        self.assertIn('does not automatically retire its target', overview)


class OverviewTests(DecisionFixture):
    def test_numeric_sort_is_independent_of_filesystem_and_dict_order(self):
        for identifier in ('B-PR100-100', 'B-PR9-10', 'B-PR100-02', 'B-PR9-02'):
            self.add_record(identifier)
        records = decisions.validate(self.root)
        overview = decisions.render(records, SOURCE_SHA)
        reverse = dict(reversed(list(records.items())))
        self.assertEqual(overview, decisions.render(reverse, SOURCE_SHA))
        self.assertEqual(overview, decisions.render(records, SOURCE_SHA))
        ids = re.findall(r'^\| \[([^]]+)\]', overview, flags=re.MULTILINE)
        self.assertEqual(ids[:44], [f'B{n:02d}' for n in range(1, 45)])
        self.assertEqual(ids[44:], ['B-PR9-02', 'B-PR9-10', 'B-PR100-02', 'B-PR100-100'])

    def test_supersession_sort_is_also_numeric_and_deterministic(self):
        for identifier in ('B-PR100-01', 'B-PR9-10', 'B-PR9-02'):
            self.add_record(identifier, supersedes=['B44'])
        records = decisions.validate(self.root)
        overview = decisions.render(records, SOURCE_SHA)
        self.assertEqual(overview, decisions.render(dict(reversed(list(records.items()))), SOURCE_SHA))
        row = next(line for line in overview.splitlines() if line.startswith('| [B44]'))
        self.assertLess(row.index('[B-PR9-02]'), row.index('[B-PR9-10]'))
        self.assertLess(row.index('[B-PR9-10]'), row.index('[B-PR100-01]'))

    def test_overview_links_are_portable_pinned_and_tables_are_escaped(self):
        self.add_record(title='A | B and <literal>')
        overview = decisions.render(decisions.validate(self.root), SOURCE_SHA)
        prefix = f'https://github.com/awesomeopen/awesome-open/blob/{SOURCE_SHA}/'
        self.assertIn(f'[B-PR100-01]({prefix}brand/decisions/B-PR100-01.md)', overview)
        self.assertIn(f'[Guide]({prefix}site/RETRO-SCRAPERISM.md)', overview)
        self.assertIn(f'[accounting]({prefix}site/OBSERVATORY.md#accounting)', overview)
        self.assertIn('https://github.com/awesomeopen/awesome-open/pull/11', overview)
        self.assertIn('A &#124; B and <literal>', overview)
        self.assertNotIn(str(self.root), overview)
        self.assertTrue(overview.endswith('\n'))

    def test_overview_requires_a_full_lowercase_commit_sha(self):
        records = self.all_records()
        for source_ref in ('HEAD', 'main', 'abc123', 'a' * 39, 'a' * 41, 'A' * 40, '../main'):
            with self.subTest(source_ref=source_ref), self.assertRaisesRegex(ValueError, 'full commit SHA'):
                decisions.render(records, source_ref)

    def test_generation_is_offline_and_has_no_git_dependency_with_explicit_source(self):
        self.add_record()
        with patch.object(decisions, 'git', side_effect=AssertionError('Unexpected Git access')):
            overview = decisions.render(decisions.validate(self.root), SOURCE_SHA)
        self.assertIn('B-PR100-01', overview)


class CliTests(DecisionFixture):
    def setUp(self):
        super().setUp()
        self.add_record()
        self.prepare_cli()

    def test_plain_validation_does_not_write_or_require_git(self):
        before = self.snapshot()
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('45 records (44 legacy)', result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_generate_then_check_preserves_every_file_byte_and_mtime(self):
        args = ('--output', 'tmp/brand-decisions.md', '--source-ref', SOURCE_SHA)
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / 'tmp/brand-decisions.md'
        self.assertEqual(output.read_text(), decisions.render(self.all_records(), SOURCE_SHA))
        before = self.snapshot()
        result = self.cli(*args, '--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_missing_output_check_fails_without_creating_directories_or_files(self):
        before = self.snapshot()
        result = self.cli('--output', 'tmp/nested/overview.md', '--source-ref', SOURCE_SHA, '--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing or stale', result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / 'tmp').exists())

    def test_stale_output_check_fails_without_repairing_output(self):
        self.write('tmp/overview.md', 'stale content\n')
        before = self.snapshot()
        result = self.cli('--output', 'tmp/overview.md', '--source-ref', SOURCE_SHA, '--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing or stale', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_check_requires_output_and_does_not_mutate_sources(self):
        before = self.snapshot()
        result = self.cli('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--check requires --output', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_generation_outside_ignored_tmp_is_rejected(self):
        for output in ('brand/overview.md', 'tmp/../brand/overview.md', 'tmp-sibling/overview.md'):
            with self.subTest(output=output):
                before = self.snapshot()
                result = self.cli('--output', output, '--source-ref', SOURCE_SHA)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('must stay under ignored tmp/', result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_generation_rejects_output_symlink_without_touching_destination(self):
        original = self.write('tmp/original.md', 'Do not overwrite.\n')
        (self.root / 'tmp/overview.md').symlink_to(original)
        before = self.snapshot()
        result = self.cli('--output', 'tmp/overview.md', '--source-ref', SOURCE_SHA)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_generation_rejects_symlinked_tmp_root_escaping_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'tmp').symlink_to(outside, target_is_directory=True)
            result = self.cli('--output', 'tmp/overview.md', '--source-ref', SOURCE_SHA)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(outside) / 'overview.md').exists())

    def test_generation_rejects_symlinked_parent_escaping_tmp(self):
        self.write('outside/keep.md', 'Unchanged.\n')
        (self.root / 'tmp').mkdir()
        (self.root / 'tmp/nested').symlink_to(self.root / 'outside', target_is_directory=True)
        before = self.snapshot()
        result = self.cli('--output', 'tmp/nested/overview.md', '--source-ref', SOURCE_SHA)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_generation_uses_git_head_when_source_ref_is_omitted(self):
        base = self.init_git()
        result = self.cli('--output', 'tmp/overview.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'Source revision: `{base}`.', (self.root / 'tmp/overview.md').read_text())

    def test_cli_rejects_invalid_pr_number_or_absent_base(self):
        for args in (('--pr-number', '100'), ('--pr-number', '0'), ('--pr-number', '-1')):
            with self.subTest(args=args):
                before = self.snapshot()
                result = self.cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('positive PR number requires an actual base', result.stderr)
                self.assertEqual(self.snapshot(), before)


class HistoryTests(DecisionFixture):
    def test_legacy_evidence_correction_preserves_ids_and_heading_anchors(self):
        base = self.init_git()
        corrected = LEGACY_BYTES.replace(b'Fixed specimen concept;',
                                        b'Fixed specimen concept (evidence clarified);', 1)
        self.write(decisions.LEGACY_PATH, corrected)
        decisions.validate(self.root, base=base)

    def test_removing_an_existing_legacy_heading_anchor_is_rejected(self):
        base = self.init_git()
        self.write(decisions.LEGACY_PATH,
                   LEGACY_BYTES.replace(b'## Open items', b'## Current open items', 1))
        with self.assertRaisesRegex(ValueError, '[Aa]nchor'):
            decisions.validate(self.root, base=base)

    def test_adding_legacy_heading_without_removing_old_anchors_is_allowed(self):
        base = self.init_git()
        self.write(decisions.LEGACY_PATH, LEGACY_BYTES + b'\n## Review context\n\nEvidence note.\n')
        decisions.validate(self.root, base=base)

    def test_valid_existing_identity_allows_content_and_status_updates(self):
        self.add_record()
        base = self.init_git()
        self.add_record(title='Clarified rationale', status='accepted')
        records = decisions.validate(self.root, base=base, pr_number=101)
        self.assertEqual(records['B-PR100-01'].status, 'accepted')

    def test_existing_record_deletion_is_rejected(self):
        path = self.add_record()
        base = self.init_git()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'cannot be removed or renamed'):
            decisions.validate(self.root, base=base)

    def test_consistent_id_and_filename_rename_is_rejected_by_history(self):
        path = self.add_record()
        base = self.init_git()
        path.unlink()
        self.add_record('B-PR101-01')
        # Structural validation alone cannot know that this was a renaming.
        decisions.validate(self.root)
        with self.assertRaisesRegex(ValueError, 'cannot be removed or renamed: B-PR100-01'):
            decisions.validate(self.root, base=base)

    def test_id_only_change_and_filename_only_change_are_rejected(self):
        path = self.add_record()
        base = self.init_git()
        path.write_text(record_text('B-PR101-01'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'filename/ID mismatch'):
            decisions.validate(self.root, base=base)
        path.write_text(record_text(), encoding='utf-8')
        path.rename(path.with_name('B-PR101-01.md'))
        with self.assertRaisesRegex(ValueError, 'filename/ID mismatch'):
            decisions.validate(self.root, base=base)

    def test_pr_namespace_check_applies_only_to_new_records(self):
        self.add_record('B-PR100-01')
        base = self.init_git()
        self.add_record('B-PR101-01')
        records = decisions.validate(self.root, base=base, pr_number=101)
        self.assertEqual(len(records), 46)
        with self.assertRaisesRegex(ValueError, 'new record must use this PR number'):
            decisions.validate(self.root, base=base, pr_number=100)

    def test_concurrent_prs_share_ordinals_without_table_or_counter_edits(self):
        legacy_before = (self.root / decisions.LEGACY_PATH).read_bytes()
        self.add_record('B-PR100-01')
        self.add_record('B-PR101-01')
        self.add_record('B-PR100-02')
        records = decisions.validate(self.root)
        self.assertTrue({'B-PR100-01', 'B-PR100-02', 'B-PR101-01'}.issubset(records))
        self.assertEqual((self.root / decisions.LEGACY_PATH).read_bytes(), legacy_before)
        self.assertEqual(len(list((self.root / decisions.RECORD_DIR).iterdir())), 3)

    def test_first_migration_base_can_have_no_individual_record_directory(self):
        (self.root / decisions.RECORD_DIR).rmdir()
        base = self.init_git()
        self.add_record()
        decisions.validate(self.root, base=base, pr_number=100)

    def test_pr_number_requires_positive_integer_and_real_base(self):
        base = self.init_git()
        for value in (True, False, 0, -1, '100', 1.5):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'positive PR number'):
                decisions.validate(self.root, base=base, pr_number=value)
        with self.assertRaisesRegex(ValueError, 'actual base revision'):
            decisions.validate(self.root, pr_number=100)

    def test_invalid_or_option_like_base_cannot_be_silently_skipped(self):
        self.init_git()
        for base in ('does-not-exist', '--help', '--output=owned'):
            with self.subTest(base=base), self.assertRaises(subprocess.CalledProcessError):
                decisions.validate(self.root, base=base)
        self.assertFalse((self.root / 'owned').exists())


class WorkflowTests(unittest.TestCase):
    def test_ci_checks_history_runs_tests_and_uploads_the_checked_artifact(self):
        workflow = (ROOT / '.github/workflows/check-brand.yml').read_text()
        self.assertIn('fetch-depth: 0', workflow)
        self.assertIn('permissions:\n  contents: read', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('${{ github.event.pull_request.base.sha }}', workflow)
        self.assertIn('${{ github.event.pull_request.number }}', workflow)
        self.assertIn('--base "$BRAND_BASE_SHA" --pr-number "$BRAND_PR_NUMBER"', workflow)
        self.assertIn('test_brand_decisions.py', workflow)
        generated = 'python3 scripts/brand_decisions.py --output tmp/brand-decisions.md --source-ref "$GITHUB_SHA"'
        self.assertIn(generated + '\n', workflow)
        self.assertIn(generated + ' --check', workflow)
        self.assertIn('path: tmp/brand-decisions.md', workflow)
        self.assertIn('if-no-files-found: error', workflow)
        self.assertIn('/tmp/', (ROOT / '.gitignore').read_text().splitlines())
        self.assertNotIn('git push', workflow)
        self.assertNotIn('pull_request_target', workflow)


if __name__ == '__main__':
    unittest.main()
