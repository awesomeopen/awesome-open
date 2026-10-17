# Maintenance procedure

## How it runs

Maintenance is part of the agent's ordinary edit-and-PR workflow. `AGENTS.md`
directs it to the brand reference; the project skill gives the steps; the PR
template asks for impact and validation. A GitHub Actions check validates tracked
integrity and issues an advisory when design changes lack documentation changes.
These files do not wake an agent, remember a chat, or make design judgments.

Junge can run this workflow whenever assigned work in this repository. A separate
recurring audit is optional and is not configured by this PR. The existing data
collection schedules continue unchanged.

## Per-change responsibilities

| Change | Update in the same PR | Validation |
| --- | --- | --- |
| New brand decision | Relevant guide + individual PR-scoped record with status/evidence; see [authoring guide](DECISION-GUIDE.md) | ID/reference checks; human/agent review of intent; affected visual states |
| Token/type change | Tokens + detailed guide + reference examples | Contrast, fonts/rights, narrow reading, offline output |
| UI/copy change | Source generator/assets; decision record if it changes a rule | Relevant source/DOM/browser checks; main and standalone output |
| New artwork | Existing asset manifest/provenance + bytes + asset checksum inventory | Actual image review; correct ID, dimensions, alt and status |
| Reusable skill update | Full pinned folder + source revision + skill lock | Skill validator, diff review, check referenced files |
| Project workflow update | Repository skill + docs; sync installed mirror after merge | Validate skill; report synced commit |
| Bug fix with no rule change | Explain “Brand impact: none” in PR body | Regression check appropriate to the bug |
| Routine catalog/evidence refresh | Existing data/source workflow only | Existing offline and evidence checks |

## Commands

```sh
python3 scripts/check_brand.py
# Only after intentional asset/pinned-skill changes and provenance review:
python3 scripts/check_brand.py --refresh
python3 scripts/check_brand.py
# Stable-ID history/namespace checks and advisory against the actual PR base:
python3 scripts/check_brand.py --base origin/main --pr-number 100
# Generate the combined overview into ignored output (use your own PR number):
python3 scripts/brand_decisions.py --output tmp/brand-decisions.md
python3 scripts/brand_decisions.py --output tmp/brand-decisions.md --check
```

The check fails on missing/mismatched asset or pinned-skill inventories, missing
core documentation, unsafe paths, invalid/duplicate decision IDs, filename
mismatches, unknown references, broken local documentation links, and invalid
supersession. With a base revision it also prevents removing or renaming merged
decision identities and legacy heading anchors; CI supplies the actual PR number
for new records. Legacy status/evidence corrections need review evidence and do
not renumber or redefine a decision. See the authoring guide for the bounded
reference scope. Refresh computes byte hashes and sizes; it
does not set review status or import files. The design-impact advisory is based on
changed paths. It cannot establish semantic consistency or approval. Existing
branch protections are unchanged; making this a required merge check would be a
separate repository setting change.

## Handoff to Junge or another agent

Use this instruction at the start of a repository task (or add it to the existing
agent's project instructions through its supported interface):

> In awesomeopen/awesome-open, read AGENTS.md and brand/README.md before brand or
> design work. Use the repository's awesome-open-brand skill. Update affected
> documentation, decisions and asset/skill provenance in the same PR; otherwise
> explain why the change has no brand impact. Run scripts/check_brand.py and the
> relevant checks. Open a draft PR; do not merge automatically. Use the current
> checkout and source revision, not a remembered preview.

This is a handoff instruction, not a message sent to Junge. Agents operating only
through GitHub APIs must explicitly fetch these files; do not assume their runtime
auto-loads AGENTS.md. A brand rule mentioned only in chat remains at risk of being
lost until the working agent records it in a PR.

## Publication and reconciliation

GitHub owns authored source. Main's existing publisher produces the public site.
The private Sites host is a disposable review copy with separate Git history;
there is no automatic two-way sync. A wrapper commit is not the GitHub source SHA.
Record the source SHA in `preview.json` for review builds.

When an approved change is discovered only in a built preview, port it back to the
generator in a reviewable commit. Rebuild from that source before the next preview
refresh; do not use stale output to overwrite a newer GitHub change. This PR ports
the four row-detail refinements from the 2026-10-13 private preview and preserves
the subsequently merged medium-width source fixes. It does not redeploy the Site.

## Implementing an approved prototype

A prototype approval covers what the prototype shows. When porting it to the
generator, compare the prototype and the built page section by section. In the
PR body and the decision entry, list every prototype element that was left out
or changed, with the reason (missing data, review feedback, scope). Otherwise the
decision record describes a reduced design as if it were the approved one.

## If drift is found

Identify both versions and the discrepancy. Use explicit decisions and provenance
to propose a resolution. Record unresolved items instead of making up approval.
Archive superseded rationale with a clear banner; keep useful links working.
Do not delete original artwork or historical files just to make the index shorter.
