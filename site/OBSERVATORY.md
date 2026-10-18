# Collection observatory

The `/observatory/` route is a deterministic snapshot view of the same validated
catalog built by `scripts/build_site.py`. It receives that in-memory catalog and
its HN evidence, after optional evidence and approved artwork have been attached.
There is no second collector, API, wall clock, backfill, historical dataset or
forecast model. The main-only publisher includes the route automatically.

## Accounting

- Totals count canonical project IDs once. Cross-listed category memberships may
  overlap, so their sum is not a unique-project count and they are not a pie.
- Shared names use one matching key per displayed name: lowercase (`str.lower`
  in Python, `toLowerCase` in JavaScript), then remove Unicode `White_Space`,
  hyphen and underscore. The explicit White_Space set is U+0009–000D, U+0020,
  U+0085, U+00A0, U+1680, U+2000–200A, U+2028–2029, U+202F, U+205F and U+3000.
  Zero-width space, BOM, the dot and other punctuation are retained; spelling and
  sound-alike names are not matched. Projects with equal keys form one group, so
  each canonical project ID belongs to at most one group and groups cannot chain.
  A group needs two distinct project IDs; empty keys never match. **Identical
  name** groups display one name; **Spelling variants** display several. Variant
  groups carry non-exclusive tags (Case, Spacing, Exact duplicates); tag counts do
  not sum to a total. The headline counts tools in all groups. Groups follow the
  selected category/license filters. Plates show unchanged displayed names,
  source URLs and the catalog's short description; a shared key does not
  establish an alias or relationship. No additional collection or dependency.
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
- Coverage is whole-collection, labeled “Whole collection” and unaffected by filters. Optional
  provider counts distinguish checked/cached and available/partial/stale/missing.
  Scorecard is coverage only; there is no combined security score or verdict.
- HN coverage counts tracked and chart-eligible projects separately. Story IDs
  deduplicate within a project and globally; project–story matches can exceed
  globally distinct stories. This hand-mapped subset is not representative.
- Star-history coverage is separate from present stars. It means monthly stars
  still retained at a successful fetch, not historical totals or net growth.
  Aligned-chart coverage stays separate from cached results.

## Presentation and data

The B31 layout and its method are recorded in
[OBSERVATORY-REDESIGN.md](OBSERVATORY-REDESIGN.md).

Standard-library Python renders every chart server-side as an HTML bar list:
zero-based and linear, labels wrap instead of truncating, Unknown bars are hatched
as well as labeled. The visual is `aria-hidden`; a folded “Chart data” table per
chart is the accessible equivalent. Categories are sorted by count (ties keep
catalog order, Unknown last). Last push and latest release share one maximum,
marked “shared scale”. Route-only JavaScript
progressively filters a thin embedded projection, with category/license URL state
and Back/Forward support. Native HTML tables, exact values, source revision,
snapshot date and every project row remain available without JavaScript. The
project data table is collapsed by default in a native `details` disclosure whose
summary starts “Data table” and states the selected row count; exports remain
visible. Name-group plates are folded the same way (“Show name groups”), with
“How groups are formed” as a nested disclosure; the unit tally above them stays
open, one equal-weight mark per tool, square for identical names and circle for
spelling variants. The CSV includes every displayed data field
with full timestamps, plus project IDs, category IDs, GitHub-mapping flags and
snapshot/revision provenance, and the catalog's short `description`. Illustration
never changes a measured mark.

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
  and Commit Mono pair, linear charts and explicit evidence labels. The header
  repeats the ledger's links (Ledger, About, Observatory, GitHub), with Observatory
  marked as the current page; the standalone report points them at the live site. One sticky
  selection bar without visible labels (each select has an accessible name) and
  bold section jumps; no kickers; “N/N selected.” ends the Shared names paragraph.
- Closing mark: the existing 128px botanical logo is centered before the footer,
  with 128px of vertical space above and below (96px on narrow screens) and no
  visible caption. Its size stays within the source resolution; the standalone
  report embeds it. The opening is text-only, unruled and uses its full available
  width; the snapshot date and source revision sit in the footer link list.
  Chart geometry and project specimen artwork remain unchanged.
- Editorial hand: a bounded whole-collection finding with a to-scale share strip,
  and scarlet underlines that mark only real name differences.
  No invented danger seals, risk colors or forecast language.

This extends the existing Retro-Scraperism and Speculative FOSSoligy contract,
without changing their portable skill pins or the catalog's accepted hero.

## Checks

Run `python3 -m unittest discover -s scripts -p 'test_*.py'`,
`python3 scripts/check_brand.py` and a production-shaped site build. The existing
browser check invokes `scripts/check_observatory_browser.cjs`, retaining route
screenshots and a source manifest in the existing browser artifact. No new
workflow, permissions, dependencies or public preview host is needed.

## Reviewed rhyming names

The separate clickable “tools have rhyming names” disclosure is a bounded
editorial measure, not another shared-name category. It does not increase the
shared-name headline. A project can occur in both measures; totals are not additive.
Native HTML shows the reviewed groups without JavaScript. Category/license
filters recalculate both participation and reviewed-reading coverage.

`data/name_rhymes.json` owns the small reviewed subset. Records bind the exact
current displayed name to its canonical project URL, resolved to the existing
project ID. Build validation rejects unknown URLs, duplicate IDs, name drift,
invalid phonemes and inconsistent onset/ending decomposition. The index and
snapshot preserve review date, reviewer, source URL and explicit assumption basis.
Missing records mean unclassified, never a claim that the name cannot rhyme.

The initial seven project readings form two groups: OpenChat (two separate
projects), OpenCat and OpenVat; OpenShell, OpenSpell and Openbell. They use ordinary
American English readings of the single-syllable remainder after Open. Official
source links establish names, not officially approved pronunciation. The display
states this limitation. A key consists of the final stressed vowel and subsequent
sounds in ARPABET; `1` marks primary stress. A group needs at least two different
normalized display names and two different preceding consonant onsets. Identical
names alone, homophones alone and identical terminal words do not form groups.
A duplicate-named project can participate when another genuinely rhyming name is
present, but each canonical ID counts once. Language and exact ending form the
bucket, so groups cannot chain.

Aliases and abbreviations are never expanded or added to rhyme matching. There
is no suffix-letter heuristic, automatic pronunciation service or browser API.
Acronyms, invented words, numbers, ambiguous and non-English readings remain
unclassified in this initial subset. The initial validator deliberately accepts
single-syllable ARPABET remainders only; broadening coverage or languages requires
reviewing that contract rather than guessing. No catalog identity, HN attribution,
workflow, collection budget, credential, dependency or hosting change is involved.
