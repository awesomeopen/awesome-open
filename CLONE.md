# Clone Awesome Open\*

Awesome Open\* can be reused as the starting point for an **Awesome Something**
list: a curated Markdown catalog, evidence snapshots, a searchable static site,
an Observatory, and a serialized publisher. It currently requires source edits.
There is no general-purpose configuration file or one-command list initializer.

This document has two halves. Part I records the current reuse proposal and its
trade-offs. Part II is the setup checklist to retain once the adaptation work is
implemented and tested. No configuration, automation runner, or second catalog
is introduced by this document. Source audit: `32eba2f`, 2026-10-14.

## Part I — Reuse proposal

### What is reusable now

- `README.source.md` owns names, official URLs, descriptions, categories and
  reviewed alternatives. The parser accepts arbitrary project names; the Open
  prefix is the editorial policy in `CONTRIBUTING.md`.
- Categories come from Markdown headings. Canonical URLs establish record
  identities; cross-listed entries keep their category memberships.
- Cached GitHub/HN data, reviewed evidence and source content feed deterministic
  README, catalog JSON, website and static record outputs.
- The site includes search, combined filters, permalinks, evidence drawers,
  accessible fallbacks and an aggregate Observatory.
- Offline tests, browser checks, preview artifacts, brand integrity and a
  single-writer publisher already live in the repository.

The domain-specific parts remain coupled to Awesome Open\*: wording and URLs,
seven named hero specimens, category artwork, reviewed project mappings, and
tests tied to the current catalog. Replacing the Markdown alone is insufficient
for a complete production build.

### First changes worth making

1. **One configuration file.** Extract repeated list identity and deployment
   values first. Proposed fields: display name, naming rule, description,
   repository URL, public site URL, support URL, source path, featured record
   IDs, category artwork mapping, and enabled optional evidence modules.
   Validate it once and consume it in README/site/Observatory builders and
   tests. Keep evidence in its existing typed files. A proposed filename such
   as `catalog.config.json` is not recognized by current code.
2. **This setup guide.** Keep a tested sequence with exact inputs, commands,
   known adaptation points, permissions and publication checks. Verify it using
   a small second list before claiming template support.
3. **Small sample later, if useful.** A reviewed Closed\* example would exercise
   different names, hosted services, open-source libraries, duplicate names and
   old repositories. Keep it small; a second maintained production catalog is
   unnecessary for testing portability.
4. **Separate fixtures only when they block reuse.** Catalog-specific visual
   assertions should eventually use explicit fixtures or configurable inputs.
   Preserve parser/evidence/publisher regression coverage. Avoid a broad engine
   extraction merely to make the repository look generic.

Develop these changes incrementally in this repository. A schema, package,
plugin system or compatibility promise should follow demonstrated reuse needs.

### Comparable repository systems

Checked 2026-10-14. These five systems are ranked for a Git-backed software
catalog with automated refresh and static publishing. This is a fit judgment,
not a benchmark or an exhaustive market ranking. Criteria, in order: reusable
setup/structured source, repeatable enrichment/traceability, submission/review,
then browsing/outputs. Stars do not determine rank. Claims reflect inspected
documentation; undocumented features may still exist.

| Rank / system | Setup and source | Automation and review | Outputs | Compared with Awesome Open\* |
| --- | --- | --- | --- | --- |
| 1. [awesome-selfhosted-data](https://github.com/awesome-selfhosted/awesome-selfhosted-data) + [hecat](https://github.com/nodiscc/hecat) | Per-project YAML; separate tags, platforms and licenses; adaptable Python pipeline | GitHub/GitLab enrichment, consistency/dead-link checks and [PR curation](https://github.com/awesome-selfhosted/awesome-selfhosted-data/blob/master/CONTRIBUTING.md) | README and multipage Sphinx HTML; hecat also supports HTML tables | Closest data-to-publication reference; self-hosted-specific schema and presentation need adaptation. Data: CC BY-SA 3.0; hecat: GPL-3.0 |
| 2. [best-of-generator](https://github.com/best-of-lists/best-of-generator) | YAML projects/categories/labels, CLI, GitHub Action and [setup guide](https://github.com/best-of-lists/best-of/blob/main/create-best-of-list.md) | GitHub/package metrics, scheduled updates, trends and CSV history; maintainer-supplied projects | Ranked Markdown and metadata history | Easier metrics-backed README setup; reviewed narrative evidence and a full interactive site are outside its documented core. [GPL-3.0](https://github.com/best-of-lists/best-of-generator/blob/main/LICENSE) |
| 3. [awesome-list-site](https://github.com/krzemienski/awesome-list-site) | React/Express/PostgreSQL; structured resources, three-level categories and list import | Approval/edit queues, audit trail, link checks, GitHub sync and Claude enrichment | Fuzzy search, bookmarks, learning journeys, admin UI and Markdown export | Broad in-app curation; more infrastructure than a static list. AI enrichment needs Anthropic access; supplied content/branding is video-specific. MIT |
| 4. [openawesome](https://github.com/chenz24/openawesome) | Next.js/PostgreSQL; projects, lists, alternatives, tags/stacks; seed/migration/Docker setup | Authenticated editing and GitHub-issue suggestions; comparable scheduled evidence enrichment not established by README | Search/filtering, project pages, English/Chinese routes, RSS | Ready-made directory application; database and admin OAuth setup required. Equivalent static evidence/refresh pipeline not documented. AGPL-3.0-or-later |
| 5. [Minted Directory Astro](https://github.com/masterkram/minted-directory-astro) | GitHub template; Markdown/frontmatter, JSON and CSV; Astro | File-based editing; comparable software-metadata enrichment/review queue not documented | Tags, search, directory components, themes and static output | Simple site-first starting point with less maintenance machinery. README has conflicting content-folder paths and empty Notion/Airtable setup sections; verify integrations. MIT |
| Baseline: Awesome Open\* | Markdown source, canonical-URL identities; manual theme/category/fixture adaptation | Daily GitHub refresh, bounded star history, reviewed-identity HN data, evidence records and PR browser QA | README, searchable site, Observatory, static record pages and data exports | Evidence-rich static workflow; not yet a turnkey template. External curation and assistant-operated jobs are not inherited by cloning |

Use awesome-selfhosted-data/hecat as the maintenance-pipeline reference,
best-of-generator for a metrics-backed README, and Minted for a small static
directory. Choose either database-backed application when in-app administration
justifies its services. Reuse Awesome Open\* when its evidence model and
presentation fit and manual adaptation is acceptable.

[generator-awesome-list](https://github.com/dar5hak/generator-awesome-list) was
also considered: GitHub marks it archived on 2026-07-01, and its documented scope
is Markdown/contribution scaffolding. The five ranked repositories showed no
archive banner when checked.

### Optional convention checks: awesome-lint

[awesome-lint](https://github.com/sindresorhus/awesome-lint) belongs alongside
these systems as an optional Markdown/Awesome-convention linter. It does not
provide catalog discovery, evidence enrichment or site generation, so it does
not replace a system in the ranking. Checked upstream `4f870ab`, 2026-10-14;
source review only.

Its [default configuration](https://github.com/sindresorhus/awesome-lint/blob/4f870abda373cfa18c67822c39ee29c451ae8a70/config.js)
enables GFM tables and checks table formatting. Our two-column catalog is not
inherently unsupported, but the
[`awesome-list-item` rule](https://github.com/sindresorhus/awesome-lint/blob/4f870abda373cfa18c67822c39ee29c451ae8a70/rules/list-item.js)
checks list nodes, not table rows: it would not validate our entry-description
conventions. Keep the existing parser and evidence tests.

There is no blanket HTML or image ban in that configuration. The
[`awesome-no-ci-badge` rule](https://github.com/sindresorhus/awesome-lint/blob/4f870abda373cfa18c67822c39ee29c451ae8a70/rules/no-ci-badge.js)
targets image titles containing `build status`, `travis` or `circleci`, and image
URLs containing Travis/CircleCI; it does not prohibit our HN images merely
because they are images. This does not establish that the whole generated
README passes. HTML metrics and HN counts still need our renderer/evidence
checks, which a convention linter cannot replace.

For a future trial, target `README.source.md` explicitly; a default invocation
finds the README, which here is generated. The
[documented API](https://github.com/sindresorhus/awesome-lint/blob/4f870abda373cfa18c67822c39ee29c451ae8a70/readme.md#api)
accepts `filename` and a custom remark-plugin `config`. Prefer a reviewed
configuration for intentional catalog differences. Upstream also documents
HTML-comment `lint disable`, `lint enable` and next-node `lint ignore`
directives; these are non-rendered comments, not visible catalog prose. Do not
hand-edit generated output to suppress warnings. The default
[Contents rule](https://github.com/sindresorhus/awesome-lint/blob/4f870abda373cfa18c67822c39ee29c451ae8a70/rules/toc.js)
only activates for `## Contents` and expects a list there; our three-column
`## Table of Contents` falls outside that check. Keep our own anchor checks
rather than assuming the linter validates this navigation.

Start with a pinned-version, advisory-only trial after reviewing its selected
rules and results on the source and a disposable rendered preview. Keep
repository-specific validation authoritative. No package, lint configuration,
workflow or required status check is added by this proposal.

### A Closed\* trial catalog

Use software whose own name begins with **Closed**, ignoring case, spaces and
punctuation, as the trial rule. This tests a naming rule that is independent of
license or source availability. Verify each identity independently; similar
names do not establish a relationship.

Verified from official pages/repositories on 2026-10-14:

| Candidate | Function and useful test case |
| --- | --- |
| [Closed Caption Creator](https://www.closedcaptioncreator.com/) | Desktop/web software to create, edit, translate and review post-production captions/subtitles; hosted/commercial identity without invented GitHub statistics |
| [Closedloop.ai](https://www.closedloop.ai/) | Team agentic software development, with web control plane, desktop client and Claude Code plugins in its [current documentation](https://www.closedloop.ai/docs); do not reuse older healthcare descriptions |
| [ClosedXML](https://github.com/ClosedXML/ClosedXML) | .NET library to read, modify and write `.xlsx`/`.xlsm` files without Excel; [documentation](https://docs.closedxml.io/en/latest/) |
| [Closed AI](https://github.com/closedai-project/closedai) | Self-hosted OpenAI-compatible server using open models; README describes a drop-in API and marks it work in progress |
| [Closedverse](https://github.com/ariankordi/closedverse) | Python/Django Miiverse clone; README explicitly references PF2M's Openverse, not the unrelated media-search project |
| [ClosedSea](https://github.com/Vectorized/closedsea) | Solidity library for OpenSea-style NFT operator filtering associated with royalties; a library, not an NFT marketplace |
| [ClosedLoopDriver](https://github.com/neuroprod/ClosedLoopDriver) | Arduino closed-loop stepper-motor code; one observed default-branch root commit, dated [2015-02-05](https://github.com/neuroprod/ClosedLoopDriver/commit/772f2c2532da8256b342ae3ab042e05c3bb019be), useful for sparse-history/unknown-license display |

The additional “ClosedLoop” lead is ambiguous. Distinct possibilities include
[ClosedLoop at closedloop.sh](https://closedloop.sh/), which extracts product
insights from customer conversations, tickets and surveys, and
[Closed-Loop EEG Neurofeedback System](https://github.com/gretatuckute/ClosedLoop),
a real-time Python research framework. Neither is selected here as the intended
lead; keep their identities separate from Closedloop.ai.

[Close CRM](https://www.close.com/crm) is a sales CRM with calling, email, SMS,
pipelines and automation. **Close** does not begin with **Closed**. Exclude it
from the strict trial or document a deliberate exception; do not silently widen
the naming rule.

This is a candidate set. Preserve the
projects' own spellings and factual functions. Do not infer that a project mocks
another product from its name, or call an old repository abandoned from a date.

### An Awesome Anything trial catalog

**Awesome Anything** is another worthwhile list alongside Closed\*: a showcase
of the recurring **Anything** naming pattern in software. A proposed rule is to
match official names containing Anything, including joined words and case/spacing
variants, while preserving each project's own spelling.

Official examples checked 2026-10-14:
[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm),
[REA — Reverse Engineer Anything](https://github.com/morluto/rea), and
[RSI-Anything](https://github.com/Gen-Verse/RSI-Anything), a framework for recursive
self-improvement using world-model predictions and interaction feedback.
The lead “LLManything” still needs an exact official identity; do not silently
equate it with AnythingLLM or count it as a separate project.
Research the emerging naming-trend idea before making claims about its growth.
This is a list proposal, with no catalog entries or implementation added here.

### Put assistant-assisted workflows in the repository

The repository can hold the public specification of a task even when its runner
lives elsewhere. Author portable, user-owned task instructions from the public
catalog policy. Do not export an assistant's private configuration, conversation
history, credentials or internal instructions.

The current [automation inventory](automation/README.md) records the five hosted
tasks, their nominal cadences, public operating contracts and review boundaries.
It also distinguishes the GitHub publisher. It is documentation only: no runner,
scheduler registration or portable executable tooling is included.

The remaining portable layout is **future work**:

```text
automation/
  README.md                 # present: dated operating inventory and ownership
  discovery.md              # inclusion, deduplication and candidate contract
  alternatives.md           # official comparison evidence contract
  accuracy.md               # identity, description and evidence recheck
  function-summaries.md      # reviewed capability summaries and source links
  artwork.md                # source review, provenance and visual approval
  schedules.example.json    # desired cadence/timezone; no live registration
  schemas/                  # versioned candidate/run-report contracts, later
```

Each task specification should record:

| Field | Required content |
| --- | --- |
| Goal and scope | Source files, eligible projects, allowed source types, bounded work budget |
| Inputs | Repository/ref, naming policy, existing records and evidence contracts |
| Method | Search guidance, canonical-URL deduplication, official-source verification, ambiguity handling |
| Output | Candidate or correction, source URLs, checked UTC date, evidence excerpt/summary, affected paths, unresolved questions |
| Review | Explicit write authorization, factual checks and exact tested revision; draft PR/maintainer approval by default, no automatic merge. The current discovery-only direct-source exception is recorded in the inventory and is not inherited by clones |
| Schedule | Proposed timezone/cadence and manual trigger; operator explicitly installs/enables it |
| Failure | Rate limits, stale/unknown data, last-good preservation, retry budget and visible failure report |
| Run record | Start/end time, input revision, task-spec version, changed files, checks and PR URL |

A portable discovery instruction can say: “Read `AGENTS.md`, `CONTRIBUTING.md`
and the relevant evidence contract. Find eligible software absent from the
catalog. Verify its name and function from official sources. Return deduplicated
candidates with URLs and checked dates. Propose curated edits in a draft PR;
leave generated outputs to the publisher.” This defines work another operator
can run without inheriting anyone else's account access.

Extend the inventory into approved portable task specifications and examples
before adding a thin CLI or GitHub Actions adapter with dry-run output, schema
validation, bounded retries, tests and draft-PR creation. A scheduler, runner and model provider can change
without changing the evidence/review contract.

Keep accounts, repository grants, service connections, model-provider billing,
secrets, credentials and actual scheduler registrations outside Git. Document
the permission names and setup steps; never their values. Review grants under
the new owner's account. A copied schedule file does not activate a job, and
`AGENTS.md` does not start an agent.

### What GitHub Actions already does

| Workflow | Current behavior |
| --- | --- |
| [Brand integrity](.github/workflows/check-brand.yml) | Validates assets, pinned skills and reference files; flags design changes lacking documentation |
| [Source and preview checks](.github/workflows/check-updaters.yml) | Runs offline tests, renders README/site previews, checks Chromium behavior and uploads review artifacts; pull requests that change only documentation or brand records skip it |
| [Publisher](.github/workflows/update-stats.yml) | On relevant `main` changes, daily at 00:00 UTC, or manual dispatch: fetches current `main`, refreshes metrics/HN/due optional signals and star history, validates, commits generated paths, builds the accepted revision and deploys Pages |

The publisher serializes runs and retries against fresh `main` when another
commit lands. Core collection errors stop publication; optional upstream errors
can retain last-good evidence under their contracts. It never discovers catalog
entries, authors reviewed alternatives, approves artwork, or merges curation PRs.

The collection job uses the built-in `GITHUB_TOKEN` with `contents: write`.
The separate deployment job uses `pages: write` and `id-token: write` with the
`github-pages` environment. Current workflows require no custom AI secret or
personal access token. Repository rules may still prevent bot writes.

A clone copies workflow files and public task descriptions. It does not copy
enabled schedules, repository settings, branch rules, environments' protection
settings, secrets, external runner connections, paid accounts, approval grants,
or another maintainer's assistant-operated jobs.

## Part II — Set up your own Awesome Something list

This is the current source-adaptation route. Steps 4–6 require code/data changes
until configuration support exists. Keep publication disabled until checks pass.

### 1. Create your repository

Fork or copy this repository into one you control. Review copied Actions before
enabling schedules. Keep `main` unless adapting the publisher too. Clone your
remote, create a branch and record the baseline:

```sh
git clone https://github.com/YOUR-OWNER/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
git switch -c setup/my-list
git rev-parse HEAD
git remote -v
```

Review [LICENSE.md](LICENSE.md), vendored licenses and asset provenance. The list
is CC0; retain applicable third-party notices and review asset rights.

### 2. Check the baseline

Read [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md) and
[brand/README.md](brand/README.md). Use Python 3.11+; CI uses Python 3.12 and
Node 22. Run these before and after adaptation:

```sh
python3 scripts/check_brand.py
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/render_readme.py --output tmp/readme-preview/README.md
python3 scripts/build_site.py --output tmp/site --production
```

### 3. Write your policy and catalog

Replace the Open-prefix policy in `CONTRIBUTING.md`, the PR template and relevant
brand foundation text. State exceptions explicitly; Close CRM is outside a
strict Closed-prefix rule. Edit `README.source.md`, including its title, table
of contents, category headings and alphabetized two-column tables:

```markdown
| Project | Description |
| --- | --- |
| [ClosedXML](https://github.com/ClosedXML/ClosedXML) | .NET library for reading and writing Excel files. |
```

Keep anchors and cross-listed descriptions consistent. Use official URLs. Leave
metrics and generated `README.md` to the publisher.

### 4. Adapt identity, artwork and fixed assumptions

No config switch exists yet. Locate identity references with:

```sh
git grep -n -E 'awesomeopen|awesome-open|Awesome Open|Genus Open|buymeacoffee'
```

- Update repository/public/support links, titles and offline URLs in
  `scripts/build_site.py`, `scripts/build_observatory.py` and relevant previews.
  Do not bulk-replace names inside upstream evidence or historical records.
- Adapt `scripts/build_jar_preview.py`: `DISPLAY` requires seven named Open
  records. Replace its selection/artwork or implement and test a no-hero mode
  before production builds. Adapt other fixture-specific preview selections.
- Replace prefix styling, logos, category-art mappings and catalog-specific
  assertions, including the 21-category tests in `scripts/test_category_art.py`.
  Preserve generic parser, evidence, accessibility and publisher coverage.
- Update the fork's brand/provenance documents and intentional inventories.
  `scripts/check_brand.py --refresh` updates hashes, not approval status.

### 5. Reconcile evidence

Replace project identities in `data/hn_projects.json` and
`data/star_history_projects.json`. Review alternatives, function summaries,
deployment evidence and specimen-art mappings against their `site/` contracts.
Remove unrelated evidence; never relabel another project's facts. Regenerate
GitHub metrics when collection is enabled and reconcile cached HN/signals/star
history. Keep valid schema/version fields and supported empty structures;
required JSON files cannot all be replaced with `{}`. Test non-GitHub entries,
unknown values and distinct projects sharing a name.

### 6. Inspect previews and browser behavior

Repeat step 2, then follow [CONTRIBUTING.md](CONTRIBUTING.md#filterable-website-preview)
and [site/PREVIEW.md](site/PREVIEW.md) for the complete local/CI checks. The CI
preview sequence adds:

```sh
python3 scripts/build_exhibition_preview.py --output tmp/site
python3 scripts/build_jar_preview.py --output tmp/site
npm ci --ignore-scripts
npx --no-install playwright install --with-deps chromium
python3 -m http.server 8000 --bind 127.0.0.1 --directory tmp/site
```

In another terminal, run `SITE_URL=http://127.0.0.1:8000 npm run test:browser`
and the exhibition/jar checks documented in
[the PR workflow](.github/workflows/check-updaters.yml). Inspect desktop/mobile,
filters/history, keyboard/no-JavaScript behavior, Observatory exports and
static record pages. Update catalog-specific test expectations; keep previews in
ignored `tmp/`. Dependency installation needs network access.

### 7. Configure publication

Review `.github/workflows/`, then enable Actions under your account. Set
Settings → Pages → Build and deployment to **GitHub Actions**. Review
`github-pages` environment approvals and branch rules for generated-path writes.
Keep `contents: write` in collection and `pages: write`/`id-token: write` in the
separate deployment job. No custom AI key or personal token is required.

For another default branch, update `main` assumptions in the workflow,
`scripts/publish_readme.py`, `scripts/build_published_site.py` and their tests.
Review the daily schedule and request budgets before enabling them.

### 8. Review and verify the first publication

Open a draft PR with policy, evidence, exact revision and check results. Keep
routine catalog edits source-only; review any generated-data migration
separately. After maintainer approval and merge, dispatch **Publish README and
field guide** if needed. Verify its accepted `published_sha`, generated README
commit, Pages deployment and live site's revision/links. Collection success
alone does not establish deployment. If a later deployment stage fails, fix it
and **re-run all jobs**; see [publication guidance](CONTRIBUTING.md#github-pages-publication).

### 9. Connect optional curation

Write public task contracts for discovery, accuracy, alternatives or function
summaries using Part I. Test one manual run and its evidence/draft PR first.
Connect your runner, grant bounded access and register any desired schedule
separately. Keep secrets in the runner's secret store and require maintainer
review before merging curated changes.

Contribution by Junge (AI).
