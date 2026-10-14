# Collection observatory

The `/observatory/` route is a deterministic snapshot view of the same validated
catalog built by `scripts/build_site.py`. It receives that in-memory catalog and
its HN evidence, after optional evidence and approved artwork have been attached.
There is no second collector, API, wall clock, backfill, historical dataset or
forecast model. The main-only publisher includes the route automatically.

## Accounting

- Totals count canonical project IDs once. Cross-listed category memberships may
  overlap, so their sum is not a unique-project count and they are not a pie.
- Stars sum observed cached GitHub counts, including actual zeroes; missing
  metrics remain null. The top-ten concentration denominator is that same sum.
  Neither stars nor a push timestamp is a quality, usage or maintenance verdict.
- Detected licenses retain literal SPDX identifiers. Missing/unrecognized values
  are Unknown, not “unlicensed.” No inferred license family or open-source status.
- Age and recency use UTC calendar-date differences against `metrics_as_of`.
  Timestamp offsets convert to UTC before taking the date. Same-day timestamps
  count as zero days. Invalid/future dates are Unknown.
  Repository creation is not a founding date. Release uses the cached latest full
  GitHub release's `published_at`, not tag creation, last push or fetch date.
  Release cache status and checked time remain explicit in the underlying table.
- Coverage is whole-collection and labeled as unaffected by filters. Optional
  provider counts distinguish checked/cached and available/partial/stale/missing.
  Scorecard is coverage only; there is no combined security score or verdict.
- HN coverage counts tracked and chart-eligible projects separately. Story IDs
  deduplicate within a project and globally; project–story matches can exceed
  globally distinct stories. This hand-mapped subset is not representative.
- Star-history coverage is separate from present stars. It means monthly stars
  still retained at a successful fetch, not historical totals or net growth.
  Aligned-chart coverage stays separate from cached results.

## Presentation and data

Native SVG and standard-library Python do the chart work. Route-only JavaScript
progressively filters a thin embedded projection, with category/license URL state
and Back/Forward support. Native HTML tables, exact values, source revision,
snapshot date and every project row remain available without JavaScript. The
project data table is collapsed by default in a native `details` disclosure labeled
“Data table”; exports remain visible. The CSV includes every displayed data field
with full timestamps, plus project IDs, category IDs, GitHub-mapping flags and
snapshot/revision provenance. Charts
use linear zero-based geometry; illustration never changes a measured mark.

`observatory/snapshot.json` contains the thin rows, derived aggregates and coverage.
`observatory/projects.csv` is the complete projection. The browser's CSV link
exports the selection, including snapshot/revision provenance; formula-like cells
are escaped. `observatory/report.html` embeds runtime dependencies and downloads
for offline use. Optional external source links still need a network. The report
is generated from the same revision and is not a separately refreshed publication.

The chart/table selection and four headline metrics change together. The top
collection finding and coverage explicitly retain whole-collection scope.
Unknown remains a category even when its count is zero. Empty selections do not
manufacture percentages, missing values or a zero-star observation.

## Visual concept

- Instrument: white/cool-mist reading ground, Prussian rules, the existing Fraunces
  and Commit Mono pair, linear charts and explicit evidence labels.
- Specimen: reuse the approved Open Doc folded-paper organism as one compact,
  original interpretation beside the opening. It is not an official logo or an
  encoding of project counts. No new art bytes, giant montage or raster edits.
- Editorial hand: numbered observations and a bounded whole-collection finding.
  No invented danger seals, risk colors or forecast language.

This extends the existing Retro-Scraperism and Speculative FOSSoligy contract,
without changing their portable skill pins or the catalog's accepted hero.

## Checks

Run `python3 -m unittest discover -s scripts -p 'test_*.py'`,
`python3 scripts/check_brand.py` and a production-shaped site build. The existing
browser check invokes `scripts/check_observatory_browser.cjs`, retaining route
screenshots and a source manifest in the existing browser artifact. No new
workflow, permissions, dependencies or public preview host is needed.
