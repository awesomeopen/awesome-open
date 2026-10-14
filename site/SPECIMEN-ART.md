# Specimen illustration handoff

Read [the current brand reference](../brand/README.md) and use the pinned skills under `.agents/skills/`. Add this instruction to Junge's discovery workflow after a project is accepted:

> Use **@Speculative FOSSoligy** and **@Retro-Scraperism** to generate one original specimen illustration from the project's repository and documentation. Read the repository first. Derive one coherent visual analogy from the tool's actual function. Use hand-drawn ink/pencil, a distinct silhouette, selective color, a square white background and no lettering. This is Awesome Open artwork, not the project's official logo. Avoid repeated anatomy and obligatory gears. Do not regenerate an existing accepted illustration unless asked.
>
> Save an optimized WebP as `site/specimens/<project-id>.webp`. Add its record to `data/specimen_art.json`. Regenerate the display cut-outs with `python3 scripts/build_specimen_cutouts.py` (needs Pillow, NumPy and SciPy) and refresh checksums with `python3 scripts/check_brand.py --refresh`. Submit all of it in the same PR. Review the image before marking it `approved`; leave unreviewed work `pending`. If image generation is unavailable or fails, continue discovery without an illustration. No placeholder is needed.

Skills are instructions, not APIs or image-generation services. Junge must have access to the two skills and an image-generation tool. Where skill mentions are unavailable, provide the skill files in its environment and instruct it to read them. Do not claim to invoke a skill by running an invented command.

## Identity and destination

Build the catalog after adding the accepted project:

```sh
python3 scripts/build_catalog.py --output tmp/catalog.json
```

Find the project by its canonical URL in `tmp/catalog.json` and use its complete `id`. This is the SHA-256 of the catalog's canonical URL. Do not hash the display name, use a category position, or shorten the hash. Cross-listed projects use one asset. Non-GitHub projects use the same catalog ID convention and their official documentation as the source. Renamed or redirected URLs require an explicit identity update.

Paths in the manifest are relative to the built site: `specimens/<project-id>.webp`. The source file is under `site/`. Commit durable asset bytes; never use a temporary image-generation URL or chat attachment as the site's dependency. Prefer a 768–1280px square WebP, under 500KB where possible. Preserve the complete silhouette. White is the default ground; do not use aged/cream paper. Record actual pixel dimensions.

## Manifest contract

The file has `schema_version: 1` and an `artworks` object keyed by full catalog ID. Each record contains:

```json
{
  "project_url": "https://github.com/owner/repository",
  "path": "specimens/<project-id>.webp",
  "alt": "A concise description of the illustrated subject and its action.",
  "width": 1024,
  "height": 1024,
  "source_document": "https://github.com/owner/repository/blob/main/README.md",
  "source_blob_sha": "<exact Git blob SHA of the consulted source document>",
  "created_at": "YYYY-MM-DD",
  "generator": "<actual image-generation tool/model if known>",
  "style": "Speculative FOSSoligy / Retro-Scraperism",
  "prompt": "<complete final generation prompt>",
  "review_status": "pending",
  "reviewed_by": null,
  "review_note": ""
}
```

For a source outside Git, replace `source_blob_sha` with `source_retrieved_at` and `source_content_sha256`. Record what was actually read; a source-document blob SHA is not a repository commit SHA. Keep generation provenance in the manifest; only path, alt text and dimensions enter the public catalog payload.

Review checks: function-based analogy; coherent structure; distinct silhouette within the series; no official-logo claim; readable at drawer size; no lettering; correct background; safe local path and matching project identity. The reviewer can be the design agent. `approved` means checked for inclusion in the proposed build; merging the PR remains the owner's publication approval. A change in star ranking does not delete existing artwork.

## Build behavior

Only approved records with existing files render. Missing files warn and are omitted; pending/rejected records are omitted. Missing entries leave no image or empty image box. An invalid approved identity, path, alt text or image format fails the build rather than publishing a mismatched asset. The builder copies active assets into `specimens/` and embeds them in `standalone.html`. Builds never call image generation or fetch remote artwork.

Pilot artwork covers OpenTofu, OpenRefine and OpenSCAD. The remaining top-three repositories can be processed in reviewed batches after this treatment is accepted.

## Display cut-out

The expanded record shows `site/specimens/cutouts/<project-id>.webp`, a transparent derivative
with only the border-connected white ground removed, so the decorative contour floor passes
behind the drawing. `site/specimens/cutouts.json` records the source and derivative hashes and
the subject's bounding box (used to place the feature-note crops). A missing or stale cut-out
never blocks a build: the original is shown without the floor and the build warns.
