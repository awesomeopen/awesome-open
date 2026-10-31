# Visual system

The detailed specification remains [site/RETRO-SCRAPERISM.md](../site/RETRO-SCRAPERISM.md).
The exact token values live in [site/design/tokens.css](../site/design/tokens.css).
Update both in one PR when changing the system. The [HTML reference](../site/design/index.html)
demonstrates the system; the current generated production entry point demonstrates
the full application. Historical demo routes do not establish current behavior.

## Current contract

- High-contrast white/cool mist, Prussian blue and dark ink. Restrained scarlet
  directs attention. Saturated color may belong to specimens and jar lighting.
- Półtawski Nowy regular 400 headings and wordmark; Commit Mono ledger, prose and metadata. Automatic optical sizing, restrained tracking, consistent 16/24/32px spacing. Keep bundled provenance and SIL OFL notices.
- Ruled, searchable records and expandable evidence. Dense comparable information
  stays close; do not replace the ledger with generic cards or forced AIDA.
- Plain labeled controls, visible focus, native disclosures, touch/keyboard
  access, readable narrow layouts and a useful no-JavaScript fallback.
- Motion has a purpose, pause control and reduced-motion fallback. No mandatory
  scroll trapping, GSAP pinning, random font changes or theme lotteries.
- Reject parchment/kraft/sepia page treatments, wax-seal controls, fake risk
  stamps and decorative mechanisms everywhere. The older Library brief is a
  historical input, not the current specification.

## Implemented application and bounded exceptions

The seven-jar photographic hero was promoted to production in PR #26. Preserve
its glass/photo layers, original drawn contents, shallow depth, selection light,
brief vapor, pause and reduced-motion behavior. Photographic glass is a deliberate
container treatment; specimens keep FOSSoligy's drawing rule.
Colored jar lighting is decorative, not a status classification. This specific
approved component takes precedence over generic “no glow” guidance.

The header combines the botanical mark, Awesome Open* wordmark and compact search.
Typing filters; search submit jumps to the first result. Two crack stages lead to
inspection on the third click, which restores the glass. Preserve the calmer first
crack stage. Native navigation remains available.

Expanded records use the specimen plate below. The normal ledger loads a plate
on demand and retains a full-record fallback for no-JavaScript access and printing;
the fallback line is hidden while loading and after success, and returns on failure
([B-PR126-01](decisions/B-PR126-01.md));
static record pages reuse the B42 route shell and are the complete printable
record. See [B-PR111-01](decisions/B-PR111-01.md) and the
[loading contract](../site/DETAIL-LOADING.md). Missing
artwork leaves no placeholder. Reviewed alternatives are the evidence grid's last
row. The HN and stars “past 2y” window is stated in their popups. Repository departure
links name recognized hosts; homepage and unrecognized destinations use “Explore [name]”. ID tooltips name the identifier type: “Registry ID” and
“Folio number”. These four refinements were initially present only in the private
Sites output; this PR restores them to the generator.

Collapsed ledger numbers show the current visible result position, starting at 001
and updating with sorting and filtering. Expanded Folio and Field notes numbers
retain alphabetical catalog position; Registry IDs and permalinks retain URL-based
identity. See [B-PR104-01](decisions/B-PR104-01.md).

The footer uses one transparent valley/abyssal image per load over Prussian blue,
with a static masked upper fade and clear reading space. Panoramas keep their native pixel dimensions, centered horizontally and bottom aligned at every viewport width; clip overflow rather than resize. Excess bottom padding is cropped before lossless WebP conversion, with the original source revision/hash, crop rectangle, output dimensions and checksum recorded in footer provenance. Its data notes default
open; the coffee support link has its own paragraph. Black footer metadata
backings are a specific implemented choice.

The site publishes no single-file download of the ledger or the Observatory
([B-PR176-01](decisions/B-PR176-01.md), [B-PR184-01](decisions/B-PR184-01.md)).
Verify copy and evidence changes in the ledger and the static record pages.

## Review

Check the affected component, not an invented whole-site redesign. For visible
changes check the relevant desktop/narrow states, keyboard/focus, reduced motion,
real asset paths and output modes. Record unavailable browser checks explicitly.
Do not mark a reference “approved” merely because a build succeeds.

## Icons (B-PR101-01, proposed)

Status, link, control and setup icons follow the [icon map](icons.md). Icons
restate a visible evidence label and add no judgment of their own. No
icon artwork is implemented yet. Icons are hand-written SVG, not
Speculative FOSSoligy drawings ([B-PR102-01](decisions/B-PR102-01.md)).

## Specimen plate for every record (B29)

Reviewed aliases sit directly below the Field notes heading, one name per line,
with “Also known as:” on the first line and official source links on the names.
Omit the block when only the canonical display name or no aliases are present.

The expanded record is one plate for all projects; the bounded three-record study
(B13–B15) and its plain restoration (B24) are superseded. Order: Function statement and reviewed prose, the specimen,
feature notes, the specimen label, then the fixed evidence grid
([B-PR158-01](decisions/B-PR158-01.md)) ending with the centered “Explore”
departure on a Prussian band.

- The illustration stands on a decorative contour “floor”, seeded by Registry ID and
  confined to the lower half. Contours encode no data. The floor is drawn only behind a
  transparent cut-out derivative so it never crosses the drawing.
- Artwork retains its 627px canvas-width cap, shrinking to available width without
  changing proportions (a 2:1 downscale for 1254px sources; some sources are 1024px).
  Stored subject bounds compact the vertical field with 8% source-height safety
  padding above and below; the full image remains rendered without clipping. The
  floor follows the subject baseline and the label stays with the specimen. Missing
  or invalid bounds keep the full canvas. A frameless loupe magnifies the displayed
  drawing 2× under the pointer or a tap. No sway: rotating a
  raster blurs it. Opening draws the floor and settles the art once; reduced motion is static.
- Up to two feature notes carry small/tiny enlarged windows of the drawing joined by
  scarlet leader lines from the ground, echoing the jar captions. Notes are sourced
  software facts; no anchors are placed on the drawing.
- The label overlaps the illustration by 4em using negative margin to reclaim flow
  space. It uses 65% width (a 320px minimum capped at available width for legibility),
  white background, 1px rule border, 2px radius and 0.8 opacity. Links have no
  underline; the QR code has a 2px white border. Without artwork, the label stays
  in normal flow inside the plate.
- Label contents: a QR code of the permalink, “Awesome Open* · Field
  record” (or “Archived on GitHub” when GitHub reports it), name, Registry ID · Folio,
  “Domain:” with every domain, and the permalink. No paper or object treatment (B28).
- Section labels are blocks with mist type and no horizontal rules inside the plate;
  spacing and labels carry the hierarchy. “I / Function” and “Explore” are scarlet
  (5.86:1); grid labels II–VI are muted grey (6.9:1). Chart axes remain.
- The project name in the reviewed prose is highlighted on scarlet with white type.
  A Function statement over 90 characters steps down to 24–30px.
- Evidence grid ([B-PR158-01](decisions/B-PR158-01.md)): eight columns of white
  boxes (1px Prussian border, 2px radius) on a mist panel, four below 1100px, one
  below 720px. Fixed rows and numbers: II / Repository record (stars, license,
  created, push; then the timeline), III / Observations & evidence (GitHub stars and
  HN sparklines on a shared baseline, a reserved box, OpenSSF Scorecard), IV / Release
  record, a reserved box, V / Where it runs, VI / Reviewed alternatives in thirds.
  Every box keeps its place and size without evidence and reads “Unknown”; only
  the alternatives row may be absent. Reasons, provider status, windows and sources
  open from a bare “i” in the box corner (native disclosure, one open at a time).
  Reserved boxes are solid verdigris, decorative and hidden below 720px. Serif values
  are 33px. Where it runs chips fill per line: amber run modes, trace install
  methods, emerald platforms, with ink text.
- Repository timeline: a literal timeline of creation, latest release and last push;
  one line, “Repository timeline: Unknown”, when no dates are known. A reviewed exact
  rename date joins it as a marker and a label such as “Renamed: OpenDevin → OpenHands
  (i)”; the “(i)” opens its sources. Unknown/coarse dates and discovery/review dates
  stay in folded secondary evidence. See [B-PR139-01](decisions/B-PR139-01.md),
  [B-PR150-01](decisions/B-PR150-01.md) and the
  [history contract](../site/PROJECT-HISTORY.md). Study:
  [plate evidence grid](studies/plate-grid/README.md).

## Clearer jar glass

Glass uses feathered transparent centers, neutral lifted midtones and retained
rim/base detail. Specimen color is independent. Selected light stays near the foot;
a faint shared rear gradient and short base shadows give the white scene depth.
See B16 and the detailed guide. Source photographs are unchanged.

The second glass pass extends the clear area through shoulders and side walls,
softens dark reflections and reduces contact-shadow density. Specimen color and
room shading remain independent.

The two worn paper stickers remain opaque as independent photographic overlays.
The rear room gradient is broader and stronger; it does not tint the glass layer
or the page globally.

Natural brown cork likewise bypasses the neutral glass correction.

The latest depth direction (B19) supersedes the broad rear gradient: a shallow arc
in actual jar placement, matched footprint shading and short rear shadows. White
space remains clear around the collection. Labels retain their common baseline.

## Observatory snapshot

The `/observatory/` route (B20, redesigned under user-approved B31) uses the
current typography and white/Prussian instrument language for literal snapshot
distributions, HTML bar lists drawn linearly from zero and accessible underlying
tables. The 128px botanical logo is the centered closing mark without a caption
(B27); artwork never modifies chart geometry. Filters update distributions and
records together. Whole-collection findings and coverage retain explicit scope.
Layout: [detailed guide](../site/RETRO-SCRAPERISM.md#observatory-instrument-b31-b34-b35);
data meaning: [observatory contract](../site/OBSERVATORY.md); method and contract
changes: [B31 record](../site/OBSERVATORY-REDESIGN.md).
The Observatory top navigation omits the GitHub link (the footer retains it).
Only the first summary metric (Unique projects) uses the selected category’s small
illustration at 88% 0,
without repetition; All/reset has no image. Inner label and value spans use the
existing paper token to keep text legible where art underlaps on narrow screens.

## Category illustrations

The Table of contents pairs each category name with its existing transparent
illustration at 48 CSS px. Keep the entire silhouette, a fixed image box and
readable wrapping labels/counts inside the existing native disclosure. The
adjacent text names the link; the image has empty alternative text. Preserve
keyboard selection, current-category marking, narrow layouts and text-only
fallbacks when a category has no artwork. The All link has no artwork placeholder.
Use four columns on desktop, two at medium widths and one on mobile. On hover
or keyboard focus, enlarge the icon to its native 104px canvas, clipped by its
row without changing layout. Use local responsive derivatives and lazy loading.
The ledger closing mark shows the selected category’s medium (207px) image; All
or a category without artwork restores the 96px fruit. Keep the desktop name
column capped at 240px (200px at medium widths), leaving descriptions the remaining
space. Plate evidence headings read “Hacker News stories” and “GitHub stars”.

## Weekly jar occupants

B38 replaces the hardcoded occupant policy after the first saved draw activates.
The seven existing jars and interactions stay fixed. Their left-to-right order
is now original jars 1, 2, 5, 3, 4, 6, 7; each retains its contents and calibrated
geometry, and the narrower column follows the tall vessel at desktop, medium
and mobile widths ([B-PR134-02](decisions/B-PR134-02.md)). A seeded weekly draw selects
only illustrated catalog projects, independent of stars, with an initial four-week
cooldown; the draw is displayed the following week. Assign the seven illustrations
to windows by reviewed body fit, with complete-subject fallback. Protrusions may
clip at photo-traced inner glass walls while original illustrations remain whole. The static `/spotlight/` archive is linked from the footer; the hero has no edition link. The archive uses the Observatory route shell
with a specimen tray per edition (B44). See [calendar, evidence and fallback
rules](../site/WEEKLY-DRAWS.md). The original display remains the commissioning
fallback.

## Crisp jar motion (B40)

Use fixed, whole-pixel jar layout dimensions close to the previous resting
composition; the central jar retains its relative prominence. No whole-vessel
scale, perspective or rotation at rest or on selection. Small spring-driven
position changes create parallax between glass, specimen and reflection. Snap
settled offsets to whole CSS pixels and keep the vessel free of ancestor
transforms. Remove glass displacement of the drawing and its idle rotation;
occasional brief translation remains. Preserve the reviewed glass color/opacity,
labels, cork, shallow arc, lighting, lid opening, vapor, cracks and controls.
Pause and reduced motion retain the same jar sizes. The no-JavaScript layout
keeps its existing 300px vessels and readable record links.

## Sibling routes share the Observatory shell (B42)

Every new top-level page starts from the Observatory's header, column, display
heading, scarlet section labels, scope summary, folded detail, closing botanical
mark and Prussian patterned footer. A page built only from a heading and
paragraphs on the ledger stylesheet is incomplete, whatever its content. See the
[route shell](../site/RETRO-SCRAPERISM.md#route-shell-for-sibling-pages-b42) and
the [visual reference](../site/design/index.html), which is maintained with these
rules and lists retired patterns.

## Ledger copy cleanup (B43)

The top navigation omits GitHub. Repository vitals place creation before push;
labels read “Repository push” and “GitHub release”. Close creation/push timestamps
keep literal marker positions; creation text sits 8px left of its marker and is
right aligned, while push text sits 8px right and is left aligned.
Chart month ranges use non-breaking spaces around an en dash, without the
“oldest at left” caption. Fetch dates remain in retrieval history; fresh metrics
omit the observation sentence while stale/unavailable notices remain visible.
Scorecard coverage ends at “returned”.


## Catalog and Spotlight naming

Page titles are “Awesome Open* Catalog” and “Awesome Open* Observatory”.
Top navigation uses Catalog and links About to the catalog footer’s `#about`.
The weekly draw archive uses `/spotlight/` and the visible page name Spotlight.
Edition labels, current-edition values and anchors use ISO week years/numbers
(`2026-W43`, linking to `/spotlight/#2026-W43`). Its page hides the section jump
navigation, omits the scope and method blocks, and removes Observatory links and
the footer’s Return to project ledger link. Download draw records · Draw contract
sits in the footer immediately above GitHub. The download lives at
`/spotlight/draws.json`; the draw evidence contract and saved dates are unchanged.
See [B-PR134-01](decisions/B-PR134-01.md). The catalog footer puts GitHub immediately before
Top. Its shortened stars note follows the HN note; source evidence remains linked.

## Compact Catalog rows and centered departure contours

The Catalog omits the snapshot/setup explanation beneath Filters. Folded summaries
have no authored padding or minimum height at desktop or narrow widths; folio
numbers retain 4px left padding ([B-PR128-01](decisions/B-PR128-01.md)).
The “Explore” departure uses plain Prussian blue with decorative contours
centered around its link (y=200 in the 1000 × 400 viewBox). The navy texture
remains in the footer only. Asset pixels, filter semantics, contour styling and
clipping are unchanged. See [B-PR129-01](decisions/B-PR129-01.md).

## Settled typography

Półtawski Nowy is the user-directed default at regular 400 for every serif role.
The font comparison is retired. Old serif query parameters are ignored; there is
no selector or preference runtime. Offline editions embed Półtawski and Commit Mono.
See [PREVIEW.md](../site/PREVIEW.md#serif-selection).

Hosted fonts use separate same-origin WOFF2 files; only Półtawski and
Commit Mono are requested. Font failure leaves readable system fallback text. Complete font outlines, provenance and licenses are retained.

Półtawski supports genuine bold 700 when explicitly requested with `font-weight: bold` or `700`. Its existing variable file exposes 400–700; regular 400 remains the default for headings and wordmarks. No extra font download or synthetic bold is needed. Italic cuts are not included.

## Jar callout colors and Inspect link

Jar function text (`.label-ink`) has a `#ffc800` backing; `.jar-metrics span` uses `#D9EEF8`. These are local callout treatments rather than a page palette change. The link reads “Inspect”, with no visible resting border and a 3px solid border on hover or keyboard focus. Reserve transparent border space to avoid layout shift. The third-activation accessible label also reads Inspect. See [B-PR141-01](decisions/B-PR141-01.md).

Body-led wall clipping is proposed in [B-PR143-01](decisions/B-PR143-01.md).

## Observatory shared-name comparisons

Shared-name plates reuse approved project illustrations at the outer edges of
paired introductions, with centered headings and project names. Images retain
their full proportions; missing art adds no placeholder. Catalog links appear
as linked Registry IDs in the regular facts list. Narrow screens stack records.
See the [Observatory contract](../site/OBSERVATORY.md#shared-name-illustrations).

## Scoreboard proposal

The Scoreboard uses the B42 sibling-route shell for six comparative ranking tables.
Each table states qualifying coverage, units and foldable source evidence. A
small outlined cup and place numeral identify shared ranks 1–3; the same compact
metric links appear beneath the specimen label's domains. The weekly edition is
stated once above those links. Existing category-star bolding remains separate.
See [the measurement and weekly contract](../site/SCOREBOARD.md).


## Compact Scoreboard rows

Ranking entries use one line with place, truncated project name and numeric
evidence control. Counts open native disclosures styled as plain underlined
links, with marker-free overlays. Units stay in column headers and cache status
stays in the evidence. Current display headings and the omitted coverage section
are recorded in [B-PR234-01](decisions/B-PR234-01.md).
