# Reviewed name-change history

`data/project_history.json` is an optional, curated event ledger. It adds sourced
history to the shared specimen record. The full
catalog JSON retains each event for later reuse. Missing records mean unreviewed,
not that a project has never changed its name.

## Schema 1

The document contains `schema_version: 1` and an `events` array. Each event has:

- `id`: unique, stable lowercase hyphenated event ID.
- `project_url`: an existing canonical catalog URL. The event does not change it.
- `kind`: `software_rename`, `repository_rename` or `owner_transfer`.
- `old_name`, `new_name`: evidenced software names, repository paths or owners,
  appropriate to the event kind. Alias corrections and forks are not renames.
- `occurred`: null when the occurrence date is unknown, otherwise an object with
  `value`, `precision` (`day`, `month`, `year`), `basis` (`announcement`,
  `implementation`, `effective`, `release`) and an official `source_url` from
  the event's sources with the same role. Values preserve precision as
  `YYYY-MM-DD`, `YYYY-MM` or `YYYY`; never invent a first day of a month/year.
- `sources`: one to five objects with HTTPS `url`, plain `title`, `role` (one of
  the bases above, or `identity`) and a dated source's ISO `date`, or null.
  A source's publication/merge/release date is not automatically the event date.
- `checked_at`, `reviewed_by`: actual review provenance.
- `note`: what the evidence establishes and any real uncertainty. It appears in
  folded Name-change evidence for events off the axis and stays in the published
  data for plotted ones; do not add sentences disclaiming claims the record never
  makes ([B-PR150-01](../brand/decisions/B-PR150-01.md)).
- Optional `first_observed_at`: our first observation date, only when known.
  A new review does not backfill a previously unknown first-observation date.

Review the official sources, identity continuity, date meaning and precision.
Pin source revisions where useful. An API redirect/same repository ID can support
repository continuity but does not date a move or prove a software rebrand.
Current README wording on an old-dated webpage is insufficient: old articles
can be rewritten. Preserve the distinction between software names and paths.

The first two records are OpenTF → OpenTofu's public naming announcement on
2023-09-20, and OpenDevin → OpenHands' project-wide name change merged into main
on 2024-08-19. The latter changed the README and code, and was included in the
2024-08-23 release. The release is supporting evidence.

## Display and future counting

Only verified day-precision occurrence dates enter the timeline. They join the
existing Repository record timeline ([B-PR150-01](../brand/decisions/B-PR150-01.md)):
a true-date marker on the axis and a label above it reading, for example,
"Renamed: OpenDevin → OpenHands (i)" with the date below. The "(i)" disclosure
opens the sources line only, every source link with its role and date; the label
already gives the names and date, and the reviewer is not shown
([B-PR158-01](../brand/decisions/B-PR158-01.md)). Upper labels whose dates are close climb a row instead of
moving their markers; rename labels sit above the release label. Repository
creation/release/push retain their literal meanings. The axis spans all
verified dates, including events before the current repository existed; the
repository lifetime segment still starts at repository creation. Missing
repository dates are omitted, without hiding a verified project-name event.
Records without reviewed history keep their existing timeline unchanged.

Approximate/unknown occurrence dates, review dates and first observations never
enter the axis or future monthly occurrence counts. Events without an exact date
stay in the folded, secondary **Name-change evidence** block. An announcement
about a future change needs that distinction in its evidence; do not mark a
proposal as an accomplished rename.

The same renderer serves fetched drawers, full record pages, exhibition and
offline output. The standalone includes its evidence in the catalog JSON.
Source links need a network; no runtime collection is introduced. The "(i)" is
a native disclosure and works without JavaScript.

Future Observatory use must count event IDs once, retain event kinds and date
bases, and state coverage. A release corroborating an implementation is not a
second rename. Category memberships can overlap. A current-catalog-only backfill
misses projects that renamed away from Open. Ex-Open archival eligibility remains a separate
curated decision; the proposed frozen archive is not implemented here.

## Checks

Run the full offline Python suite and brand checks, build production-shaped
output, and run the existing browser suite. History regressions cover invalid
schema/identity/dates, unknown and coarse dates, source roles, duplicate events,
the rename label and its details, stacked close labels, pre-repository events and
absent repository dates. Browser checks exercise the seeded records at 320px and
desktop in drawers, full records and standalone output: label text, keyboard
opening of "(i)", the source link and details fitting the viewport.
