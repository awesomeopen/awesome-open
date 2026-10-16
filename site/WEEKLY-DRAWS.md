# Weekly specimen draws

The hero draws seven distinct catalog projects with approved, present specimen
illustrations. GitHub presence, stars and category rank do not affect eligibility.
Selection is independent of jar fit. The seven photographic jars, their order,
windows, heights, shadows, stickers, cork and interactions stay unchanged.

## Calendar and publication

Weeks are Monday–Sunday in `America/New_York`. On the first successful normal
publisher run in a week, `scripts/weekly_draw.py` records a draw for the following
week. Subsequent runs retain it, even if new artwork arrives. The existing daily
workflow drives this; there is no browser timer, external automation or additional
GitHub collection. Activation occurs on the first successful normal publication
in the display week, not necessarily at midnight. Cached backfill publication
and offline builds neither advance dates nor create draws.

`data/weekly_draws.json` is publisher-owned, committed alongside the other caches.
Only successful publication establishes an edition; unpublished retries are
recomputed against current main. The archive records the exact candidate IDs,
excluded IDs, eligible count, source SHA, seed, algorithm, dates and selected
project snapshots. A rerun never replaces an accepted edition. Missing weeks
are not retrospectively drawn. Launch has no fabricated past: the original
seven remain until the first recorded draw reaches its display week.

## Selection and cooldown

Algorithm `sha256-week-project-v1` orders candidate IDs by the SHA-256 digest of
`seed + "\n" + project_id`, breaking ties by project ID, and takes seven. The seed
is `awesome-open/weekly-draw/v1/YYYY-MM-DD`, where the date is draw-week Monday.
This is a reproducible pseudo-random draw, not a security lottery. Names, stars,
repository order and image aspect ratio do not affect selection probability.

Initial cooldown: four complete subsequent scheduled display weeks. Exclude any
project selected for one of the four preceding display weeks. If fewer than seven
eligible projects remain, make no draw; do not shorten cooldown silently. Retry
later in the same week if enough new illustrations become available. Retain the
most recent complete, still-illustrated edition in the header, labeling its
original week. If no edition can be displayed, use the original commissioning
set. Removing a selected project's art never causes a same-week redraw.

Eligibility uses the same manifest validation as the catalog: approved art,
matching canonical project identity/path, present regular WebP, valid dimensions
and descriptive alt text. A cut-out is optional; absent art is never eligible.

## Fit and archive

Try all 5,040 assignments of the selected seven to the seven fixed windows.
Maximize total occupied subject area, using source-matched cut-out subject boxes
where available and whole-image bounds otherwise. Scale and center the subject
inside its window with 12% room for motion. Do not crop the subject or change jar
geometry. Equal fits break deterministically by project ID. Existing responsive
art derivatives are reused where available; newly eligible art uses its committed
full-resolution source/cut-out without a runtime image-processing dependency.

`/draws/` shows current and past scheduled editions, newest first, with permanent
`#week-YYYY-MM-DD` links. Show saved names/functions/categories, illustrations when
still present, first/returning appearance and literal draw details. Stars are not
a selection metric and are omitted. Future draws remain committed evidence but
are omitted from the archive listing/download until their display week. Snapshot
copy stays frozen; illustration files retain their existing source identity and
may change under the ordinary artwork review process (not a byte-frozen image
archive). Links to removed catalog records use their saved official source URL.
The standalone ledger links to the hosted archive; no jar animation is embedded.

The page uses the Observatory route shell (B42, B43): shared header and nav,
display heading, four literal metrics (current edition, editions shown, distinct
projects shown, eligible count at the last draw), a mist scope band, then the
latest edition as a four-column specimen tray and earlier editions as a compact
seven-column tray. Each edition folds its draw record; the method and download
follow, then the closing mark and patterned footer with source revision.
