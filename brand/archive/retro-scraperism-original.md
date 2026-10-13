> Historical input, captured 2026-10-13. Not current instructions. See the [archive index](README.md) and [current reference](../README.md).

<!-- Original source body begins below. -->
# **Retro-Scraperism:** 

# **Design System & Style Guide**

Retro-Scraperism balances the cold, speculative engineering of the early 20th century against the raw, organic chaos of field biology and human editorial intrusion. It treats the user interface not as a clean canvas, but as an excavated cyanotype (*or other monochrome*) drafting sheet that has been physically claimed by an obsessive field naturalist.

## **1\. Core Principles & Philosophy**

* **The Substrate Precedes the Organism:** The foundation is always structural, technical, and mechanical—ornithopter schematics, planetary gear trains, dials, and tripod drafting lines locked into a monochromatic cyanotype grid.  
* **Tactile Parasitism:** Natural history components (insects, feathers, botanical fragments, specimen cards) never sit cleanly within the grid; they physically overlap, pin down, clip to, and tear through the technical blueprints.  
* **The Living Hand (Editorial Friction):** Clean layouts are dead layouts. High-contrast human corrections—red pen annotations, spilled chemical stains, wax seals, and ink stamps—create urgency and focal points.

## **2\. Color Palette & Token Architecture**

The palette uses a binary split: a cold, monochromatic blueprint foundation balanced against warm cellulosic substrate tones, broken open by high-saturation chemical and biological accents.

| Token Role | Name | Visual Reference | Hex Code (Target) | Application |
| :---- | :---- | :---- | :---- | :---- |
| **Base Canvas** | blueprint-prussian | Deep Prussian cyanotype wash | \#0B2546 | Full-page backgrounds, technical surfaces |
| **Drafting Line** | blueprint-trace | Exposed blueprint white/cyan | \#D9EEF8 | Grid lines, schematics, technical UI borders |
| **Substrate Primary** | paper-parchment | Aged library paper, manila card | \#F3E8CE | Specimen cards, data containers, modal windows |
| **Substrate Secondary** | paper-kraft | Heavy cardboard, envelope kraft | \#A07855 | Secondary cards, tag overlays, torn backings |
| **Primary Accent** | ink-scarlet | Curator's red ink, wax seal | \#D9251D | Critical alerts, active states, rubber stamps |
| **Chemical Wash** | stain-amber | Acid yellow reagent, shellac wash | \#FFC800 | Highlighting, hover blooms, focus rings |
| **Biological Flare** | chitin-emerald | Metallic buprestid beetle wing | \#00A86B | Primary badges, success states, hero visuals |
| **Oxide / Fastener** | metal-verdigris | Tarnished brass, oxidized copper | \#4A7C72 | Clips, safety pins, grommets, frame brackets |

## 

## **3\. Typography Hierarchy**

Four distinct typographic voices collide across layers:

> 1. **The Technical Blueprint (Drafting & Specs):**  
   * *Style:* Monospaced drafting sans or technical stencil (e.g., *Share Tech Mono*, *DIN 1451 Mittelschrift*).  
   * *Usage:* Data values, coordinates, technical specs, navigation indicators, breadcrumbs.  
   * *Treatment:* High letter-spacing, uppercase, rendered in blueprint-trace.  
> 2. **The Field Catalog (Structure & Readability):**  
   * *Style:* High-contrast Victorian or Edwardian book serif (e.g., *Scotch Modern*, *Caslon*, *Century Schoolbook*).  
   * *Usage:* Primary card headers, specimen names, long-form content, modal headers.  
   * *Treatment:* Classic title casing, dark sepia ink tones (\#2B1E16).  
> 3. **The Urgent Margin (Human Annotation):**  
   * *Style:* Frantic, loose fountain pen script or architect’s pencil scrawl.  
   * *Usage:* Microcopy, contextual hints, user-driven notes, validation warnings.  
   * *Treatment:* Slightly rotated (-2° to 4°), color-coded in ink-scarlet or raw carbon.  
> 4. **The Administrative Bureaucracy (Action & State):**  
   * *Style:* Bold, distressed rubber-stamp serif or industrial block (e.g., *Special Elite*, *Stamp Gothic*).  
   * *Usage:* Status tags (CONFIDENTIAL, SPECIMEN NO. 4, REJECTED, ALERT).  
   * *Treatment:* Framed inside jagged borders, stamped at an angle, ink-bleed edges.

## 

## **4\. UI Components & Interaction Patterns**

### **Containers & Cards**

* **The Pinned Specimen Card:** White or aged ivory background with a thin double-hairline border. Positioned offset from the base grid, carrying a hard drop shadow (rgba(0, 0, 0, 0.45) with 0px blur, 6px offset) to mimic paper thickness.  
* **Torn Edge Dividers:** Section breaks should use jagged alpha masks representing torn blueprint paper rather than straight horizontal rules.  
* **Physical Framing:** Containers are held in place visually by vector brass clips, safety pins, or rusted binder clasps anchored along the borders.

### **Action Elements (Buttons & Inputs)**

* **Primary Actions:** Styled as deep-red embossed wax seals or vivid rubber-stamp badges (CONFIDENTIAL 1904, PROCEED). On hover, the element slightly shifts angle, increases shadow depth, and reveals a faint scarlet ink halo.  
* **Secondary Actions:** Shaped like manila shipping tags with reinforced brass grommets and string cutouts.  
* **Form Inputs:** Styled as formal field-journal blanks with dotted lines on parchment or blueprint grid boxes. Typing triggers an analog typewriter or drafting-ink font style.

### **Badges, Status & Feedback**

* **Status Badges:** Small rectangular taxonomic labels affixed with virtual masking tape or straight brass pins (SPECIMEN NO. 4, RESTRICTED).  
* **Warnings & Alerts:** Freehand scarlet circles, underlined scrawls, and arrows that look drawn directly over the blueprint canvas (ALERT\!, VOID?).  
* **Highlighting / Selection States:** Translucent, irregular splatter washes of stain-amber beneath active text or selected rows, mimicking dropped liquid reagent or highlighter ink.

### **Hero Imagery & Visual Anchors**

* **Subject Treatment:** Botanical sketches and dull brown textures are strictly paired with or replaced by **iridescent macro-zoological assets**—jewel beetles with emerald and sapphire carapaces, vibrant orange-and-crimson silk moths, and peacock quill feathers.  
* **Mechanical Counterweight:** Always juxtapose biological assets against finely detailed Victorian sci-fi apparatus: brass vacuum tubes, three-legged walking tanks, exposed pendulum gearworks, and astronomical dial rings.
