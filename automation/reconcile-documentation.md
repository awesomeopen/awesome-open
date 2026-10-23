# Reconcile documentation

## Runner and authority

A separately registered assistant runs this job daily at **04:00
America/New_York**, following daylight saving time, on an exact schedule.
Activate it only after this contract is reviewed and merged and the registration
is verified. Editing this file creates no timer. See the [inventory](README.md)
for runtime state; leave other jobs and the publisher unchanged.

Read fresh main's [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md),
this contract and the relevant domain guides. Same-PR documentation maintenance
remains the first responsibility; this job catches drift that escaped it.

Compare three distinct sources: approved intent in current contracts and
reviewed decisions; behavior in merged code, schemas and tests; and actual
registered jobs and workflow runs. Code proves implementation, not approval.
A runtime discrepancy or implementation bug needs a scoped report, not a rewrite
of intent to make it disappear. When registration is inaccessible, mark that
part unverified and continue independent repository checks.

## Bounded selection

Check active attempts and relevant open PRs first. Keep at most **one pending
documentation-reconciliation draft** and never start a duplicate or concurrent
batch. While it awaits review, stay quiet unless something materially changes.

On ordinary days, inspect changes since the last successfully inspected main
commit available in task history, including affected documentation and callers.
If that baseline is unavailable or no longer an ancestor, inspect the preceding
seven days of main history and state the coverage limit in any resulting PR.
Exclude generated cache churn unless its schema or behavior changed.

On Sundays, also inspect one broader area, rotating through the table below.
Use the ISO week number modulo four (0–3) as the area index, so recovery requires
no repository cursor. Within that area, prioritize concrete inconsistencies and
shortening opportunities. Propose at most **five related discrepancies** per
run; unrelated findings wait for their own review. Never imply exhaustive
coverage from this bounded pass.

| Index / area | Implementation evidence | Primary documentation |
| --- | --- | --- |
| 0 · Catalog and publication | README renderer, collectors, workflow definitions | CONTRIBUTING.md, automation/README.md |
| 1 · Enrichment | Catalog loaders, curated-data schemas, validation tests | automation/backfill-*.md, site/* evidence contracts |
| 2 · Site and previews | Site builders, routes, runtime assets, browser checks | site/PREVIEW.md and relevant site contracts |
| 3 · Brand and maintenance | Tokens, asset/skill manifests, brand checks | brand/README.md, brand/maintenance.md, AGENTS.md |

This map is a navigation aid, not a second inventory of every file. Follow
imports, links and tests from the affected implementation.

## Reconcile and tighten

Check paths and anchors, documented commands and flags, schema fields, generated
outputs, ownership, bounds, review gates, schedules and stale rollout language.
Read tests and actual implementations before concluding a statement is wrong.
Check relevant accepted decisions and owner edits before changing a rule.

Prefer one authoritative explanation with short links at its callers. Shorten
repetition and remove completed-work narration from active instructions when it
adds no continuing operational value. A document should help someone operate,
change, understand or safely migrate the current project.

- Keep active contracts, runnable instructions and rationale that still explains
  a constraint or prevents a likely mistake.
- Remove guidance for a removed feature only after verifying its removal in
  merged implementation and checking callers, compatibility and migration needs.
  Do not substitute a permanent “this feature was removed” section when no
  ongoing obligation remains.
- Preserve evidence, provenance, rights/license/security records, stable decision
  identities and useful migration or compatibility guidance. Follow their own
  contracts when shortening references; unresolved authority needs owner review.
- Broken links, absent outputs, duplicate paragraphs, obsolete terminology and
  unreferenced files are candidates for inspection. Age, no inbound links or a
  keyword match alone never authorizes deletion. Tests cannot decide enduring
  usefulness; document the concrete reason for each proposed removal in the PR.

Use Git and PR history for completed work. Do not create per-run audit documents,
ever-growing status tables, verification-date churn, “still applies” entries or
logs of log maintenance. Keep an inspected revision/rotation cursor in available
task history, not a tracked file; routine clean runs stay quiet.

## Proposal boundaries

Change authored Markdown documentation only, including links and examples within
it. Preserve concurrent edits and any applicable decision-record requirements.
Do not change code, tests, schemas, generated README/site output, curated evidence,
assets, workflows, registered prompts/schedules, credentials or security settings.
If a fix needs those changes, report it separately with the evidence and smallest
next step. Do not weaken a contract to accommodate a bug.

An editorial correction follows verified existing policy. A normative change
needs explicit owner review; do not silently change approval, scope, retention
or safety rules under “cleanup”. Never erase Git history or rewrite accepted
decision identities. Do not copy private prompts, account IDs or credentials
into public documentation.

Re-fetch main and target files immediately before writing, recheck overlapping
PRs, and reconcile only the selected edits. Submit a scoped draft PR on a fresh
branch with `Contribution by Junge (AI)` in the commit message. Preserve actual
account attribution. No empty PRs, merge, ready marking, auto-merge or force-push.

## Verification and reporting

Validate changed local links, anchors and examples against the final tree. Run
`python3 scripts/check_brand.py`, the full offline test suite and the README
preview command in CONTRIBUTING.md. Build the catalog/site and run applicable
browser/preview checks when a changed instruction describes them. Use the
current implementation's commands and outputs, rather than resurrecting removed
features to satisfy an old checklist. Generated checks/previews stay uncommitted.

Inspect the remote diff, exact head and draft state. Follow exact-head required
CI to its terminal outcome, distinguishing passed, failed, skipped and
unavailable checks. Do not change unrelated tests to make a docs PR green.

The PR body holds the bounded findings, evidence revisions/links, reasons for
deletions and verification limits. Report meaningful proposals or actionable
blockers in the requesting ChatGPT conversation with verified links. Quiet runs
need no new document or reconfirmation record. Stop dependent writes on substantive
auth, permission, implementation or validation failure; preserve useful work.
Respect live quota/reset/Retry-After limits and existing access. Never route
around a denial or introduce new credentials, personal cookies or paid fallback.
