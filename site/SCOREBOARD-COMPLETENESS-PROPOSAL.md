# Most up to date — proposed Scoreboard contract

**Status: proposal for owner review; implementation and evidence prerequisites
remain open.** Add one current Top 10 board named **Most up to date**. Rank only
complete records, first by **Recent signals** and then by their oldest successful
verification date, newest first. The existing [six-board contract](SCOREBOARD.md)
continues to govern production.

## Completeness gate: proposed checklist v1

“Complete” means every requirement below has a resolved, source-backed state for
the frozen edition. Use one versioned checklist for the whole catalog. Each
requirement needs applicable evidence, verified absence within a stated scope,
or a reviewed reason it is not applicable. Missing evidence, unresolved
applicability, partial/inconclusive results, stale evidence and failed checks
block qualification. A low observed score, zero stars or `archived: true` is a
known value and can qualify.

| Required domain | Proposed resolved state and current source |
| --- | --- |
| Identity and canonical URL health | Full canonical catalog ID and URL; reviewed official identity; successful URL check with its actual final destination and check time. Any redirect or repository-path mismatch needs identity review before qualification. `repository_identity` in GitHub metrics supports repository continuity; it supplies no general URL-health verdict. |
| Repository facts and license | For a supported GitHub repository: fresh creation/push dates, observed star count, explicit archive boolean, and known detected SPDX license from `data/github_metrics.json`. Null, `NOASSERTION` and `OTHER` remain unknown. A different, source-reviewed license/absence claim needs its own schema and label; it cannot overwrite GitHub detection. Confirm provider applicability for other catalog URLs from official evidence. |
| Full-release evidence | For applicable GitHub release coverage: `release.status == available`, validated `last_good.value` containing release ID, tag, `published_at` and official release URL in `data/project_signals.json`; alternatively an explicitly reviewed absence for that release channel. HTTP 404 / `not_found` currently means unavailable. |
| HN evidence | Completed current-window collection for the exact identity/matching fingerprint, queue status `ok`, known `last_good.collected_at`, and validated deduplicated stories/monthly counts in `data/hn_evidence.json`. An observed zero-story collection qualifies within its matching scope. Partial pages, missing collection dates and previous-window results do not. The historical chart `eligible` flag is irrelevant. |
| Scorecard | For applicable provider coverage: `scorecard.status == available`, known aggregate score and conclusive scores for every returned check, with repository, scan date, source commit and tool version. Retain the provider's check list/scope; unreturned checks are outside that declared observation, never passed checks. Unsupported coverage needs a reviewed applicability reason; missing scans cannot imply it. |
| Function and capabilities | An approved 40–80-word Function summary with official sources, reviewer and actual review date, plus at least one sourced feature note or an explicit reviewed resolution that no separate note is supported. Use [the summary contract](FUNCTION-SUMMARIES.md); feature-only review provenance must become structured before it can improve this domain's verification date. |
| Deployment facts | Approved [deployment evidence](DEPLOYMENT-EVIDENCE.md), with each of its six dimensions resolved for a declared version/deployment scope: `run_modes`, `install_methods`, `platforms`, `external_services`, `packages`, `requirements`. Use sourced facts or reviewed absence/not-applicability per dimension. Listed package relationships must be known. A sparse approved record alone is insufficient. |

The deployment scope must describe the supported paths actually reviewed; it
does not require enumerating every possible OS, package or resource footprint.
Artwork, alternatives, aliases, rename history and retained-star charts remain
optional enrichments. Their absence does not block this checklist. Completeness
describes the declared evidence coverage; the board makes no quality or
recommendation claim.

### Schema prerequisites before enabling the board

Current loaders do not represent all these resolutions. In particular,
deployment schema 1 requires nonempty lists when present and treats omissions as
unknown; releases cannot encode verified absence; summaries have no structured
feature-only verification date or no-note resolution. General URL health and
reviewed provider applicability also need agreed contracts.

Propose versioned domain-resolution records keyed by canonical ID and checklist
requirement, carrying applicability, result (`observed`, `verified_none`,
`not_applicable`, or unresolved), scope, official sources/revision, reviewer,
successful verification date and precision, plus latest attempt outcome. These
are proposed concepts, not accepted field names or new data in this PR. Require
source-backed reasons for `verified_none` and `not_applicable`; “not found”, an
omitted field, private access or a failed fetch cannot supply either. Preserve
each existing source's meaning and review status through explicit adapters.

Evaluate freshness at the frozen reference time: preserve the release three-day
and Scorecard thirty-day rules in `scripts/signals.py`, require fresh repository
metadata and a completed HN window, and reject a known failed subsequent check.
URL-health freshness requires agreement with its producer. Curated reviews keep
their actual successful dates until superseded or invalidated; their age affects
the tie-break. Do not invent a periodic expiry or advance a date when a job runs.
An unsupported required resolution remains a blocker until its contract and
validator are reviewed. Data backfill follows those schema decisions separately.

## Recent signals and ordering

Freeze a UTC `reference_date` from the edition's metrics date and retain the
actual freeze timestamp separately. The proposed activity window is calendar
dates **reference_date − 90 days through reference_date, inclusive** (ages 0–90).
The 90-day boundary is a policy choice for owner review.

Count at most one point for each observed event type:

1. Last repository push, using `pushed_at`.
2. Latest published full GitHub release, using `published_at`.
3. At least one matched HN story, using its original `created_at`.

Total: **0–3 Recent signals**. Volume within a type adds no points. Verified
absence and reviewed non-applicability earn zero for that type while satisfying
their completeness requirement. An unresolved type prevents qualification.
Reject future or inconsistent event/check timestamps; none may follow the frozen
reference date or actual freeze instant.

HN contributes only inside the intersection of this window and the cache's
24 completed UTC months, with the cache's start-inclusive/end-exclusive bounds
shown explicitly. The ongoing month is excluded. A zero means no recent matched
story in that observed intersection; it makes no claim about ongoing-month HN.
Deduplicate stories by ID, releases by repository/release ID and pushes by
repository/event type; corroborating sources never add activity points.

For each complete record, take the **oldest successful verification date across
every required fact/resolution**, then prefer the newest such date among equal
activity counts. Repository `last_success_at`, signal `last_success_at`, HN
`last_good.collected_at`, and actual curated review dates supply their respective
dates; event dates, snapshot regeneration and failed-attempt `checked_at` values
cannot substitute. A successful 304 can verify release evidence; it cannot make
an old Scorecard scan current. Include applicability/absence reviews in the
minimum, so a fresh check of one easy field cannot hide neglected evidence.

Propose UTC **day** comparison for verification ties, since curated reviews
already use day precision. Retain original timestamps and precision in evidence;
same-day seconds do not break a tie. Month/year-only verification dates cannot
satisfy this daily key until a real dated review occurs. Preserve coarse event
dates as supplied; do not invent midnight or a first day. An activity event with
insufficient precision to establish window membership stays unresolved.

Rank complete records by the tuple `(recent_signal_count, oldest_verified_day)`,
descending. Equal tuples share competition places (`1, 1, 3`); canonical ID only
stabilizes display order. Include all places at most 10, including cutoff ties.
Only qualifying current records at places 1–3 receive trophies. Show qualifying
coverage and **“No complete records qualify for this edition”** when empty.

## Presentation and weekly compatibility

Use the existing compact table with **Recent signals** as its value header.
Its native evidence disclosure lists the checklist version and resolved states,
applicability/scope, source links, event dates, per-domain verification dates,
oldest verification day, reference date and exact activity/HN windows. Show the
count and tie-break separately; do not collapse them into a blended score.

Freeze alongside existing boards through the normal publisher's weekly process.
Implementation needs a new schema/algorithm version for tuple ranking and input
fingerprints covering every consumed source and checklist definition, including
new URL-health/resolution evidence, Function and deployment files, and HN
identity/alias inputs where consumed. Missing inputs must be recorded explicitly.
Preserve schema 1/2 readers and the six-metric validation rules for their versions.
Existing editions remain byte-for-byte frozen, including the adoption week;
start the seventh board at the next eligible weekly freeze. Earlier observations
say **not measured** for this metric. Retain future count, tie-break and coverage
facts without manufacturing historical ranks, zeroes or inferred winners.

## Producer handoff and implementation review

Proposed handoffs from URL checking and deployment research should carry canonical
ID/URL, requirement or event type, official evidence/revision, occurrence date
and precision, observation/check date and outcome, applicability/result/scope,
and producing task/PR. Reconcile on fresh main after owner review. Inspect open
proposals by ID before importing; preserve concurrent owner edits. Redirects
become review candidates, with identity continuity and software-rename occurrence
handled under [the history contract](PROJECT-HISTORY.md). Deduplicate per event
type and preserve unknown, month and year occurrence dates. These handoffs add no
running status log or schedule. [PR #239](https://github.com/awesomeopen/awesome-open/pull/239)
is the separate deployment-backfill proposal; its proposed job and schema must
be reconciled from merged work before use.

| Implementation area | Concrete acceptance tests |
| --- | --- |
| Evidence adapters in `scripts/build_catalog.py`, `deployment.py`, `signals.py` and the reviewed URL/resolution schema | Missing vs observed zero/verified none; evidence-backed applicability; sparse deployment fields and unknown package relationship; approved vs pending/rejected summary; structured feature review dates; stale/failed checks; missing successful timestamps. |
| `scripts/weekly_scoreboard.py` and `test_weekly_scoreboard.py` | Checklist gate, maximum three signals, no volume weighting, duplicate events, complete zero-activity records, tuple ties/cutoff ties, ID-only stable ordering; refreshing one fact cannot advance the oldest-date key. |
| Snapshot/history validation and `test_scoreboard_history.py` | Version-specific metrics and tuple validation; all input fingerprints, concurrent-input detection, explicit missing inputs; schema 1/2 compatibility, not-measured history, same-week byte immutability across adoption. |
| Time and HN fixtures in `test_weekly_scoreboard.py`, `test_update_hn.py` | UTC offsets/leap dates, inclusive ages 0 and 90, exclusion at 91, future timestamps, date precision, ongoing-month exclusion, mismatched identity/window, completed zero stories vs unfinished pages. |
| `scripts/build_scoreboard.py`, `scoreboard_trends.py`, `build_site.py` and Scoreboard browser tests | Empty qualification, visible count/tie-break/checklist/windows, seven-board new editions vs six-board legacy editions, trophy eligibility, native keyboard/no-JavaScript disclosures and narrow layouts. |

Owner review must settle checklist scope/applicability (including the Scorecard
provider's declared check scope), absence schemas, URL-health freshness, the
90-day window and day-precision tie-break before implementation. Run full offline
tests, brand checks, README/catalog/site previews and applicable browser checks
for that implementation; this proposal changes documentation only.

Contribution by Junge (AI)
