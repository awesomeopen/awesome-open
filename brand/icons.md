# Icon map

Status: proposed ([B-PR101-01](decisions/B-PR101-01.md)). No icon artwork exists yet and no generator reads the
manifest. Audited against main `4bc3d97` on 2026-10-16; line references point to
that revision and drift as code changes, so each one also names an anchor string.

The machine-readable twin is [`site/brand/icons.json`](../site/brand/icons.json).
Both must carry the same IDs, shapes, tokens and sizes; change them together.

## What an icon may say

An icon restates an evidence label. It never replaces the label and never adds a
judgment the label does not make.

- **State, not quality.** Icons describe what we know about a record and how
  recently we observed it. “Failed” means our retrieval attempt failed; it says
  nothing about the project. A Scorecard 3/10 is a value with no state icon.
- **Unknown is not negative.** `state.unknown` is muted and dashed, never scarlet
  ([guide, Status](../site/RETRO-SCRAPERISM.md)).
- **Shape carries meaning; colour confirms it.** Every glyph must be
  distinguishable in monochrome and in forced-colours mode. Colour is never the
  only signal ([guide, Color](../site/RETRO-SCRAPERISM.md)).
- **Aged is a modifier, not a midpoint.** A stale value had a good observation
  that is now old or followed by a failed attempt. It gets the `badge.aged`
  overlay, not a step between current and failed.
- **Do not mark everything “cached”.** The whole site is a snapshot. Use the aged
  state only where the code already distinguishes retained values.
- **Always pair with text.** Decorative icons next to their label get
  `aria-hidden="true"` / empty `alt`. An icon that stands alone (for example in
  the 11px status pill) needs an accessible name equal to the paired label.

### Excluded on purpose

No “verified”, “safe”, “healthy”, “maintained”, “trending” or “popular” glyphs; no
shields, padlocks, warning triangles, stamps or seals; no filled or repeated star
ratings; no vendor logos or mascots (container, package-manager or forge marks).
Each would turn a literal label into a verdict or impersonate a third party. The
existing search loupe, botanical mark and fruit stay as they are and are outside
this set.

## Colour

Tokens from [`site/design/tokens.css`](../site/design/tokens.css). Ratios are
against `--rs-paper` (#FFFFFF); WCAG 1.4.11 asks 3:1 for graphical objects.

| Token | Hex | On paper | Role in this set |
| --- | --- | --- | --- |
| `--rs-emerald` | #006B4F | ≈6.5:1 | Current, reviewed (positive status with words) |
| `--rs-scarlet` | #B62420 | ≈6.4:1 | Our attempt failed; nothing else |
| `--rs-blueprint` | #0B2546 | ≈15.4:1 | Aged, partial, scope, views, info |
| `--rs-muted` | #465665 | ≈7.6:1 | Pending, none, unknown, badge |
| `--rs-ink` | #111820 | ≈18:1 | Nouns, links, controls |
| `--rs-amber` | #FFC800 | ≈1.6:1 | **Not an icon stroke.** Allowed only as a fill inside an ink outline |

There is no yellow checkmark: amber (≈1.6:1) fails the contrast floor on white. Pending
uses a muted dotted ring instead. On Prussian surfaces (footer, departure band)
draw every glyph in `--rs-paper` or `--rs-trace`; state colours are not used
there.

## Sizes and drawing grid

Draw every icon once as a 96px master; 96 divides evenly into all three display
sizes (8×, 6×, 4×). Do not simply downscale: each size has its own detail level.

| Size | Display px | Stroke | Padding | Detail | Typical use |
| --- | --- | --- | --- | --- | --- |
| `s` | 12 | 1.5px | 1px | Silhouette only; no badge | 11px `.signal-status` pill, 12px fine print, `feature-source` |
| `m` | 16 | 1.5px | 1px | Silhouette plus one interior detail | 15px evidence-note body, chips, link suffixes, summaries |
| `l` | 24 | 2px | 2px | Restrained pencil character allowed | Headings, Observatory coverage legend, empty states, setup chips |

Bases are part of the grammar:

- **Ring** = shared evidence state (automated observation).
- **Square, 2px radius** (`--rs-radius`) = human review.
- **No container** = links, controls, nouns. Rings are reserved for states, so
  `control.info` is a bare “i”, not the usual circled “i”.
- `badge.aged` sits in the lower-right quadrant (about 45% of the canvas) with a
  1px paper knockout around it.

### Production

- Output small sizes (`s`, `m`) as hand-tuned SVG on the pixel grid with
  `stroke="currentColor"` / `fill="currentColor"`, so CSS applies the token and
  forced colours work. Image generation cannot hit a 12 or 16px grid reliably:
  generate the 96px sheet, then trace and tune.
- `l` may remain a drawn raster (WebP, transparent) when the pencil character
  matters; otherwise use the same SVG.
- File names: `site/brand/icons/{id}-{size}.svg`, for example
  `state.failed-m.svg`. Add byte provenance next to them and refresh
  `brand/assets.lock.json` when they land.
- Line style: Retro-Scraperism ink, square caps, no gradients, no shadows, no
  perspective except where a shape says “isometric”.

### Brief for the drawing skill

> Draw one sheet of icon masters at 96×96 px each, transparent ground, ink
> (#111820) only, consistent stroke weight, square caps, no shading. Use the
> “Shape” column of `brand/icons.md` verbatim for each ID and label each cell
> with its ID. Rings mean automated evidence state, rounded squares mean human
> review, everything else has no container. Do not draw shields, stamps, seals,
> warning triangles, stars as ratings or any vendor logo. Colour is applied
> later from tokens; do not colour the masters.

Draw the `today` rows first; `planned` rows can come in the same sheet so the
set stays consistent.

## Map

`today` = the label or element is rendered now and would take the icon.
`planned` = data or a likely feature exists but nothing renders it yet.

### A. Shared evidence states

Ring base. One glyph serves retrieval checks, repository-metric freshness and Observatory coverage; the family is the usage, the state is the drawing.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `state.current` | today | A value was observed within its freshness window | “Available”; “Cached GitHub metrics (coverage count)” | Check mark inside a closed ring | `--rs-emerald` | s m l | scripts/build_site.py:239 `signal-status`<br>scripts/signals.py:79 `available`<br>scripts/build_observatory.py:704 coverage states |
| `state.aged` | today | A last good value is retained, but it is old or the latest attempt did not succeed | “Stale”; “Stale GitHub metrics; last successful observation: …” | Check mark inside a closed ring with the aged badge in the lower-right quadrant | `--rs-blueprint` | s m l | scripts/build_site.py:239 `signal-status`<br>scripts/signals.py:69 `stale`<br>scripts/build_site.py:508 `metrics_freshness`<br>scripts/build_site.py:740 About the data “Stale:”<br>scripts/build_observatory.py:775 “Cached measurements may be stale” |
| `state.partial` | today | Results were returned but not all of them carry a score | “Partial”; “Inconclusive”; “Aggregate inconclusive” | Ring with the left half filled solid | `--rs-blueprint` | s m l | scripts/build_site.py:239 `signal-status`<br>scripts/signals.py:78 `partial`<br>scripts/build_site.py:183 `Aggregate inconclusive`<br>scripts/build_site.py:187 `Inconclusive` |
| `state.pending` | today | No check has completed yet: not checked, queued or deferred | “Pending”; “Provider pending”; “Not checked”; “Check deferred”; “Release not checked.” | Ring of eight evenly spaced dots, empty centre | `--rs-muted` | s m l | scripts/build_site.py:163 fetch_status labels<br>scripts/build_site.py:153 `Release not checked.`<br>scripts/signals.py:67 `pending` |
| `state.none` | today | The provider was asked and returned no result | “No result returned” | Closed ring with one short horizontal dash | `--rs-muted` | s m l | scripts/build_site.py:163 `not_found` |
| `state.failed` | today | Our retrieval attempt failed or the source was unavailable; says nothing about the project | “Unavailable”; “GitHub metrics unavailable; no successful observation.” | Diagonal cross inside a closed ring | `--rs-scarlet` | s m l | scripts/build_site.py:163 `error`<br>scripts/signals.py:67 `unavailable`<br>scripts/build_site.py:502 `metrics_freshness` |
| `state.unknown` | today | The value is not recorded or not detected; unknown, never negative | “Unknown”; “Push date unknown”; “License unknown”; “Not recorded”; “GitHub metrics: Unknown” | Dashed ring with a question mark | `--rs-muted` | s m l | scripts/build_site.py:587 `Detected license` Unknown<br>scripts/build_site.py:498 `GitHub metrics: Unknown`<br>scripts/build_site.py:728 filter options<br>scripts/build_site.py:729 `Not recorded`<br>scripts/build_observatory.py:304 `obs-unknown` |
| `badge.aged` | today | Overlay for retained or old values on any base glyph | “Stale (with the base glyph's own label)” | Small clock face (two hands) in a paper-knockout disc; composited onto another glyph's lower-right quadrant | `--rs-muted` | m l | scripts/signals.py:69 `stale` |

### B. Human review

Square base, so review by a person never looks like an automated check.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `review.current` | today | A person reviewed this evidence against cited sources on the stated date | “Reviewed {date}”; “Checked {date}”; “Approved evidence record” | Check mark inside a closed square with 2px radius | `--rs-emerald` | s m l | scripts/build_site.py:572 `function-provenance`<br>scripts/build_site.py:537 `evidence-date`<br>scripts/deployment.py:153 `Approved evidence record` |
| `review.pending` | planned | A review record exists but is not approved yet | “Review pending” | Square drawn as evenly spaced dots, empty centre | `--rs-muted` | s m l | scripts/deployment.py:49 `review_status` pending (not rendered today) |

### C. GitHub status

Literal provider status.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `status.archived` | today | GitHub reports the repository as archived | “Archived on GitHub” | Closed archive drawer with a horizontal handle | `--rs-ink` | s m l | scripts/build_site.py:392 `label-status` |

### D. Links

No container; direction or object only.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `link.external` | today | Leaves the site for an external source | “Explore {name} on {host}”; “Feature source ↗”; “Provider source”; “Hacker News stories”; “{tag_name}”; “{summary source title}”; “{alternative name}” | Arrow leaving the top-right corner of an open square | `--rs-ink` | s m l | scripts/build_site.py:492 `departure-arrow`<br>scripts/build_site.py:451 `feature-source`<br>scripts/build_site.py:231 `Provider source`<br>scripts/build_site.py:550 `hn-chart`<br>scripts/build_site.py:173 `note-value`<br>scripts/build_site.py:572 summary sources<br>scripts/build_site.py:537 alternative links |
| `link.permalink` | today | Stable link to this specimen record | “Specimen: {name} (permalink)”; “QR code: permalink to {name}” | Two interlocking chain links | `--rs-ink` | s m l | scripts/build_site.py:402 `permalink`<br>scripts/build_site.py:397 `label-qr` |
| `link.commit` | today | Links to the exact repository commit a result came from | “Repository commit {sha}” | Short horizontal line through a small open circle | `--rs-ink` | s m | scripts/build_site.py:197 Scorecard commit |
| `link.download` | today | Downloads a file | “Download”; “Download selection CSV”; “Download standalone report” | Down arrow onto a short baseline | `--rs-ink` | s m l | scripts/build_site.py:740 `standalone.html`<br>scripts/build_observatory.py:775 `export-csv`<br>scripts/build_observatory.py:847 report |
| `link.data` | today | Opens raw evidence or catalog data | “HN evidence”; “Comparison evidence”; “Catalog JSON”; “GitHub metric snapshot”; “Release and Scorecard evidence”; “Star-history evidence” | Curly braces { } on a page with a folded corner | `--rs-ink` | s m | scripts/build_site.py:740 About the data links<br>scripts/build_observatory.py:757 `evidence_links` |
| `link.copy` | planned | Copies a link or value to the clipboard | “Copy link” | Two offset overlapping rectangles | `--rs-ink` | s m | — |

### E. Disclosure and controls

No container.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `disclose.closed` | today | A native disclosure that is closed | “Table of contents”; “Filters”; “More filters”; “About the data”; “View source & retrieval history”; “Check results and scan provenance”; “View setup facts & sources” | Plus sign | `--rs-ink` | s m | scripts/build_site.py:725<br>scripts/build_site.py:728<br>scripts/build_site.py:729<br>scripts/build_site.py:740<br>scripts/build_site.py:239 `note-provenance`<br>scripts/build_site.py:196 `signal-checks`<br>scripts/deployment.py:154<br>site/styles.css:445 `.drawer-sign` |
| `disclose.open` | today | A native disclosure that is open | (same summaries, open state) | Minus sign, same length and stroke as the plus | `--rs-ink` | s m | site/styles.css:457 `.drawer-sign` open |
| `control.reset` | today | Clears filters back to the default view | “Reset filters ↺” | Open circular arrow turning counter-clockwise | `--rs-ink` | s m | scripts/build_site.py:733 `clear-filters` |
| `control.info` | planned | Links a term to its definition | “Stale”; “OpenSSF Scorecard”; “Square-root scale”; “Registry ID”; “Folio number”; “How groups are formed” | Lowercase i with a heavy dot, no container (rings belong to states) | `--rs-blueprint` | s m | scripts/build_site.py:740 About the data definitions<br>scripts/build_site.py:557 `star-window`<br>scripts/build_site.py:400 `title="Registry ID"`<br>scripts/build_observatory.py:387 shared names |
| `control.sort-asc` | planned | Ascending sort order | “Name A–Z” | Up arrow beside three bars of increasing length | `--rs-ink` | s m | scripts/build_site.py:733 `sort-order` |
| `control.sort-desc` | planned | Descending sort order | “Most stars”; “Latest push” | Down arrow beside three bars of decreasing length | `--rs-ink` | s m | scripts/build_site.py:733 `sort-order` |
| `control.filter-active` | planned | At least one filter is applied | “Filters” | Funnel with a small filled dot at the upper right | `--rs-ink` | s m | scripts/build_site.py:728 `filter-options` |

### F. Observatory

Scope and view markers.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scope.collection` | today | Figure covers the whole collection and ignores filters | “Whole collection” | 3×3 grid of filled squares | `--rs-blueprint` | m l | scripts/build_observatory.py:774 `obs-label` |
| `scope.filtered` | planned | Figure covers only the current filter selection | “Selection” | 3×3 grid with four filled and five outlined squares | `--rs-blueprint` | m l | scripts/build_observatory.py:771 `observatory-filters` |
| `view.chart` | today | Chart view or chart data | “Chart data” | Three horizontal bars from a shared left axis | `--rs-blueprint` | s m | scripts/build_observatory.py:562 `obs-chart-data` |
| `view.table` | today | Tabular view of the records | “Data table” | Ruled grid of three rows and two columns | `--rs-blueprint` | s m | scripts/build_observatory.py:775 `project-records` |

### G. Setup facts and package channels

Values from `scripts/deployment.py`. Package channel states are upstream-documented facts, not our check.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `run.cli` | planned | Runs from a command line | “Command line” | Prompt chevron followed by an underscore | `--rs-ink` | m l | scripts/deployment.py:11 `RUN_MODES` |
| `run.desktop` | planned | Runs as a desktop application | “Desktop application” | Application window with a title bar | `--rs-ink` | m l | scripts/deployment.py:11 `RUN_MODES` |
| `run.local-web` | planned | Runs a browser interface on the local machine | “Local browser interface” | Browser window with a small house in the address bar | `--rs-ink` | m l | scripts/deployment.py:11 `RUN_MODES` |
| `run.server` | planned | Runs as a self-hosted server | “Self-hosted server” | Two stacked rack units with status dots | `--rs-ink` | m l | scripts/deployment.py:11 `RUN_MODES` |
| `run.library` | planned | Used as a library or SDK inside other code | “Library / SDK” | Three stacked blocks, top block offset | `--rs-ink` | m l | scripts/deployment.py:11 `RUN_MODES` |
| `run.firmware` | planned | Runs as device firmware | “Device firmware” | Chip outline with pins on two sides | `--rs-ink` | m l | scripts/deployment.py:12 `RUN_MODES` |
| `install.binary` | planned | Installed from a downloadable binary or archive | “Downloadable binary / archive” | Archive box with a zip seam | `--rs-ink` | m l | scripts/deployment.py:13 `INSTALL_METHODS` |
| `install.installer` | planned | Installed with an installer | “Installer” | Open box with an arrow entering it | `--rs-ink` | m l | scripts/deployment.py:13 `INSTALL_METHODS` |
| `install.container` | planned | Runs from a container image | “Container” | Isometric cube with ribbed sides (generic, no vendor mascot) | `--rs-ink` | m l | scripts/deployment.py:14 `INSTALL_METHODS` |
| `install.package-manager` | planned | Installed through a package manager | “Package manager” | Parcel with a tied label | `--rs-ink` | m l | scripts/deployment.py:14 `INSTALL_METHODS` |
| `install.source` | planned | Built from source | “Build from source” | Angle brackets around a slash | `--rs-ink` | m l | scripts/deployment.py:15 `INSTALL_METHODS` |
| `install.firmware-image` | planned | Flashed as a firmware image | “Firmware image” | Chip outline with a down arrow above it | `--rs-ink` | m l | scripts/deployment.py:15 `INSTALL_METHODS` |
| `channel.documented` | planned | Upstream documents this package channel | “documented” | Page with three text lines | `--rs-ink` | s m | scripts/deployment.py:106 package `status` |
| `channel.disabled` | planned | Upstream documents the channel as disabled | “disabled” | Page with three text lines and a diagonal slash | `--rs-muted` | s m | scripts/deployment.py:106 package `status` |
| `channel.deprecated` | planned | Upstream marks the channel as deprecated | “deprecated” | Page with three text lines, the lines struck through | `--rs-muted` | s m | scripts/deployment.py:106 package `status` |
| `channel.discontinued` | planned | Upstream states the channel is discontinued | “discontinued” | Empty page with a diagonal cross | `--rs-ink` | s m | scripts/deployment.py:106 package `status` |

### H. Record changes

Snapshot-to-snapshot facts; no collector exists yet.

| ID | Status | Meaning (literal) | Paired label (current text) | Shape | Token | Sizes | Source today |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `change.moved` | planned | The canonical URL now redirects elsewhere | “Moved to {url}” | Arrow from one small square to another | `--rs-ink` | s m | — |
| `change.renamed` | planned | The project name changed | “Renamed from {name}” | Label tag with a small right arrow | `--rs-ink` | s m | — |
| `change.mirror` | planned | The repository is a mirror or fork of another record | “Mirror of {name}”; “Fork of {name}” | Two identical squares offset diagonally | `--rs-ink` | s m | — |
| `change.new` | planned | Added since the previous snapshot | “New since {date}” | Small eight-ray spark (not the brand asterisk) | `--rs-blueprint` | s m | — |
| `change.updated` | planned | Record fields changed since the previous snapshot | “Changed since {date}” | Page with a filled dot at the upper-right corner | `--rs-blueprint` | s m | — |
| `change.license` | planned | The detected license identifier differs from the previous snapshot | “Detected license changed from {old}” | Page with a small delta (Δ) in the lower-right | `--rs-ink` | s m | — |

### Not icons

- Unknown bars in Observatory charts keep their hatch pattern
  (`site/observatory.css:141` `.obs-bar-unknown`); it is a fill, not a glyph.
- The departure “↗” and the reset “↺” are typographic characters today. Swapping
  them for `link.external` / `control.reset` is an implementation choice to
  review, not part of this map.

## Maintaining the map

1. Add or change the row here and the entry in `site/brand/icons.json` in the
   same PR. A new state needs a literal meaning tied to a field or label in code.
2. Record new rules as a PR-scoped record under [decisions/](decisions/) following the [decision guide](DECISION-GUIDE.md); when artwork lands, add the
   family to the [asset index](assets.md) with provenance and refresh the lock.
3. Before implementing an icon, re-check the referenced line and label against
   the current source.
