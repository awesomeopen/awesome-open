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

Expanded records place artwork/identity left and function/evidence right. Missing
artwork leaves no placeholder. The comparison note spans the grid and follows all
half-width evidence cards. HN and stars summaries use “past 2y”. GitHub official
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

## Proposed specimen-plate study

Three records test a stronger unfolded composition: OpenTofu, OpenRefine and
Open WebUI. See the specimen-plate section of the detailed guide for the bounded
layout, artwork-detail, evidence and departure treatments. Folded rows and all
other records retain the established layout pending review.

## User-directed plate refinement

The three prototypes omit early official-source links in favor of a centered
“In the wild” departure. Identity lines use consistent spacing and literal
Domain/Specimen labels. First tool-name mentions in long prose receive a
Prussian/white highlight. Setup facts sit in the release card without implying
they were checked against that release. Feature captions are reviewed software
facts with their own sources; artwork crops remain decorative. Star plots and
concise counts link to the aggregate source; About retains the counting method.
See B14 and the detailed guide.

## Two specimen staging passes

OpenTofu crosses the main-study lower rule; OpenRefine rises through a heading
rule (its own study rule on mobile). Wider versus taller detail windows follow
the two drawings' anatomy. Preserve complete main silhouettes and keep overlap
inside whitespace, clear of prose and links. Capability notes can sit directly
beside enlarged drawing details: sourcing governs their claims; visual
separation is not required. See B15 and the detailed guide.


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
and accessible underlying tables. A single compact approved Open Doc specimen
interrupts the opening; artwork never encodes a value or modifies chart geometry.
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

## Background versus interrupted rule comparison

The preview-only `/specimen-comparison.html` compares the same OpenTofu plate at
identical scale and position. A flat cool-blue field sits behind the specimen in
A; a single horizontal rule passes behind its silhouette in B. A native radio
group switches treatments without motion or layout movement. Detail crops return
to 104px, or 88px on narrow screens. This study awaits visual selection (B16).
