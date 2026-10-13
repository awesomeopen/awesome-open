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

B15 varies the two existing images' display scale, gutter intrusion and CSS
close-up windows. No new derivative image, redraw or raster edit is made. Full
silhouettes are retained; only inset windows crop. The adjacent capability note
is source-backed software copy and needs no visual separation from the inset.
