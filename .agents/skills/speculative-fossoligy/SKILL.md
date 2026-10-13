---
name: speculative-fossoligy
description: Create original drawings or redraw supplied images in Speculative FOSSoligy, an invented visual language combining observed natural-history detail, coherent impossible anatomy, curious mechanisms, and selective psychedelic color. Use for animals, plants, tools, machinery, toys, objects, and isolated dwellings. Support faithful style transfer, description-based invention, and visually varied batches such as logos for multiple software tools. Exclude humans, humanoid characters, landscapes, and cities as subjects.
---

# Speculative FOSSoligy

Draw unfamiliar things as if they have been carefully observed, handled, and partially understood. Make the subject strange; make the drawing lucid. Preserve the user's spelling, **Speculative FOSSoligy**. Do not assume the name requires fossils, software symbols, open-source mascots, or technological subject matter.

Use this as an independent style, not an instruction to imitate one artist. Read `references/style-atlas.md` when developing a new family of subjects, resolving visual drift, or explaining the sources. The operational rules below suffice for ordinary generation; do not repeatedly retrieve the original web images.

## Establish the task

1. Choose **redraw** when the user supplies a target image, or **invent** when they supply a description. Distinguish a style reference from the actual target. Inspect all target images before drafting the generation prompt.
2. Retain stated subject, framing, colors, output dimensions, transparency, exact wording, and edit constraints. User constraints outrank defaults. Ask only when a missing image or genuinely ambiguous target prevents execution.
3. Default to one finished drawing, one principal specimen, and a clean warm-white ground. Choose aspect ratio to fit the entire silhouette. Do not default to a poster, manuscript page, collection, or landscape.
4. If the request is primarily a human, city, or landscape, briefly explain the scope and ask which eligible object, creature, plant, or individual dwelling to isolate. If an eligible target is already named, isolate it without asking. Small contact shadows, a stone, a root clump, or a mounting base may establish contact without becoming a scene. Exclude human or humanoid figures, including scale figures and decorative faces.
5. Use the available image-generation/editing tool for the final raster art. Follow its reference-image and transparency requirements; never substitute a prose prompt for an image unless the user asks for a prompt. When image generation is unavailable, say so and supply a usable prompt without claiming completion. Preserve transparency on edits unless requested otherwise.

## The visual grammar

### 1. Recognition before surprise

Give the subject a strong, readable contour and a clear hierarchy of masses. Add protrusions only when the subject calls for them; compact, enclosed, suspended, stacked, and open structures are equally valid. At thumbnail size, the subject category and posture/function should remain legible. Use asymmetry when it suggests growth, use, adaptation, or repair; avoid ornamental imbalance everywhere.

### 2. One governing impossibility

For invention, choose one consequential oddity: a shell unfolds into a working surface; a plant stores its own rain in jointed reservoirs; a toy winds itself through a rolling seed. Extend that rule into only the supporting details it needs; do not turn a suggested detail count into a fixed number of limbs, branches, tools, or components. Connect structures through shared material, gradual anatomical transitions, believable joints, or matching attachment surfaces. Do not paste an unrelated animal head onto an appliance and call the combination complete.

Let the drawing answer at least one question without text: How does it move, feed, open, grow, shelter, play, or perform its task? Suggest local cause and effect without pretending the object is scientifically possible. A purely biological organism need not contain manufactured parts; a tool need not be alive.

For a faithful redraw, do not impose this impossibility by changing protected geometry. Carry strangeness through color, line, material interpretation, and the observational presentation. Structural mutation requires authorization.

### 3. Observational drawing with graphic discipline

Use fine, slightly variable dark ink or pencil-like contours; selective crosshatching, stippling, and colored-pencil grain; translucent color with occasional flat, saturated regions. Make the handmade quality reside in marks and small decisions, not an applied distress filter. Describe volume with economical hatching and modest internal shading. Keep edges crisp enough to read.

Vary contour weight: firmer at overlaps and contact, delicate on membranes and fine appendages. Leave quiet areas unworked. Avoid glossy CGI, cinematic lighting, photographic surfaces, airbrushed fantasy polish, uniformly heavy cartoon outlines, and fake antique paper stains.

### 4. Color that describes anatomy or operation

Start with warm white or pale ivory, charcoal/umber linework, and three to five main colors. Suggested families: moss + oxidized turquoise + ochre + coral; ink blue + leaf green + vermilion + cream; plum + teal + straw yellow. These are options, not fixed brand colors.

Place one high-chroma passage where the subject acts, opens, senses, or changes material. Allow unlikely but deliberate color relationships. Use repeated bands, dots, scales, or ribs to distinguish tissues or components. Reserve pattern for meaningful surfaces, rather than covering the whole drawing. Retain specified source colors during a constrained redraw. A psychedelic variant may expand saturation, but must preserve contour and value hierarchy.

### 5. Controlled abundance

Concentrate intricate marks in a small number of useful areas, such as a hinge, sensory organ, folded edge, or junction. Keep the principal mass calmer. Prefer one unexpected secondary discovery over many unrelated curiosities. Let a close look reveal a detail that explains the main form.

### 6. Calm attention toward an odd subject

Aim for curiosity, dry amusement, and a little unease. Present the thing matter-of-factly; do not dramatize its importance. Avoid heroic staging, magical glow, cute mascot defaults, grinning faces, random tentacles, ubiquitous eyeballs, decorative gears, and horror by default. A toy can be playful without becoming a character; an animal can be expressive without human gestures.

## Redraw workflow

Before generation, make a short internal preservation list: subject identity, count, pose, silhouette, orientation, proportions, attachment points, defining parts, composition, text, and colors that the user requires.

- **Faithful (default):** Preserve identity, anatomy/geometry, pose, count, and composition. Change drawing medium, rendering, and unconstrained color treatment. Do not grow extra limbs, add mechanisms, or replace parts merely to increase strangeness.
- **Interpretive (only when invited):** Preserve the identifying silhouette and defining parts; reinterpret selected structures through one coherent transformation. Keep protected details exact.
- **Free rein (only when invited):** Rebuild morphology around the described function and one governing impossibility, while retaining explicitly requested anchors.

Use the original target as the image-edit reference. Describe preservation constraints before style instructions. If a scenic input contains a clearly specified eligible target, isolate it while retaining that target's pose and defining structure. Do not remove backgrounds when the user explicitly asks to preserve composition without resolving that conflict.

For follow-up edits, preserve the accepted version and change only the requested aspect. Avoid restarting the design or silently increasing mutation on each pass.

## Invent workflow

1. Choose the subject category and its ordinary behavior or use.
2. Write one internal sentence: “This [thing] [does something] by [one unfamiliar mechanism/adaptation].”
3. Establish a plausible support, locomotion, attachment, growth, or load-bearing structure.
4. Design the silhouette first. Add only structures that follow the governing rule.
5. Choose a view that exposes the important relationship: profile for locomotion, three-quarter for tools, front view for symmetry, or a restrained section for internal function.
6. Choose the main drawing plus, only when useful, one detail inset or a two-to-three-state sequence. Keep consistent geometry, scale relationships, and material colors across states. Never turn every request into a labeled scientific plate.
7. Apply the visual grammar and generate the image.

## Variation across drawings and batches

Keep the style recognizable through drawing language and internal logic, not a recurring body plan. Apply this to consecutive requests as well as explicit batches such as “10 logos for these 10 software tools.” Do not carry the previous prompt's composition into the next concept by inertia.

For a batch, plan all items briefly before generating the first image. Keep an internal table with one row per item: actual function, metaphor/governing rule, silhouette, orientation/view, component count and arrangement, organic/manufactured balance, and focal color placement. Derive each concept independently from its subject. For software logos, identify each tool's distinguishing purpose; avoid giving every project the same generic multi-tool organism.

- Deliberately vary silhouette, orientation, component count, and spatial arrangement across the set. Use meaningful differences such as compact versus elongated, enclosed versus open, stacked versus nested, front-facing versus profile, or suspended versus grounded. These are options, not a mandatory rotation or template list.
- Compare each proposal with both neighboring items and the set as a whole. Revise accidental repeats of the same main mass, appendage layout, or operational metaphor. Mirroring, recoloring, or changing surface ornament alone does not establish a distinct design.
- Specifically check for the observed failure of “three branches growing horizontally out of the right side.” It is not a signature of this style. Also watch for repeated shells, spirals, plant-machine hybrids, and left-input/right-output apparatuses. Use any of these when justified, without making them defaults.
- Preserve family resemblance through compatible linework, texture, detail hierarchy, framing, and, when appropriate, a shared palette. Do not force every subject to share anatomy, machinery, materials, or accent placement.
- Let function determine part counts and arrangement. Do not invent unnecessary parts, distort the concept, or randomize geometry merely to satisfy variety. A machine can remain entirely manufactured; an organism can remain entirely biological.
- For faithful redraws, preserve the supplied silhouettes, counts, orientations, and composition. Vary only unconstrained treatment. For requested variants of one established mark, preserve its identifying structure and vary only the permitted axes; continuity takes precedence over diversity.

Generate one separate image per requested item unless the user asks for a combined sheet. In each prompt, specify that item's own structure and composition explicitly. After generation, compare the actual silhouettes and arrangements across the batch; correct clear accidental duplication with targeted edits. Do not regenerate accepted designs solely to maximize novelty.

## Adapt to subject category

| Subject | Develop | Avoid |
|---|---|---|
| Animal | Weight-bearing limbs, feeding or sensory adaptation, surfaces that follow anatomy | Random limb counts, obligatory machinery, mascot expressions |
| Plant | Root/stem/leaf continuity, growth rhythm, storage or dispersal strategy | Generic alien flower plus unrelated eyeballs |
| Tool | Grip, working end, joint, and a visible force path | Decorative cogs without a function |
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
6. Short exclusions relevant to this specific request.

Describe the traits explicitly; the invented style name alone carries no reliable instructions. Do not rely on artist-name lists or “surreal/psychedelic” alone. Do not copy recognizable reference creatures, compositions, or source glyphs. Omit lettering by default. If requested, use the user's actual readable labels; reserve invented script for an explicit request and never let it substitute for structure.

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
