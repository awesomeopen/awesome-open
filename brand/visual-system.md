# Visual system

The detailed specification remains [site/RETRO-SCRAPERISM.md](../site/RETRO-SCRAPERISM.md).
The exact token values live in [site/design/tokens.css](../site/design/tokens.css).
Update both in one PR when changing the system. The [HTML reference](../site/design/index.html)
demonstrates the system; the current generated production entry point demonstrates
the full application. Historical demo routes do not establish current behavior.

## Current contract

- High-contrast white/cool mist, Prussian blue and dark ink. Restrained scarlet
  directs attention. Saturated color may belong to specimens and jar lighting.
- Fraunces Light 300 / SuperSoft 100 headings and Semibold 600 wordmark; Commit Mono ledger, prose and metadata. Automatic optical sizing, restrained tracking, consistent 16/24/32px spacing. Keep bundled provenance and both SIL OFL notices.
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
container treatment; it does not change FOSSoligy's drawing rule for specimens.
Colored jar lighting is decorative, not a status classification. This specific
approved component takes precedence over generic “no glow” guidance.

The header combines the botanical mark, Awesome Open* wordmark and compact search.
Typing filters; search submit jumps to the first result. Two crack stages lead to
inspection on the third click, which restores the glass. Preserve the calmer first
crack stage. Native navigation remains available.

Expanded records use the specimen plate below. Missing
artwork leaves no placeholder. Reviewed alternatives follow the evidence as their
own band. HN and stars summaries use “past 2y”. GitHub official
source links name GitHub. ID tooltips name the identifier type: “Registry ID” and
“Folio number”. These four refinements were initially present only in the private
Sites output; this PR restores them to the generator.

The footer uses one transparent valley/abyssal image per load over Prussian blue,
with a static masked upper fade and clear reading space. Its data notes default
open; the coffee support link has its own paragraph. Black footer metadata
backings are a specific implemented choice, not a new global surface token.

The standalone download is a motion-free ledger with embedded dependencies. It
need not recreate the interactive photographic hero. Verify copy and evidence
changes in both generated outputs.

## Review

Check the affected component, not an invented whole-site redesign. For visible
changes check the relevant desktop/narrow states, keyboard/focus, reduced motion,
real asset paths and output modes. Record unavailable browser checks explicitly.
Do not mark a reference “approved” merely because a build succeeds.

## Specimen plate for every record (B29)

The expanded record is one plate for all projects; the bounded three-record study
(B13–B15) and its plain restoration (B24) are superseded. Order: Function statement and reviewed prose, the specimen,
feature notes, the specimen label, then II / Repository record, III / Where it runs,
Observations & evidence and Reviewed alternatives (numbered by presence), and the
centered “In the wild” departure on a Prussian band.

- The illustration stands on a decorative contour “floor”, seeded by Registry ID and
  confined to the lower half. Contours encode no data. The floor is drawn only behind a
  transparent cut-out derivative so it never crosses the drawing.
- Artwork shows at exactly half its 1254px source (627px) for a crisp 2:1 downscale; a
  frameless loupe magnifies the source 2× under the pointer or a tap. No sway: rotating a
  raster blurs it. Opening draws the floor and settles the art once; reduced motion is static.
- Up to two feature notes carry small/tiny enlarged windows of the drawing joined by
  scarlet leader lines from the ground, echoing the jar captions. Notes are sourced
  software facts; no anchors are placed on the drawing.
- The label under the illustration: a QR code of the permalink, “Awesome Open* · Field
  record” (or “Archived on GitHub” when GitHub reports it), name, Registry ID · Folio,
  “Domain:” with every domain, and the permalink. No paper or object treatment (B28).
- Section labels are scarlet blocks with mist type (5.86:1). No horizontal rules inside the
  plate; spacing and labels carry the hierarchy. Chart axes remain.
- Repository record: large values plus a literal timeline of creation, latest release and
  last push. Where it runs: reviewed run/install/platform chips with the setup disclosure.

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

The user-directed `/observatory/` extension uses the current typography and
white/Prussian instrument language for literal snapshot distributions, native SVG
and accessible underlying tables. The existing 128px botanical logo appears
in the opening without a visible caption; artwork never modifies chart geometry.
Filters update distributions and records together. Whole-collection findings and
coverage retain explicit scope. See [observatory contract](../site/OBSERVATORY.md)
and B20; the initial implementation awaits visual review.

## Category illustrations

The Table of contents pairs each category name with its existing transparent
illustration at 48 CSS px. Keep the entire silhouette, a fixed image box and
readable wrapping labels/counts inside the existing native disclosure. The
adjacent text names the link; the image has empty alternative text. Preserve
keyboard selection, current-category marking, narrow layouts and text-only
fallbacks when a category has no artwork. The All link has no artwork placeholder.
Use local responsive derivatives and lazy loading; embed the small source in the
standalone edition. Existing hero, ledger and filter behavior remain unchanged.
