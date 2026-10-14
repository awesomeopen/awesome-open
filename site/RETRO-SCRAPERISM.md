# Retro-Scraperism — Awesome Open design system

Version 0.1 · established project guide · consolidated 2026-10-13

**Specimen is the chosen concept spine.** It is a deliberate fit for inspecting software and its evidence, not the result of a random theme selection. Retro-Scraperism is a precise, high-contrast field of technical information interrupted by curious hand-drawn life and visible editorial attention. Think a working sketchbook meeting a drafting instrument: lucid, slightly strange, and useful.

This is the detailed canonical project guide. Start at [the brand reference](../brand/README.md) for current status, assets, skills and maintenance. Later component sections retain their original proposal wording as implementation history; see [the decision register](../brand/decisions.md) for current status. [The visual reference](design/index.html) and [CSS tokens](design/tokens.css) make it concrete. The portable `retro-scraperism` skill carries these principles elsewhere; for Awesome Open, this document wins over its bundled snapshot. The current production composition is recorded in [the visual-system index](../brand/visual-system.md).

## 1. Direction and boundaries

The interface helps people inspect, compare, and follow evidence about open software. A specimen is an inspectable record, not a verdict, a collectible rarity, or a claim about biological ancestry. Functional labels remain ordinary language: Search projects, Repository, License, Last push, Sources.

Three layers work together:

1. **Instrument:** a stable grid, readable type, explicit labels, tables, rules and traceable evidence.
2. **Specimen:** a distinctive drawn subject with one coherent impossibility. Its form can suggest a tool's function without claiming facts about that tool.
3. **Editorial hand:** a small number of meaningful brackets, corrections, underlines or marginal notes. These direct attention; they do not obscure information.

The instrument remains usable when the other two layers are removed. The atmosphere comes from the tension between precision and irregular drawing, not simulated dirt.

### Critical reading of the supplied brief

The supplied Markdown, “Retro-Scraperism - Design System, Style Guide”, and attached moodboard establish the direction, not an implementation specification. The moodboard's dark cyanotype panel, red marks and jewel-colored anatomy are the useful signal. Its wood desk, aged cards, strings, seals and stain density are not default interface treatments.

| Proposal in the notes | Decision for this system | Reason |
| --- | --- | --- |
| Prussian blueprint substrate | Keep as a strong cover/inverse surface, with true white | Distinctive contrast without sepia nostalgia |
| Parchment and kraft cards | Replace with white or cold mist | The user explicitly rejects sandy/yellow notebook aesthetics |
| “Clean layouts are dead layouts” | Reject as a UI rule | Dense evidence needs order; interruptions belong in margins and art |
| Mechanical substrate always | Interpret as measured construction, not mandatory machinery | A grid can be technical without gears, brass or walking tanks |
| Four simultaneous typographic voices | Reduce to two functional voices; optional editorial third | Legibility and cohesion matter more than theatrical authenticity |
| Wax-seal primary buttons and shipping-tag controls | Use plain labeled rectangular controls | Actions must be recognizable and accessible |
| Frantic handwritten warnings, VOID/CONFIDENTIAL stamps | Reserve marks for actual editorial meaning | Decoration must not invent risk, secrecy or status |
| Saturated specimens and ink annotations | Keep, sparsely | A restrained interface gives unusual subjects room to register |

## 2. Color system

White is paper here. Yellow is a small signal, never the page's atmosphere. Do not drift through ivory, warm gray, khaki, sand, kraft or sepia into a beige design.

| Token | Value | Intended role |
| --- | --- | --- |
| `--rs-paper` | `#FFFFFF` | Default reading surface |
| `--rs-mist` | `#F0F5F8` | Cool secondary surface, subtle grouping |
| `--rs-ink` | `#111820` | Primary text and hard rules |
| `--rs-blueprint` | `#0B2546` | Inverse sections, major anchors |
| `--rs-trace` | `#D9EEF8` | Text/rules on blueprint |
| `--rs-muted` | `#465665` | Secondary text on paper/mist |
| `--rs-scarlet` | `#B62420` | Readable editorial red on paper |
| `--rs-scarlet-art` | `#D9251D` | Original brief's vivid red, artwork only |
| `--rs-amber` | `#FFC800` | Small highlight with ink text; focus on dark surfaces |
| `--rs-emerald` | `#006B4F` | Readable positive status on paper, with words/icon |
| `--rs-emerald-art` | `#00A86B` | Saturated anatomy, not default text |
| `--rs-verdigris-art` | `#4A7C72` | Optional material note inside artwork |

Start with approximately 80% neutral reading space, 15% blueprint and 5% accents on a reading view. These are composition prompts, not quotas; a cover may be predominantly blueprint. Use one leading accent in a component. Do not make every row a rainbow.

Approved small-text pairs: ink/paper, ink/mist, muted/paper, muted/mist, paper/blueprint, trace/blueprint, scarlet/paper, emerald/paper, ink/amber. The reference lists calculated contrast ratios. Do not assume scarlet or emerald text works on blueprint. On inverse surfaces use white/trace text, with separate accent marks.

Color alone never communicates selection, errors or maintenance state. Use a label, icon, border or explicit state change. Focus uses a 3px scarlet outline on light surfaces and amber on blueprint, with a 3px offset. Check adjacent colors if changing these combinations.

## 3. Typography

Use locally bundled **Fraunces** for editorial headings and **Commit Mono** for the
ledger, evidence, controls and reading text. This is the user's typography direction
of 2026-10-13, replacing the earlier Outfit/system-monospace baseline.

- Headlines and the large Function description: Fraunces **300**, `SOFT 100`,
  `WONK 1`, automatic optical sizing. Use 28–42px and line-height 1.15–1.22.
- Header wordmark: Fraunces **600**, `SOFT 100`, `WONK 1`, 26–30px.
- Ledger names: Commit Mono **450**, 16px/1.5; category leaders **650**.
- Ledger descriptions: Commit Mono 14px/1.6. Expanded prose: 15px/1.7 (14px on narrow screens).
- Metadata: 12–13px with 1.5–1.65 line-height. Keep numbers tabular and labels literal.
- Evidence headings: Fraunces 300 at 21px/1.25; factual values stay Commit Mono.
- Preserve monospaced character advances; do not enable programming-symbol
  substitutions in evidence labels or source URLs. Do not synthesize missing weights.
- Keep 48px minimum row targets, measured column gaps and consistent 16/24/32px
  detail spacing. Reduce arbitrary gaps, not legibility. Keep narrow details stacked.
- Both families use SIL OFL 1.1. Complete font data and notices are embedded in
  `site/vendor/fonts.css`, including the standalone edition. Exact source revisions,
  axes and hashes live in `FONT-PROVENANCE.json`. No live Google Fonts dependency.

The portable skill snapshot still describes the older font choice; its instruction
to read this project guide takes precedence. Do not change the reusable style for
other projects just to make its snapshot match this project-specific decision.

## 4. Layout, scale and texture

Use a 4px spacing base: 4, 8, 12, 16, 24, 32, 48, 64, 96. Reading sections use 48–96px separation on desktop and 32–56px on mobile. Dense catalog rows keep useful data close; dramatic empty space is a cover privilege.

Maximum content width: 1440px; side gutters 24–48px desktop and 16–24px mobile. Use full-width ruled records for the ledger and a clear reading column for explanations. A catalog does not become a bento dashboard to satisfy a generic layout skill. On small screens, stack labeled fields or provide an explicitly labeled horizontal table region; do not hide key facts.

Edges are square or minimally rounded (0–2px). Use crisp 1px rules and occasional 2px emphasis. Optional hard offset shadow: 4px 4px 0 ink, limited to a featured sheet or selected artifact. Not every row floats. Double borders belong to occasional specimen frames, not every control.

Texture is opt-in and sparse: a faint drawing field behind an illustration, a rough ink stroke, a pencil study inset. No blanket paper noise, faux aging, torn reading edges, brass fasteners, leather, wood background or stain overlays. A decorative grid must not resemble an interactive chart or reduce text contrast.

## 5. Components and interaction

| Component | Default | Avoid |
| --- | --- | --- |
| Cover | Blueprint or white, bold short title, one drawn subject, plain next action | Generic SaaS badges, beige notebook, faux archive secrecy |
| Navigation | Plain links, obvious active state, skip link | Tiny stamps as the only navigation |
| Primary button | Ink or blueprint fill, white label, rectangular, clear hover/focus | Wax seal hit targets, rotated labels, ambiguous “PROCEED 1904” |
| Secondary action | Underlined link or bordered white button | Manila tag skeuomorphism |
| Search/filter | Persistent visible label, conventional input, explicit clear/reset | Dotted journal fields without boundaries or placeholder-only labels |
| Specimen record | Project name, concise purpose, comparable facts, source links | Art competing with the evidence or invented classifications |
| Detail drawer | Descriptive heading, close control, predictable keyboard behavior | Hover-only evidence, scroll traps, decorative obstruction |
| Status | Text plus optional simple shape; distinguish unknown from negative | Red “REJECTED” because license data is missing |
| Annotation | Short, purposeful, anchored to its referent, outside hit targets | Random exclamation marks, clipping or fake redactions |
| Empty/loading/error | Plain reason and next action where possible | Mystery stamps and invented diagnostic confidence |

Aim for 44px interactive targets. All controls work with a keyboard and show visible focus. Use semantic headings, links, buttons and form labels. Meaningful illustrations have concise alt text; purely decorative strokes have empty alt text or are hidden from assistive technology. Hover is supplementary, never the only route to a fact.

Motion clarifies state: short opacity/position transitions, roughly 120–220ms. A reduced-motion preference removes nonessential movement. No automatic marquee, mandatory parallax, scroll pinning, scrubbing, stacked-sheet trapping or entry animation that leaves content hidden when JavaScript fails. If later motion earns its place, review its purpose and fallback separately.

Category navigation uses the owner-uploaded category illustrations at 48 CSS px
inside the existing Table of contents disclosure. Keep complete silhouettes,
wrapping category labels, counts and current-category marking. The illustration
is decorative beside its text label, with empty alt text. Preserve the All link
without a placeholder. Local 104/207/414px WebPs provide responsive candidates;
native lazy loading defers closed-menu artwork. The standalone edition embeds
only the small variant. See [category provenance](domains/provenance.json).

## 6. Artwork: strange, obscure, direct

Apply Speculative FOSSoligy through disciplined observation and invention. Start with a readable silhouette and credible structure; introduce one governing impossibility. Ink, pencil, crosshatching and selective translucent color should feel made by a curious observer. A second look reveals the oddity; a first look still identifies the subject.

Pure biology is welcome. Machinery is optional. Do not attach a brass gear to every animal or render every tool as a bio-steampunk insect. Vary function, family, pose, materials and scale across a series. Jewel green, cyan, red or violet may be concentrated in the specimen while the interface stays restrained. Choose white, cold mist, blueprint or transparent backgrounds, explicitly overriding the illustration skill's warm-paper default.

For software symbols, infer a visual analogy from the tool's actual function, not its popularity or an unsupported personality. Preserve established logos/favicon unless replacement is explicitly in scope. Label conceptual diagrams as schematic; decorative anatomy is not technical architecture or genealogy.

**Prompt scaffold:** “An original hand-drawn [subject/function analogy], [clear silhouette], whose single impossible principle is [coherent transformation]. Observed structure, intentional ink and pencil lines, selective [one/two colors], [white/transparent] ground. Strange but immediately legible; flat study, no photoreal desk, aged paper, obligatory brass gears, fantasy glow, text or watermark. Leave [placement] quiet for live HTML text.”

When generating website reference images, request one separate horizontal image per requested section, as the frontend-image skill specifies. Do not generate a stitched entire website. For this guide, the supplied moodboard is a reference, not an asset to republish: provenance/licensing of that watermarked image is not established. The visual reference therefore demonstrates actual type, tokens and controls without copying it. Generate new specimens when a concrete component needs one.

## 7. Evidence and language

Preserve the site's existing evidence boundaries:

- Unknown license means unknown; it is not a legal verdict.
- Last push is a UTC repository timestamp, not a maintenance diagnosis.
- Repository creation is not project birth or a specimen collection date.
- Stable IDs derive from actual identifiers; display positions are not identities.
- Reviewed alternatives are comparisons, not descent or dependency claims.
- HN counts/charts represent matched submissions, not sentiment or controversy.
- Never invent clades, motives, citations, testimonials or compliance claims.

Metaphor lives in headings and illustration. Searchable labels, evidence units and destinations remain literal. A scarlet mark can identify an editorial question; it cannot silently convert absence of evidence into alarm.

### Writing style and voice

Apply these rules to all writing: interface copy, headings, annotations, documentation, reports, PR descriptions, and assistant responses.

- **Voice and tone:** Be neutral, terse, and matter-of-fact. Speak like a pragmatic senior colleague. Use the professional register of a staff engineer or technical editor: an unadorned report style. Avoid unsolicited empathy, pastoral warmth, inspirational framing, therapy speak, pseudo-profound framing, and rhetorical elevation.
- **Zero interpretation:** Do not analyze, reflect on, or comment on the user's mindset, emotions, motives, or underlying journey. Answer only the explicit operational premise. State relevant facts, actions, constraints, and uncertainties.
- **Answer first:** Put the concrete answer, result, or required action in sentence one. Never begin with a rhetorical wind-up or warm-up phrase such as “It makes sense that…”, “At its core…”, or “This speaks to a larger truth…”.
- **No editorial taglines:** Omit closing encouragement, philosophical takeaways, life advice, closing remarks, and unsolicited summaries. Stop when the requested information is complete.
- **Direct structure:** Omit filler transitions. Use precise verbs and literal headings. Include explanation only when it supports the requested operational answer; do not turn a technical observation into a broader life lesson.

The specimen concept governs visual organization and artwork; it does not authorize elevated prose or commentary about the reader.

| Avoid | Use |
| --- | --- |
| “It makes sense that you want clarity here.” | “The license is unknown.” |
| “At its core, this is a journey toward transparency.” | “Each record links to its sources.” |
| “You're building something meaningful. Keep going.” | Omit the closing remark. |

## 8. Implementation and skill precedence

Ship fonts and artwork as repository assets with relative paths that work under `/awesome-open/` as well as at a preview root. Preserve font licenses and asset provenance. Do not depend on chat attachment URLs, temporary generated-image URLs or a developer's local filesystem. Test the built deployment and standalone export separately; an offline document needs embedded or packaged dependencies, not just a working hosted page.

Use `design/tokens.css` as the versioned reference. The ledger-first build loads these tokens before its component CSS. Update the shared tokens and reference together.

For this project, explicit user decisions and this system override generic skill defaults: specimen is fixed, no theme lottery; Fraunces/Commit Mono are deliberate choices, no random font swap; evidence-first layout, not forced marketing AIDA or bento; useful motion, not mandatory GSAP effects; cold white, not warm naturalist paper. GPT Taste contributes hierarchy, composition and refinement. The frontend-image skill contributes coherent section direction. FOSSoligy contributes original drawing logic. None makes the current interface inaccessible or changes the task's scope.

## 9. Extension and review

Use a focused design branch from current main. `design/exhibition-preview-1` was the initial prototype branch; it is not a permanent active branch. The user's dot agent remains the repository administrator. Changes travel through a draft PR and a private clickable preview before merge; see [PREVIEW.md](PREVIEW.md). No direct design pushes to main.

For each extension, add the rule, token/component example, reason, accessibility implications and a decision-log entry in the same PR. Distinguish a proposal from an approved direction. Update the portable skill's reference snapshot when an approved system change should apply outside this repo. Do not let independent snapshots silently override the project guide.

### Review checklist

- Does the page read as high-contrast specimen work, without beige/sepia drift?
- Can the main task be completed without artwork, motion or metaphor?
- Is the artwork coherent and varied, rather than mechanical by habit?
- Do font assets, links and artwork work from the deployed base path?
- Are small text, focus, keyboard operation and narrow-screen reading usable?
- Are annotations truthful, bounded and distinct from actual state?
- Does the preview identify the exact source revision being reviewed?

### Decision log

| Date | Status | Decision |
| --- | --- | --- |
| 2026-10-12 | User direction | Specimen spine; high contrast; reject sandy/light-yellow look; establish reusable system |
| 2026-10-12 | User workflow approval | Codex owns active design branch; disposable clickable preview before merge |
| 2026-10-12 | Proposed implementation | White/Prussian/ink base; sparse scarlet; two functional type voices; restrained material cues |
| 2026-10-12 | Proposed implementation | Keep existing Outfit and branding; migrate components gradually after guide review |
| 2026-10-12 | User direction | Ledger-first layout; remove cover/reading-room/band; optional specimen artwork; shared README top-three ranking |
| 2026-10-12 | User direction | Neutral professional voice, answer first, no mindset interpretation or closing taglines |

| 2026-10-12 | User direction | Compact header search; adjacent closed category/filter disclosures; white attached brand asterisk; category-only leader subtitles. Native controls retain keyboard access and expand in document flow. |


### Exhibition components — preview 01 proposal

- **Instrument:** compact shared search, category index number, predictable specimen labels, native evidence drawers and complete category ledger. Exhibition and ledger controls change density while retaining filters.
- **Specimen:** three category leaders on white fields, with a large upright subject and two smaller horizontal subjects. Artwork sizes follow silhouettes; names and inspect actions stay in consistent positions. Projects without art retain their full evidence records without placeholders.
- **Editorial hand:** one scarlet registration cross and a short illustration note per subject. Notes explain the visual analogy and make no additional software claims.
- Search or license filtering hides the exhibition and reveals matching ledger records. Clearing filters restores the selected view. Each illustrated label opens the corresponding source-backed record; shared URLs preserve filters and record anchors.
- On small screens, exhibits stack in reading order. Images use contain sizing; no cropped anatomy, horizontal carousel, scroll pinning or hover-only information. Keyboard focus and reduced-motion behavior remain native.
- Reuse existing white, Prussian, scarlet, Outfit and monospace tokens. No additional palette or font family. The implemented component example is `/exhibition.html` in the private preview.

| Date | Status | Decision |
| --- | --- | --- |
| 2026-10-12 | Preview proposal | Infrastructure & DevOps exhibition: OpenObserve, OpenResty and OpenTofu above the complete category ledger. Review before production adoption. |
### Compact ledger copy — 2026-10-12

User direction: blank header search with a dashed underline; retain accessible labels without visible text. Remove the visible page heading, snapshot heading and column header band. Names set compact row height; desktop descriptions use one-line ellipsis and mobile descriptions move into the open record. Complete descriptions and evidence remain available in drawers. Unknown license fields remain blank. Revision, total project count and snapshot coverage are generated in the footer, never hard-coded. Footer explanations use short lists. License wording remains a verification instruction because the pipeline detects licenses and does not independently verify terms.

### Preview 02: layered jar study (proposal)

Instrument: the complete ledger and live HTML labels. Specimen: existing original function-derived artwork inside three SVG vessels. Editorial hand: anchored scarlet leaders on hover/focus. This bounded motion study is built only for design previews at `jars.html`; it does not alter the production page.

The header is unboxed on white. Glass front/back move as one vessel, with restrained additional specimen depth; pointer motion is local and reduced motion is static. The open jar's specimen rests rather than floats. Shadows and an optional fine baseline can be compared without a table. Names remain visible; touch layouts show metrics without hover. Links open ledger records. No new typeface, aged paper, scroll pinning, or fabricated weekly curation is introduced.

### Preview 03: photographic vessel density (proposal)

Seven vessels form a shallow arch: tallest in the middle, heights falling toward both sides. Position encodes physical height only. Use contact shadows; remove the baseline comparison. Photograph-like glass surrounds original drawn specimens, with independently replaceable assets, restrained displacement and front reflection. Glass texture can be imperfect; the page stays white.

Desktop hover or keyboard focus raises one annotation over adjacent vessels on a small white backing. Touch first selects, then the separate Inspect record link navigates. Escape dismisses. Medium screens show the central five; narrow screens keep all seven in a horizontal display. Reduced motion removes depth movement. No 3D runtime is required. Vessel prompts and dimensions live in `site/jars/provenance.json`; two new function-derived specimens (OpenSSL and OpenSearch) follow the existing artwork manifest contract.

Preview 03 refinement: omit the preview captions beneath the display. Replace the enclosing hover card with three separately positioned labels for function, cached metrics and the record link. Fine scarlet leaders end in open point markers on the specimen; line drawing is disabled under reduced motion. Two photographic jars carry small illegible white paper stickers. These marks are decorative, not project identity or evidence. The photographic assets retain their original unlabelled versions and record their edit prompts in `site/jars/provenance.json`.

### Preview 04: approach and inspect (proposal)

The photographic parade starts at 82% scale, with the middle vessel at 94% for a stronger central silhouette. A nearby pointer creates a shallow approach wave; the selected vessel advances to 110% (the middle vessel therefore grows less), with its contents enlarging as part of the same object. A shared virtual camera adds differential translation and perspective tilt (12° forward pitch on selection, pointer-adjusted up to 22° vertically and 8° horizontally), while internal contents and reflection strength respond independently. This is limited-angle 2.5D using photographs, not a rotatable 3D model. Labels remain in the reading plane; their leaders follow the specimen.

Use a damped spring and stable hit regions. Keyboard focus and touch selection also advance the selected jar. Stop rendering once settled or offscreen; suspend in background tabs. Reduced motion keeps vessels at static full size and removes tilt/depth movement. Never intercept scroll or request device-orientation access. “Inspect record” has a dashed border, solid on hover or keyboard focus, with no layout shift.


### Preview 05: underlight and occasional movement (proposal)

Selection adds a base light matching the jar’s assigned smoke hue at 75% intensity inside the vessel footprint, an alpha-masked upward wash on the glass and a small brightness/contrast increase on the specimen. Contact shadows remain. A tiny matching LED point sits directly beneath the jar; matching colored spill tints the retained contact shadow. The upward wash stays inside the glass footprint. The light and smoke share one per-jar neon hue; this is an artwork-lighting accent.

The two glass stoppers and screw cap are isolated with CSS clipping and lift 4px while tipping 12°. The wire clamp and cork stay closed; already-open jars need no moving lid. Neon smoke uses three decorative characters drawn without replacement per jar from the fixed pool `∰⋈⌘∑∂∇∞⊕⋇AXRkx0279`, hidden from assistive technology. Characters stay fixed until reload. Their starting position is raised 18px above the earlier mouth-aligned placement so they clear the lid. Each fades in and out once over 1.6 seconds, with starts 300ms apart. No pose alternation, loop, blurred cloud or particles. Each jar receives a distinct random neon hue on page load, retained across selections; colors shuffle on reload. This is a limited photographic-layer illusion, not a physically modeled hinge or fluid simulation.

Specimens stir by 1–2px and less than 1° in short staggered intervals, with long still periods. A lower-right `[II]` button pauses decorative motion and switches to `[>]` to resume; accessible labels name each action. Reduced motion leaves only immediate static illumination; offscreen/background scenes pause animation. Labels, hit targets and evidence remain fixed.

| Date | Status | Decision |
| --- | --- | --- |
| 2026-10-12 | User direction / preview proposal | LED-like underlight on selection, slight lid opening with vapor, intermittent specimen movement. Implemented with existing photos and CSS layers. |

Search uses the owner-supplied turquoise loupe at 32px inside a 44px submit button to the right of the input. Clicking or pressing Enter applies the current query immediately; live filtering remains available.

### Hero release candidate and ledger refinement — 2026-10-12

The user considers the photographic hero a release candidate. Preserve its approved interaction and appearance during the next ledger pass. Expanded and linked ledger rows have no scarlet left rule. Their disclosure indicator changes from a plus to an upright asterisk; native details retain the accessible expanded state.

### Specimen sheets — preview proposal

Instrument: a two-column open record, with a prominent literal function description at upper right, followed by ruled repository facts. Specimen: the original illustration at left, with registry ID, alphabetical folio, category links and source/permalink beneath. No repeated title, illustration caption, empty artwork placeholder, UTC suffix on date labels, or repeated cache/snapshot paragraph.

Editorial hand: release, Scorecard and reviewed alternatives read as separate accumulating evidence notes. Use square ruled edges, Prussian headings, a restrained cool backing and a small hard offset shadow. No parchment, tilted text, invented annotations or decorative stamps. Keep status visible; put full retrieval history in native disclosures. Unknown and retained results keep their existing factual labels. Cards do not imply endorsement or feature parity. On narrow screens the image/identity precedes function and single-column notes. Missing artwork produces a narrower identity column, not a blank exhibition plinth.


### Sheet refinement — HN and metadata

Folded names include a small HN discussion trace where evidence exists; hide that duplicate trace while the record is open. The full HN evidence is a ruled note with a smaller linked chart. Counts describe matched stories, not adoption, quality or sentiment. License, star count and date values use the accessible scarlet token. Omit the rule beneath artwork and the generic feature-parity caveat beneath alternatives; retain each reviewed scope and its source.

Proposed next data extension: keep the existing short description for folded rows and add an independently reviewed function summary from the official README or documentation. Record its source URL, checked date and source revision when available. Do not expand sparse prose with random claims or infer capabilities from popularity/activity metrics. Missing summaries fall back to the existing description. This is a proposal, not an enabled automation.

### Reviewed Function summaries — implemented proposal

The concise description remains the large Function headline and folded-row description. Approved 40–80-word prose appears underneath at reading size, followed by literal source links and the review date. This keeps longer documentation readable without making a paragraph-sized headline. Missing summaries add no placeholder or repeated text. The curated contract and Junge handoff are in [FUNCTION-SUMMARIES.md](FUNCTION-SUMMARIES.md); publication does not fetch or invent prose.


### Footer backgrounds

Owner-supplied transparent valley and abyssal artwork occupy the footer floor over Prussian blue. Text and controls stay above the artwork on solid blue. Fade the upper edge with a CSS mask; do not animate the background. Select one image uniformly per page load using the number of available images. Keep the first sorted image as a no-JavaScript fallback.

Add a PNG or WebP to `site/footer-backgrounds/` and rebuild to extend the pool; do not edit probabilities or JavaScript. Keep artwork provenance beside the assets. The standalone download embeds the complete pool and uses the same selection logic. On narrow screens crop the decorative panorama centrally while preserving legible footer text.

### Specimen plates — three-record study, 2026-10-13

Proposed on OpenTofu (broad), OpenRefine (upright), and Open WebUI (without art).
Folded summaries remain unchanged. An open plate pairs a larger complete specimen
with a Fraunces function statement, then spans the sheet with a compact repository
register, paired observation plots, ruled evidence notes, reviewed alternatives,
and a prominent literal GitHub departure link. The source link lives in the centered final “In the wild” capstone; omit the duplicate identity link in these prototypes.

Existing artwork supplies a rectangular detail enlargement. The caption is a source-backed software feature, independent of the drawing's meaning. Select from optional reviewed features attached to Function summaries, using a stable per-project choice; omit it when no reviewed feature is available. Source artwork
is not modified; the full silhouette remains above the cropped detail. A scarlet
leader connects the specimen study to its note; a bracket groups reviewed prose.
No tape, cardboard, fake stamps, new fonts, or invented evidence are added.

Records without artwork use an identity rail and larger function typography,
never an empty image space. Mobile reading starts with function and record identity, then the specimen,
repository facts, evidence, and departure. The DOM retains a logical
identity/function/evidence sequence. Opening settles the art by 6px and draws its
leader once; reduced motion is static, and content is never hidden for animation.
This is a bounded prototype, not a catalog-wide promotion.


### Record refinements — 2026-10-13, user direction

Use “Table of contents” and “All” in category navigation. Highlight the first
complete tool-name mention in the long Function prose with a Prussian backing
and white type; do not alter folded summaries or invent a missing name.

The three plate identities show Registry ID, Folio number, “Domain: …” and
“Specimen: Name (permalink)” with consistent 12px gaps and line heights. Keep
identifier titles. The final “In the wild” source capstone centers its heading,
link and repository address. The artwork crops remain decorative; feature notes
make literal software claims with a separate feature-source link.

Embed reviewed setup evidence in Latest GitHub release, retaining independently
reviewed setup dates and fact sources. A missing release stays “not checked”; it
does not hide reviewed setup facts. Disclosure labels are “View setup facts &
sources” and “View source & retrieval history”. Stars link their plot and
“count stars / past 2y” summary to the aggregate provider, matching HN's linked
plot treatment. Keep cache status and observation date; place the counting
method in About. No historical-total or adoption claim is implied.

### Two specimen staging passes — 2026-10-13, user-authorized prototype

OpenTofu's broad pod is enlarged past the left artwork gutter and the ruled
boundary separating its main study from the close-up. Reserve the space below
that rule so the full silhouette remains visible and the note stays readable.
Its enlargement is a horizontal view into the seed chambers. OpenRefine's
upright calyx rises through the heading rule on desktop; its close-up is a tall
strip of the central strands. On mobile, the calyx crosses its own upper study
rule after the Function/identity block. All full images use contain sizing;
only the deliberately enlarged detail windows crop the source drawing.

Feature notes may be directly attached to drawing enlargements. Independence
is semantic: factual capability copy cites official sources and never argues
that a drawn shape demonstrates software performance or superiority. No visual
separator, disclaimer or analogy explanation is required. Preserve the current
reviewed capability copy and source links during these composition passes.

Each main drawing settles once in 320–360ms; the scarlet leader draws once.
Content is immediately available. Reduced motion shows the finished composition.
Keep the folded ledger, type, evidence and centered departure stable. Open WebUI
remains the text-only control. Source image bytes and provenance are unchanged.


### Clear glass and shallow room — 2026-10-13

User-directed refinement: broad jar interiors approach the surrounding white;
material contrast stays at rims, shoulders, closures and bases. Apply a feathered
transparency window to the photographic glass layer using each vessel's existing
content bounds. Lighten and neutralize glass independently of the drawn specimens;
preserve specimen saturation, dark ink and the existing reflection layer. Do not
reduce opacity on the whole vessel or its contents. Original asset bytes remain
unchanged.

Selected underlight remains colorful at the foot, fading within the lower third
of the vessel. Keep the small LED and tighten its surface spill. Add a static,
faint cool rear gradient behind the group and short rear/contact shadows at each
base. Foreground, captions and surrounding reading surface stay white; no hard
horizon, shelf, enclosure or new motion. Preserve all selection, crack, pause,
keyboard and reduced-motion behavior. Reference: owner-supplied nineteenth-century
specimen photograph, used for lighting direction only, not copied as a site asset.

Second airy-glass pass: extend the transparency feather through the shoulders and
side walls, reduce center density further and soften the darkest glass reflections.
Lift glass midtones without applying that correction to specimen art. Rims and
bases remain defined but no longer read as heavy metallic outlines. Reduce contact
shadow density; retain the faint rear room shading and existing foot illumination.

Restore the two existing photographic paper stickers as clipped, opaque overlay
layers on the square cork and ribbed jars. Their worn texture and ink can remain
old-fashioned; the page and glass stay cool white. Labels bypass glass lightening
and transparency. Use the original jar assets, without inventing readable labels.
Strengthen and broaden the static rear gradient to suggest room depth behind the
collection, with soft transitions into the white foreground and surrounding page.

The square bottle also restores its natural brown cork through a clipped opaque
layer, independent of glass desaturation and lightening.

### Shallow footprint arc — replaces the broad room gradient

Place the seven jar bases on a shallow arc: outside to center setbacks of
0, 7, 11 and 12px, mirrored on the right. Shift each vessel, contact shadow and
light source together. Keep labels on their shared reading baseline. The center
stands slightly farther back; do not change the approved jar sizes or glass.

Replace the broad rear gradient with one faint blurred curved shadow trail along
the footprints, and short individual shadows directed behind each base. There is
no drawn arrow, shelf edge, horizon or shaded wall. Hide the shared trail in the
no-JavaScript stacked fallback. Preserve the paper stickers and natural cork.

Jar captions use the single literal space between number and name; the number
span adds no extra margin. Rear shadows stay close to the bases, never a rising
cloud between the jars.
