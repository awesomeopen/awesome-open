# Asset index

Keep deployable assets in their documented `site/` families. Repeating CSS
textures live in `site/patterns/`; rotating panoramas live in `site/footer-backgrounds/`. This
index centralizes discovery. [assets.lock.json](assets.lock.json) records paths,
byte sizes and SHA-256 hashes; it is an integrity inventory.

| Family / use | Durable source | Status and provenance |
| --- | --- | --- |
| Header botanical mark | `site/brand/botanical-128.png` | Implemented; [owner source and lettering-removal edit](../site/brand/BOTANICAL-LOGO.md); rendered at 64 CSS px |
| Fruit variants / favicon | `site/brand/fruit-16.png`, `fruit-32.png`, `fruit-96.png`, `favicon.ico` | Tracked brand assets; fruit-96 marks ledger end for All or categories without artwork; earliest generation provenance remains incomplete |
| Full logo artwork | `site/brand/awesome-open-logo.png` | Retained tracked asset; do not infer that every retained variant is the active header |
| README catalog banner | `site/brand/readme-banner.png` | User-selected revised image; unchanged 2172 × 724 PNG, source and SHA-256 in [banner provenance](../site/brand/README-BANNER.md); README-only placement for review |
| README Browse link | `site/brand/browse-catalog.svg` | Local flat-square Prussian text vector; recipe and status/count ownership in [README badge contract](../site/brand/README-BADGES.md); generated count SVG remains publisher-owned under `assets/readme/` |
| Interface icons | `site/brand/icons/{id}-{size}.svg` | 21 proposed `today` icons at 12/16/24 px, written by `scripts/build_icons.py` from the [icon map](icons.md); method and reference drafts in [icon provenance](../site/brand/icons/provenance.json) (B-PR103-01); not used by the site yet |
| Search loupe | `site/brand/search-loupe.png` | Implemented; [owner-supplied icon](../site/brand/SEARCH-ICON.md); 96px source, 32px display in 44px target |
| Catalog specimen interpretations | `site/specimens/*.webp` | Per-entry status, alt, prompt and source in [specimen manifest](../data/specimen_art.json); approved present art is eligible for the weekly jar draw and archive (B38), and is reused in Observatory shared-name comparisons |
| Category illustrations | `site/domains/*-{s,m,l}.webp` | 21 owner-uploaded category interpretations; medium variants also close the selected category’s ledger; source filename mapping, verified derivative hashes/dimensions, recipe and provenance limits in [category provenance](../site/domains/provenance.json) |
| Photographic jars | `site/jars/*.webp` | Active/retained unlabelled variants distinguished by [jar provenance](../site/jars/provenance.json) |
| Footer pattern | `site/patterns/navypattern2.png` | Owner-committed repeating CSS background for the footer, kept separate from transparent panorama rotation; unchanged bytes and provenance limits in [pattern provenance](../site/patterns/provenance.json) |
| Footer floor images | `site/footer-backgrounds/*.{png,webp}` | Native-size, centered/bottom-aligned panoramas; PNG sources converted to lossless WebP with bottom-only crop boxes, original source revisions/hashes and output checksums in [footer provenance](../site/footer-backgrounds/provenance.json); aquatic-wreck/electrical-relics use 75% Lanczos derivatives with gentle alpha-preserving sharpening (B41) |
| Commit Mono | `site/vendor/fonts.css`, `site/vendor/*.woff2` | Unchanged complete WOFF2 bytes, separately hosted for demand loading; [pinned source provenance](../site/vendor/FONT-PROVENANCE.json) and [SIL OFL notice](../site/vendor/FONT-LICENSE.txt) |
| Półtawski Nowy | `site/vendor/serif-preview/` | Settled serif at regular 400, with genuine bold 700 in the same variable file. [Pinned source provenance](../site/vendor/serif-preview/provenance.json) and adjacent OFL notices. Offline editions embed Półtawski + Commit Mono only. |
| Tokens | `site/design/tokens.css` | Exact color/type/spacing values; editable implementation source, not raster artwork |
| Specimen display cut-outs | `site/specimens/cutouts/*.webp` | Transparent derivatives of approved specimens (border-connected white ground removed); source/derivative hashes, subject box and recipe in [cut-out manifest](../site/specimens/cutouts.json); regenerate with `scripts/build_specimen_cutouts.py` |
| Specimen plate variants | `site/specimens/responsive/*.webp` | 512/768 px display copies of each plate's shown source (cut-out or original), for `srcset`; source/variant hashes and recipe in [variant manifest](../site/specimens/responsive.json); regenerate with `scripts/build_specimen_variants.py` (B-PR196-01) |
| Icon draft study | `brand/studies/icon-drafts/*.webp` | 21 generated Retro-Scraperism reference drafts for the interface icons, not deployed; FLUX.2 [klein] 4B (Apache-2.0), seeds, prompts and hashes in [study provenance](studies/icon-drafts/provenance.json) (B-PR130-01) |
| Label paper studies | `brand/studies/label-papers/*.webp` | Rejected study, not deployed; generator, prompts, seeds, source hashes and keying recipe in [study provenance](studies/label-papers/provenance.json) |
| Plate evidence grid study | `brand/studies/plate-grid/*.png` | Cropped screenshots of the fixed evidence-grid mock-up, not deployed; regenerated from real catalog data by the study generator, see [study notes](studies/plate-grid/README.md) |

## Originals outside the repository

The owner's file collection retains these named sources. Filenames identify
candidates, not proof that duplicate imports contain identical bytes:

- `Awesome Open botanical fruit half logo.png`
- `Awesome Open botanical fruit half logo-1.png`
- `Awesome Open botanical fruit half logo-1(1).png`
- `Awesome Open botanical fruit half logo-1(2).png` — named source of header edit
- `Ivory-handled turquoise magnifying glass icon(1).png`
- `Boschlike Creatures in a Transparent Valley(1).png`
- `Strange Abyssal Life Network(1).png`

Use recorded original hashes where available to resolve ambiguous duplicates.
This consolidation does not re-upload large originals or claim byte equivalence
without comparison. No temporary signed URLs or private Library identifiers belong
in public manifests. Newly accepted source assets need durable bytes or a stable
retrieval reference plus checksum; the production site must use local derivatives.

## Rights

Retain existing owner-supplied / generated provenance accurately. The repository's
CC0 notice does not prove rights in third-party references or grant trademark
clearance. Preserve separately licensed font notices. No independent rights audit
of historical logo/owner-supplied art is claimed. Add missing provenance when it
can be established; do not invent a generator, rights holder or license.

The specimen-plate study reuses the approved OpenTofu and OpenRefine WebP files
at their existing paths. Each full illustration is accompanied by a CSS-cropped
detail beside a separately sourced software feature note (B14 supersedes the
drawing-analogy captions). No artwork bytes or upstream provenance change; the
software claims come from reviewed Function sources, not from these crops.

## Hero display derivatives

The seven hero jars and seven composited specimens have display-only 256/512/768px
wide WebP derivatives under `site/jars/responsive/`. Their original files, prompts,
review status and use in expanded artwork and print stay unchanged. `site/jars/responsive.json` records original hashes, derivative hashes,
dimensions and the encoding recipe; `brand/assets.lock.json` inventories the bytes.

Regenerate deliberately with `python3 scripts/build_hero_images.py` using Pillow
12.3.0 and libwebp 1.6.0, then inspect glass/ink at 1×/2×/3× and hover size before
refreshing the checksum inventory. Normal builds copy the committed derivatives
and need no new Python dependency. The hero's responsive sizes cover its fixed CSS
heights, 110% hover scale and 300px no-JavaScript fallback. Glass/reflection/lid/sticker/cork and
CSS underlight use matching candidate resolutions to reuse the same download.
Print selects original sources; expanded art and the offline edition still use
original specimen bytes. This is a delivery optimization.

B15 varies the two existing images' display scale, gutter intrusion and CSS
close-up windows. No new derivative image, redraw or raster edit is made. Full
silhouettes are retained; only inset windows crop. The adjacent capability note
is source-backed software copy and needs no visual separation from the inset.

The square-cork and ribbed jar photographs also supply clipped paper-label overlays
in the hero. These restore their original worn stickers above the glass treatment;
no source image bytes or provenance changed (B18).

The square bottle also reuses its original brown cork as a clipped overlay.

## Observatory use

The Observatory opening uses `site/brand/botanical-128.png`, the existing 128 × 128
botanical logo, without a visible caption. Display it at no more than its intrinsic
width; retain descriptive alt text.
The previous Open Doc specimen remains unchanged in the catalog; its Observatory
placement is superseded by the user-directed logo replacement (B23). No asset
bytes or source provenance changed.

## Category navigation

The 21 category illustrations retain all 63 owner-uploaded WebPs unchanged from
commit `7045703d7b8fa09135fee41dd4a72da42476c6f3`. The variants are 104, 207 and
414px square with transparency, totaling 1,874,384 bytes. The Table of contents
uses 48 CSS px decorative images beside the existing category names and counts.
Responsive candidates choose the small source at 1×/2×; native lazy loading
defers the closed disclosure's images. The full small set is 150,040 bytes.
No category art is added to the hero, project identities or Observatory charts.
The Observatory reuses the small source as a decorative background in each
summary metric when its category is selected; All/reset has no background.
Asset bytes are unchanged.

Original PNGs stay in the owner's archive. The public provenance records their
descriptive filenames and the known resize recipe, but original hashes, original
encoding versions, generation tool and prompts remain unknown. The recorded
validation environment describes synthetic tests, not the original encoder.
See [regeneration instructions](../scripts/RESIZE-CATEGORY-IMAGES.md). Do not claim a
byte-identical rebuild until the archived originals and toolchain are verified.

The geometry trials are withdrawn by B24. Original illustration bytes remain
unchanged; no comparison clipping contour or new shadows are deployed.

## Specimen plate derivatives

The plate shows a transparent cut-out of each approved specimen so the decorative
contour floor can pass behind it. `scripts/build_specimen_cutouts.py` (Pillow 12.3.0,
NumPy, SciPy, libwebp 1.6.0) removes only white ground connected to the image border;
pale areas inside a drawing stay opaque. The manifest records each source hash, so a
changed original silently falls back to itself (with a build warning) until the cut-out
is regenerated. Normal builds copy the committed bytes and need no new dependency.
Originals, alt text and approval status are unchanged. Permalink QR codes are generated
during the build (`scripts/qr.py`) and are not committed assets.

On 2026-10-17 UTC, the owner approved the existing OpenCode, openpilot and
OpenAssistant drawings as-is for inclusion. Their manifest entries retain the
prior visual observations and generation provenance. The full source WebPs are
unchanged; three display cut-outs were added using the existing recipe. Each new
cut-out records its actual tool versions without rewriting older derivatives or
their provenance. This updates asset eligibility.

The 2026-10-19 jar-fit proposal adds only the missing OpenTaco, Open Moderator
and Open3D display cut-outs from their existing approved originals. Source bytes,
identity and approval status remain unchanged. Their cut-out manifest entries
record source/derivative hashes, measured bounds and the actual encoding tools;
older derivatives and their provenance are preserved.

The same proposal adds only those three cut-outs' 256/512/768px hero derivatives
with the existing Lanczos/WebP q85 recipe, under distinct `-cutout-` filenames.
Per-source recipes and hashes live in `site/jars/responsive.json`; no existing
hero derivative is replaced. These reduce their screen payload; original cut-outs
remain the high-density and print candidates.

The plate's image also offers 512 and 768 px wide WebP variants of its shown
source through `srcset` (B-PR196-01), written by `scripts/build_specimen_variants.py`
with the hero's Lanczos/WebP q85 recipe under `site/specimens/responsive/`. The
source stays the widest candidate and the loupe's image. Source bytes, alt text
and approval status are unchanged. See
[display variants](../site/SPECIMEN-ART.md#display-variants).

## Jar body composition

The hero may fit a reviewed horizontal body span while peripheral parts disappear
behind a photo-traced inner-wall contour. OpenObserve's span and original-source
hash live in `scripts/build_jar_preview.py::SPECIMEN_BODY_SPANS`; complete subject
bounds, original WebPs, cut-outs and record/Spotlight archive illustrations remain
unchanged. Contours are manually calibrated against the existing photographic
sources, including the low jar's leaning-lid occlusion. They affect display
composition only; no asset bytes or checksum inventory change. See the
[fit contract](../site/WEEKLY-DRAWS.md#fit-and-archive).

The Scoreboard `rank.trophy` interface glyph is authored by `scripts/build_icons.py`;
its shape, 16px grid and label contract are in the icon map. Provenance is in
`site/brand/icons/provenance.json`; it uses no specimen or generated-image source.
