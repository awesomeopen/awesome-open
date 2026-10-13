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
