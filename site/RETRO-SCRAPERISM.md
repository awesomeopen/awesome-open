# Retro-Scraperism — Awesome Open design system

Version 0.1 · proposed foundation · 2026-10-12

**Specimen is the chosen concept spine.** It is a deliberate fit for inspecting software and its evidence, not the result of a random theme selection. Retro-Scraperism is a precise, high-contrast field of technical information interrupted by curious hand-drawn life and visible editorial attention. Think a working sketchbook meeting a drafting instrument: lucid, slightly strange, and useful.

This is the canonical project guide. [The visual reference](design/index.html) and [CSS tokens](design/tokens.css) make it concrete. The portable `retro-scraperism` skill carries these principles elsewhere; for Awesome Open, this document wins over its bundled snapshot. This proposal does not restyle the production site by itself.

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

Keep the existing locally bundled, OFL-licensed **Outfit** for headings and reading text in this first iteration. Pair it with a system monospace stack for compact metadata, source identifiers and tabular values. A future font change is a separate reviewed decision with repository redistribution rights, license files, local assets and an offline check. Do not bundle Cabinet Grotesk merely because another skill selects it.

- Body: 17–18px, line-height 1.5–1.6; about 60–72 characters per line.
- Small metadata: at least 13px, line-height 1.4–1.5; never shrink evidence to fit.
- Headings: fluid, strong, usually 2–4 words per line; allow natural wrapping on mobile. Do not impose a six-line slogan or crop meaningful text for drama.
- Mono: short labels and numeric evidence, with tabular numerals. Avoid paragraphs of uppercase mono.
- Optional third voice: an editorial serif for a substantial essay or cover, introduced through a future PR. Do not add one solely for period flavor.
- Handwriting is a drawing or a short supplemental note, not a body font, warning label, button label or source citation. Repeat meaningful written content as accessible text.

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

For this project, explicit user decisions and this system override generic skill defaults: specimen is fixed, no theme lottery; Outfit is retained, no random font swap; evidence-first layout, not forced marketing AIDA or bento; useful motion, not mandatory GSAP effects; cold white, not warm naturalist paper. GPT Taste contributes hierarchy, composition and refinement. The frontend-image skill contributes coherent section direction. FOSSoligy contributes original drawing logic. None makes the current interface inaccessible or changes the task's scope.

## 9. Extension and review

The active design branch is `design/exhibition-preview-1`, owned by Codex for the exhibition prototype. The user's dot agent remains the repository administrator. Changes travel through a draft PR and a private clickable preview before merge; see [PREVIEW.md](PREVIEW.md). No direct design pushes to main.

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
