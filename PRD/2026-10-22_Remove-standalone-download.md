# PRD: Remove the standalone download

- **Date:** 2026-10-22
- **Status:** Implemented in [#184](https://github.com/awesomeopen/awesome-open/pull/184);
  size budget in [#186](https://github.com/awesomeopen/awesome-open/pull/186), deferred-only
  ledger in [#194](https://github.com/awesomeopen/awesome-open/pull/194)
- **Owner:** Project owner
- **Decision:** [TODO.md entry 261022](../TODO.md),
  [B-PR176-01](../brand/decisions/B-PR176-01.md),
  [B-PR184-01](../brand/decisions/B-PR184-01.md) (Observatory report)
- **Related:** [Performance tuning](2026-10-22_Performance-tuning.md), phase 2

## Decision

Stop generating `standalone.html` and remove every link to it. The owner knows of
no one who uses it. Offline reading and printing stay available through the
static record pages (`records/<id>.html`) and the `catalog.json` and evidence
downloads.

## Why

- **Weight:** 116 MB of the 256 MB site (2026-10-22, main `7da9631`): base64
  artwork (69 MB), JSON downloads (37 MB) and SVG charts and QR codes (6.5 MB).
  It grows with every new specimen illustration and dominates the path to the
  1 GB GitHub Pages limit.
- **Build time:** it needs a second full, non-deferred ledger render and a
  literal-replacement pass that takes about 5 s of a 19 s build.
- **Maintenance:** about 15 Python test modules, 7 browser checks and a dozen
  documents assert or describe its behavior, so every UI change is verified twice.

## Scope

In scope: `standalone.html`, its "Download" links, and the code, tests, checks
and documents that exist only for it.

Added on 2026-10-22: `observatory/report.html` (the Observatory's standalone
report) and the Observatory's project data table. The owner decided to remove
both when reviewing the
[performance PRD](2026-10-22_Performance-tuning.md#w4-payload-reduction-phase-3);
see [B-PR184-01](../brand/decisions/B-PR184-01.md).

Out of scope: `catalog.json`; the evidence downloads; the Observatory CSV and
snapshot JSON; static record pages; the exhibition preview.

## Inventory

### Generator

- `scripts/build_site.py`
  - `build()`: the non-deferred `page = render_html(...)` render, the
    replacement map and the `standalone.html` write (about lines 777 and
    895–956).
  - `replace_literals_once()`: used only for the standalone.
  - Ledger footer link `<a href="standalone.html" download>Download</a>`
    (`render_html`, footer actions).
  - Record footer link "Download complete catalog" (`render_record`).
- `render_html(deferred=False)` remained the test fixture for the full ledger in
  several test modules. [#194](https://github.com/awesomeopen/awesome-open/pull/194)
  makes the deferred ledger its only mode; those tests read plates from the
  static records.
- `scripts/font_assets.standalone_font_css` stays:
  `site/design/observatory-redesign/build.py` uses it.
- `site/catalog.js` handles "legacy fully rendered standalone and single-record
  pages" (`site/test_catalog.js:1337`). Record pages still need the fully
  rendered path; only the standalone wording and fixture change.

### Tests (Python, `scripts/`)

`test_build_site.py`, `test_standalone_embedding.py` (delete),
`test_lazy_details.py`, `test_category_art.py`, `test_deployment.py`,
`test_fonts.py`, `test_footer_art.py`, `test_hero_images.py`,
`test_metrics_freshness.py`, `test_observatory.py`, `test_project_history.py`,
`test_signal_site.py`, `test_star_history_site.py`. Each asserts output in
`standalone.html`; keep the assertion for the remaining outputs (ledger,
records) and drop the standalone branch.

### Browser checks (`scripts/*.cjs`)

| Check | Standalone role | Replacement |
| --- | --- | --- |
| `check_site_browser.cjs` (about lines 625–663) | Offline route; DOM-size control for the deferred ledger | Drop the offline route; compare the deferred ledger with a static record or a fixed element budget |
| `check_specimen_bounds_browser.cjs` | Original-resolution embedded artwork | Drop |
| `check_plate_browser.cjs`, `check_history_browser.cjs`, `check_star_history_browser.cjs`, `check_deployment_browser.cjs` | Second route for the same assertions | Keep the record route |
| `check_fonts_browser.cjs` | Embedded fonts route | No-JS record page and `/observatory/` (the report is removed too) |

### Documents

- Contributor and product docs: `CONTRIBUTING.md` (the "Every build also emits
  `tmp/site/standalone.html`" paragraph and the motion note), `CLONE.md`,
  `PRODUCT.md` (routes list).
- Site contracts: `site/DETAIL-LOADING.md`, `site/PREVIEW.md`,
  `site/PROJECT-ALIASES.md`, `site/PROJECT-HISTORY.md`,
  `site/RETRO-SCRAPERISM.md`, `site/WEEKLY-DRAWS.md`,
  `site/SPECIMEN-VOICE-PLAN.md`, `site/DEPLOYMENT-EVIDENCE.md`.
- Brand references: `brand/visual-system.md` (the standalone download
  paragraph and two mentions), `brand/assets.md`, `brand/maintenance.md`
  (output modes to check), `brand/icons.md` and `site/brand/icons.json`
  (`link.download` lists "Download" and points at `standalone.html`).
- Merged decision records that mention the standalone (B-PR104-01, B-PR111-01,
  B-PR112-01, B-PR114-01, B-PR128-01, B-PR134-01, B-PR150-01, B-PR158-01) keep
  their text and IDs. The new record cites the parts that change.

## Requirements

1. A production build writes no `standalone.html`, and no generated page links
   to it.
2. The build performs one ledger render (the deferred ledger) plus the static
   records.
3. Static records remain complete, printable and usable without JavaScript.
4. `catalog.json` and the evidence downloads stay linked from the ledger footer.
5. Requests to `/standalone.html` on Pages return 404; no stub page.
6. Documents and brand references describe the remaining output modes, and the
   decision record moves to `implemented` when the PR merges.
7. The size budget limit for the total site drops by the removed bytes in the
   same PR.

## Verification

- Offline Python and Node tests pass; tests refer to `standalone.html` only to
  assert that it is absent.
- `python3 scripts/check_brand.py` passes.
- PR CI browser suites pass; screenshots show the ledger footer without the
  "Download" link.
- `scripts/check_budget.py` reports the new total, about 140 MB at the
  2026-10-22 catalog size (measured: 128.0 MiB with the Observatory report
  removed too). [#186](https://github.com/awesomeopen/awesome-open/pull/186)
  scales its limits with the number of static records.
