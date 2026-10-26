# PRD: Performance tuning for the field guide

- **Date:** 2026-10-22
- **Status:** In progress. Phase 1 merged in [#176](https://github.com/awesomeopen/awesome-open/pull/176)
  and [#177](https://github.com/awesomeopen/awesome-open/pull/177); phase 2 merged in
  [#184](https://github.com/awesomeopen/awesome-open/pull/184) and
  [#194](https://github.com/awesomeopen/awesome-open/pull/194); phase 3a is in
  [#195](https://github.com/awesomeopen/awesome-open/pull/195).
- **Owner:** Project owner
- **Related:** [Remove the standalone download](2026-10-22_Remove-standalone-download.md)
  (separate PRD), TODO entry "Responsive hero images and compact catalog index"

## Problem

The catalog ledger keeps growing: more projects, more specimen artwork, more
automation and more subpages. The GitHub Pages output, the build and CI all grow
linearly or faster with it. Without a measured budget, regressions arrive
unnoticed through daily publisher runs and agent PRs.

## Baseline

Measured on 2026-10-22 from main `7da9631` with
`python3 scripts/build_site.py --production` on a local Linux machine, 525
projects / 547 category memberships, cached data.

| Output | Size | Composition |
| --- | --- | --- |
| Whole site | 256 MB, 2,043 files | |
| `standalone.html` | 116 MB (61 MB gzip) | Base64: 69 MB artwork, 37 MB JSON, 6.5 MB SVG |
| `specimens/` | 71 MB | 34 MB originals plus 37 MB cutouts; both are shipped |
| `catalog.json` | 13 MB | 3.9 MB written compactly; 3.3 MB of it is `star_history.last_good` |
| `data/` | 15 MB | `star_history.json` 9.9 MB indented, 2.8 MB compact |
| `observatory/report.html` | 10 MB | Base64 artwork and downloads |
| `assets/qr/` | 4.2 MB | 525 SVGs at about 8 KB each |
| `index.html` | 928 KB (136 KB gzip) | 532 articles (680 KB) plus a 236 KB search index |

Build time: about 19 s wall clock (21 s under the profiler).

| Hot spot | Time | Cause |
| --- | --- | --- |
| `qr.svg` / `qr.encode` | 9.1 s | 525 encodes; bitwise GF(256) multiply, mask flips and penalty scoring recomputed per code |
| `replace_literals_once` | 5.0 s | One regex alternation of about 1,300 literals over the full ledger, for `standalone.html` only |
| `update_star_history.monthly_counts` | 3.0 s | 520,000 `datetime.fromtimestamp().strftime()` calls; the cache is validated twice per build |

Asset URLs use three cache-busting schemes:

- Content hash: `catalog.js`, `tokens.css`, `vendor/fonts.css`, `jars.css`.
- Source revision: `styles.css?v=<source sha>`, which changes on every daily
  evidence-only publish.
- None: `observatory/observatory.css`, `observatory/observatory.js`, `jars.js`,
  `spotlight/draws.css`.

Specimen artwork growth: about 176 of 525 projects have artwork, and each
addition ships an original (about 200 KB) plus a cutout (about 250 KB). GitHub
Pages limits a published site to 1 GB. At the current per-project cost, full
artwork coverage puts the site near 500 MB, and the catalog reaches the limit
at roughly 1,000 projects (estimate from the figures above).

## Goals

1. A production build in under 5 s on the baseline machine, with byte-identical
   output wherever the change is internal.
2. Every runtime CSS/JS URL is versioned by its content, so a deploy never mixes
   old and new files and an evidence-only publish reuses cached runtime bytes.
3. A size budget measured on every build and enforced in CI, with figures in the
   GitHub step summary.
4. Site weight that grows with the catalog, not with duplicated copies of it.
5. CI time spent on the changes a PR actually makes.

Evidence meanings, labels, artwork bytes, identities and permalinks stay as they
are. Removing `standalone.html` has its own PRD because it touches tests, browser
checks and brand references across the repository.

## Workstreams

### W1. Build speed (Phase 1)

- **QR encoder:** log/antilog tables for GF(256), a cached Reed–Solomon divisor
  per degree, cached function patterns and mask flip positions per version, and
  string-based penalty scoring. Output stays byte-identical; a test compares the
  SVG for fixed inputs against a recorded digest.
- **Star-history validation:** memoize the UTC month per day number in
  `monthly_counts`. Results are identical; the existing validation tests apply.
- **`replace_literals_once`:** this cost belongs to the standalone build and
  disappears with it; see the separate PRD.

Acceptance: generated site identical to the pre-change build apart from
versioned asset URLs (W2). Phase 1 brings the build from about 19 s to about
10 s; with the standalone removed (Phase 2) it falls under 5 s.

### W2. Content-hashed asset URLs (Phase 1)

Version `styles.css`, `observatory/observatory.css`, `observatory/observatory.js`,
`jars.js` and `spotlight/draws.css` with the same 16-hex-digit SHA-256 content
hash `font_asset_url` uses. Literal replacements that inline these files into
offline pages, and browser routes that intercept them, match the versioned URLs.

Acceptance: every same-origin `<link rel="stylesheet">` and `<script src>` in
generated HTML carries `?v=<content hash>`; a CSS-only change alters only that
file's token.

### W3. Size budget (Phase 1)

`scripts/check_budget.py` measures a built site: total bytes and files, the
largest files, `index.html` raw and gzip, `catalog.json`, and the largest image.
Limits live in one table in the script with the reason for each. The script
prints a Markdown table, appends it to `$GITHUB_STEP_SUMMARY` when present and
exits non-zero when a limit is exceeded. The PR workflow enforces it after
building; the publisher runs it with `--warn-only`, so a daily publish is never
blocked.

Initial limits sit just above the current baseline, so the check catches new
growth; each later workstream lowers its limit in the same PR.

The catalog is planned to grow to about 1,000 records, so outputs that grow
with it (the site without `specimens/`, file count, `index.html`,
`catalog.json`, the largest data file) take a limit of a fixed part plus an
amount per static record. Specimen artwork grows by design, in batches of up to
40 projects (about 16 MiB each); its limit is the average bytes per illustrated
project (original plus cutout). The site total limit is 640 MiB, above the
projected 490 MiB at 1,000 records with artwork for each.

### W4. Payload reduction (Phase 3)

- Write site-only JSON (`catalog.json`, the copied `data/*.json`) compactly. The
  repository copies keep their indented, diffable form.
- Ship star history once: `catalog.json` refers to `data/star_history.json`
  instead of embedding `last_good` per project, or the reverse; pick one owner.
  Chosen in [#195](https://github.com/awesomeopen/awesome-open/pull/195):
  `data/star_history.json` owns the counts, keyed by `star_history.repo`.
  `catalog.json` falls from 12.2 MiB to 1.3 MiB and `data/` from 14.6 MiB to
  6.2 MiB.
- Add responsive specimen artwork (`srcset` at 512/768/1254 px) to static
  records and drawers. The plate is at most 627 px wide and `.specimen-art` at
  most 400 px; phones currently download the 1254 px original. Derived variants
  follow the `jars/responsive/` pattern and need provenance and a
  `brand/assets.md` update.
  Proposed in [#196](https://github.com/awesomeopen/awesome-open/pull/196)
  ([B-PR196-01](../brand/decisions/B-PR196-01.md)) at 512/768 px plus the
  source; the loupe keeps the source.
- Review whether both the original and the cutout need to ship for every project
  that has a cutout.
- New image files (the responsive variants, and any change to which of original
  and cutout ships) go into a PR of their own with its own review, separate from
  the JSON changes ([B-PR184-02](../brand/decisions/B-PR184-02.md)).
- `observatory/report.html` (10 MB): decided on 2026-10-22. The owner removed it
  together with the Observatory's project data table in phase 2
  ([B-PR184-01](../brand/decisions/B-PR184-01.md)).

### W5. CI and automation (Phase 4)

- Path filters on `check-updaters.yml`, so docs-only and brand-record PRs skip
  the full build and the browser plan (about 17 minutes). `check-brand.yml`
  still runs for them.
- Cache the Playwright browser directory (`~/.cache/ms-playwright`) keyed on the
  locked Playwright version.
- Cache derived outputs that change only with their inputs (QR SVGs, responsive
  image variants) with `actions/cache` keyed on input hashes.

### W6. Later, as the catalog grows

- **Ledger DOM:** `content-visibility: auto` with `contain-intrinsic-size` on
  ledger rows; chunked rendering once the ledger passes about 1,500 rows.
- **QR SVG size:** draw modules as a single stroked path with relative moves
  (about 60% smaller). This changes asset bytes, so it needs a visual check.
- **Repository growth:** the pack is 118 MB, and `data/star_history.json`
  (9.9 MB) is rewritten on most publishes. Options: Git LFS for
  `site/specimens/`, or bulky caches on a data branch.
- **CSS overlap:** record pages load all of `styles.css` and `observatory.css`;
  measure the unused share before splitting.
- **Identifiers:** the 64-hex Registry IDs account for about 180 KB of
  `index.html` attributes. Gzip absorbs most of it, and they are the permalink
  contract, so they stay.

## Phasing

| Phase | Scope | Brand impact |
| --- | --- | --- |
| 1 | W1, W2, W3 | Implementation only |
| 2 | Remove `standalone.html` ([PRD](2026-10-22_Remove-standalone-download.md)) and `observatory/report.html` | Decision records and guide updates |
| 3a | W4 data: compact site JSON, one owner for star history | None |
| 3b | W4 images: responsive specimen variants, original/cutout review; own PR and review | Asset provenance for new variants |
| 4 | W5 | None |
| Later | W6 | Per item |

## Verification

- `python3 -m unittest discover -s scripts -p 'test_*.py'`
- `node --test site/test_*.js`
- `python3 scripts/check_brand.py`
- A production build diffed against the pre-change build, plus
  `scripts/check_budget.py`
- The browser suites through `scripts/run_browser_checks.py` in PR CI
