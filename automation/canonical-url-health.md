# Canonical URL health audit

Status: PROPOSED. Not registered, not scheduled, not implemented. This file is a plan only. Editing, cloning, or merging this file does not register a task, enable a schedule, or authorize a run. A run becomes executable only after this contract and its linked implementation are reviewed and merged, the owner authorizes registration, and the actual registration is verified separately. This draft was prepared locally for owner review on 2026-10-30, submitted as draft pull request #231, and merged on 2026-10-31. The redirect-triage and slow-host amendments in section 6, added 2026-10-31, are proposed in a follow-up draft and take effect only when that follow-up is merged. No schedule, code, or catalog change accompanies them.

Signing: contributions prepared by the assistant for this repository are signed "Superhirn (AI)" in the pull request and commit descriptions, and in any author or reviewer field where the assistant is the author. Owner review and merge remain separate and are not signed by the assistant.

## 1. The job in one paragraph

Check, once a week, every catalog project's canonical URL: whether it still responds, where it redirects, and whether a GitHub repository has moved to a new path with the same repository ID. Record only the observed HTTP facts, with dates and redirect chains, in a new evidence file, and file a draft only when an observation has changed or a monthly coverage checkpoint is due (section 8). Propose nothing automatically. Any change to a catalog name, URL, alias, or history record remains a separate curated change, reviewed and merged by the owner. The job exists because catalog URLs decay: repositories rename, owners transfer, domains lapse, and pages move. Today those changes are found ad hoc. The reviewed rename ledger in CONTRIBUTING.md shows the pattern: each rename was verified manually by comparing repository IDs, and only the history endpoint changed, while the catalog name and URL stayed unchanged until a separate curated change. No collector in `scripts/` probes canonical URLs, no job in `automation/README.md` owns URL health, and no entry in TODO.md covers it. The scripts directory listing as read on 2026-10-30 contains collectors for GitHub metrics, Hacker News, star history, and signals, and browser checks for the rendered site, and none for canonical-URL availability, redirects, or dead links.

## 2. Philosophy fit

This job follows the catalog's stated principles, in PRODUCT.md and CONTRIBUTING.md:

- Facts stay literal. An observation records an HTTP status, a Location header, and a date. It never records a verdict such as dead, abandoned, or unhealthy.
- Inspection first. The evidence a comparer needs, the current canonical URL and where it leads, is one predictable step away, in one evidence file keyed by the same catalog ID used everywhere else.
- Wonder lives in the artwork and organization. This job adds no display, no badge, and no score to the site in version 1. It only keeps the underlying facts current.
- One curated source, one publisher. The audit never edits `README.source.md`, the generated README, or the site. The publisher remains the only writer of generated output.
- Missing work is omitted. An unprobed URL, a blocked probe, or an unverified redirect stays Unknown, with the reason recorded, rather than being filled in by inference.
- Inclusion is a naming rule only. A failed probe never removes a project, never changes eligibility, and never becomes a quality or maintenance verdict. WORKFLOW.md already states the rule this job codifies: an inaccessible page alone proves no withdrawal, and research is deferred when an official source is unavailable.

## 3. Scope

In scope, version 1:

- Every unique canonical URL in `README.source.md`, counted once per catalog ID. Cross-listed entries share one ID and one observation. As counted from the source file on 2026-10-30, that is 552 unique URLs in 577 table rows across 21 categories. Recount from the catalog at run time; never hard-code the total.
- One probe per canonical URL per sweep, following the HTTP rules in section 6.
- GitHub repository identity verification, only through the public repository API record and repository ID comparison, when a token is available and only for URLs that redirect.
- Recording observations in `data/canonical_url_health.json`, with the schema in section 7.
- One scoped draft pull request per sweep, only when section 8 requires one, under the review gates in section 9.

Out of scope, version 1:

- Changing any catalog entry, name, URL, category, description, alias, alternative, or history record. Those are separate curated changes.
- Displaying health, availability, or redirect information on the website, in the README, or in the Observatory. No display contract exists yet; a display proposal is a separate decision.
- Probing any URL other than a canonical URL, following links found on a project's page, executing JavaScript, logging in, or submitting forms.
- Installing, executing, or downloading candidate software. The probe reads headers and at most a capped response head; it never runs code from a project.
- Contacting project owners, opening issues in other repositories, or reporting broken links externally.
- Any paid service, paid API, or new credential beyond the existing GitHub token used by the publisher, if the owner authorizes its use for ID verification only.

## 4. Inputs and identity

Read fresh `main` on every run, in this order:

1. `AGENTS.md`, `CONTRIBUTING.md`, this contract, and `automation/README.md`.
2. `README.source.md`, through the existing catalog builder, never through a hand-written parser.
3. `data/canonical_url_health.json`, if present, and relevant open pull requests and active work, to deduplicate by canonical ID.
4. `site/PROJECT-HISTORY.md` and `site/PROJECT-ALIASES.md`, for the identity and alias contracts that govern any follow-up proposal.

Identity rules, reused exactly from `scripts/build_catalog.py`:

- Build the catalog with `python3 scripts/build_catalog.py --output tmp/catalog.json`.
- Use the complete catalog `id`, the SHA-256 of the canonical URL. Never hash the display name, use a category position, or shorten the hash.
- Use the builder's `canonical_url` normalization: host names are case-insensitive, GitHub owner and repository path segments are case-insensitive, other path segments, query strings, and fragments stay case-sensitive, and only root paths and GitHub repository URLs normalize a trailing slash.
- Cross-listed projects use one record. A renamed or redirected URL requires an explicit identity update, under the existing contracts; this job never performs that update itself.

Environment, version 1:

- Python 3.12, Python standard library only. No new dependency. The checker reuses `urllib`, `hashlib`, `json`, and the catalog builder, in the same style as `update_stats.py`, `update_hn.py`, and `update_star_history.py`.
- No network access in tests. Tests use fixtures that replay recorded redirect chains.
- A GitHub token is optional, and only for repository-ID verification after a redirect. If no token is available, GitHub redirects are recorded as redirect-observed, identity-unverified, and the run continues. The token is never sent to a non-GitHub host, never sent on a redirect to another host, and never written to any file or report.

## 5. Sweep: every URL, every week, with per-host politeness

Revision note, 2026-10-30: the first draft of this plan used a rotating batch of 40 URLs per run, borrowed from the enrichment backfills. That was the wrong bound for this job. A HEAD probe is cheap, the catalog is 552 URLs, and a 40-per-week rotation takes about 14 weeks to cover the catalog once, which leaves no headroom at 1,000 URLs, where the same rotation would take 25 weeks, longer than the 90-day reachable due interval. The bound that matters here is not the number of URLs, it is the request rate to any one host, and the review burden of the resulting draft. This section replaces the rotation with a full weekly sweep and changed-only drafts.

The sweep probes every unique canonical URL in the freshly built catalog, once per scheduled run, in ascending catalog ID order. No selector, no due dates, and no cursors are needed. The order is deterministic so two runs over the same catalog produce the same probe order, and the digest in section 7 proves the same sweep was performed.

Why a full sweep is cheap, measured from the catalog as read on 2026-10-30: 577 table rows, 552 unique first-link URLs, of which 500, about 91 percent, are on github.com. The remaining 52 URLs sit on 51 other hosts. A HEAD request that answers in 0.5 seconds takes about 4.6 minutes sequentially for 552 URLs, and about 1 minute with 8-way parallelism across hosts. At 1,000 URLs the same figures are about 8.3 minutes sequential and about 1 minute parallel, before per-host throttling. The real cost is the github.com share: 500 requests to one host must be paced, not parallelized.

Concurrency and politeness bounds, version 2:

- At most 8 probe workers in total, and at most 1 in-flight request per host. Different hosts run in parallel; the same host is always probed serially.
- A minimum interval of 1.0 second between requests to github.com, and 0.5 seconds between requests to any other host. These intervals, not a batch cap, pace the sweep. With 500 github.com URLs at 1.0 second, the github.com leg takes about 8.3 minutes, while the other hosts finish in parallel. At 1,000 URLs with the same github.com share, the sweep takes about 15 minutes.
- At most 1,200 HTTP requests per run, counting redirect hops, and at most 45 minutes of total probe time. A run that would exceed either bound stops, preserves the observations already recorded, and reports the bound as a blocker. The bound is a safety stop, not a batch size: a normal sweep of 552 URLs uses about 552 requests plus a small number of redirect hops.
- The per-hop timeouts, body cap, and retry rule from section 6 apply within these bounds.

If a previous material draft is still pending review, the next sweep still runs, because a sweep is only observation, but it files no new draft. Its results are held for the next draft, and the sweep summary in section 11 records that a draft was skipped for that reason. This differs from the enrichment one-pending-draft gate, which pauses the work itself; here the observation work is cheap and safe to repeat, and only the filing is gated. A sweep never overwrites a pending draft's branch, and it never merges anything itself.

Cadence, proposed, to be authorized by the owner before registration:

- Weekly, Tuesdays, nominal 10:00 America/New_York, flexible. Tuesday at 10:00 avoids the enrichment windows at 08:00, 15:00, and 19:00, the documentation reconciliation run at 04:00, and the publisher's daily run at 00:00 UTC. The exact registration, runner, and timezone handling, including daylight saving changes, must be verified in the registration itself, not inferred from this file.
- Manual dispatch is allowed for a bounded recheck of a single persistent failure, with the same per-host bounds, and only after the owner authorizes the scope. Manual dispatch never starts a full sweep and never changes the schedule.

## 6. HTTP protocol: what a probe does, and what each result means

Revision note, 2026-10-31: the pilot sweep of the first 100 URLs, reported in chat, found two probe defects in this section's first draft. First, `https://osdoc.cogsci.nl` (OpenSesame) answers GET in about 11 seconds and never answers HEAD within 10 seconds, for any User-Agent, so a HEAD-only 10-second timeout recorded a transport error for a site that opens in a browser. Second, a permanent redirect alone does not say whether the change is a URL correction, a move, or a rename, or whether it is already recorded. This section now requires a GET fallback on a HEAD timeout, with a longer timeout and a method switch on retry, and adds redirect triage and handover below. The contract version stays 1: the original contract was merged as PR #231, and this amendment is proposed as a follow-up draft.

One probe, per selected URL, in this exact sequence:

1. Send an HTTP HEAD request to the canonical URL, with a distinct honest User-Agent that identifies the audit, a 10-second timeout per hop, and no credentials, cookies, or Referer. Follow no redirects automatically. Use an opener that refuses redirects, in the style of the NoRedirect handler already used in `scripts/update_signals.py`, so each hop is observed and recorded separately.
2. If HEAD returns 405, 501, or another method-related rejection, or if HEAD times out, send one HTTP GET request to the same hop URL, with the same headers, a 30-second timeout, reading at most 64 KB of the body and then closing the connection. Never read a full page, never parse scripts, and never follow links in the body. A GET fallback may occupy its host slot for up to 30 seconds; that time counts toward the 45-minute run bound in section 5. A HEAD timeout alone is never recorded as a transport error.
3. Follow redirect responses, 301, 302, 303, 307, and 308, one hop at a time, recording each hop's status and Location header, up to 5 hops. Stop at the first non-redirect response, at 5 hops, or at a redirect loop, and record the stopping reason. Never follow a redirect to a URL with a username, password, or encoded host. Never send a credential on any hop.
4. On HTTP 429, read the Retry-After header if present, record it, and stop that URL for this run. Do not retry the URL in the same run. On a timeout, DNS failure, or TLS failure, record the error kind, retry once after a 5-second pause, switching method: a HEAD failure is retried as GET with a 30-second timeout, and a GET failure is retried once as GET with a 30-second timeout. Record both attempts and the method of each attempt in `review_note` when the methods differ. A second failure ends that URL for this run. A transport error is recorded only after the GET fallback in step 2 has also failed.
5. For a URL whose host is github.com and whose final response is a redirect, verify identity only when a GitHub token is available: request the repository API record for the old path and for the new path, and compare repository IDs. Record both IDs, or record that verification was unavailable. The catalog name and URL stay unchanged regardless of the result; only a separate curated change, under the history and alias contracts, may update them.

Status taxonomy, and the only meanings the evidence file may record:

- `reachable`: a final 2xx response. Meaning: the canonical URL responded on the checked date. It is not a statement about the project's quality, activity, or content.
- `redirect-permanent`: a 301 or 308 hop in the chain. Meaning: the server asked clients to use a different URL permanently. It is not, by itself, an identity change; identity requires the repository-ID check for GitHub URLs, or official-source review for other hosts.
- `redirect-temporary`: a 302, 303, or 307 hop. Meaning: the server asked clients to use a different URL for now. Treat it as less stable than a permanent redirect, and recheck in 30 days.
- `client-error`: a final 4xx response, including 404 and 410. Meaning: the server answered that the resource was not found or unavailable on the checked date. A single client error never establishes withdrawal, removal, or a name change.
- `server-error`: a final 5xx response. Meaning: the server failed to answer on the checked date. It establishes nothing about the project.
- `blocked`: a 403, 429, or a response that indicates bot or rate-limit handling, or a redirect loop. Meaning: the probe was refused or limited. It establishes nothing about the project, and it must never be reported as a dead link.
- `transport-error`: a DNS failure, TLS failure, connection failure, or timeout after the GET fallback and the one retry in steps 2 and 4. Meaning: the probe could not reach the server. It establishes nothing about the project. A HEAD timeout alone is a probe artifact, not a transport error, and it never counts toward persistent failure.
- `unknown`: any result that does not fit the taxonomy, or a probe that could not run. Meaning: no observation was recorded for that URL in that run.

Persistent failure, the only aggregate state the job may compute:

- A URL is in persistent-failure state after the same client-error, server-error, or transport-error result on two consecutive runs on different UTC dates, with no reachable observation in between. A blocked result never counts toward persistent failure. A persistent failure is a prompt for human review, never a proposal to remove, rename, or delist a project. The review may lead to a history record, an alias record, an identity update, or no change, each through its own contract and draft pull request.

Redirect triage and handover. Before an evidence draft is filed, every `redirect-permanent` record is triaged into one class, and a temporary redirect is triaged only when its identity is verified. The class, the check for an existing record, and the handover, if any, are stated in the run report in section 11. Triage never changes a catalog entry by itself.

- Class A, URL correction: the final URL differs from the canonical URL only by a trailing slash, a scheme, or another difference the builder's `canonical_url()` already absorbs. No identity change, no follow-up. A correction record is recorded once; later sweeps confirm the same chain and file no new packet. If the chain changes, the record is triaged again.
- Class B, move: the host or path changed, the project is the same, and no software-name change is evidenced. The follow-up depends on identity verification: for a GitHub URL, the repository-ID comparison in step 5; for another host, an official HTTPS source stating that the same project moved. If identity is verified and the move is not yet recorded in the history file or the rename ledger in CONTRIBUTING.md, the handover is a history event of kind `repository_rename` or `owner_transfer`, or a star-history endpoint mapping, as the relevant contract requires. If the software name may also have changed, that check is done before any proposal, and a move and a rename are never bundled into one packet.
- Class C, rename: the repository path changed and a software-name change is evidenced by an official source, such as a rename commit, an announcement, or a release. The handover is a history event of kind `software_rename`, one event for one rename, under `site/PROJECT-HISTORY.md`, with the occurrence date at the precision the source supports and the source that supports it. A display-name update is a separate curated change and is never included in the history packet.

For every class B and class C record, the agent checks, before proposing anything, whether the same change is already recorded: in `data/project_history.json` for an event with the same catalog URL, kind, old and new names, and occurrence; in `data/project_aliases.json` for an existing alias; and in the rename ledger in CONTRIBUTING.md and `REVIEWED_REPOSITORY_RENAMES` for an existing path mapping. If it is already recorded, the report states that, with the location, and no packet is prepared. If it is not recorded, the handover packet contains the catalog ID, the old and new URLs, the full redirect chain, the identity evidence with both repository IDs or the official source, the date basis with its sources, the exact content of the proposed change, and a separate flag for any display-name decision the owner must still make. The packet is proposed as a separate scoped draft pull request under its own contract, never inside the evidence draft, and it requires its own owner review and merge. If no official source establishes an exact occurrence date, the packet proposes `occurred: null` with an explicit unknown-date note, so the event stays in the folded secondary evidence block and never enters the timeline on an invented date.


## 7. Evidence schema: `data/canonical_url_health.json`

The file has `schema_version: 1`, a `last_sweep` summary object, and a `records` object keyed by the complete catalog ID. The publisher does not read this file in version 1, and no site, README, or Observatory output reads it. That separation is deliberate: the evidence must prove itself in review before any display contract is proposed.

Changed-only records. A sweep probes every URL, but it writes a record only when the observation is actionable or has changed since the previous sweep. An actionable observation is any status other than `reachable` with no redirect, or a reachable observation whose redirect chain, final URL, or GitHub identity verification differs from the previous record. A URL that answers cleanly, sweep after sweep, has no record, or has its previous record removed under the pruning rule below. This keeps the evidence file small and the draft reviewable: the reviewer reads only what changed, not 552 unchanged confirmations. Coverage for the unchanged URLs is proved by the sweep summary, not by a record per URL.

The `last_sweep` object records, for the most recent completed sweep: the UTC date, the catalog source SHA, the total number of unique URLs checked, the count per status, the list of changed catalog IDs, the digest, the total requests and elapsed probe time, and any limits hit. The digest is the SHA-256 of the sorted lines `catalog_id:status:http_status:final_url`, one line per checked URL, using an empty final URL when no response was received. Any agent that re-runs the sweep over the same catalog and gets the same observations must reproduce the same digest, except for live HTTP differences, which it must then explain from the changed records.

Pruning. When a URL with an existing record answers cleanly with no redirect, its record is updated to that clean observation, kept for one further sweep, and removed in the following sweep if it is still clean. The removal is listed in that sweep's changed IDs, so a reviewer can see a resolution and its confirmation. A record is never removed in the same sweep in which it first became clean, and never removed while its status is anything other than clean and reachable.

Each record contains:

```json
{
  "project_url": "https://github.com/example/openexample",
  "canonical_url_checked": "https://github.com/example/openexample",
  "checked_at": "2026-11-03",
  "checked_by": "canonical-url-health/1",
  "status": "redirect-permanent",
  "http_status": 301,
  "final_url": "https://github.com/example/openexample-core",
  "redirect_chain": [
    {"status": 301, "location": "https://github.com/example/openexample-core"}
  ],
  "github_repo_id_before": 123456789,
  "github_repo_id_after": 123456789,
  "github_identity_verified": true,
  "error_kind": null,
  "attempts": 1,
  "review_status": "pending",
  "review_note": "Permanent redirect to a repository with the same ID. Identity update is a separate curated change; catalog name and URL unchanged.",
  "observations": []
}
```

Field rules:

- `project_url` is the exact catalog URL from the catalog builder. `canonical_url_checked` is the URL actually probed, after the builder's normalization, and it matches `project_url` in version 1. If a future version probes a different URL, the two fields diverge and the reason is recorded in `review_note`. A retained record for a URL that has left the catalog also carries `last_present_source_sha`, the last catalog revision in which its ID was present.
- `checked_at` is the actual UTC date of the probe, `YYYY-MM-DD`. `checked_by` is the job name and contract version, `canonical-url-health/1`.
- `status` uses only the taxonomy in section 6. `http_status` is the final response status, or null for a transport error. `final_url` is the URL of the final response, or the canonical URL when no redirect occurred, or null when no response was received.
- `redirect_chain` lists every hop in order, each with its status and Location header value exactly as received. An empty list means no redirect occurred. A chain longer than 5 hops is recorded as truncated, with the stopping reason in `review_note`.
- `github_repo_id_before`, `github_repo_id_after`, and `github_identity_verified` are present only for GitHub URLs that redirected. When verification was unavailable, `github_identity_verified` is false and the IDs are null, with the reason in `review_note`. When verification ran and the IDs differ, the record states that plainly: the redirect leads to a different repository, and no identity is established.
- `error_kind` is one of `timeout`, `dns`, `tls`, `connection`, `rate-limited`, `redirect-loop`, `too-many-hops`, or null. It is never a free-text diagnosis.
- `observations` keeps at most the three most recent observations, each with the same fields as a record minus `observations` itself, so a reviewer can see a failure's history without reading the whole file. The top-level fields always describe the most recent observation.
- `review_status` starts as `pending` for every new or changed record. It becomes `approved` only when a reviewer has checked the observation against its method and recorded that check in `review_note` with a date and reviewer name. `rejected` means the observation was found to be an artifact, for example a probe error misclassified by the checker, and the record is retained with the rejection reason, not deleted. Review status here is a check on the observation, not approval to change the catalog. Owner merge approval for any follow-up change remains separate.
- Existing records are preserved. A run applies only its changed additions and updates, re-fetching fresh `main` immediately before writing, and preserving unrelated records, owner edits, and overlapping proposals. A record is never deleted by this job. If a project leaves the catalog because its canonical URL changed, its record is retained under its old catalog ID, marked with `last_present_source_sha` for the last catalog revision in which that ID was present, until a separate curated decision re-keys it to the new ID or closes it. Retained records are exempt from the present-in-catalog validation below; no new record may be created under a stale ID.

Validation, run before any draft is filed:

- The JSON parses, the schema version is 1, every non-retained key is a complete catalog ID present in the freshly built catalog, every retained record carries `last_present_source_sha` and no other record uses a stale ID, and every record's `project_url` matches the catalog URL for that ID or, for a retained record, the URL for that ID at `last_present_source_sha`.
- Every `status` is in the taxonomy, every date is a valid UTC date, every redirect chain has at most 5 hops, and every GitHub verification claim includes both IDs or an explicit unavailable reason.
- No record proposes a catalog change. The file contains no `README.source.md` edit, no name change, and no URL change.
- The offline test suite passes, including fixture tests that replay a permanent redirect, a temporary redirect, a 404, a timeout, a redirect loop, a HEAD timeout followed by a successful GET, a slow host that answers GET only after 10 seconds, and a GitHub rename with matching and mismatching repository IDs, with no network access.

## 8. Output and pull request scope

One run produces at most one draft pull request, with this exact scope:

- `data/canonical_url_health.json`, with only the selected records added or updated.
- A run report in the pull request description, using the format in section 11. No report file is committed in version 1, so the evidence file stays the only durable artifact and the report stays attached to its review.
- Test and fixture changes, only when the contract or checker changed in that run. Implementation changes and evidence updates never share a draft with a catalog change.

The draft pull request:

- Uses a focused branch, a draft state, and a title that names the job, the sweep date, and the number of changed records, for example `canonical-url-health: 2026-11-03, 6 changed` or, for a monthly checkpoint with no changes, `canonical-url-health: 2026-11-24 sweep summary`.
- Links this contract, the catalog source SHA, the sweep summary and digest, and the exact-head CI result.
- States the actual coverage: how many URLs were checked, how many were reachable, redirected, failed, or blocked, and how many records are new, updated, or unchanged.
- Includes the redirect triage table from section 11, with one row per triaged record, stating its class, whether the change is already recorded and where, or a link to the separate handover packet, or that no follow-up is required and why.
- Makes no claim beyond the observations. It does not say a project is dead, moved, or withdrawn. It does not say the catalog is healthy or unhealthy as a whole.
- Never merges itself, never marks itself ready, never enables auto-merge, and never changes repository protections. Owner merge approval remains separate, and a passing check alone does not merge it.

A draft is filed only in two cases. First, a material change: at least one new or changed actionable record, a new persistent failure, a GitHub redirect with a verified matching repository ID, or an actionable blocker. Second, a monthly coverage checkpoint: the first sweep of a calendar month, even when nothing changed, so the sweep summary and digest reach the repository at least monthly. In every other case the sweep stays quiet and files no draft. Its summary is held for the next draft that is filed, which then lists every sweep since the last merged draft. If a draft from a previous sweep is still pending review, the next sweep still runs, but it files no new draft and it never overwrites the pending draft's branch; its results are held for the draft that follows the pending one's merge.

## 9. Review gates and follow-up changes

Two reviews, kept separate:

1. Observation review. A reviewer checks that each new or changed record matches its method: the status fits the taxonomy, the redirect chain is complete, the GitHub ID comparison, when claimed, used the repository API records, and the dates are actual UTC dates. The reviewer records the check in `review_note` and sets `review_status` to `approved` or `rejected` in a follow-up commit to the same draft, or in review comments that the integrator applies before merge. Stylistic reservations about wording are nonblocking notes; a factual error in an observation blocks approval of that record.
2. Catalog change review, only when a follow-up is proposed. A permanent redirect with a verified matching repository ID, a documented rename, or a persistent failure may lead to a separate proposal, each under its own contract: an identity update under the catalog builder rules and the migration procedure in section 10, an alias record under `site/PROJECT-ALIASES.md`, or a history record under `site/PROJECT-HISTORY.md`. The proposal arises from the redirect triage in section 6, is prepared as a handover packet with its exact content, and uses a separate scoped draft pull request, never the evidence draft, and it requires its own owner review and merge. The evidence record's `approved` status does not authorize the catalog change.

No task, including this one, merges, marks a draft ready, enables auto-merge, or changes repository protections. No force-push is used. Concurrent edits are preserved by re-fetching fresh `main` and rechecking open pull requests before writing, and by applying only the selected records.

## 10. Identity-change migration: what moves, in what order, when a canonical URL changes

This section applies only when the owner has decided, under section 9, that the catalog's canonical URL itself changes. It does not apply to the default case. The default case is to keep the catalog URL and ID unchanged and record a repository rename or owner transfer as a history event. A migration is required only when the normalized canonical URL changes, which means the catalog ID changes, because the ID is the SHA-256 of the normalized URL. A change that normalization already absorbs, such as a difference in GitHub owner or repository letter case, or a trailing slash on a GitHub repository URL, is not an identity change and requires no migration.

### 10.1 Continuity proof, before any file changes

No file moves until identity continuity is proved outside the probe. A permanent redirect, even a 301, is not proof. For a GitHub repository, the proof is the repository API record for the old path and for the new path reporting the same repository ID, with both records read and recorded in the migration PR description. For a non-GitHub project, the proof is an official HTTPS source, such as an announcement on the project's own site or repository, stating that the same project moved to the new URL, with the same name and purpose. If continuity cannot be proved, the migration does not proceed. The old URL stays canonical, the health record stays under the old ID, and the curator records the investigation as a note, not as a migration.

### 10.2 The migration rule

A canonical-URL change is one atomic, owner-merged draft pull request, or it does not happen. Every file that keys evidence by the old URL or old ID moves in that same PR, in the order below, so the build passes at the PR head and no evidence is orphaned in between. A partial migration, a URL change in `README.source.md` without the evidence moves, or a hand edit to a derived snapshot, is not a migration. If validation fails at any step, the whole PR is reverted, not merged in part. The old ID remains canonical until the migration PR merges.

### 10.3 Tier A: evidence keyed by URL or ID, moved in the same PR

These files fail the build, or silently drop the evidence, if the old key is left behind. The builder keys projects by normalized URL, attaches history and aliases only when their `project_url` is a listed canonical URL, rejects reviewed alternatives that refer to unlisted projects, and rejects function-summary and deployment records whose ID or `project_url` does not match the rebuilt project. Move each record by changing its key and its `project_url` together, preserving every other field except where this section requires a re-review. Never copy a record to a different repository ID, a different project, or a fork.

1. `README.source.md`: change the row's URL, and the display name only when the official source establishes a new software name. Keep the category and description unless the official source establishes a change to them. Check the row against the alternatives rule in the same edit: any inline `Alternative to:` text must match the reviewed alternatives exactly.
2. `data/alternatives.json`: re-key the record from the old canonical URL to the new one, preserving the reviewed alternatives, their source URLs, scopes, and checked dates. If an alternative's own source URL was the old canonical URL, re-check it against the official source at the new location; do not carry a stale source URL forward.
3. `data/project_aliases.json`: re-key the record to the new canonical URL, preserving the alias names, their official source URLs, and the review provenance. If the old display name is now an alternate name, add it as a reviewed alias in this same PR, with an official source, rather than losing it. Do not infer aliases.
4. `data/project_history.json`: update `project_url` on every existing event for this project to the new canonical URL, preserving event IDs, kinds, occurrence dates, sources, and review provenance. Then add the new event for this change, with kind `repository_rename`, `owner_transfer`, or `software_rename` as appropriate, an occurrence date from an official source at the precision the source supports, sources with roles, and a note stating what the evidence establishes. An event never changes the catalog URL by itself; the URL change is the source edit in step 1.
5. `data/function_summaries.json`: re-key the record from the old ID to the new ID and update `project_url`. Set `review_status` back to `pending`, with a new `checked_at` and reviewer only when a reviewer has re-checked that the summary text and its sources still describe the same project at the new URL and under the new name. An approved summary carried across an identity change without re-review would attach immediately on the next build, which is why the status reset is mandatory. Records that were already pending or rejected under the old ID stay pending or rejected under the new ID, with the same reason, and are never promoted by the migration.
6. `data/deployment_evidence.json`: re-key the record from the old ID to the new ID and update `project_url`, preserving the sources. Re-review the record before it can be treated as approved at the new identity: every source must still use HTTPS and still support the project at the new URL, and `checked_at` and `reviewed_by` must record the re-review. If a source URL was the old canonical URL, replace it only with the corresponding official source at the new location.
7. `data/canonical_url_health.json`: re-key the health record from the old ID to the new ID and update `project_url` and `canonical_url_checked`. Carry the `observations` history forward, so the new record shows the redirect that caused the migration. Retain a copy under the old ID, marked with `last_present_source_sha` for the last catalog revision in which the old ID was present, as section 7 requires. No new record may be created under the old ID after the migration.
8. `data/hn_projects.json` and `data/hn_evidence.json`: update `readme_url`, `repositories`, `queries`, and `identity_sources` together to the new identity. Keep the `slug` stable unless the software name itself changed, because the slug names the chart asset. Do not hand-edit story counts in `hn_evidence.json`. A substantive change to the HN identity rules or queries invalidates the existing collection fingerprint, so the next Hacker News collection must be a complete new collection under the existing HN contract, not a partial refresh. Record that requirement in the migration PR description.

### 10.4 Tier B: evidence keyed by repository path, decided, not hand-edited

These files are keyed by the lowercase repository path, not by the catalog URL, so a catalog URL change does not automatically require a key change, and hand-editing them would falsify their provenance.

- `data/star_history.json`: do not rename the cache key or rewrite monthly counts by hand. Decide, with owner review, between the two documented paths. The preferred path, when the catalog URL is kept, is to add a reviewed entry to `REVIEWED_REPOSITORY_RENAMES` in `scripts/update_star_history.py` and a matching entry in the rename ledger in CONTRIBUTING.md, so the collector fetches the same repository's history through its new endpoint while the cache identity stays unchanged. The other path, when the catalog URL itself changes, is to let the collector create a record under the new repository path on its next run, after verifying the same repository ID, and to record in the migration PR whether the old chart record was carried over by re-keying `repo`, `readme_url`, and `source_url` together, or left to be recollected. Never copy monthly counts to a different repository ID. `data/star_history_projects.json` needs no change in a migration: as verified on 2026-10-30 it is exactly `{"schema_version": 2, "scope": "catalog_github"}`, and `load_projects()` in `scripts/update_star_history.py` derives every eligible repository from `README.source.md` for schema 2, so a new canonical GitHub URL joins automatically and the old repository leaves the published cache on the next refresh, because `refresh()` retains only repositories in the eligible set. Schema 1 explicit lists remain readable only for fixtures or scoped manual runs. Record the file's `schema_version` and `scope` in the migration PR description; if it has ever been changed to a schema 1 explicit list, that list must be updated in the same PR.
- `data/github_metrics.json` and `data/project_signals.json`: do not hand-edit. Both are snapshots keyed by repository path and re-derived by their collectors. Until the next refresh under the new path, the new repository has no cached metrics or signals, which means unknown, never zero, and the rendered metadata is omitted rather than invented. The migration PR must state that the next metrics and signals refresh is expected, and must not claim fresh metrics for the new identity.
- `data/chart_observations.json`: do not hand-edit. It is the collector's archive of star-history observations. The collector appends to it; a migration does not rewrite history.

### 10.5 Tier C: historical and artwork records, left alone or moved separately

- `data/weekly_draws.json`: never rewrite a past draw. A draw record that names the old ID or old name is a historical record of that week's draw. Future draws use the current catalog IDs.
- `data/specimen_art.json` and the specimen assets: do not rename an asset file as part of the migration PR. Move the artwork in a separate scoped artwork draft PR, under `site/SPECIMEN-ART.md`, with the bytes unchanged and no regeneration of the original: (1) rename `site/specimens/<old-id>.webp` to `site/specimens/<new-id>.webp`; (2) re-key the `data/specimen_art.json` record from the old ID to the new ID and update its `project_url` and `path`, preserving alt text, dimensions, source provenance, and review fields, re-inspecting the pixels only if the alt text or name refers to the old name, and then amending the alt text and `review_note` accordingly; (3) regenerate the matching cut-out `site/specimens/cutouts/<new-id>.webp` with `python3 scripts/build_specimen_cutouts.py` and update the corresponding `site/specimens/cutouts.json` record (source and derivative hashes and bounding box) to the new ID, removing the old-ID cut-out record; (4) refresh `brand/assets.lock.json` with `python3 scripts/check_brand.py --refresh` for the changed checksums only, preserving unrelated entries. Responsive variants in `site/specimens/responsive/`, if present for the old ID, may be included in the same artwork PR or added by a later run; a source without current variants is shown alone and the build warns. Verify the artwork draft against the current catalog and the specimen contract: the approved record exists at the new ID with an existing file, and no old-ID asset or record remains. If any step cannot be verified, leave the artwork unchanged under the old ID and record the gap in the artwork PR, rather than deleting or silently re-keying it.
- `data/name_rhymes.json`: check at migration time whether it is keyed by ID or name. If it is, treat it as Tier A in the same PR; if its keying cannot be established from the file and its contract, leave it unchanged and record the check in the PR description. Do not assume.

### 10.6 Display-name-only changes, and repo renames with the URL kept

A display-name-only change, where the URL and its normalization are unchanged, is not a migration: the ID, permalink, and every URL-keyed record stay valid. In that case, check only the name-dependent evidence in the same PR: Hacker News `name`, `title_aliases`, and `queries` that contain the old name, and any function-summary text that states the old name, which returns to pending for re-review. A repository rename or owner transfer where the catalog URL is kept is likewise not a migration: the only changes are a history event, and, for star history, a `REVIEWED_REPOSITORY_RENAMES` entry with its CONTRIBUTING ledger entry. The catalog URL, ID, and all URL-keyed evidence stay unchanged.

### 10.7 Validation and publication, in order

1. Re-fetch fresh `main` and re-check open pull requests for overlapping work on this project, including any pending health draft. The migration PR must be based on the head that contains the approved health observation, or it must state why it is not.
2. Run the full offline Python suite, `python3 scripts/build_catalog.py`, and `python3 scripts/check_brand.py`, and build production-shaped output. Every identity check above must pass, including the unused-evidence checks for alternatives, aliases, and history, and the identity-mismatch checks for summaries and deployment records. A build failure on any one file blocks the merge.
3. Run the existing browser checks for the affected record, at desktop and 320px, and confirm the new permalink, the attached evidence, and the drawer and full-record rendering. Record the exact source revision and the verification limits in the PR description.
4. Merge by the owner only, in the migration draft. No task merges, marks a draft ready, enables auto-merge, or changes repository protections.
5. After the publisher runs, verify the live record at the new permalink: the new name and URL, the attached history, alias, summary, and deployment evidence, and the absence of the old ID from the rebuilt catalog JSON. The old permalink is not redirected by the catalog; if external links point to it, record that break in the PR description rather than claiming a redirect exists.
6. After the next scheduled metrics, signals, and star-history refreshes, verify that the new repository path has fresh records under the new identity, and that no stale record under the old path is still attached to the new project. Until that refresh, the record's missing metrics are unknown, not a failure of the migration.

## 11. Run report format

Every run that checks at least one URL files a report in its draft pull request description, or, when no draft is filed because nothing changed, records a quiet run with no routine report. The report uses this exact structure, with actual numbers:

```text
Canonical URL health audit — <UTC date>
Catalog source: <source SHA, 40 characters>
Checked: <total unique URLs> of <total unique URLs> canonical URLs
Reachable <N>, redirect-permanent <N>, redirect-temporary <N>,
  client-error <N>, server-error <N>, blocked <N>, transport-error <N>, unknown <N>
Digest: <SHA-256 of the sorted observation lines, section 7>
Changed records: <N> — new: <N>, updated: <N>, pruned: <N> — unchanged and unrecorded: <N>
Persistent failures, two consecutive runs: <list of catalog IDs and names, or "none">
GitHub redirects with verified matching repository ID: <list, or "none">
GitHub redirects with unverified or mismatching identity: <list, or "none">
Redirect triage: <one row per triaged record: catalog ID and name, class A/B/C, already recorded and where, or separate handover packet link, or no follow-up and why; or "none">
Skips and limits: <quota, timeout, or access limits hit, or "none">
Blockers: <actionable blockers, or "none">
```

A run with no supported changes and no actionable blocker stays quiet. A run that hits a quota, a token failure, or a validation failure reports the blocker, preserves useful work, and stops the affected operation until it can proceed safely. It never fabricates an observation, and never uses a paid fallback.

## 12. Failure handling and safety bounds

- Quota and rate limits: on HTTP 429, honor Retry-After, stop that URL for the run, and record the limit in the report. If more than 10 URLs in a sweep return 429, stop the whole run, preserve the observations already recorded, and report the limit as a blocker. Never retry a rate-limited URL in the same run.
- Token failure: if GitHub ID verification fails for authentication reasons, record every GitHub redirect as identity-unverified, continue with the rest of the sweep, and report the token failure as a blocker. Never retry with a different credential, and never write a credential to any file.
- Validation failure: if the evidence file fails validation, file no draft, preserve the observations in the run's local output only, and report the failure. Never publish an unvalidated evidence file.
- Catalog drift: if `main` advances between selection and writing, discard the selection, rebuild the catalog from fresh `main`, and reselect. Never write observations against a stale catalog revision.
- Redirect to an unexpected host: record the chain and stop. Never follow a redirect that carries credentials, never send a token to the new host, and never treat a redirect to a different host as an identity match without official-source review.
- Large or slow responses: the 64 KB body cap, the 10-second HEAD timeout, the 30-second GET fallback timeout, and the 45-minute run budget are hard bounds. A URL that exceeds the GET fallback and its retry is recorded as a transport error with the bound that was hit, not retried with a larger budget in the same run. A URL that answers GET only after the HEAD timeout is recorded as reachable with that method in its `review_note`, not as a transport error.

## 13. Optimization over time: calibration, not drift

After every four scheduled runs, the job's operator, who may be the owner or a reviewer, performs a calibration review, recorded as a decision note in the draft that proposes any change. The review measures, from the evidence file and run reports:

- Coverage: the share of unique catalog URLs checked in the most recent sweep, and the number of sweeps since the last merged sweep summary. Target: 100 percent of URLs checked in every sweep, and a merged sweep summary at least monthly.
- False-positive rate: the share of persistent failures that human review later found to be artifacts, such as a temporary block, a probe error, a timeout recorded only because HEAD timed out, or a redirect that resolved. Target: below 5 percent of persistent failures. If the rate is higher, the first change is to the classification or retry rule, never to the taxonomy's meanings.
- Proposal acceptance: the share of follow-up identity, alias, or history proposals that the owner merged, and the share rejected. A low acceptance rate means the proposal threshold is too eager; a high rate with few proposals means the threshold may be too cautious. Either way, the threshold change is proposed as a contract change, with the numbers quoted.
- Cost: median probe latency, requests per run, and runs stopped by quota. If the median latency rises, the first change is to lengthen the per-host interval or the per-hop timeout, never to drop the redirect-chain recording.
- Review lag: the median time from draft filing to owner decision. If lag grows, the first change is to file drafts less often for unchanged sweeps, so each draft is easier to review, never to skip review.

A calibration change follows the same rule as every other contract change: update this contract, the implementation, and the tests together, in one reviewed change, and activate the new behavior only after the merged contract is present on `main`. The hosted prompt or schedule, when one exists, activates the new contract version only after that merge. Editing this file alone changes nothing about a registered task. The contract version in `checked_by`, `canonical-url-health/1`, increments only on a merged contract change, and old observations keep the version that produced them.

## 14. Handover: how any agent takes over this job

A new agent, with only this file, `AGENTS.md`, `CONTRIBUTING.md`, and the repository, must be able to reproduce a run. The handover checklist, in order:

1. Read fresh `main`, `AGENTS.md`, `CONTRIBUTING.md`, this contract, and `automation/README.md`. Read the catalog builder, `scripts/build_catalog.py`, and the identity rules in section 4. Read the evidence contracts for history and aliases.
2. Check the actual registration: runner, cadence, permissions, and last run report. If registration is inaccessible, mark that part unverified and continue only the repository checks. Never infer registration from this file.
3. Check open pull requests and active work for this job and for overlapping evidence work. If a draft from this job is pending, run the sweep but file no new draft, and hold its results for the next draft.
4. Build the catalog and run the sweep in dry-run mode against fixtures. Confirm the probe order matches section 5 for the current catalog, and record the source SHA and the expected digest for the fixtures.
5. Run the checker in dry-run mode against fixtures, with no network access, and confirm the recorded chains match the fixtures. Then run the live sweep, within the bounds in sections 5 and 6, and validate the evidence file.
6. File one scoped draft pull request, with the report format in section 11, and follow exact-head CI to its terminal result. Report failed, skipped, or unavailable checks accurately.
7. Stay quiet if nothing changed. Report only material additions, persistent failures, and actionable blockers, with verified commit, pull request, or run links.

Commands, version 1, to be finalized with the implementation and kept exact in the implementation's own documentation:

```sh
python3 scripts/build_catalog.py --output tmp/catalog.json
python3 scripts/check_canonical_urls.py --catalog tmp/catalog.json --evidence data/canonical_url_health.json --output data/canonical_url_health.json --dry-run
python3 scripts/check_canonical_urls.py --catalog tmp/catalog.json --evidence data/canonical_url_health.json --output data/canonical_url_health.json
python3 scripts/test_canonical_url_health.py
python3 -m unittest discover -s scripts -p 'test_canonical_url_health.py'
```

The script names above are proposed, not yet implemented. Until they exist, a run must not claim to have used them. The implementation phase, section 15, creates them, with tests, before any scheduled run.

## 15. Implementation roadmap

Phase 0, contract review, no schedule, no code. Owner reviews this file, corrects the cadence and the per-host intervals, and decides whether GitHub ID verification may use the existing token. No registration is created. The inventory in `automation/README.md` is updated only to list this job as Proposed, with its runner and cadence marked To be authorized, never as Enabled.

Phase 1, offline implementation, no network. Implement the sweep, the evidence schema and validation, and the fixture tests. The checker runs in dry-run mode only, against recorded redirect chains. A draft pull request carries only the contract, the implementation, and the tests. No live probing, no evidence file, and no schedule are included.

Phase 2, pilot, bounded and reviewed. With owner authorization, run one live pilot sweep of 100 URLs in ascending catalog ID order, and file one draft pull request with the observations. The owner reviews every record against its method before any further sweep. If the pilot's false-positive rate, latency, or review burden is unacceptable, the contract is corrected before Phase 3.

Phase 3, first full sweeps. Run the full weekly sweeps on the proposed cadence, filing drafts only under section 8. After four sweeps, perform the first calibration review in section 13, and propose contract changes only with the measured numbers.

Phase 4, registration. Only after Phase 3 has produced reviewed, merged evidence does the owner authorize registration of the hosted or scheduled task, verify the actual registration, and update the inventory to Enabled with the verified cadence, runner, and last-run link. The registration checklist, to be completed and kept with the registration, not in Git, is: runner identity, cadence and timezone, permissions and secrets, the exact prompt or workflow that invokes the commands in section 14, the one-pending-draft gate, and the procedure for disabling the task. Credentials, connection details, raw prompts, and private run context stay outside Git.

Phase 5, steady state and optimization. Continue the weekly sweeps, the calibration reviews, and the contract versioning in section 13. A display proposal, if the owner wants one, is a separate decision with its own evidence contract, and it must not reuse this job's observations as a health score or verdict.

## 16. Inventory entry, proposed

When Phase 0 is approved, add this row to the hosting and cadence table in `automation/README.md`, and a matching section in the same style as the other jobs. Until registration is verified, the operating state stays Proposed, never Enabled:

| Task | Runner | Configured cadence | Operating state |
| --- | --- | --- | --- |
| Canonical URL health audit | To be authorized | Weekly, nominal Tuesday 10:00 America/New_York, flexible | Proposed, not registered |

The section that follows the table must state, in the same words as the other jobs, that editing the inventory does not register the task, and must link this contract, the sweep and checker commands, and the evidence file. The inventory update is part of the Phase 0 draft, not a separate change.

## Appendix A. Machine-readable job descriptor, proposed

This descriptor is a codification aid, not a registration. No runner in this repository reads it today, and no schedule follows from it. It exists so a future runner, and any agent taking over, can check the registered task against one typed record, field by field, instead of inferring settings from prose. If a runner is ever built to read it, the descriptor's schema, validation, and activation rule must be reviewed and merged first, in the same change as the runner.

```json
{
  "job": "canonical-url-health",
  "contract_version": 1,
  "contract_path": "automation/canonical-url-health.md",
  "status": "proposed",
  "runner": null,
  "cadence": {"kind": "weekly", "weekday": "Tuesday", "time": "10:00", "timezone": "America/New_York", "flexible": true},
  "sweep": {"scope": "all unique canonical URLs", "max_requests_per_run": 1200, "max_minutes_per_run": 45, "max_workers": 8, "max_concurrent_per_host": 1, "min_interval_seconds_github": 1.0, "min_interval_seconds_other_hosts": 0.5, "max_hops_per_url": 5, "timeout_seconds_head_per_hop": 10, "timeout_seconds_get_fallback": 30, "max_body_bytes": 65536},
  "drafts": {"on_material_change": true, "monthly_coverage_checkpoint": true, "changed_records_only": true},
  "inputs": ["README.source.md", "scripts/build_catalog.py", "data/canonical_url_health.json"],
  "outputs": ["data/canonical_url_health.json"],
  "pr_scope": ["data/canonical_url_health.json"],
  "gates": {"one_pending_draft": true, "direct_main": false, "auto_merge": false, "force_push": false},
  "http": {"method": "HEAD, then GET on method rejection or HEAD timeout", "stdlib_only": true, "credentials": "none, except optional GitHub token for repository-ID verification after a redirect", "user_agent": "distinct honest audit identifier, to be fixed in implementation"},
  "taxonomy": ["reachable", "redirect-permanent", "redirect-temporary", "client-error", "server-error", "blocked", "transport-error", "unknown"],
  "display": "none in version 1"
}
```

## Appendix B. Worked example, illustrative, from the documented rename ledger

This example is illustrative only. It is drawn from the rename ledger already documented in CONTRIBUTING.md, and it is not a fresh live observation. No URL was probed to write it.

A catalog URL `https://github.com/openremote/openremote` is swept. The probe records a 301 hop to `https://github.com/openremote/core`. The checker, with a token available, requests both repository API records and finds the same repository ID, `50994619`, in both. The evidence record states: status `redirect-permanent`, redirect chain with one 301 hop, GitHub identity verified, and a review note stating that a separate curated change is required before the catalog URL or history endpoint changes, and that the catalog name stays unchanged. The draft pull request for that sweep contains only the evidence record. Under the redirect triage rule in section 6, the sweep's draft report also states the triage class for this redirect, and any handover packet for a follow-up is a separate draft. The owner may then propose, in a separate draft, an identity update under the catalog rules, or a history record under the history contract, or no change. If the two repository IDs had differed, the record would state that plainly, identity would stay unverified, and no identity proposal would follow from that observation alone.

## Appendix C. Open questions for the owner

1. Cadence and pacing: is a weekly Tuesday full sweep, paced at 1.0 second per github.com request and 0.5 seconds per other host, the right starting point, or should the first sweep be paced more conservatively?
2. GitHub token: may the checker use the existing publisher token for repository-ID verification after a redirect, and only for that purpose?
3. User-Agent: what distinct honest identifier should the checker send? Fix it in the implementation, and record it in the contract, before the first live run.
4. Display: should the evidence file ever be displayed, for example as Observatory coverage, or should it remain a reviewer-only evidence file? No display work starts until that decision and its contract exist.
5. Runner: should this job run as a hosted assistant task, in the same style as the other enrichment jobs, or as a GitHub Actions workflow, in the style of the publisher? The contract is written to work under either, but the registration, permissions, and secrets differ, and the choice must be made before Phase 4.
