# Repository integration and sources

Use paths below relative to `awesomeopen/awesome-open`. Read their current
contents before applying them. In an installed skill, locate or fetch the
repository; these paths refer to the project checkout.

## Existing project rules

- `AGENTS.md`: source ownership, positive statements, checks, and draft PRs.
- `brand/foundation.md`: purpose, voice, and evidence meanings.
- `site/RETRO-SCRAPERISM.md`, “Writing style and voice”: direct, neutral copy;
  meaningful limits once in a method or disclosure.
- `CONTRIBUTING.md`: name-based inclusion and contributor procedures. Preserve
  the current policy when shortening an introduction.
- `brand/decisions/B-PR152-01.md` and [PR #152](https://github.com/awesomeopen/awesome-open/pull/152):
  earlier repository-wide positive-statement cleanup, extending the timeline
  disclosure work recorded in `brand/decisions/B-PR150-01.md`.

Carry the earlier cleanup forward by stating the value's meaning, preserving a
useful qualification, and removing unsolicited rebuttals. Keep historical
decision records intact when editing current documentation.

## Source and check workflow

1. Read the surrounding documentation or rendered UI state. Find the authored
   string with `rg -n -F 'distinctive text' scripts site brand`. Check curated
   `data/` files if the passage comes from evidence notes. Quote shell input safely.
2. Edit the generator or authored source. Follow the existing publisher for
   generated HTML and README output.
3. Inspect affected tests for assertions on the old wording. Update assertions
   that encode superseded copy while preserving coverage of values, links,
   disclosure behavior, accessibility, and evidence meaning. Prefer observable
   behavior or semantic structure where literal copy is incidental.
4. Run the relevant tests and `python3 scripts/check_brand.py`. Follow the brand
   workflow for a changed rule and open a focused draft PR.

The source review on 2026-10-23 at `ac4d218c81b585f21dc379b5feae290089b8cf8d`
found the earlier cleanup in rules, generators, and targeted regression tests.
A reusable positive-language rewrite script was not located. The existing check
scripts verify output and behavior; use editorial judgment for the rewrite.

Relevant checks, selected by changed content:

| Content | Existing checks |
| --- | --- |
| Monthly stars and their disclosure | `scripts/test_star_history_site.py`, `scripts/check_star_history_browser.cjs` |
| Stale or unavailable metrics | `scripts/test_metrics_freshness.py` |
| Observatory explanations | `scripts/test_observatory.py`, `scripts/check_observatory_browser.cjs` |
| Catalog and expanded records | `scripts/test_build_site.py`, `scripts/check_plate_browser.cjs` |
| Brand references and pinned skills | `scripts/check_brand.py` |

For example, run the offline monthly-stars checks from the repository root with:

```sh
python3 -m unittest discover -s scripts -p 'test_star_history_site.py'
```

Read `scripts/run_browser_checks.py` and the relevant check's setup before running
browser tests. Keep this skill's changes scoped to editorial work. Add wording
assertions only when exact wording is part of the product requirement.

## External influences

Consulted on 2026-10-23; this skill contains original project-specific instructions.

- [rand/cc-polymath: anti-slop](https://github.com/rand/cc-polymath/tree/main/skills/anti-slop),
  inspected `skills/anti-slop/SKILL.md`, Git blob
  `32273d2f49d591717a9d8497a978e8335278af4c`:
  use direct claims, specifics, and context-sensitive judgment. Here, structural
  editing comes first; automated scoring and blanket rewrites are excluded.
- [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop), inspected
  `skills/no-ai-slop/SKILL.md`, Git blob
  `e2008aa08d688846b0373b83d7c3d33b85eaabdd`:
  preserve meaning and useful voice, remove generic importance and defensive
  contrasts, and test whether a sentence contributes to its subject. Here, the
  intended voice is factual documentation; examples serve comprehension, and
  edits can restructure a whole section when that makes its purpose clearer.

Keep terminology, negation, punctuation, and sentence length available when they
carry meaning. Apply the reader-question test before considering word patterns.
