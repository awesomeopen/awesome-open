# Weekly specimen draws

The hero draws seven distinct catalog projects with approved, present specimen
illustrations. GitHub presence, stars and category rank do not affect eligibility.
Selection is independent of jar fit. The seven photographic jars retain their
windows, heights, shadows, stickers, cork and interactions. Their left-to-right
order is original jars 1, 2, 5, 3, 4, 6, 7; occupants move with their vessels
([jar order](../brand/decisions/B-PR134-02.md)). Specimen interiors
are calibrated separately from the glass-light and crack geometry.

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
This is a reproducible pseudo-random draw. Names, stars,
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

Try all 5,040 assignments of the selected seven to the seven measured glass
interiors. Maximize the least-filled interior first, then total fractional fill.
Use source-matched, reviewed body spans where present, otherwise the complete
cut-out subject box or whole canvas. Equal fits break deterministically by
project ID. Selection remains independent of placement: the saved seven projects
and draw counts never change to improve a composition.

`scripts/build_jar_preview.py::SPECIMEN_INTERIORS` records fitting boxes in
percentages of each original photograph's full canvas. Separate photo-traced
`SPECIMEN_INTERIOR_CONTOURS` follow the inner walls, shoulders, curved floors and
leaning-lid occlusion. Convert those contours into window coordinates and keep
the clipping boundary fixed to the glass while existing specimen motion runs.
Do not clip at an arbitrary inset rectangle: an interrupted protrusion must meet
the visible inside wall. Glass feathering, cracks, lights, closures and vessel
layout dimensions retain their independent coordinates.

Fit the visible body wall-to-wall, preserving aspect ratio. Do not subtract a
horizontal motion inset: existing pointer/idle movement may pass behind the
stationary glass contour. Keep 2.25 CSS px of vertical clearance above/below the
height-limited subject, and put all remaining vertical slack above it so the
baseline sits near the glass floor. No opacity reduction, stretching, grouping
or original-art changes. Unreviewed or invalid composition metadata retains the
complete subject as the fitting target; peripheral motion may still meet the wall.

`SPECIMEN_BODY_SPANS` contains a reviewed horizontal span for OpenObserve's
mineral column, keyed to its original source hash. It excludes the left ribbons
and forked foot tips from scale/centering, but retains complete subject height.
Those protrusions are still rendered and only disappear at the physical glass
boundary. Replaced source art automatically falls back to whole-subject fitting.
The original and record/Spotlight archive illustrations remain complete.

Before the first scheduled edition activated on October 19, OpenObserve used the
commissioning layout's fixed 300% zoom and horizontal clipping, about 154px tall
at the enhanced footprint. Whole-silhouette fitting reduced it first to about
83px and then 64px. Body-led placement restores approximately that original scale
inside the more accurate glass contour. No browser pixel analysis is introduced. Visual review includes
matched before/after pixels, current occupants, extreme tall/wide approved art,
mobile, active motion and reduced motion. Tests alone do not establish aesthetic
acceptance.

`/spotlight/` shows current and past scheduled editions, newest first, with permanent
`#YYYY-WNN` ISO week links, such as `/spotlight/#2026-W43` for the display week
beginning 2026-10-19. Use the ISO week year even at calendar-year boundaries.
Current-edition values and edition headings use the same label; saved record dates
retain their existing ISO date format. Show saved names/categories, illustrations when
still present, and literal draw details. Stars are not
a selection metric and are omitted. Future draws remain committed evidence but
are omitted from the archive listing/download until their display week. Snapshot
copy stays frozen; illustration files retain their existing source identity and
may change under the ordinary artwork review process (not a byte-frozen image
archive). Links to removed catalog records use their saved official source URL.

The page uses the Observatory route shell (B42, B44): shared header and nav,
display heading, four literal metrics (current edition, editions shown, distinct
projects shown, eligible count at the last draw), then every edition as a compact seven-column tray.
Category metadata uses 10px type with -0.05em letter-spacing. Each edition folds its draw record. The scope and method
blocks are omitted; the section jump navigation is hidden. The header links read Catalog, Observatory, Scoreboard, Spotlight in that order. The closing mark and
patterned footer remain; Download draw records · Draw contract appears immediately
above GitHub, followed by the source revision. The download is
`/spotlight/draws.json`. See [the route decision](../brand/decisions/B-PR134-01.md).

Body-led wall clipping is proposed in [B-PR143-01](../brand/decisions/B-PR143-01.md).
