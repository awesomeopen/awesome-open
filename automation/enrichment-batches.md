# Summary and feature batches

Version 2 batches research up to 40 projects, prioritizing projects whose
approved illustrations can already display feature notes. One integrator
publishes one reviewed data PR; several researchers can work in parallel.
Summary and feature jobs keep their separate ownership, three daily windows,
one-pending-draft gates and full validation requirements.

## Select once, reserve once

Read fresh main and the relevant job contract. Check open PRs and active work,
including discovery, summaries, features and other evidence edits. Collect their
full canonical IDs into an ignored JSON array such as `tmp/reserved-ids.json`.
Preserve existing records and owner edits. A pending draft for the same job
pauses selection; another job's unrelated IDs may proceed.

Build the catalog, then use the shared offline selector:

```sh
python3 scripts/build_catalog.py --output tmp/catalog.json
python3 scripts/select_enrichment_backfill.py \
  --job summaries --catalog tmp/catalog.json \
  --date YYYY-MM-DD --slot 0 \
  --exclude-ids tmp/reserved-ids.json --output tmp/selection.json
```

Replace the date with the actual UTC run date. Slots 0, 1 and 2 identify the
nominal 08:00, 15:00 and 19:00 New York windows. Use `--job features` for missing
notes on approved existing summaries. Missing summaries belong to the summary
job; existing records of every review status are excluded from summary batches.
The selector reads the current data and verifies displayable approved artwork
through the site's artwork loader. It performs no network requests or research.

The 40-project plan allocates up to 30 slots to illustrated projects and reserves
10 for unillustrated projects. Either tier borrows unused slots from the other.
This prioritizes immediately visible notes while keeping the rest of the catalog
moving. Smaller diagnostic plans reserve one quarter, rounded up, for the
unillustrated tier; a one-project plan chooses illustrated work first.

Within each tier, sort full canonical IDs and resume strictly after its last
considered ID, wrapping once. Pass saved cursors with `--after-illustrated ID`
and `--after-unillustrated ID`. An earlier scalar cursor can seed both with
`--after ID`. If a tier has no cursor, the fallback offset is
`(UTC days since 1970-01-01 * 3 + slot) % tier size`. Record the fallback
and offsets. Eligibility scanning is separate from source research.

Publish the selected full IDs to the active-work handoff before assigning
research. These reservations are coordination context, not new catalog data.
The aggregate run limit stays 40, even when several workers are available.

## Research in parallel, integrate once

The plan divides candidates into at most four disjoint groups of at most ten.
Use available parallel workers; fewer workers may process the same plan when
capacity is limited. Give each worker the exact IDs, current record, applicable
contract and file scope. Workers return source URLs/revisions, proposed prose,
claim checks and skip reasons. They do not write the shared data file, create
branches or submit individual PRs. Never install or execute candidate software.

For new summaries, write the 40–80-word summary and one to five supported feature
notes during the same official-source review. Every feature URL must be one of
the new summary's reviewed sources. A source-limited feature omission does not
invalidate a supported summary; record the reason. Existing-summary feature
batches retain their narrower source and field-preservation rules.

One integrator reviews every proposal and source, checks the worker's claims,
and rejects unsupported prose. Parallelism does not replace review. Re-fetch
main and the data immediately before publication, recheck reservations and PRs,
and apply only the selected additions. Skip or re-review changed records,
preserving newer content. Validate the combined batch once, inspect its previews,
submit one scoped draft and follow exact-head CI to its terminal result.
Keep owner review, no-force-push and no-auto-merge boundaries unchanged.

## Continue from actual work

Retain the plan, actual considered IDs in order, per-project outcomes, evidence,
source limitations and both tier cursors in the run report. Advance a tier's
cursor through the completed contiguous prefix of that tier's planned order,
including source failures and raced proposals—not whichever worker finishes
last. Retain later completed proposals for reuse after an interrupted gap.
Planned candidates or an interrupted worker alone do not advance it. Keep an
unconsidered tier's cursor unchanged. The last considered ID may
also be retained for older readers, but version 2 resumes from both tier cursors.

Before starting another batch, recover prepared proposals and interrupted
assignments from accessible reports, revalidate their evidence and fresh-data
eligibility, and count reconsidered projects toward the current limit. Do not
repeat an unchanged source-limited record within the same sweep. A later sweep
may revisit it after source change or access recovery. Save no run reports,
reservations or cursor schema in the repository. Existing schedules stay intact.
