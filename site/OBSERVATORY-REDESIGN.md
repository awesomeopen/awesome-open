# Observatory redesign proposal

Status: **User-approved; implemented for review** (B30). The generator, runtime,
styles and tests implement this design; [OBSERVATORY.md](OBSERVATORY.md) carries the
updated contract. This note keeps the reasoning and the reusable method. One
difference from the mock: repository paths show the catalog's canonical URL rather
than the casing in `README.source.md`.

Reviewed mock: private artifact
[Collection Observatory Redesign](https://claude.ai/artifact/8TVofdsPuHy4mJNk4J2X6L),
with the earlier single-section study
[Shared Names Redesign](https://claude.ai/artifact/M7NQmyxCtfRuSWbHyYgSnP). Both
were built from the published `observatory/snapshot.json` (metrics as of
2026-10-14, source `f906165`) and the short descriptions in `README.source.md`.
They reproduce the published aggregates in page script; they are not output of
`scripts/build_observatory.py`. The full-page mock's source is in
[design/observatory-redesign/](design/observatory-redesign/): rebuild it with
`python3 site/design/observatory-redesign/build.py SNAPSHOT_JSON OUTPUT_HTML`.

## How to use this for a similar redesign

Follow the "Design a new page or route" route in [the brand reference](../brand/README.md),
then work through each block in this order:

1. **State the reader's question per block.** Shared names answered "how many";
   the reader asks "which one is which". Design for the question.
2. **Keep the evidence contract fixed.** Counting rules, scope labels (whole
   collection versus selection), Unknown values and literal labels do not change
   in a visual pass. Write down any contract change explicitly (see below).
3. **Unfold graph-driven blocks; fold listings.** Charts, metrics and tallies
   stay open. Listings of projects (name-group plates, the data table) sit behind
   a native disclosure whose summary states what it holds.
4. **Mark only true differences.** Emphasis (bold owner, scarlet underline)
   points at the one fact that distinguishes items. It never implies a relation,
   rank or verdict. Categorical marks use equal weight and differ by shape;
   dark/light pairs read as done/not done or as progress.
5. **Remove explanatory captions the layout already makes clear.** Keep method
   text in one disclosure rather than repeating it beside every block.
6. **Verify numbers against the published snapshot** before review, and record
   the source revision and viewport limits.

## Page changes

| Area | Current | Proposed | Basis |
| --- | --- | --- | --- |
| Opening | Kicker, title, provenance lines | Title only, no rule above it. Snapshot date and source revision move to the footer | Opening stays text-only (Observatory contract) |
| Kickers | Small uppercase eyebrow above most blocks (`01 / projects`, `Whole collection`, …) | Removed. Section headings carry the structure: h2 for Shared names, Charts, Evidence coverage and Project data; h3 per chart | User direction 2026-10-14 |
| Header links | Project ledger · Coverage · Data | The ledger's own links: Ledger · About · Observatory · GitHub, with Observatory marked current (`aria-current`, scarlet underline). Coverage and Data stay in the selection bar's jumps | User direction 2026-10-14 |
| Filters | Labeled selects above the metrics | One sticky selection bar for the whole page: Category, Detected license, Reset (disabled at default) and section jumps. No visible labels; `aria-label` names each select. Section jumps are bold | User direction 2026-10-14 |
| Selection count | “N projects selected.” paragraph | “N/N selected.” at the end of the Shared names paragraph; the metric row repeats the selected total | User direction 2026-10-14 |
| Metrics | Four numbers | Ruled row of four; ratio metrics show “456 / 501” and a 4px linear proportion line | Literal values; linear geometry |
| Finding | Sentence | Sentence that states its scope (“Across the whole collection, …”) plus a whole-collection strip: top-10 star share against other mapped projects, drawn to scale | Finding keeps whole-collection scope |
| Charts 01–06 | Fixed-viewBox SVG, label column truncated at 28 characters | HTML/CSS bar lists, zero-based and linear, labels wrap instead of truncating. Narrow screens put the label above its bar. Unknown bars are hatched as well as labeled. Categories sorted by count. Push and release charts are paired on one shared scale, marked “shared scale”. “Chart data” tables stay in folded disclosures | Linear from zero; no new dependency |
| Chart notes | Longer method captions | 01 “Projects can belong to several categories.” · 02 “Cached GitHub license identifiers.” · 03 “Top 10 specimen by GitHub stars.” · 06 “Days since last GitHub release (cached, excludes prereleases).” Method detail stays in the CSV, snapshot and this contract | User direction 2026-10-14 |
| Shared names | Count, closed group disclosures with name and URL | Open unit tally: one mark per tool, clustered by group, all marks the same Prussian fill and distinguished by shape (square for identical names, circle for spelling variants; no star, which reads as GitHub stars). Squares and circles start on separate lines. Zero counts stay in the legend; tag counts are not shown there. Below it, one folded “Show name groups” disclosure (summary: groups · tools) holds the comparison plates: repository, short description, category, license, GitHub stars, created, last push, ledger record, aligned across columns. “How groups are formed” is a nested fold-out at the bottom of “Show name groups”. Both disclosures are borderless and open from a right-facing arrow that turns down when open. A tally cluster opens the disclosure and jumps to its plate | Dense comparable information stays close; no implied progress |
| Grouping | Three groups filled in order (exact, capitalization, whitespace); a project placed in an early group is withheld from later ones | One matching key per name (see below). Two groups: Identical names and Spelling variants. Variant groups carry tags: Case, Spacing, Exact duplicates | Removes ordered withholding; see “Name grouping model” |
| Identical names | Name repeated | Owner set bold in the repository path | Emphasis anchored to the differing identifier |
| Spelling variants | Variants joined with a slash | Letters whose case differs are underlined in scarlet; a differing separator is underlined, and a missing one shows as a thin scarlet bar (form, not only color) | Scarlet directs attention |
| Relationship | Only in the contract | Paragraph states that a shared name does not mean the projects are related; plates list category/license “In common”, nothing more | Name matches do not establish aliases |
| Match-type labels | Sub-heading and summaries with rule captions | Scarlet block labels with mist type and no rule caption; rules live in “How groups are formed” | B29 label treatment |
| Coverage | Table | Mist band labeled “Whole collection” (no further scope sentence); each row has a linear bar of value / total, the count and the scope note. Collection dates and evidence links span the full width | Coverage keeps whole-collection scope |
| Project data | Downloads, folded table | Downloads as bordered links; table folded, summary shows the selected row count | Listing folded so the page stays short |
| Metrics | — | “Detected license available” reads “License detected” (metric and filter option) | User direction 2026-10-14 |
| Closing, footer | Logo, footer | Closing logo unchanged. Footer links become a list at the lower right: Return to project ledger, GitHub, Source revision, Metrics snapshot (UTC date) | B27; user direction 2026-10-14 |

Removed copy (user direction 2026-10-14): the Category and License labels above
the selects, the “compare owners and descriptions” advice, the three match-type
rule captions (“Identical displayed names…”, “Names match after lowercasing…”,
“Names match after removing whitespace…”), “Sorted by count”, “Missing or
unrecognized identifiers are Unknown”, and the coverage sentence “Unaffected by
filters. Counts are out of 501 unique projects.” The rendered “Unknown” labels and
the Whole collection label carry those meanings.

## Name grouping model

The current rules assign groups in order and withhold matched projects from later
groups. Names that differ in more than one way fall through. With the current
rules, “Open pilot” would match nothing: it lowercases to `open pilot`, not
`openpilot`, and the whitespace step preserves case and excludes OpenPilot and
openpilot, which the capitalization step already took. A third project “openbot”
would likewise stay unlisted beside the two exact OpenBots.

Proposed model: group first, then describe.

1. Deduplicate by canonical project ID.
2. Matching key: lowercase the displayed name, then remove Unicode White_Space,
   hyphen and underscore. Use `str.lower()` in Python and `toLowerCase()` in JS
   for parity (`casefold` has no JS counterpart).
3. Projects with the same key form one group; a group needs two distinct project
   IDs. Each project belongs to at most one group. Equality of keys is transitive,
   so groups cannot chain.
4. Kind: **Identical name** when all members display the same name, otherwise
   **Spelling variants**.
5. Tags on variant groups, not exclusive: **Case**, **Spacing** (whitespace,
   hyphen, underscore) and **Exact duplicates**. Tag counts do not sum to a total
   and are not drawn as shares.

Not matched: other punctuation (the dot can be part of a name), spelling and
sound-alikes. Automated phonetic matching was considered and rejected: every name
starts with “Open”, so short suffixes collide (Metaphone-style keys merge many
unrelated names), English-centric rules handle acronyms and digits poorly, and
“sounds like” is a judgment rather than a fact. If sound-alikes matter later, use a
reviewed data file with sources and check dates, shown as its own block outside
the counted total.

Effect on the 2026-10-14 snapshot: 18 tools in 9 groups instead of 16 in 8. The
new group is open-dashboard / OpenDashboard (Case, Spacing), which the current
rules miss because it differs in case and hyphen at once. A future “Open pilot”
would join OpenPilot and openpilot in one group of three (Case, Spacing).

## Unchanged

- Canonical-ID deduplication, filter behavior and project-once counting in
  shared names; histogram buckets and UTC day differences.
- Filters drive metrics, shared names, charts and the listing together; the
  finding and coverage keep whole-collection scope.
- “GitHub stars”, UTC dates, “Unknown” for missing licenses and dates.
- White/Prussian palette, Fraunces and Commit Mono, 4px spacing, native
  disclosures, closing mark, standalone report, downloads.

## Contract changes (applied in the implementation)

- **Chart rendering.** Replace “Native SVG … do the chart work” in
  OBSERVATORY.md with HTML/CSS bars rendered server-side, keeping the zero-based
  linear rule and the folded tables.
- **Description field.** Add `description` (the short description from
  `README.source.md`) to the thin projection. Document it in `snapshot.json`, the
  CSV columns and OBSERVATORY.md.
- **Category order.** Sorting the category chart by count changes it from catalog
  order; record this in OBSERVATORY.md.
- **Shared push/release scale.** Document that charts 05 and 06 share one maximum.
- **Name grouping.** Replace the ordered exact/capitalization/whitespace
  assignment in OBSERVATORY.md “Accounting” with the single-key model above, in
  both `shared_names` and `sharedNames`, with parity tests for case, whitespace,
  hyphen, underscore, mixed differences and exact duplicates inside a variant
  group.

## Implementation map

- `scripts/build_observatory.py`: render the selection bar, metrics, finding
  strip, bar lists, tally and plates, coverage rows and the folded listing
  server-side, so the no-JS page and `report.html` stay complete.
- `site/observatory.js`: re-render the same markup on filter change. Keep URL
  state for category and license, Back/Forward support and selection CSV export.
- `site/observatory.css`: replace the chart, shared-names and coverage blocks.
- Tests: update `test_observatory.js` and the Python tests for markup parity; run
  `python3 scripts/check_brand.py` and `scripts/check_observatory_browser.cjs`.

## Verification of the mock

- The page script reproduced the published aggregates: 501 projects, 456 with
  GitHub metrics, 3,611,407 stars, 344 detected licenses, 37.7% top-10 share,
  every chart row. The current shared-name rules gave 16 tools (10 exact, 6
  capitalization, 0 whitespace); the proposed model gives 18 tools in 9 groups
  (10 identical, 8 variants; tags Case 4, Spacing 1).
- Looked at once at 375px (the Shared names study) and once at 1280px (the full
  page). Keyboard, reduced motion and intermediate widths were not checked.
- Artifact limits: downloads link to the live files; selection CSV export and
  URL filter state are not present in the mock.
