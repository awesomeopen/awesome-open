---
name: after-sf
description: Create original drawings or redraw supplied images in "After Speculative FOSSoligy" (after-sf), an invented visual language combining observed natural-history detail, coherent impossible anatomy, curious mechanisms, and selective psychedelic color. Use for animals, plants, tools, machinery, toys, objects, and isolated dwellings. Support faithful style transfer, description-based invention, and visually varied batches such as logos for multiple software tools. Exclude humans, humanoid characters, landscapes, and cities as subjects.
---

# After Speculative FOSSoligy

Draw unfamiliar things as if they were recovered from an alien taxonomy or an untranslated natural-history encyclopedia - carefully observed, clinically cataloged, and fundamentally estranged from earthly biology or human ergonomics. Make the subject deeply uncanny and dream-like; make the drafting lucid and matter-of-fact. Preserve the user's spelling, **After Speculative FOSSoligy** or after-fs. Do not assume the name requires fossils, software symbols, open-source mascots, or modern technological subject matter.

Use this as an independent style, not an instruction to imitate one artist. Read `references/style-atlas.md` when developing a new family of subjects, or when resolving visual drift.

## Establish the task

1. Choose **redraw** when the user supplies a target image, or **invent** when they supply a description. Distinguish a style reference from the actual target. Inspect all target images before drafting the generation prompt.
2. Retain stated subject, framing, colors, output dimensions, transparency, exact wording, and edit constraints. User constraints outrank defaults. Ask only when a missing image or genuinely ambiguous target prevents execution.
3. Default to one finished drawing, one principal specimen, and a clean warm-white ground. Choose aspect ratio to fit the entire silhouette. Do not default to a poster, manuscript page, collection, or landscape.
4. If the request is primarily a human, city, or landscape, briefly explain the scope and ask which eligible object, creature, plant, or individual dwelling to isolate. If an eligible target is already named, isolate it without asking. Small contact shadows, a stone, a root clump, or a mounting base may establish contact without becoming a scene. Exclude human or humanoid figures, including scale figures and decorative faces.
5. Use the available image-generation/editing tool for the final raster art. Follow its reference-image and transparency requirements; never substitute a prose prompt for an image unless the user asks for a prompt. When image generation is unavailable, say so and supply a usable prompt without claiming completion. Preserve transparency on edits unless requested otherwise.

## The visual grammar

### 1. Stark, hand-drafted silhouette without modern CAD neatness

Give the subject a distinct, surprising outer contour and an articulated hierarchy of parts - never a passive lump, boulder, or static monolith. Reject modern graphic-design neatness: never use ruler-straight lines, parallel rails, smooth Bezier curves, bubbly inflated balloons, or neatly filleted plastic corners.

Whether the subject is an organism, instrument, machine, or dwelling, its geometry must feel purposefully grown, tensioned, distended, woven, blown, or hand-forged by an unfamiliar intelligence: taut membranes stretched over angular struts, asymmetric counterweights, pinched conduits, segmented carapaces, and delicate cantilevered probes. Every edge should carry the crisp, slight tremor of unassisted hand drafting.

### 2. Embedded in an unseen world of purpose

Never invent a passive object or a mere geological curiosity. Every subject must look like an active participant extracted from a dense, self-consistent, non-earthly world of industry, signaling, cultivation, symbiosis, or ceremony. Anchor the design in one governing dream-logic operation and show how it couples to its wider environment:
- **Physical interfaces to the unseen:** Include specific couplings, mooring hooks, intake funnels, optical lenses, acoustic horns, dosing spouts, or grafting collars that imply the object plugs into a larger apparatus, host organism, or ritual practice outside the frame.
- **Traces of active operation:** Show functional tension and history - a distended bladder holding pressurized mist, a calibrated scale marked with non-human increments, a polished wear-zone where an unfamiliar appendage grips it, or condensation beading on a cooling coil.
- **Cross-kingdom synthesis:** Seamlessly fuse incompatible domains - botanical vascularity, blown vitreous chambers, iridescent insectoid plating, taut acoustic membranes, and pre-modern clockwork or hydraulic linkages - into a single coherent anatomy.

Keep the uncanny strictly lucid, structural, and taxonomic: never use gore, open wounds, viscera, blood, or sexualized anatomy.

### 3. Brittle ink, drypoint etching, and chalky wash

Use fine, slightly scratchy dip-pen, etching-needle, or hard-lead contours with irregular hand pressure. Build volume through dense directional crosshatching, stippled pores, etched striations, and dry colored-pencil or chalk grain over translucent, slightly uneven watercolor or gouache washes.

Vary contour weight: incisive and dark in deep crevices and overlaps, thread-thin and fragile on membranes, filaments, and brittle edges. Leave open areas of raw, pale ground so the specimen feels isolated on an examination plate. 

Strictly avoid: smooth digital gradients, bubbly 3D shading, vector cleanliness, uniform cartoon outlines, glossy specular highlights, airbrushed softness, and fake coffee-stained parchment filters.

### 4. Surreal taxonomic coloration and shadowless cabinet lighting

**Lighting:** Illuminate the specimen with clear, shadowless encyclopedic studio light (or subtle internal translucency where chambers hold fluids, gases, or bioluminescence). Avoid muddy atmospheric shadows, grimdark vignette lighting, or earthy brown gloom. Volume must come from crosshatching, surface patterning, and translucent pigment washes rather than heavy chiaroscuro.

**Color:** Start with a clean warm-white, ivory, or pale stone ground and fine soot-black, indigo, or sepia ink linework. Do not default to earthy brown, moss green, weathered bone, or sulfur yellow. Instead, select a deliberate, high-estrangement palette of three to five pigments that differentiate functional materials (e.g., translucent membrane vs. rigid carapace vs. fluid conduit). Vary palettes across drawings using families such as:
- **Vitreous & marine:** Ultramarine + coral carmine + milky opal + tarnished silver-gray
- **Botanical & apothecary:** Amethyst violet + celadon green + saffron gold + pale porcelain
- **Nocturnal & iridescent:** Prussian blue + magenta-rose + beetle-wing teal + chalk white
- **Alchemical & dry:** Verdigris + burnt sienna + lavender-ash + cadmium orange

Use crisp chromatic boundaries, striped or spotted biological markings, and translucent washes so the specimen feels vividly alive or newly operational, never dusty or fossilized.

### 5. Controlled abundance

Concentrate intricate marks in a small number of useful areas, such as a hinge, sensory organ, folded edge, or junction. Keep the principal mass calmer. Prefer one unexpected secondary discovery over many unrelated curiosities. Let a close look reveal a detail that explains the main form.

## 6. Clinical estrangement and fever-dream lucidity

Present nightmare-like or non-earthly subjects with the deadpan detachment of an 18th-century naturalist or pre-modern encyclopedist who finds nothing unusual about them. Aim for quiet alienation, solemn absurdity, and dream-logic inevitability - never whimsy, cuteness, or theatrical horror.

Exclude: cute proportions, bubbly silhouettes, friendly or menacing faces, glowing magic runes, steampunk brass gears, modern plastic/metal industrial design, sci-fi LED panels, random tentacles, and viscera. If an object has a handle or aperture, shape it for an unfamiliar grip or non-human anatomy so it resists easy domestic familiarity.

## Redraw workflow

Before generation, make a short internal preservation list: subject identity, count, pose, silhouette, orientation, proportions, attachment points, defining parts, composition, text, and colors that the user requires.

- **Faithful (default):** Preserve identity, anatomy/geometry, pose, count, and composition. Change drawing medium, rendering, and unconstrained color treatment. Do not grow extra limbs, add mechanisms, or replace parts merely to increase strangeness.
- **Interpretive (only when invited):** Preserve the identifying silhouette and defining parts; reinterpret selected structures through one coherent transformation. Keep protected details exact.
- **Free rein (only when invited):** Rebuild morphology around the described function and one governing impossibility, while retaining explicitly requested anchors.

Use the original target as the image-edit reference. Describe preservation constraints before style instructions. If a scenic input contains a clearly specified eligible target, isolate it while retaining that target's pose and defining structure. Do not remove backgrounds when the user explicitly asks to preserve composition without resolving that conflict.

For follow-up edits, preserve the accepted version and change only the requested aspect. Avoid restarting the design or silently increasing mutation on each pass.

## Invent workflow

1. Choose the subject category and define its active role inside a larger unseen world (what does it harvest, measure, transmit, distil, parasitize, or shelter?).
2. Write one internal sentence: "In its native world, this [thing] [performs specific purposeful action] by [one unfamiliar mechanism or cross-kingdom adaptation]."
3. Establish an articulated, active architecture - cantilevers, tensioned frames, chambers, limbs, or linkages. **Never default to a rock, boulder, shell-lump, or static mineral mass as the base form.**
4. Design a dynamic silhouette with clear intakes, working surfaces, and outputs. Add only structures that serve the governing purpose.
5. Choose a view that exposes the important relationship: profile for locomotion, three-quarter for tools, front view for symmetry, or a restrained section for internal function.
6. Choose the main drawing plus, only when useful, one detail inset or a two-to-three-state sequence. Keep consistent geometry, scale relationships, and material colors across states. Never turn every request into a labeled scientific plate.
7. Apply the visual grammar and generate the image.

## Variation across drawings and batches

Keep the style recognizable through drawing language and internal logic, not a recurring body plan. Apply this to consecutive requests as well as explicit batches such as "10 logos for these 10 software tools." Do not carry the previous prompt's composition into the next concept by inertia.

For a batch, plan all items briefly before generating the first image. Keep an internal table with one row per item: actual function, metaphor/governing rule, silhouette, orientation/view, component count and arrangement, organic/manufactured balance, and focal color placement. Derive each concept independently from its subject. For software logos, identify each tool's distinguishing purpose; avoid giving every project the same generic multi-tool organism.

- Deliberately vary silhouette, orientation, component count, and spatial arrangement across the set. Use meaningful differences such as compact versus elongated, enclosed versus open, stacked versus nested, front-facing versus profile, or suspended versus grounded. These are options, not a mandatory rotation or template list.
- Compare each proposal with both neighboring items and the set as a whole. Revise accidental repeats of the same main mass, appendage layout, or operational metaphor. Mirroring, recoloring, or changing surface ornament alone does not establish a distinct design.
- Specifically check for the observed failure of "three branches growing horizontally out of the right side." It is not a signature of this style. Also watch for repeated shells, spirals, plant-machine hybrids, and left-input/right-output apparatuses. Use any of these when justified, without making them defaults.
- Preserve family resemblance through compatible linework, texture, detail hierarchy, framing, and, when appropriate, a shared palette. Do not force every subject to share anatomy, machinery, materials, or accent placement.
- Let function determine part counts and arrangement. Do not invent unnecessary parts, distort the concept, or randomize geometry merely to satisfy variety. A machine can remain entirely manufactured; an organism can remain entirely biological.
- For faithful redraws, preserve the supplied silhouettes, counts, orientations, and composition. Vary only unconstrained treatment. For requested variants of one established mark, preserve its identifying structure and vary only the permitted axes; continuity takes precedence over diversity.

Generate one separate image per requested item unless the user asks for a combined sheet. In each prompt, specify that item's own structure and composition explicitly. After generation, compare the actual silhouettes and arrangements across the batch; correct clear accidental duplication with targeted edits. Do not regenerate accepted designs solely to maximize novelty.

## Adapt to subject category

| Subject | Develop | Avoid |
|---|---|---|
| Animal | Weight-bearing limbs, feeding or sensory adaptation, surfaces that follow anatomy | Random limb counts, obligatory machinery, mascot expressions |
| Plant | Root/stem/leaf continuity, growth rhythm, storage or dispersal strategy | Generic alien flower plus unrelated eyeballs |
| Tool | Grip, working end, joint, and a visible force path. Do not rely solely on modern industrial design. Consider equally: hostile or indifferent affordances - tools built for non-human appendages or unknown senses. | Decorative cogs without a function, human-friendly curves |
| Machine | Input, transformation, output; selectively exposed connections | Tangled tubes that go nowhere, steampunk by default |
| Toy or object | Handling, balance, movement, tactile affordance | Human hands demonstrating use, face on every object |
| Dwelling | One self-contained shelter, clear entrance and support, material logic | Streets, settlement views, scenic horizons, human occupants |

## Prompt construction

Build a concrete prompt in this order:

1. Target and mode; exact preservation constraints for edits.
2. Subject, view, behavior/function, and governing oddity if invention is allowed.
3. Connected construction and the specific details that explain it.
4. Drawing medium, line hierarchy, selective texture, palette, and focal accent.
5. Framing, background/transparency, whitespace, and any authorized inset.
6. Mandatory geometric and surface exclusions: explicitly forbid smooth vector curves, rounded chamfered corners, ruler-straight lines, bubbly inflated forms, modern industrial design ergonomics, glossy rendering, cute neotenous proportions, and visceral gore. Require hand-etched irregularity, brittle or calcified edges, and dry matte pigment.

Describe the traits explicitly; the invented style name alone carries no reliable instructions. Do not rely on artist-name lists or "surreal/psychedelic" alone. Do not copy recognizable reference creatures, compositions, or source glyphs. Omit lettering by default. If requested, use the user's actual readable labels; reserve invented script for an explicit request and never let it substitute for structure.

## Check the result

Inspect the generated image when the tool permits, and correct clear mismatches with a focused edit:

- Does the subject read at a glance and belong to the allowed scope?
- For redraws, did the identity, pose, count, and protected details survive?
- Is the governing oddity coherent, with connected joints and believable support?
- Are marks drawn rather than glossy, muddy, uniformly noisy, or mechanically perfect?
- Does concentrated detail reward inspection while leaving calm areas?
- Does color separate functional regions without overwhelming the contour?
- Is it an original subject rather than a close replica of a reference motif?
- Across recent drawings or a batch, does it have a purpose-specific silhouette and arrangement, rather than a recolored or mirrored repeat? Preserve intentional continuity and redraw constraints.
- Is the output actually an image, at the requested framing and transparency?

Fix structure before embellishment. Do not keep regenerating merely for novelty. Deliver the drawing with minimal prose. Explain concept choices only if useful or requested.

Use `references/style-atlas.md` for resolving visual drift.
