# Adding a brand decision

New decisions use `B-PR<number>-<ordinal>`: the pull request number plus a
zero-padded ordinal starting at `01`. The PR supplies a repository-unique
namespace; contributors do not reserve the next global number.

## Authoring workflow

1. Read current main, relevant brand rules, the [legacy register](decisions.md)
   and [individual records](decisions/). Preserve work from other PRs.
2. Open a draft PR with a useful, nonempty documentation or implementation commit
   to obtain its actual number. Do not publish an empty placeholder PR.
3. Add `brand/decisions/<ID>.md` using that number. Within one PR, use `01`, `02`,
   and so on; after `99`, use `100`. PR numbers have no leading zeros; ordinals
   use exactly two digits below 100 and their ordinary decimal form thereafter.
4. Update the affected guide and include rationale, evidence, limitations and
   status in the record. Run the commands below before requesting review.
5. Keep IDs and matching filenames stable after merge. Closed, unmerged PR
   numbers are not reused for a different proposal. If a proposal moves to a
   different PR before merge, give its new record the new PR's namespace.

A PR number identifies where a record originated, not approval or implementation.
New records use this PR's number; existing records retain theirs. Separate files
allow parallel PRs to choose ordinal `01` without colliding. Ordinary concurrent
edits to the same substantive guide can still require reconciliation.

## Record format

Use UTF-8 Markdown with the following JSON front matter between `---` lines.
JSON is a YAML-compatible subset with unambiguous types; no YAML dependency is
needed. The example is a template.

```markdown
---
{
  "id": "B-PR123-01",
  "title": "Concise decision title",
  "date": "2026-10-16",
  "status": "proposed",
  "type": "workflow",
  "supersedes": []
}
---

# Concise decision title

Decision, rationale, evidence links, scope and limitations.
```

All six fields are required; unknown or duplicate fields are rejected. Titles
must be nonempty, single-line strings; dates must be valid `YYYY-MM-DD` dates.
Use the recorded project date rather than guessing from a commit's timezone.

- Status: `proposed`, `accepted`, `implemented`, `rejected`, or `unresolved`.
  `accepted` needs actual approval evidence; `implemented` describes merged
  behavior. A draft implementation can remain `proposed` until reviewed.
- Type: `design`, `artwork`, `content`, `evidence`, or `workflow`.
- `supersedes`: a list of distinct existing decision IDs, empty by default.

Include evidence in the Markdown body, with useful links. Do not publish private
conversation transcripts or manufacture sign-off. Correct factual metadata with
review evidence; a changed rule requires a new record.

## Stable identity and supersession

Never rename a merged record or change its ID. A replacement gets a new ID and
names the old ID in its own `supersedes` list. Keep the old record and its
historical status unchanged. The generated overview derives reverse links from
the new record; contributors do not edit the replaced record to add a backlink.
Self-supersession, missing targets and cycles are invalid.

A proposed replacement is still a proposal. The overview shows the declaring
record's status rather than automatically retiring its target. Multiple proposed
replacements can coexist; review must resolve conflicts. Use `supersedes` only
for a full replacement. For a partial change, cite the affected decision in the
body and explain which part changes; leave the full-supersession list empty.

This migration preserves the [legacy register](decisions.md) byte-for-byte from main
`f44054ee109cc38eb984e00eafacefdbd612348c`, including all B01–B44 entries and its
existing headings, wording, links and historical statuses. Its old authoring
sentence is historical; this guide governs additions. New decisions can supersede
legacy entries without editing them. Later factual status or evidence corrections
are allowed with review evidence; retain IDs, original meaning and working links.
Use a new record for a changed rule rather than redefining the historical one.
Existing guide anchors such as the
[route shell](../site/RETRO-SCRAPERISM.md#route-shell-for-sibling-pages-b42) stay
valid. Old PR descriptions may contain pre-merge numbers; follow the merged
record when they disagree. This change does not rewrite past PR bodies.

## Validation and generated overview

Run from the repository root. Substitute the actual PR number and current base.

```sh
python3 scripts/check_brand.py --base origin/main --pr-number 100
python3 -m unittest discover -s scripts -p 'test_brand_decisions.py'
python3 scripts/brand_decisions.py --output tmp/brand-decisions.md
python3 scripts/brand_decisions.py --output tmp/brand-decisions.md --check
```

The overview contains the legacy rows followed by new records in numeric
PR/ordinal order. It includes source links pinned to a full commit SHA. The
source ref defaults to local HEAD; to review an exact published revision, pass
`--source-ref <full-commit-sha>` while running from that revision. Uncommitted
records will not yet exist at HEAD's GitHub links.

Output stays under ignored `tmp/`. Do not commit it or append another shared
table. The **Brand reference integrity** Actions run generates and checks the
same overview, uploads the `brand-decision-overview` artifact, and includes it
in the job summary. Download it from the PR's Checks tab or the
[workflow runs](https://github.com/awesomeopen/awesome-open/actions/workflows/check-brand.yml).
The checked-in individual records remain directly readable without generating
anything. The overview is never a second source of truth.

Validation is offline and checks IDs, filenames, metadata, the legacy ID set,
supersession and current authored documentation. With `--base`, it
also rejects removing or renaming existing decision identities; CI passes the
actual PR base and number to check every newly added namespace. An unavailable
base fails explicitly rather than skipping history checks. Fetch current main
before the local history check. Default snapshot validation does not establish
identity stability across revisions.

Reference scope is `brand/**/*.md`, `site/**/*.md`, the repository brand router,
root `AGENTS.md`, `CONTRIBUTING.md`, and the PR template. It validates inline and
reference-style local Markdown link targets and Markdown/HTML anchors, and known
decision IDs in current prose, headings and inline code. Fenced examples, external
URL payloads, archived source captures, pinned reusable skills, generated output,
and historical `site/DESIGN.md` / `site/design_plan.md` are excluded. External
sites are not contacted. Write example IDs in fenced blocks; placeholders such
as `B-PR<number>-<ordinal>` are also safe. These structural checks do not verify
external evidence, adjudicate conflicting intent, or grant approval.

Contribution by Junge (AI)
