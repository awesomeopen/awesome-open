# Contributing

## Brand and design changes

Start with [the brand reference](brand/README.md), [agent instructions](AGENTS.md), and [maintenance procedure](brand/maintenance.md). Update affected rules, decisions and asset/skill provenance in the same PR; explain when a fix has no brand impact. Run `python3 scripts/check_brand.py` alongside the checks relevant to the change. Routine catalog/evidence refreshes keep their existing workflow.

## Reviewed deployment and installation

The website's eight-project setup pilot uses optional, source-reviewed `data/deployment_evidence.json`. Follow [the deployment evidence contract](site/DEPLOYMENT-EVIDENCE.md) for canonical identities, multi-valued run/install facts, qualified platforms/services/packages/requirements, provenance and review status. Missing facts remain unknown. This is distinct from Function summaries and does not change short descriptions or README output. Contributions stay review-only and must pass offline and browser checks; no new collection schedule or package execution is introduced.

## Scope

Awesome Open catalogs software projects whose names begin with **Open**. This naming convention is the sole defining criterion for inclusion. Capitalization, spacing, and punctuation do not alter eligibility: `OpenSomething`, `Open Something`, `openSomething`, and `Open-Something` are equivalent forms. Use the project's own spelling, and link to an official source that establishes its name and purpose.

The word must belong to the software's name. An organization named OpenSomething does not make all its products eligible, and describing software as “open source,” “open access,” or “open standards” does not qualify it. A documented expanded name qualifies when the project commonly uses an abbreviation, such as Open Broadcaster Software (OBS).

Licensing, source availability, pricing, popularity, maturity, and maintenance status are not admission criteria. Proprietary products, hosted services, libraries, command-line tools, and archived projects are welcome on the same terms. Inclusion records a name and function; it is not an endorsement or a claim that the software is open source.

## Evaluating projects for your needs

If you are looking for vetted open source software or production-ready open source tools, check each project's official sources for an OSI-approved license, recent commits or releases, clear documentation, and a setup path that fits your environment. Contributions verify the project's identity and basic description; production readiness and security require a separate assessment for your use case.

## Adding or updating an entry

1. Find the appropriate functional category in [README.source.md](README.source.md), or add one and update the three-column table of contents.
2. Add the project alphabetically, using its official name and website or canonical repository. Prefer the project's own brief description; shorten marketing copy to a factual sentence describing what it does.
3. Use the existing two-column format: **Project · Description**. Edit the source as plain Markdown: `| [OpenName](official-URL) | Brief factual description. |`. Do not add STATS/HN markers, statistics, charts, or bold project-name links; the renderer owns those. New GitHub entries without cached metrics render with no metrics or placeholder until the publisher fetches them. For other hosts or services, do not invent GitHub statistics or infer a license.
4. Repeat an entry in multiple categories when its functionality warrants it. Keep the name, link, description, and alternatives consistent across occurrences.
5. Run the tests and offline preview below, then check the rendered table, links, spelling, and category anchors. Include the official source in your pull request so the name and description can be verified. Commit the source and any reviewed evidence changes only; do not commit generated `README.md`, metrics snapshots, HN SVGs, or preview files in a content-only PR.

Corrections, additional categories, and newly discovered projects are welcome. There is no minimum star count, release age, or requirement to have used a project personally. Keep descriptions concise and omit promotional claims.

Contributions to this list are made under [CC0-1.0](LICENSE.md). Listed projects retain their own licenses.

## Reviewed project aliases

Use the optional [alias contract](site/PROJECT-ALIASES.md) for official expanded, abbreviated or alternate names. The curated display name can change without changing the canonical URL or stable project ID. Alias evidence is reviewed separately from HN attribution; search inclusion never grants HN matching permission.

## Alternatives

Keep the two-column table. When official evidence explicitly supports a relevant alternative, add `<br>Alternative to: [Name](official-evidence-URL), [Name](official-evidence-URL)` immediately after the existing description in `README.source.md`. Use one to three targets; omit the entire line when none is verified. Do not add generated markers, and do not rewrite the description to accommodate it. Entries without GitHub metadata may also use this format.

Link each target name to the project's official comparison, alternative statement, or migration guide, rather than a generic product homepage or third-party list. Record the canonical entry URL, target name, evidence URL, checked UTC date, and brief use-case scope in [`data/alternatives.json`](data/alternatives.json). Apply the same links to every category occurrence. Evidence establishes a relevant alternative, not feature parity, production suitability, or universal drop-in compatibility; migration caveats still apply.

Alternatives are curated manually. Discovery and accuracy checks remain review-only: proposed additions or corrections need review before changing the curated source or evidence. Neither collector nor the renderer populates alternatives. Tests validate link placement, evidence agreement, cross-category consistency, and preservation during metadata/chart regeneration.

## Source, previews, and publication

`README.source.md` is the human-editable catalog: introduction, table of contents, categories, links, descriptions, inline alternatives, and legend. `README.md` is generated. The sole renderer, `scripts/render_readme.py`, combines the source with `data/github_metrics.json` and `data/hn_evidence.json`, and writes README plus HN SVGs. It reuses the existing metadata and chart formatting functions.

The renderer also writes `assets/readme/specimen-count.svg` from distinct canonical catalog URLs (including non-GitHub projects), using the exact label “N specimen”. Cross-listed projects count once. This generated badge belongs to the existing publisher; do not hand-edit its number or include routine badge updates in source-only catalog PRs. Offline previews copy the local README banner and Browse badge alongside the generated count. See the [README badge contract](site/brand/README-BADGES.md).

For a contribution, run these network-free commands with Python 3.11 or newer:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/render_readme.py --output tmp/readme-preview/README.md
```

Open the generated Markdown with a Markdown viewer; the adjacent `assets/hn` directory keeps chart links intact. Pull requests run the same tests and upload a downloadable README preview artifact with its assets and a diff against the checked-in README. The checked-in README is expected to lag while a source-only PR is reviewed; checks validate the preview instead of requiring a clean README diff. New entries can be reviewed without network access or credentials. A missing metrics record omits statistics and ranking for that entry until collection attempts it. An explicit unavailable record instead displays unknown values and its failed-check status; it does not enter star rankings. HN identity-map-only edits use the previous cached evidence in an offline preview; their new matching rules take effect when the publisher refreshes evidence after merge. The snapshot's `as_of` UTC date controls last-push anniversary emphasis, so a preview is reproducible on any day. It is the collection-attempt date, not a claim that every metric was observed then. GitHub metrics schema v2 stores `status`, `last_success_at`, and `last_attempt` (`at`, `status`, `http_status`, `reason`) per repository. Schema v1 remains readable; its snapshot date is preserved at date-only precision when migrating cached observations. New observations and attempts use UTC timestamps. Unavailable records have null metric fields and null last success. Stale records keep every last-good metric and last-success date until recovery. A successful fetch clears the failure status and supplies the new success timestamp. Strict publication requires a record for every listed repository, including explicit unavailable records; ordinary previews still allow an uncollected missing record.

[Publish README and field guide](.github/workflows/update-stats.yml) is the single serialized publisher. It runs after relevant source/evidence/code merges or direct main commits, daily at 00:00 UTC, and on manual dispatch. Within one serialized job it fetches fresh `main`, collects metrics and (when needed) HN evidence, refreshes due optional website signals, renders, runs all tests and an offline reproduction check, then commits generated paths only. If main advances, it regenerates from the newest source before retrying an ordinary fast-forward push. It never force-pushes or writes curated source. A contributor's source commit reaches the generated README after publication succeeds, and the public website after its dependent Pages deployment succeeds.

The publisher performs its own verification before committing; it does not depend on a `GITHUB_TOKEN` push triggering another workflow. The collection/build job uses the existing `GITHUB_TOKEN` repository-content write permission. Only the separate `github-pages` deployment job has `pages: write` and `id-token: write`; it has no checkout or content-write permission. No personal token or new secret is required. Review any repository branch rules separately if they prevent bot pushes. Core collection fails closed on authentication, rate-limit, transport/server errors, invalid local or fetched data, and an all-repository HTTP 404 batch. An isolated repository HTTP 404 does not block healthy repositories: the collector reports each failure and keeps that repository’s last successful metrics and original observation date, marked stale. With no successful cache, its values remain unknown, marked unavailable; unknown stars are never zero. A 404 does not establish whether a repository was deleted, made private, renamed, or is inaccessible to the token. Both cases record the attempted UTC check, HTTP status, and neutral reason. README and website views expose stale/unavailable status; aggregates may include explicitly dated cached values and exclude unknown counts. No repository is removed. All records are validated before one atomic snapshot replacement; source or cache changes detected before replacement abort publication. The existing publisher remains the serialized writer; collection uses a private temporary file and does not lock out external editors. Ordinary upstream failures for optional website signals preserve their last-good evidence and do not prevent core README publication; corrupt local snapshots, invalid schemas, and identity mismatches still fail visibly.

Content-only contributions must never commit generated README updates. Renderer/schema migrations may establish or update generated output together with their implementation, as this initial migration does. External curation jobs must switch to the source only after this migration is merged: daily discovery reads/deduplicates and edits `README.source.md`; alternatives discovery and accuracy review edit the source plus `data/alternatives.json` in their reviewed draft PRs. All three use the offline preview above and leave generated paths to the publisher.

## Filterable website preview

The website is an additional generated view of the same curated source, not a second catalog to edit. `scripts/build_catalog.py` reads the source using the README renderer’s entry validation and alternatives parser. It combines reviewed alternatives and cached GitHub/HN evidence into stable URL-based project identities and category memberships. `scripts/build_site.py` generates complete HTML, `catalog.json`, local CSS/JavaScript, HN SVGs, and downloadable evidence. Both commands are offline and use only Python’s standard library.

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/render_readme.py --output tmp/readme-preview/README.md
python3 scripts/build_site.py --output tmp/site
python3 -m http.server 8000 --directory tmp/site
```

Open `http://localhost:8000` in your browser. You can also open `tmp/site/index.html` directly; search and filters use a compact embedded index and do not fetch JSON. Full project records and evidence remain in the rendered drawers and downloadable `catalog.json` (also embedded as a download in the standalone page). Keep generated files under the ignored `tmp/` directory; do not commit site output. To generate only the data, run `python3 scripts/build_catalog.py --output tmp/site/catalog.json`.

The initial page contains every distinct project, sorted by cached GitHub stars descending (unknown counts last), even with JavaScript disabled. Category links open the source sections without JavaScript. With JavaScript they filter the directory in place. Search covers names, descriptions, reviewed alternative names, and optional reviewed aliases. Alias matches use word boundaries; exact short reviewed names also use boundaries in ordinary fields to avoid incidental acronym matches. See the [alias contract](site/PROJECT-ALIASES.md). Category, detected SPDX license (including known/unknown), minimum stars, and an inclusive last-push UTC date can be combined. Results default to raw star count descending, with name and stable ID tie-breaks. Explicit `sort=name` and `sort=pushed` URL choices remain supported, and reset returns to stars. Results can sort by name, raw star count, or last push; unknown numeric/date values sort last and do not satisfy a numeric/date threshold. Filter changes are encoded in URL query parameters and restore with Back/Forward. A project’s `#project-…` permalink is based on its canonical URL, so a name change does not change its anchor.

Missing metadata and `NOASSERTION`/`OTHER` licenses remain unknown. Detected licenses are not independent legal review. Last-push dates are not “active” or “abandoned” labels, and stars are not quality rankings. No trending or lifecycle claims are inferred. Alternative evidence and HN chart semantics are unchanged from the README. Cross-listed projects retain every category; different projects sharing a name stay separate.

Python tests include a complete offline site build, preservation/count checks, safe escaping, asset/evidence links, and deterministic output. When Node is installed, they also run `node --test site/test_catalog.js` for browser-independent filter and URL-state logic. Browser checks should additionally cover combined filters, empty results, repeated clear, pending search followed by Back/Forward, keyboard navigation, narrow mobile layout, and the no-JavaScript fallback. Pull requests upload a `field-guide-preview` artifact as well as the README preview. They do not deploy; publication runs only from `main`. The PR workflow also installs the locked Playwright dependency with `npm ci --ignore-scripts` and Chromium with `npx --no-install playwright install --with-deps chromium`, serves that checkout’s generated `tmp/site` on loopback, and runs the existing `scripts/check_site_browser.cjs` smoke test. It uploads `field-guide-browser-screenshots` for 14 days: `desktop.png` (1440 × 1000), `mobile.png` (390 × 844), a dimension/revision manifest, and browser/server logs. Screenshots and logs are retained even when a later browser assertion fails; a failed run also attempts a `failure.png` of the failing state. The browser step fails the check on errors. It uses no production URL or deployment credentials. Only npm packages are cached by the lockfile; Chromium and its Linux dependencies are installed together on each runner.

For the same browser check locally, install those dependencies, serve the generated site as above, then run `SITE_URL=http://127.0.0.1:8000 npm run test:browser`. `CHROMIUM_PATH` can select an installed browser. Screenshots go under `tmp/site-qa/` with fixed viewports, pixel scale, light theme, reduced motion and loaded fonts. Browser QA is separate from the network-free unit suite; dependency installation requires network access.

### Genus Open field-guide edition

The website’s visual layer is a specimen ledger: split-prefix typography, native
`details` diagnostic drawers, URL-derived registry labels, and an original SVG
prefix study. Folio numbers are alphabetical positions within the generated
edition; they are not accession dates. Function categories are unchanged. No
lineage, motive, maintenance verdict, or license-sincerity classification is
inferred from the existing data.

Additional filters include exact reviewed-alternative names, presence of cached
GitHub metrics, and snapshot-relative repository-push windows. “Within 90 days”
is inclusive from snapshot minus 90 UTC days through the snapshot day. “More
than 2 years” means strictly before the two-calendar-year anniversary, with
February 29 clamped to February 28. These controls may be combined with the
existing inclusive date threshold. Unknown dates do not match either window.

Every build also emits `tmp/site/standalone.html`. It embeds CSS, the full
catalog, scripts, licensed Fraunces and Commit Mono fonts, HN charts, and downloadable evidence.
Open that single file in a browser for an offline preview without extracting
adjacent assets. External project and source links naturally require a network.
Some messaging-app attachment viewers disable JavaScript; download the file and
open it in a browser when that happens.

Fraunces and Commit Mono are included under SIL OFL 1.1; see `site/vendor/` for exact provenance.
The current ledger no longer ships GSAP or ScrollTrigger. The photographic hero
uses bounded local motion with pause and reduced-motion support; the standalone
export is a motion-free ledger. No runtime CDN or font requests are needed.
See [the brand reference](brand/README.md) for current design decisions;
`site/DESIGN.md` retains historical one-shot rationale.

### GitHub Pages publication

The public field guide is published at
[awesomeopen.github.io/awesome-open](https://awesomeopen.github.io/awesome-open/).
Repository Settings → Pages → Build and deployment must use **GitHub Actions**.
The workflow uses the `github-pages` environment and respects its existing
protection rules; it does not change repository settings or create credentials.

The existing publisher returns the exact accepted commit SHA, including when
README and snapshots are already current, and exports it as `published_sha`.
`scripts/build_published_site.py` fetches main, verifies that revision is on
main, creates a fresh detached worktree of that exact revision, and runs the
offline site builder there. It refuses a nonempty output directory to prevent
stale files entering the artifact. The site's revision records its actual build
inputs, never the workflow's older invoking checkout.

After collection, validation and a successful build, the same workflow uploads
`tmp/site` with `actions/upload-pages-artifact`. Its dependent Pages job deploys
that artifact, using only `pages: write` and `id-token: write`. The workflow's
existing concurrency lock spans publication, build, upload and deployment, so
another run cannot overtake it. Site and HN asset edits trigger this publisher
alongside source, evidence and code changes; daily and manual runs use the same
path. No second publisher or `GITHUB_TOKEN`-push-triggered workflow is needed.
A failure stops downstream deployment and leaves the previously deployed site
in place. If README publication succeeded but a later build/deployment failed,
README may be newer than the site; **re-run all jobs** after fixing the failure.
Deployment-only retries are rejected by a recorded run-attempt check, preventing
an old failed deployment from rolling back a newer published site. The deployment
artifact name includes the run attempt, so a full rerun cannot select or collide
with an earlier attempt's artifact. The deployment
summary links the accepted catalog revision; GitHub's deployment event may label
the earlier workflow-triggering revision instead.

Local previews can still omit `--source-sha`, which honestly labels the footer
“Local preview (revision not supplied)”. That flag alone records caller-supplied
provenance; only the publication helper verifies and checks out the revision.

## Automated metadata

Metadata is rendered as `<br><sub>creation-date -- last-push-date / SPDX-license / stars</sub>`. The first date is the GitHub repository creation date, and the second is its last push date, both in UTC. The last push date is wrapped in `<b>` once its 12-calendar-month anniversary is reached (inclusive, based on today in UTC; February 29 anniversaries use February 28 in non-leap years). Missing or unknown dates are not emphasized. The daily refresh reevaluates this threshold. These are repository dates, not original project launch dates or release dates. The license is the SPDX identifier detected by GitHub; unknown licenses (including `NOASSERTION` and `OTHER`) are omitted. Star counts use compact `k` and `m` notation. Projects hosted elsewhere have no generated metadata.

Only the three highest-starred GitHub repository name links within each category are bold. Categories with fewer than three eligible repositories highlight all of them; exact star-count ties use the lowercase canonical repository path alphabetically. Cross-listed projects are ranked separately in each category. Ranking uses the unrounded API count and never reorders entries. This highlighting is independent of HN chart coverage.

Edit descriptions only in `README.source.md`. To collect a new metrics snapshot, set `GH_TOKEN` and run `python3 scripts/update_stats.py`; this collector does not write README. Then run `python3 scripts/render_readme.py` to render it. The snapshot retains raw integer star counts, creation/last-push timestamps, and the API license identifier. Collection validates every record and replaces the snapshot atomically only after all requests succeed.

## Optional website evidence

`data/project_signals.json` holds optional GitHub release and OpenSSF Scorecard
evidence for the website. It is separate from core GitHub metrics and HN
evidence, and does not change README metadata, rankings, or admission rules.
Missing, unavailable, inconclusive, and stale results remain explicit; none
means that a project passed a check. Contributor concentration and packaging
signals are outside this implementation.

The release collector checks GitHub's designated latest published full release
using `GET /repos/{owner}/{repo}/releases/latest`. This excludes drafts and
prereleases and follows GitHub's selection semantics; it does not discover every
release channel, tag, or release hosted elsewhere. The displayed release date
comes from `published_at`, not `created_at` (which can describe the release
commit's date). The tag, official release link, and publication timestamp are
evidence to inspect, not a project-health score. An old release can be appropriate
for stable software, and an unavailable result does not establish abandonment.
See the [GitHub Releases REST API](https://docs.github.com/en/rest/releases/releases).

Scorecard evidence comes from the public precomputed
[OpenSSF Scorecard REST API](https://github.com/ossf/scorecard#scorecard-rest-api),
not a locally executed security audit. Keep the upstream scan date and version,
repository identity, source link, and available check results with the evidence.
A check score of `-1` is inconclusive and must not be displayed as zero or a
pass. Checks omitted by the API are not passed checks. In particular, the public
weekly scan may omit `CI-Tests`, `Contributors`, and `Dependency-Update-Tool`.
These automated heuristics do not establish that software is secure or suitable
for a particular use. Report the evidence and its limits rather than infer a
maintenance or security verdict.

`scripts/update_signals.py` checks due releases daily and successful Scorecard
evidence weekly. A missing Scorecard result is rechecked after 14 days; errors
are eligible again the next day, subject to provider backoff. Scorecard work is
staggered oldest-first, with at most 50 requests per
daily run; the 343-repository baseline can therefore be covered over seven daily
runs when requests succeed. Collection is serial, with a 300-second scheduling
budget (no new request starts after the deadline; socket timeouts are at most
10 seconds, so a slowly streamed in-flight response can overrun that budget) and a ceiling of 350 additional GitHub release requests per run. At that
baseline, the normal full daily GitHub budget is 343 core repository requests
plus 343 release requests, or 686 total, before retries or another publisher
attempt. Scorecard requests go to its separate public API. Budget exhaustion and
ordinary upstream failures defer optional work while retaining last-good data.
The existing `GH_TOKEN` is sent only to the official GitHub API; Scorecard needs
no new credential. No workflow, permissions, repository settings, or security
settings need to change.

The publisher runs the optional collector after core collection and before
rendering in its existing fresh-main detached worktree. It supplies
`--source-sha` from that worktree's `git rev-parse HEAD` on every attempt, so a
retry after a concurrent main update records the new source revision. This SHA
identifies the collection attempt, not a fresh observation of every cached
value. Retained last-good evidence keeps its successful fetch timestamp and
upstream identity; a failed refresh does not make old data fresh. Read the last
successful fetch time and upstream release/scan date separately from the most
recent attempt. A failed refresh makes retained evidence stale; otherwise,
release evidence becomes stale after three days without successful validation,
and Scorecard evidence becomes stale when its upstream scan is over 30 days
old. An old release publication date alone does not mark its cache stale. Only
the exact `data/project_signals.json` path joins the generated-file publication allowlist.
The collector refuses redirects without following them, forwarding credentials,
or remapping repository identities. A refused redirect marks that optional
observation unavailable (or retained evidence stale), logs the original project
for review, and does not block unrelated publication. Invalid 200-response
payload identities and schemas still fail before any snapshot is written.
The collector handles ordinary upstream outages itself; other nonzero exits
are not swallowed by the publisher. Offline tests and website builds read the
snapshot without making API requests.

The initial snapshot is a three-repository checked sample: three release
results, two Scorecard results, and one missing Scorecard result. The remaining
340 GitHub repositories are explicitly not checked; this is not a catalogue-wide
coverage estimate. The retained Scorecard sample preserves its retrieval date
with `day` precision rather than inventing exact fetch seconds. New collector
requests record second-precision attempt and fetch timestamps.


## Hacker News attention sparklines

Selected names have a clickable 120 × 24 static SVG below them, with matching alt and title text `HN discussions / 2y`. The image itself links to HN search; there is no extra discussion text link. Bars show deduplicated story submissions matching a verified project identity per UTC month over the last 24 **completed** months, oldest at left. All eligible charts use the same zero-based square-root vertical scale: bar height is `20 × sqrt(monthly count / shared monthly maximum)` pixels. The maximum is shared across all eligible projects and months, so equal counts have equal heights; the square-root transform makes low counts easier to see while preserving their ordering. This measures attention, including critical or controversial coverage, not endorsement, quality, votes, historical popularity, or sentiment.

Every distinct canonical URL in `README.source.md` enters the gradual HN collection queue. [`data/hn_projects.json`](data/hn_projects.json) supplies reviewed overrides, not an eligibility shortlist. Unreviewed entries match only their exact catalog URL or canonical GitHub repository path; their names, parent domains, redirects and alternate repositories are never guessed. This narrow URL-only coverage misses third-party coverage and must not be compared as comprehensive attention coverage. Broader domains and title aliases require review, especially for shared names. OpenClaw's assistant and the unrelated Captain Claw reimplementation remain separate; OpenCode's Anomaly/SST agent and the former `opencode-ai/opencode` project remain separate.

The generated [`data/hn_evidence.json`](data/hn_evidence.json) records exact windows, monthly counts, accepted/excluded story IDs, titles, URLs, identity reasons, API query sources, eligibility and queue state. Its current-window `projects` view remains compatible with offline renderers; `queue` retains each last-good collection, attempt status/time and incomplete query pages. A chart still requires six matching stories across three months. Missing charts can mean unattempted URL-only coverage, incomplete collection, an old window, sparse history or uncertain identity. Absence is not proof of no discussion.

Queries use Algolia `search_by_date`, `tags=story`, `restrictSearchableAttributes=title,url`, disabled typo tolerance, and the same 24 completed UTC months. Candidate discovery and acceptance are separate: the union of queries is filtered by parsed official URL boundaries, exact reviewed URLs or permitted title alias/context, then deduplicated by HN story ID. Comparisons, integrations and critical third-party coverage can count when they identify the right project. Body-only and comment-only mentions are outside this metric. The clickable HN link is a broad name search with the same date window, not a reproduction of the audited accepted set; use the downloadable evidence for exact inclusion decisions.

The existing daily serialized publisher advances the queue without credentials, new permissions or another schedule. Defaults cap collection at **50 project attempts and 160 HTTP attempts per UTC day**, with a five-minute collection budget per invocation (an in-flight request can take up to 15 additional seconds). Both daily counters and the attempted identities persist in the evidence snapshot and the shared invocation guard, so repeated publisher runs and same-job main-branch retries do not reset them. Each project is attempted at most once per UTC day, including forced refreshes; its continuation or failed retry resumes on a later day. A project attempt is charged only when its first new HTTP request is about to start. Fresh-cache skips and work deferred before its first request consume neither counter. Ordinary failures do consume both attempt budgets. Legacy request-only guards are migrated conservatively by charging one project attempt per used request for that day.

Requests remain serial, spaced by 0.5 seconds, with at most 24 new pages for one project in a daily attempt. While other work is waiting, a project also yields after 90 seconds (or one third of a deliberately smaller invocation budget), plus any in-flight request timeout; this lets later lanes run despite slow pagination. HTTP 429/403 pauses further requests for the UTC day. Collection stops before starting a request on a new UTC day; the next invocation starts that day's budget. These limits are deliberately below the [public API's documented 10,000 requests/hour/IP limit](https://hn.algolia.com/api). The durable daily counters are the last successfully published snapshot; a workflow terminated before publication can lose its uncommitted counters, while the invocation guard protects retries within that job. This is bounded serialized collection, not an external cross-job rate-limiter service.

The scheduler interleaves three lanes and reserves capacity for each while it has eligible work: **20 new projects / 64 requests**, **25 refresh or retry projects / 80 requests**, and **5 continuations / 16 requests** per UTC day. Empty lanes lend their unused capacity to the others. Request reservations are released when a lane cannot use further project slots. New, never-attempted backlog entries are sorted by cached GitHub stars descending; known zero precedes unknown, with canonical URL as a deterministic tie-breaker. No extra GitHub request is made for prioritization. Failed first attempts move to the oldest-attempt refresh/retry lane instead of repeatedly blocking lower-star new entries. Refreshes and continuations rotate by oldest attempt; changed reviewed identities retain first-attempt priority within refresh work.

Successful collections become due after 30 days, a month-window change or an identity change; this is a due threshold, not a refresh guarantee. At the ideal maximum of 50 completed projects per day, 509 projects need at least 11 daily runs for a full pass; refresh reservations, pagination, failures and new entries can extend this. A reserved 25 refresh slots per day is above the approximately 17 needed to revisit a 509-project catalog over 30 days, assuming enough requests and runtime. Partial pages are checkpointed and replayed without another request; they are discarded if the identity or target window changes. Queries page fully and split time intervals before Algolia's 1,000-hit cap; incomplete counts are never published as complete.

Only completed project collections replace last-good evidence. Ordinary upstream failures preserve that evidence and partial progress while healthy projects continue. Corrupt local queue data still fails visibly. Cached results from a different window or identity stay retained but are withheld from current charts. Same-window last-good results remain available after a failed refresh, with retrieval and attempt status in the evidence. Checkpoints are atomically written after each attempted project; the existing publisher owns committing generated evidence. Run `python3 scripts/update_hn.py --refresh` to mark everything due, still within the same budgets, then `python3 scripts/render_readme.py` to render offline. Do not edit generated HN markers or SVGs manually.

The publisher never force-pushes. If another contributor or automation updates main during collection, it regenerates against the new branch tip rather than overwriting concurrent edits. Completed observations carry forward in the archive; current caches and curated input are rebuilt from fresh main.

## Reviewed Function summaries

After discovery accepts a project, follow [the Function summary handoff](site/FUNCTION-SUMMARIES.md) to add a sourced 40–80-word explanation to `data/function_summaries.json` in the same review-only PR. Keep the short description in `README.source.md`. Only approved summaries render; missing or unverified entries use the short-description fallback. The existing website build consumes this curated file offline. Do not scrape or generate prose during publishing.

## Cached GitHub star history

Expanded website cards can pair GitHub stars with existing HN charts. The README and its HN sparklines are unchanged. `data/star_history_projects.json` schema 2 selects `catalog_github`: every exact canonical GitHub repository in `README.source.md`, deduplicated across categories. New source entries join automatically; removals leave the cache on the next refresh. Schema 1 explicit lists remain readable for fixtures or scoped manual runs. Website-only URLs are not guessed into repository mappings. Non-GitHub entries and uncollected histories are omitted, not assigned zeros.

`python3 scripts/update_star_history.py --source-sha <full-sha>` uses GitHub's [privacy-safe aggregate history endpoint](https://docs.github.com/en/rest/activity/starring#get-repository-star-history), never lists individual stargazers. Its generated `data/star_history.json` belongs to the existing main publisher, alongside other snapshots. Do not hand-edit or fabricate production evidence. Site builds consume the cache without network access and generate local SVG assets; the downloadable standalone page embeds both SVG and evidence JSON.

The 24 completed calendar-month positions reuse the HN window. GitHub supplies daily bins whose boundaries are not guaranteed UTC, so attribution near a month edge is approximate. The measurement is stars created in each month that remain at the last successful fetch, not a historical total or gross new stars. Fewer stars do not establish lost users, falling sentiment, or cause-and-effect with HN coverage. Charts use the same 120×24 bar geometry as HN, with independent square-root count scales explicitly labeled. HN remains in story units; GitHub stays in star units.

Collection remains bounded to 16 HTTP attempts per UTC day in the published cache and four repositories per run. Every page and retry spends that budget. Never-attempted repositories come first, ordered by cached current star count descending; unknown counts follow real zero counts, with canonical repository IDs breaking ties. No extra request is used to rank them. Existing `checked_at` timestamps are the durable progress cursor, including unsuccessful attempts. Once attempted, repositories rotate by oldest attempt first, with star count and repository ID breaking ties. This prevents popular failures or repeated refreshes from blocking the finite unseen backlog. Newly added repositories enter the unseen queue. A continuously growing unseen backlog can postpone refreshes; this policy deliberately favors initial coverage, rather than promising both immediate backfill and frequent refreshes under a fixed budget.

Successful windows become eligible after 14 days or a month-window change; this is a due threshold, not a refresh guarantee. At approximately four pages per repository, 16 daily attempts complete at most four full histories per day. A 456-repository first pass therefore takes roughly 114 healthy daily runs, and a later full refresh rotation has a similar bound; retries, failures, new entries and longer responses can extend it. Month rollover does not reset progress. Charts whose cached month window no longer matches HN remain withheld until aligned, so many older histories may be temporarily unavailable under this small budget. Existing last-good evidence remains retained. The cache records eligible, due, attempted and never-attempted counts in `selection_report`.

Current total star counts are already maintained by the separate ordinary repository-metadata collector. These 16 calls collect the optional 24-month history, not those totals. No workflow, schedule, permission, credential or endpoint changes are introduced. This is a healthy-run budget, not a guarantee against other jobs or upstream limits. A shared, checkpointed invocation budget survives publisher worktree retries; an entirely failed job cannot persist its daily state to main, so this is not a cross-job global rate-limit ledger. The collector also respects rate-limit exhaustion.

Only complete, validated history becomes a last-good result. Missing pages, contradictory totals, HTTP failures, rate limits, or unavailable data retain prior evidence and expose status and retrieval time. A last-good chart may remain visibly stale when its month window still matches HN; mismatched windows are withheld rather than silently overlaid. SVGs are generated in preview/Pages output, not tracked. Test fixtures are synthetic and isolated from production cache.

### Reviewed repository renames

The aggregate-history collector has explicit, code-reviewed endpoint mappings:
`openremote/openremote` → `openremote/core`. On 2026-10-16 the
[old repository API path](https://api.github.com/repos/openremote/openremote)
reported a move to GitHub repository ID `50994619`, and the
[current repository API record](https://api.github.com/repos/openremote/core)
reported that same ID.

`openomsi-project/openomsi` → `openomsi-org/openomsi` was verified on 2026-10-17:
the [old repository API path](https://api.github.com/repos/openomsi-project/openomsi)
reported a move to repository ID `1391454845`, and the
[current repository API record](https://api.github.com/repos/openOMSI-org/openOMSI)
reports that same ID as `openOMSI-org/openOMSI`. The endpoint mapping uses the
collector's normalized lowercase spelling.

These mappings are in `REVIEWED_REPOSITORY_RENAMES` in
`scripts/update_star_history.py`; they apply to ordinary history collection and
the bounded backfill. They add no request or permission.

The catalog URL, project permalink, cache key, curated records and archived
observations remain under the existing identity. New histories record their
actual mapped source URLs. Previously collected evidence remains
valid with its original URLs and fetch dates; failed refreshes do not rewrite
those sources. A single history cannot mix old/new endpoints across pages or
borrow an unreviewed repository's evidence. This mapping does not change other
collectors. Further renames require independent identity verification and review;
both history transports still refuse redirects without following them.

## Observatory snapshot

The site build also creates `/observatory/` from the same validated catalog and
source revision. See [the observatory contract](site/OBSERVATORY.md) for counting,
coverage, date boundaries and export semantics. Do not add collectors, inferred
quality scores or history by changing this presentation layer. The route's compact
runtime index deliberately excludes full prose, artwork payloads and raw provider
checks. Its standalone report and CSV are generated artifacts, not authored files.

The star-history collector queries its separate history endpoint and does not turn cached star totals into new observations. It uses repository creation metadata only to bound historical coverage; unavailable creation dates remain unknown. Repository metadata collection does not write history snapshots or manufacture fresh history points.

### One-time fast star-history backfill

The publisher's manual `history_backfill` input is an opt-in, bounded chunk,
not a recurring schedule. Merge its dependency (PR #67, catalog-wide eligibility)
and this change before dispatching it on `main`. Keep the default input false
for ordinary publication; the normal 16-attempt daily history budget is unchanged.

Fast mode uses only the existing `GITHUB_TOKEN`, requests aggregate history
sequentially, and skips repositories already carrying a validated window for the
current 24 complete months. Each chunk has a 15-minute collection deadline,
a 900-request ceiling, and a live quota floor reserving one core metadata request per eligible repository,
350 optional release attempts, 16 normal history attempts, and 20 requests of
overhead (842 for 456 repositories). This reserves a healthy normal publishing
sweep; unexpected retries or unrelated simultaneous API use can still consume
shared quota. Quota headers and bounded
Retry-After/secondary-limit backoff control pacing. Authentication, unexpected
HTTP responses and invalid transport data stop the chunk for review. Incomplete
repository coverage is recorded separately while independent repositories continue.
No individual stargazer records, personal tokens, cookies, or new permissions are used.

The existing `publish-readme-main` concurrency group remains the single writer.
Every completed repository is atomically saved under `tmp/history-backfill/`.
Batches of at most 20 successful repositories are validated by the full offline
suite, merged with fresh main's eligible identities and newer evidence, and pushed
with ordinary fast-forward checks. Curated source, metadata, the daily history
budget and unrelated files are never replaced. Failed validation never publishes
that batch. A successful or time/quota-limited chunk then renders validated cached
snapshots without repeating core API collection and uses the existing Pages flow.

The run summary/checkpoint reports complete, partial or blocked, remaining
repositories, request count, the live quota reset time and `resume_after` (also
respecting Retry-After). Repository failures also report the catalog repository,
the allowlisted request URL and HTTP status when available, and a locally defined
reason. The checkpoint's `failures` list retains these details, including coverage
failures that allow other repositories to continue. Authentication and refused
redirects have distinct reasons. Response bodies, redirect destinations, tokens,
headers and raw transport exceptions are never included. For partial work, wait until `resume_after`, then dispatch
another chunk; successful
remote checkpoints are skipped automatically. Do not repeatedly dispatch a blocked
run without reviewing its reason. There is no self-dispatch loop, paid idle quota
wait, or permanent schedule to remove. The parent/requester coordinates the finite
continuations and stops when all eligible histories are complete or remaining
repositories need review. The normal publisher keeps its existing fail-closed safety checks.

An `always()` artifact step retains the per-repository checkpoint for 14 days,
including failures and ordinary cancellation when Actions still permits cleanup.
A hard runner termination can prevent upload; at most the unfinished batch then
needs recollection, while previously pushed batches remain durable. If a push
failed, the artifact is recovery evidence: validate its complete records against
current main and current eligibility before any manual import. Never overwrite
main with the artifact snapshot or bypass branch rules. This implementation does
not automatically trust/import artifacts; ordinary redispatch safely recollects
any uncommitted records. The workflow's total backfill job bound is 45 minutes,
including validation/build. No backfill is activated by opening or merging a PR.

## Retaining collected chart evidence

Completed HN and GitHub-star collections are retained in
[`data/chart_observations.json`](data/chart_observations.json), independently of
the current two-year display caches. See the [observation archive contract](site/CHART-OBSERVATIONS.md)
for immutable dates/identity revisions, raw-evidence deduplication, bounded Git
recovery, and publication/crash boundaries. Successful refreshes do not overwrite
previous observations. Star buckets remain retained-at-fetch measurements, never
historical totals. No selector, new schedule or historical API crawl is added.
