# Catalog redesign: open items

- **Date:** 2026-11-15
- **Owner:** Project owner, GitHub [@snlr308](https://github.com/snlr308)
- **Related:** [draft PR #333](https://github.com/awesomeopen/awesome-open/pull/333),
  [B-PR333-01](../brand/decisions/B-PR333-01.md) (one-screen layout),
  [B-PR333-02](../brand/decisions/B-PR333-02.md) (short category names),
  [B-PR333-03](../brand/decisions/B-PR333-03.md) (QR-height label and trophy line)

These are the parts of the Catalog redesign that PR #333 does not finish. Each item
says what is missing, why it matters and where the work starts.

## Context

On 2026-11-11 the owner asked for the Catalog to become a one-page app on desktop:
category, then name and description, then the specimen plate, in three columns. The
earlier page followed the brand guide but read as scattered on large screens; on
phones it stayed acceptable because it was simple. The owner reviewed a local
prototype from 2026-11-11 to 2026-11-15 and then asked for the real build.

PR #333 builds it into the generator. `index.html` now has a category rail with
filters, the project list under the wordmark and search, and one pane that holds the
jars, one plate, or the About sheet. About carries the former footer and opens
Observatory, Scoreboard and Spotlight in the pane. Category headings use short names
while keeping their former IDs. The specimen label is as tall as its QR code, and
Scoreboard places appear as one "N Trophies" line. The runtime is `site/app.js` and
`site/app.css`; the page is `render_html` in `scripts/build_site.py`.

At revision `1b3aec5`, the 908 offline tests pass locally and in CI. Every browser
suite passes locally (macOS); CI stops before the browser suites, see item 1.

## Open items

### 1. Site size budget blocks CI's browser checks

`scripts/check_budget.py` fails on "Largest other file": `data/hn_evidence.json` is
8.9 MiB published, against a limit of 4.6 MiB (8 KiB per record). The file grew
through main's daily publish commits from 2026-11-12 and is unchanged by PR #333, so
every PR now stops at this step and CI skips the Chromium suites.

Decide whether to raise the limit with a stated reason or publish a smaller file
(for example compact or split HN evidence), in a separate PR. Until then, browser
results come only from local runs.

### 2. Observatory keyboard step not yet seen on Linux

One step in `scripts/check_observatory_browser.cjs` changes the category filter with
Home, ArrowDown and Enter. Native selects on macOS ignore those keys, so the step
fails locally for any build; with the step done by mouse, the rest of the suite
passes. `observatory.js` is unchanged. Confirm the step on Linux once item 1 lets CI
reach the browser suites.

### 3. Plate drawings are scaled by the browser

The pane shows drawings at about 440px, from the existing 512px variant. The owner
asked for 66–75% size with an unsharp-mask pass, because the drawing style blurs
when reduced. Producing sharpened derivatives needs Pillow or ImageMagick and new
artwork bytes, so it follows the artwork rules: provenance, `brand/assets.md` and
`brand/assets.lock.json`. Start from `scripts/build_specimen_variants.py` and
`site/jars/responsive.json`.

### 4. Phone layout is not designed

Below 900px the page falls back to one column: wordmark and search, the jars, the
category row and filters, then the list. A plate or About covers the screen. It
works and passes the browser checks, but the owner has not reviewed a phone design.
The rules are at the end of `site/app.css` (`@media(max-width:899px)`).

### 5. Choosing a project in the cabinet drops the plate's permalink

`site/cabinet.js` rewrites the address hash when its selection changes. If a plate
is open, its `#project-…` permalink is lost from the address bar, although the plate
stays. The fix belongs in the cabinet's URL handling, so the cabinet keeps its
`cabinet=` parameter without replacing the hash. See the
[cabinet contract](../site/WEBMCP-CABINET.md).

### 6. Old ledger styles remain in `site/styles.css`

The former header, Table of contents, folded rows and footer rules are no longer
used by `index.html`. Record pages still use the shared plate and specimen rules, so
remove only the rest, and check each removal against the record pages and the
`check_*_browser.cjs` suites.

## Choices made in the build that the owner has not reviewed

- **Corner buttons.** WebMCPlet's "Search this list" button keeps the bottom-right
  corner; the scarlet Cabinet button stacks above it while that button is shown.
- **Jar Inspect links.** They lead to the static record, so they work without
  JavaScript; with JavaScript the plate opens in the pane.
- **Back and Forward.** They step through category and filter changes, as on the
  former page.
- **About panorama.** It shows at native size, centred and clipped, as the footer
  rule requires; the prototype had scaled it to the column width.
- **Record page link.** "Return to this project in the ledger" now reads "Open this
  project in the Catalog".
