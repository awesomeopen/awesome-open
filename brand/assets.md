# Asset index

Keep existing deployable assets in their current `site/` locations; moving them
into a new folder would add broken-path risk without improving ownership. This
index centralizes discovery. [assets.lock.json](assets.lock.json) records paths,
byte sizes and SHA-256 hashes; it is an integrity inventory, not approval metadata.

| Family / use | Durable source | Status and provenance |
| --- | --- | --- |
| Header botanical mark | `site/brand/botanical-128.png` | Implemented; [owner source and lettering-removal edit](../site/brand/BOTANICAL-LOGO.md); rendered at 64 CSS px |
| Fruit variants / favicon | `site/brand/fruit-16.png`, `fruit-32.png`, `fruit-96.png`, `favicon.ico` | Tracked brand assets; fruit-96 marks ledger end; earliest generation provenance remains incomplete |
| Full logo artwork | `site/brand/awesome-open-logo.png` | Retained tracked asset; do not infer that every retained variant is the active header |
| Search loupe | `site/brand/search-loupe.png` | Implemented; [owner-supplied icon](../site/brand/SEARCH-ICON.md); 96px source, 32px display in 44px target |
| Seven specimen interpretations | `site/specimens/*.webp` | Per-entry status, alt, prompt and source in [specimen manifest](../data/specimen_art.json) |
| Photographic jars | `site/jars/*.webp` | Active/retained unlabelled variants distinguished by [jar provenance](../site/jars/provenance.json) |
| Footer floor images | `site/footer-backgrounds/valley.webp`, `abyssal.webp` | Implemented; original filenames, original hashes and processing in [footer provenance](../site/footer-backgrounds/provenance.json) |
| Fraunces + Commit Mono | `site/vendor/fonts.css` | Embedded complete variable WOFF2; [pinned source provenance](../site/vendor/FONT-PROVENANCE.json) and [SIL OFL notice](../site/vendor/FONT-LICENSE.txt) |
| Tokens | `site/design/tokens.css` | Exact color/type/spacing values; editable implementation source, not raster artwork |
| Specimen display cut-outs | `site/specimens/cutouts/*.webp` | Transparent derivatives of approved specimens (border-connected white ground removed); source/derivative hashes, subject box and recipe in [cut-out manifest](../site/specimens/cutouts.json); regenerate with `scripts/build_specimen_cutouts.py` |
| Label paper studies | `brand/studies/label-papers/*.webp` | Rejected study, not deployed; generator, prompts, seeds, source hashes and keying recipe in [study provenance](studies/label-papers/provenance.json) |

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
review status and use in expanded artwork, the standalone download and print stay
unchanged. `site/jars/responsive.json` records original hashes, derivative hashes,
dimensions and the encoding recipe; `brand/assets.lock.json` inventories the bytes.

Regenerate deliberately with `python3 scripts/build_hero_images.py` using Pillow
12.3.0 and libwebp 1.6.0, then inspect glass/ink at 1×/2×/3× and hover size before
refreshing the checksum inventory. Normal builds copy the committed derivatives
and need no new Python dependency. The hero's responsive sizes cover its fixed CSS
heights, 110% hover scale and 300px no-JavaScript fallback. Glass/reflection/lid/sticker/cork and
CSS underlight use matching candidate resolutions to reuse the same download.
Print selects original sources; expanded art and the offline edition still use
original specimen bytes. This is a delivery optimization, not new artwork or a
change to the accepted visual system.

B15 varies the two existing images' display scale, gutter intrusion and CSS
close-up windows. No new derivative image, redraw or raster edit is made. Full
silhouettes are retained; only inset windows crop. The adjacent capability note
is source-backed software copy and needs no visual separation from the inset.

The square-cork and ribbed jar photographs also supply clipped paper-label overlays
in the hero. These restore their original worn stickers above the glass treatment;
no source image bytes or provenance changed (B18).

The square bottle also reuses its original brown cork as a clipped overlay.

## Observatory use

The snapshot observatory reuses the approved Open Doc drawing at
`site/specimens/10d69f0daa625d430823f0f96fe4a54501756699271de233b676a41c1fdc2576.webp`
as a single compact editorial specimen. It is labeled an original interpretation,
not a software logo or numerical encoding. Existing bytes, full silhouette,
manifest provenance and checksum remain unchanged. The offline report embeds
that same file; no artwork collection is downloaded by the new route.

## Specimen plate derivatives

The plate shows a transparent cut-out of each approved specimen so the decorative
contour floor can pass behind it. `scripts/build_specimen_cutouts.py` (Pillow 12.3.0,
NumPy, SciPy, libwebp 1.6.0) removes only white ground connected to the image border;
pale areas inside a drawing stay opaque. The manifest records each source hash, so a
changed original silently falls back to itself (with a build warning) until the cut-out
is regenerated. Normal builds copy the committed bytes and need no new dependency.
Originals, alt text and approval status are unchanged. Permalink QR codes are generated
during the build (`scripts/qr.py`) and are not committed assets.
