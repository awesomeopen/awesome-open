# Specimen illustration handoff

Read [the current brand reference](../brand/README.md) and use the pinned skills under `.agents/skills/`. The current discovery task attempts artwork after a project is accepted on main, independently of catalog publication. A separate daily task backfills missing artwork; see the [automation inventory](../automation/README.md#backfill-specimen-artwork) for its cadence and scope.

> Use **@Speculative FOSSoligy** and **@Retro-Scraperism** to generate one original specimen illustration from the project's repository and documentation. Read the repository first. Derive one coherent visual analogy from the tool's actual function. Use hand-drawn ink/pencil, a distinct silhouette, selective color, a square white background and no lettering. Avoid repeated anatomy and obligatory gears. Do not regenerate an existing accepted illustration unless asked.
>
> Save an optimized WebP as `site/specimens/<project-id>.webp`. Add its record to `data/specimen_art.json`. Generate the matching display cut-outs with `python3 scripts/build_specimen_cutouts.py` (needs Pillow, NumPy and SciPy), update `site/specimens/cutouts.json`, and refresh the corresponding checksums with `python3 scripts/check_brand.py --refresh`. Submit originals, matching cut-outs, both manifests and their checksum changes together in a separate scoped artwork draft PR, never in the direct catalog commit or summary PR. Preserve unrelated images and manifest/checksum entries; see the task scopes below. Inspect the actual image pixels and record review findings. New images are display-approved by default under the owner's standing direction: use `approved` once technical, provenance and safety checks pass, even when stylistic reservations remain. Record those reservations as nonblocking notes; do not wait for individual owner image sign-off. Leave work `pending` if the required inspection or checks are incomplete. If image generation is unavailable or fails, continue discovery without an illustration. No placeholder is needed.

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
  "review_status": "approved",
  "reviewed_by": "<actual inspecting agent/person; identify AI reviewers as AI>",
  "review_note": "<actual pixel-review findings and checks; display-approved under owner standing direction; any nonblocking style reservations>"
}
```

For a source outside Git, replace `source_blob_sha` with `source_retrieved_at` and `source_content_sha256`. Record what was actually read; a source-document blob SHA is not a repository commit SHA. Keep generation provenance in the manifest; only path, alt text and dimensions enter the public catalog payload.

## Default display approval and review

The owner's standing direction of 2026-10-17 approves new images for display by
default; individual drawings can be redone later. For new specimen records, use
`approved` after actual pixel inspection and the required technical, provenance
and safety checks. No separate owner sign-off on each image is needed. This
policy does not bulk-change historical statuses or authorize replacing existing
accepted illustrations.

Inspect function-based analogy, coherent structure, silhouette differentiation,
readability at drawer size, lettering, palette and background. Record what the
pixels actually show, including shortcomings. Style and aesthetic-quality
reservations are nonblocking: keep the image `approved`, describe them in
`review_note`, and identify any useful later revision. Do not claim that every
style criterion passed because display is approved by default.

Technical validity, safe local paths, matching project identity, correct image
format/dimensions, meaningful alt text, source/generation provenance, rights and
safety remain required. Do not treat an official-logo misrepresentation, unsafe
content or an unresolved rights/provenance issue as a style reservation. Use
`pending` while required inspection or checks are incomplete or unresolved;
use `rejected` for a confirmed blocking issue and record the reason. Generation
failure still leaves no placeholder.

`reviewed_by` names the actual inspector and identifies an AI reviewer as AI;
`review_note` records the checks, findings and approval basis as owner standing
direction. Never name the owner as the individual reviewer unless that review
actually happened, or invent a human review. The manifest example above is a
completed-record template, not evidence that its placeholder checks occurred.

## Publication after validation

The owner's standing direction of 2026-10-31 authorizes publication of technically
valid new illustrations without a per-image or per-batch aesthetic approval.
This applies to discovery artwork and artwork backfill only. A manifest's
`approved` status still records display eligibility, not proof of completed checks.

Create a separate scoped draft PR containing only new originals, matching new
cut-outs, their new records in both manifests and corresponding incremental
asset-lock entries. Preserve existing assets, records and owner edits. Keep at
most one backfill batch in flight; complete or resolve it before starting another.

Before publication:
- Inspect the generated pixels and verify identity, dimensions, alt text,
  technical validity, provenance, rights and safety. Record truthful AI review;
  stylistic reservations remain nonblocking.
- Save original generation artifacts, prompts, source evidence, final images,
  cut-outs, manifests and checksums in a verified recoverable bundle before
  GitHub uploads. Record durable recovery references outside the repository.
- Run the required offline tests, README/catalog/site builds and applicable
  browser/preview checks. Verify the remote diff and exact head, all required
  CI to a successful terminal outcome, and preserved unrelated records.
- Recheck current main, overlap and owner edits. Reconcile races and repeat
  affected validation; never force-push or publish an unverified changed head.

Once those checks pass, the agent may mark this new-artwork-only PR ready and
merge it using the verified expected head SHA, without waiting for owner aesthetic
review. Do not submit a PR approval review, enable auto-merge or change workflows,
credentials, permissions or branch protections. If protection requires independent
approval, access is denied, or a required check fails or is unavailable, stop
dependent publication and report the blocker; do not bypass the gate.

The existing main publisher and Pages deployment remain the publication path.
Verify their successful output includes the merged artwork before claiming it is
live. This authorization excludes policy, code, workflow and mixed-scope PRs;
their existing review rules remain unchanged. In particular, a PR changing this
policy is not a new-artwork-only PR.

Existing artwork of any review status is not replaced or regenerated without a
specific owner request. A change in star ranking does not delete artwork.

## Build behavior

Only approved records with existing files render. Missing files warn and are omitted; pending/rejected records are omitted. Missing entries leave no image or empty image box. An invalid approved identity, path, alt text or image format fails the build rather than publishing a mismatched asset. The builder copies active assets into `specimens/`. Builds never call image generation or fetch remote artwork.

The initial pilot covered OpenTofu, OpenRefine and OpenSCAD. The current daily
backfill selects up to 40 distinct canonical projects with missing artwork, in
descending cached star order, with at most one batch in flight through validation and publication. It
skips existing records of every review status, overlapping PRs and owner edits.
No eligible missing projects means report completion and disable only that
backfill task. See the [inventory](../automation/README.md#backfill-specimen-artwork)
for generation limits and review gates.

## Display cut-out

The artwork-backfill task follows this merged repository handoff. Its batch
includes the new originals, matching `site/specimens/cutouts/<project-id>.webp`
files, corresponding records in `data/specimen_art.json` and
`site/specimens/cutouts.json`, and incremental `brand/assets.lock.json` changes.
Keep those files together in the artwork PR; preserve all unrelated assets and
records. The renderer's fallback below handles absent or stale derivatives; it
does not replace the same-PR cut-out authoring requirement.

The discovery task's owner-authorized scope was aligned with this handoff on
2026-10-21: new originals, matching new cut-outs, corresponding metadata and
incremental cut-out manifest/checksum entries belong together in its separate
artwork draft PR. It attempts artwork after catalog acceptance on main. See the
[automation inventory](../automation/README.md#discover-open-software) for the
verified scope. Both artwork tasks preserve unrelated assets and records and
follow the new-artwork-only publication procedure above.

The expanded record shows `site/specimens/cutouts/<project-id>.webp`, a transparent derivative
with only the border-connected white ground removed, so the decorative contour floor passes
behind the drawing. `site/specimens/cutouts.json` records the source and derivative hashes and
the subject's bounding box (used to place feature crops, compact the vertical field
and align its decorative ground). This alpha > 0.5 box is not a pixel-clipping
boundary: display keeps 8% source-height safety padding and visible overflow,
retaining the entire image and its faint marks. No browser pixel scan is needed;
layout metadata is emitted at build time. Missing or malformed bounds retain the
full canvas. A missing or stale cut-out
never blocks a build: the original is shown without the floor and the build warns.

## Display variants

The plate's image carries a `srcset` of 512 and 768 px wide WebP variants plus its
source, the cut-out or, without one, the original. `sizes` is
`(max-width: 660px) 100vw, 627px`, the plate stage's widest extent. The loupe
magnifies the source. `python3 scripts/build_specimen_variants.py` (Pillow 12.3.0,
libwebp 1.6.0; Lanczos, WebP q85, method 4) writes
`site/specimens/responsive/<source stem>[-cutout]-<width>.webp` and records source
and variant hashes in `site/specimens/responsive.json`. It rewrites only entries
whose source changed; `--force` regenerates all. Refresh `brand/assets.lock.json`
afterwards. A source without current variants is shown alone and the build warns;
a variant whose bytes differ from the manifest stops the build. Artwork PRs may
include the variants for their new sources; otherwise a later run adds them.
