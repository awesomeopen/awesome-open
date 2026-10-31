# Nightly code-quality audit

## Runner and authority

A separately registered Grok Bot assistant, "Nightly Audit Engineer", runs this
job daily at nominal **02:00 America/New_York**, following daylight saving time,
flexible by 15 minutes. The slot finishes before
[Reconcile documentation](reconcile-documentation.md) at 04:00 and the other
listed jobs. See the [inventory](README.md) for runtime state; leave other jobs
and the publisher unchanged.

Read fresh main's [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md),
this contract and `.agents/skills/` before each run. The job reads and writes
through the GitHub API and cloud agents; it keeps no local clone.

## Scope

Authored code only: `scripts/*.py`, `scripts/*.cjs`, `site/*.js` and
`site/*.css`. Markdown belongs to Reconcile documentation. Generated
`README.md`, `data/`, `assets/`, `site/specimens/` and files changed by open PRs
are outside this job.

Each finding fits one lens:

| Lens | Example |
| --- | --- |
| Repository rules | Code that contradicts AGENTS.md or a skill in `.agents/skills/` |
| Dead code | An unreferenced function, script or stylesheet rule |
| Needless complexity | A wrapper or branch that a direct call replaces |
| Unnecessary comments | A comment that restates the next line |

## Run

1. **Research.** Read-only cloud agents split the in-scope files so each file
   has exactly one reviewer. Each reports findings with path, lens and reason.
2. **Aggregate.** Merge reports, drop duplicates, nitpicks and anything an open
   PR already covers, then group the rest into focused areas.
3. **Clean up.** One cloud agent per area opens one draft PR on a fresh branch.
   Keep at most **three pending audit drafts**; while they await review, start
   no new area.
4. **Report.** Send new PR links to the requesting Grok Bot conversation.
   Runs with nothing actionable stay quiet.

## Proposal boundaries

Each PR changes one area and preserves behavior. Do not change workflows,
schemas, curated evidence, generated output, assets, registered schedules,
credentials or security settings. A fix that needs those goes in the report.
Commits use the connected owner account with `Contribution by Nightly Audit
Engineer (AI)` in the message. No empty PRs, merge, ready marking, auto-merge or
force-push.

## Verification

Before opening a PR, run `python3 scripts/check_brand.py`, the full offline test
suite and the README preview command in CONTRIBUTING.md, plus checks for the
code changed. The PR body lists findings, reasons and a `Brand impact` line.
Follow exact-head CI to its terminal result and report failed, skipped or
unavailable checks. Stop dependent writes on auth, permission or validation
failure; never route around a denial or add credentials.
