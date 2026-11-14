# Recoverable artwork batches

Verify storage before generating an image. Save and restore each generated
original before starting the next image. Keep the batch's recovery index outside
the repository, with the exact object identities, versions and hashes needed to
restore it after losing the working computer.

This procedure supports the [specimen publication gate](../site/SPECIMEN-ART.md#publication-after-validation).
Use one in-flight backfill batch and its reserved canonical IDs. Recheck fresh
main, open PRs and active work before selecting or resuming it. A requested
recreation uses a new batch ID and new generation provenance; preserve historical
files and do not replace accepted main artwork without specific authorization.

## Checkpoint procedure selection

The [batch candidate procedure](artwork-candidates.md) is a proposed replacement
for finalization/publication archives and plan-subset re-packaging. Use it only
after its policy/code PR receives owner review and merges. Until then the
procedure below remains required. Legacy archives and receipts remain readable.

## Before generation

1. Choose an authorized durable destination with supported upload and download
   operations. Check its access, retention and size limits. Use the current
   storage service's supported tools and transfer instructions. Obtain any
   required sharing/connection permission before sending artwork or evidence.
2. Save a plan containing the batch ID, exact base revision and 1–40 full project
   IDs. Preserve its order, and publish those reservations in the active-work
   handoff. Save this plan and the run index at the chosen destination.
3. Package a small fresh text probe, upload it, and retrieve it into a separate
   local file by the returned durable object ID and exact version. Compare the
   archive and every member with `verify-restore` below. An upload response,
   download URL, chat attachment, local copy or local Git commit alone is
   insufficient recovery evidence.
4. Retain the receipt and durable index reference in the task handoff, outside
   the disposable workspace. Repeat the probe after restarting the executor,
   changing destination or credentials, or after 24 hours. Confirm the image
   tool supplies a supported save/export route before calling it.

An authentication or permission failure stops dependent generation and uploads.
Record the exact failed operation and whether it executed. Retry only after
materially new relevant authorization or connection evidence; check an uncertain
outcome first. Do not switch routes to evade an access denial, change credentials
or repository settings, buy credits, or use a paid generation fallback.

## Checkpoint one image

Run `begin` before invoking image generation. It exclusively records the next
reserved ID and blocks another generation until that ID has a verified generation,
[project skip](#skip-one-blocked-project) or
[quarantine](#quarantine-a-terminal-project-failure) receipt.
Save the actual tool output immediately, together with the complete prompt,
consulted source bytes and truthful generation provenance. Package that image's
`generation` checkpoint, upload it, independently retrieve it, and verify it.
Save the resulting receipt and update the durable run index before the next
`begin` call. Keep an original local copy as well.

A generation interruption leaves its reservation outstanding. Recover the output
or establish the exact failure before retrying. Preserve the marker and failure
record during reconciliation; do not remove a marker merely to unblock the next
image. A known no-output failure can be explicitly reconciled in the task
handoff and skipped for this batch. Never assume a timeout means no
image was generated.

After actual pixel review, optimize the final WebP and build its matching
cut-out under the [existing artwork contract](../site/SPECIMEN-ART.md).
Create, upload and restore a separate `finalization` checkpoint for that project.
Keep both verified archives. This separates original preservation from later
processing and avoids making a whole batch depend on one large archive.

## Skip one blocked project

Skip an isolated project blocker once its outcome is known and its evidence is
recoverable. Keep the original plan, reservation marker and failure evidence.
Successful projects retain their receipts and the next reserved ID can proceed.

1. Establish that generation never started or returned no output, and that the
   blocker affects only this project. Record the exact operation, reason and
   outcome. Preserve the original tool response or other supporting evidence.
2. Package a `skip` checkpoint with the unchanged reservation marker, the failure
   record below and supporting evidence. Upload it to the verified destination,
   retrieve it independently and run `verify-restore`. Save its receipt at
   `state/receipts/skips/<project-id>.json` and update the durable run index.
3. Run `next`, then `begin` for the next project. Keep skipped IDs in the handoff
   and publication index. Report successful artwork and skips separately.

Pending or interrupted requests still require outcome reconciliation. A terminal
project rejection with no returned artifact may use the quarantine procedure
below while its backend output remains unknown. An existing generated original
needs
its generation checkpoint even when later processing fails. Shared storage,
authentication, permission, quota or tool-access failures stop dependent work;
do not classify them as project-local or change routes to evade a denial.
The helper checks recorded scope and outcome; the operator verifies the evidence.

Skips apply to this batch only. Missing artwork remains eligible for future
backfill selection after checking the prior failure and current main, PRs and
active work. Retry a denied operation only with materially new relevant evidence
and the required authorization. A skip receipt grants no retry permission.
Review unresolved skips during later spot checks. If every project is skipped,
retain the recovery index and report the blockers without opening an art-only PR.

The `failure` artifact has exactly these fields:

```json
{
  "schema_version": 1,
  "plan_sha256": "<hash from the original checkpoint plan>",
  "project_id": "<full 64-character catalog ID>",
  "scope": "project",
  "outcome": "no_output",
  "operation": "<exact failed operation>",
  "reason": "<verified project-local blocker>",
  "recorded_at": "<UTC timestamp>",
  "retry": "future_batch_review"
}
```

Use `not_started` for a blocker established before generation was invoked, or
`no_output` for a completed failure verified to have produced no image. Preserve
older failure records as `evidence` when writing this reconciliation record.

## Quarantine a terminal project failure

Preserve a completed project-local rejection as a hold when it returned no image,
file, output identity or retrievable artifact, but backend output remains unknown.
This lets unrelated reserved projects continue while the held project remains
unresolved. Keep its original marker, prompt, source, complete response and request
identity in the durable evidence; never label an unknown outcome `no_output`.

1. Verify that the response is a terminal project rejection and the request is
   no longer pending. Timeouts, interrupted requests, shared authentication,
   storage, quota or tool-access failures still stop dependent work. A known or
   retrievable generated original requires its generation checkpoint.
2. Package a `quarantine` checkpoint with the unchanged reservation, a failure
   record and supporting evidence. Use the skip failure fields above, replacing
   `outcome` with `unknown_output` and `retry` with `blocked_pending_review`, and
   adding `request_state: "terminal_failure"`, `returned_artifacts: "none"` and
   `failure_class: "project_rejection"`. The operator verifies these facts from
   the preserved response; the helper validates their structure.
3. Upload and independently restore the archive using the current verified
   storage destination. Save the receipt at
   `state/receipts/quarantines/<project-id>.json`, update the durable index, then
   run `next` and `begin`. Renew an expired storage probe first.

Keep the hold in subsequent active-work handoffs and selection checks until its
outcome and any necessary authorization are reconciled. Quarantine grants no
retry permission, including for moderation-rejected requests, and no permission
to retrieve a withheld output through another route. If an original later becomes
available, preserve it and reconcile the conflicting state under a new plan;
never overwrite the hold receipt or silently substitute a generation receipt.

Publication may contain the successful projects, with holds counted separately
from completed artwork and verified no-output skips. Held IDs have no artwork,
cut-outs or asset-lock entries in the candidate. Preserve their evidence and
report the unresolved holds. A batch containing only skips/holds produces no
artwork PR. Policy/code PRs retain their normal review gate before this procedure
may be used by an automation.

## Offline helper

`scripts/artwork_checkpoint.py` packages explicit files and verifies bytes. It
makes no network requests or image-generation calls. Its receipts record the
operator's supplied storage identity; the operator must actually perform the
authorized external upload/download and preserve the index outside the workspace.
The helper's structural checks supplement source, identity, rights, safety and
pixel inspection. Its success does not establish those reviews.

Keep local state under ignored `tmp/`, and never commit recovery references,
provider credentials or private source captures. Use a unique directory per plan.
The plan has exactly these fields:

```json
{
  "schema_version": 1,
  "batch_id": "art-YYYYMMDD-recreation",
  "source_revision": "<full 40-character Git commit SHA>",
  "project_ids": ["<full 64-character catalog ID>"]
}
```

An artifact specification is a JSON array of objects with `path`, `role` and
`project_id`. Paths are relative to the supplied staging root; a batch artifact
uses null for `project_id`. Each archive embeds the plan and member SHA-256 hashes.
The helper never overwrites an existing archive. Archives are bounded to 32 MiB
including ZIP headers and reject
symlinks, unsafe paths, duplicate members, missing roles and hash mismatches.

| Kind | Project ID | Required roles |
| --- | --- | --- |
| `probe` | null | `probe` |
| `generation` | One planned ID | `original`, `prompt`, `source`, `provenance` |
| `skip` | One planned ID | `reservation`, `failure`, `evidence` |
| `quarantine` | One planned ID | `reservation`, `failure`, `evidence` |
| `finalization` | One planned ID | `final`, `cutout`, `artwork_record`, `cutout_record`, `checksums` |
| `publication` | null | `artwork_manifest`, `cutout_manifest`, `checksums`, `candidate`, `recovery_index` |

Multiple source captures may have the `source` role; multiple failure captures
may have the `evidence` role. A skip or quarantine has exactly one
`reservation` and `failure`.
Generation provenance names
the actual tool/model, returned output identity when available, date and project.
Finalization records are each project's exact record object from the two
manifests. Their `checksums` artifact is a JSON object keyed by the two
`site/specimens/...` paths, holding their exact asset-lock entries.

Example commands, after creating the plan, artifact specification and files:

```sh
python3 scripts/artwork_checkpoint.py pack \
  --plan tmp/art/plan.json --kind probe \
  --artifacts tmp/art/probe-files.json --root tmp/art/staging \
  --output tmp/art/probe-1.zip
# Use the authorized storage tool to upload and retrieve the archive separately.
python3 scripts/artwork_checkpoint.py verify-restore \
  --original tmp/art/probe-1.zip --restored tmp/art/restored/probe-1.zip \
  --storage tmp/art/storage-object.json \
  --receipt tmp/art/state/receipts/probes/probe-1.json
python3 scripts/artwork_checkpoint.py begin \
  --plan tmp/art/plan.json --state tmp/art/state
```

`storage-object.json` records nonempty `provider`, `destination`, `object_id`
and `version` strings from the actual operation. Use stable identities rather
than expiring or credential-bearing URLs. Generation receipts go in
`state/receipts/<project-id>.json`. Finalization receipts use
`state/finalization/<project-id>/<archive-sha256>.json`. Renewed probe receipts use new filenames in
`state/receipts/probes/`; the most recently verified probe governs the gate.
`next` inspects the gate without reserving work. File writes and new directory
entries are synchronized before success is reported; existing outputs are never
overwritten. The gate accepts one generation, skip or quarantine receipt for
each reserved ID; conflicting receipts fail closed. Completed plans with skips
return `generation_complete_with_skips` and list `skipped_project_ids`. Plans
with holds return `generation_processed_with_holds` and list
`quarantined_project_ids`, preserving the unresolved status.

## Before GitHub uploads

Restore-check all generation, finalization, skip and quarantine checkpoints.
Build the small
`publication` archive containing full candidate manifests, asset checksums,
candidate metadata and a recovery index. The candidate metadata includes its
exact `candidate_revision`. The recovery index has `plan_sha256`, the same
`candidate_revision`, and `images`, keyed by completed project ID. Each image
holds the full `generation` and `finalization` restore receipts. When projects
were skipped, add `skips`, keyed by project ID, containing their full `skip`
restore receipts. Held projects appear in `quarantines`, keyed by project ID,
with their quarantine receipts. Every planned ID appears exactly once across
`images`, `skips` and `quarantines`. Existing all-image indices remain valid.
The helper checks coverage,
identity and receipt structure. Keep restored archives in a
local directory named by their SHA-256 (`<sha256>.zip`), then run:

```sh
python3 scripts/artwork_checkpoint.py verify-candidate \
  --plan tmp/art/plan.json --index tmp/art/recovery-index.json \
  --root . --archives tmp/art/restored-by-hash
```

This compares the candidate's image bytes, per-project records and checksum
entries with the exact restored generation/finalization archives referenced by
the index, and verifies every referenced skip and quarantine archive. Skipped and
held IDs must have no
candidate artwork, cut-outs or checksum entries. Repackage, upload and restore-check every changed project before
updating its index receipt. Separately verify that the clean candidate checkout
is the recorded Git revision; the helper compares files and reads the revision
label supplied in the index. Project-local no-output skips keep the original
plan. Reconcile other membership changes, including raced IDs, explicitly in a
new plan and retain the earlier plan's history. A changed plan
invalidates its old receipts: repackage preserved originals/evidence under the
new plan, upload and restore-check them, and reconstruct the reservation history
before resuming. Reuse the actual originals; a plan change never calls for new
generation by itself.

Upload and restore-check that archive, then save its receipt and locator outside
the workspace. The collection of individually verified archives and its durable
index is the recoverable bundle. Retain it through publication and subsequent
regeneration or audit needs; a service's short-lived CI artifacts cannot be the
sole copy. Revalidate the candidate's actual files, source provenance, unchanged
records and current-main eligibility through the existing offline/build/browser
and exact-head CI gates before publication. Keep policy/code changes in their
own reviewed PR.
