# Collection observatory

The `/observatory/` route is a deterministic snapshot view of the same validated
catalog built by `scripts/build_site.py`. It receives that in-memory catalog and
its HN evidence, after optional evidence and approved artwork have been attached.
There is no second collector, API, wall clock, backfill, historical dataset or
forecast model. The main-only publisher includes the route automatically.

## Accounting

- Totals count canonical project IDs once. Cross-listed category memberships may
  overlap, so their sum is not a unique-project count and they are not a pie.
- Shared-name headline counts the union of canonical project IDs in the three
  displayed groups. Cross-category listings and overlapping matches count once.
  Group assignment is ordered: exact displayed names first, then lowercase-name
  matches among remaining projects, then whitespace-only matches among those
  still unassigned. Each displayed group needs at least two distinct project IDs;
  whitespace groups also need different displayed names and a nonempty key.
  Whitespace comparison removes Unicode `White_Space` characters and preserves
  case. Python and JavaScript use the same explicit set: U+0009–000D, U+0020,
  U+0085, U+00A0, U+1680, U+2000–200A, U+2028–2029, U+202F, U+205F and U+3000.
  Zero-width space and BOM are retained. Combined case-and-whitespace changes,
  punctuation and spelling are not normalized. Exact/capitalization priority can
  leave a singleton unlisted in a later group; these sections classify disjoint
  groups rather than enumerate every possible matching pair.
  All sections follow selected category/license filters. Native disclosures show
  unchanged displayed names and source URLs; name matches do not establish aliases.
  Grouping uses the existing snapshot with no additional collection or dependency.
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

A proposed redesign of this route, with a reusable method for similar passes, is
recorded in [OBSERVATORY-REDESIGN.md](OBSERVATORY-REDESIGN.md) (B30, not
implemented). The rules below remain current until it is accepted.

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

The chart/table selection, shared-name groups and four headline metrics change together. The top
collection finding and coverage explicitly retain whole-collection scope.
Unknown remains a category even when its count is zero. Empty selections do not
manufacture percentages, missing values or a zero-star observation.

## Visual concept

- Instrument: white/cool-mist reading ground, Prussian rules, the existing Fraunces
  and Commit Mono pair, linear charts and explicit evidence labels.
- Closing mark: the existing 128px botanical logo is centered before the footer,
  with 128px of vertical space above and below (96px on narrow screens) and no
  visible caption. Its size stays within the source resolution; the standalone
  report embeds it. The opening is text-only and uses its full available width.
  Chart geometry and project specimen artwork remain unchanged.
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
