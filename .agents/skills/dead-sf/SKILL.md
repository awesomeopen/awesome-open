---
name: dead-sf
description: Create original drawings or redraw supplied images in "Dead Speculative FOSSoligy" (dead-sf), an invented visual language combining observed natural-history detail, coherent impossible anatomy, curious mechanisms, and selective psychedelic color. Use for animals, plants, tools, machinery, toys, objects, and isolated dwellings. Support faithful style transfer, description-based invention, and visually varied batches such as logos for multiple software tools. Exclude humans, humanoid characters, landscapes, and cities as subjects.
---

# After Speculative FOSSoligy

Draw unfamiliar things as if they were recovered from an alien taxonomy or an untranslated natural-history encyclopedia - carefully observed, clinically cataloged, and fundamentally estranged from earthly biology or human ergonomics. Make the subject deeply uncanny and dream-like; make the drafting lucid and matter-of-fact. Preserve the user's spelling, **Dead Speculative FOSSoligy** or dead-sf. Do not assume the name requires fossils, software symbols, open-source mascots, or modern technological subject matter.

Use this as an independent style, not an instruction to imitate one artist. Read `references/style-atlas.md` when developing a new family of subjects, or when resolving visual drift.

## Establish the task

1. Choose **redraw** when the user supplies a target image, or **invent** when they supply a description. Distinguish a style reference from the actual target. Inspect all target images before drafting the generation prompt.
2. Retain stated subject, framing, colors, output dimensions, transparency, exact wording, and edit constraints. User constraints outrank defaults. Ask only when a missing image or genuinely ambiguous target prevents execution.
3. Default to one finished drawing, one principal specimen, and a clean warm-white ground. Choose aspect ratio to fit the entire silhouette. Do not default to a poster, manuscript page, collection, or landscape.
4. If the request is primarily a human, city, or landscape, briefly explain the scope and ask which eligible object, creature, plant, or individual dwelling to isolate. If an eligible target is already named, isolate it without asking. Small contact shadows, a stone, a root clump, or a mounting base may establish contact without becoming a scene. Exclude human or humanoid figures, including scale figures and decorative faces.
5. Use the available image-generation/editing tool for the final raster art. Follow its reference-image and transparency requirements; never substitute a prose prompt for an image unless the user asks for a prompt. When image generation is unavailable, say so and supply a usable prompt without claiming completion. Preserve transparency on edits unless requested otherwise.

## The visual grammar

### 1. Stark silhouette without modern geometry

Give the subject a distinct outer contour and a clear hierarchy of masses, but reject modern graphic-design neatness. Never use ruler-straight lines, parallel rails, perfect circles, smooth Bezier curves, bubbly inflated volumes, or neatly rounded/chamfered corners. 

Even when the subject is a tool, machine, or dwelling, its geometry must feel hand-formed, grown, excavated, or cobbled from refractory materials: slightly warped planes, calcified ridges, pinched joints, brittle overhangs, and weathered asymmetries. Every straight edge should carry the slight tremor of unassisted hand drafting.

### 2. One governing estrangement

For invention, anchor the subject in one unsettling, dream-logic anomaly that blurs kingdoms of matter - mineral, botanical, zoological, and pre-industrial apparatus:
- A vessel that breathes through pleated gill-bellows to distil colored vapor.
- A blind, root-bound organism that secretes geometric crystalline tiles along its spine.
- An instrument of horn and oxidized brass whose levers manipulate a suspended membrane or acoustic cavity for an unknown sense.

Extend that rule into only the supporting details it needs. Connect disparate parts through eerie but seamless anatomical or material transitions: ossified sockets, stretched parchment-like skins, chitinous collars, grafted stems, or stratified stone seats. 

Let the drawing imply a cold, self-contained purpose - locomotion, parasitism, Dormant gestation, signal reception, or alchemical filtration - that feels indifferent to human comfort. Keep the uncanny strictly dry, structural, and taxonomic: never use gore, open wounds, viscera, blood, body horror, or adult/sexualized anatomy.

### 3. Brittle ink, drypoint etching, and chalky wash

Use fine, slightly scratchy dip-pen, etching-needle, or hard-lead contours with irregular hand pressure. Build volume through dense directional crosshatching, stippled pores, etched striations, and dry colored-pencil or chalk grain over translucent, slightly uneven watercolor or gouache washes.

Vary contour weight: incisive and dark in deep crevices and overlaps, thread-thin and fragile on membranes, filaments, and brittle edges. Leave open areas of raw, pale ground so the specimen feels isolated on an examination plate. 

Strictly avoid: smooth digital gradients, bubbly 3D shading, vector cleanliness, uniform cartoon outlines, glossy specular highlights, airbrushed softness, and fake coffee-stained parchment filters.

### 4. Alchemical and mineral coloration

Start with a bone-dry warm white or pale stone ground, soot-black or raw-umber ink linework, and three to five muted, slightly unsettling mineral or botanical pigments. Suggested families:
- Jaundice ochre + verdigris + bruised plum + bone ash
- Sulfur yellow + abyssal indigo + dried-madder rust + lichen gray
- Pale celadon + oxidized copper + faded carmine + parchment buff

Introduce one jarring, high-chroma focal passage - acidic chartreuse, electric cobalt, or poisonous vermilion - strictly where the specimen secretes, senses, articulates, or vents. Use banded pigment, speckled encrustations, or translucent membrane tints to separate rigid husk from soft or hollow interior.

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

1. Choose the subject category and its ordinary behavior or use.
2. Write one internal sentence: "This [thing] [does something] by [one unfamiliar mechanism/adaptation]."
3. Establish a plausible support, locomotion, attachment, growth, or load-bearing structure.
4. Design the silhouette first. Add only structures that follow the governing rule.
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
