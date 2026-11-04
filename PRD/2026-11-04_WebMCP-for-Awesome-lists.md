# PRD: WebMCP for Awesome-list websites

- **Date:** 2026-11-04
- **Status:** Proposed product plan; no implementation or active brand-policy change
- **Owner:** Project owner
- **Baseline:** main `cdfdbbc4ac4077e2ce4950eaea6a87311e51e675`
- **Related:** [Cabinet contract](../site/WEBMCP-CABINET.md),
  [Cabinet decision](../brand/decisions/B-PR250-01.md), [reuse proposal](../CLONE.md)

## Decision and purpose

Package the Cabinet's catalog search, ordered selection and evidence comparison
for curated Awesome-list websites. Awesome Open\* is the first showcase. Visitors
can use the panel themselves, ask a small built-in assistant, or use a compatible
browser agent against the page's WebMCP tools.

Choose Chrome's Prompt API for the optional built-in assistant. Its narrow browser
scope fits a showcase; defer WebLLM. The assistant calls application-owned actions
and works independently of WebMCP. Ordinary search and comparison remain complete
without either API. No automatic model download, provider key, backend service or
paid cloud fallback is required by this product.

[Context Awesome](https://www.context-awesome.com/browse) already offers useful
cross-list discovery. Its [per-list page](https://www.context-awesome.com/list/f/awesome-chatgpt-prompts)
provides an example prompt and MCP setup link; its
[hosted endpoint](https://www.context-awesome.com/#installation) requires client
configuration, with no server installation. Local installation is a development
option. Its [server](https://github.com/bh-rat/context-awesome/blob/main/src/mcp-server.ts)
exposes sections, item search and list/section retrieval. Our product hypothesis
is that tools exposed by a visited page reduce per-service client setup for
existing browser-agent users, while Prompt API serves visitors without an agent.
This is an adoption hypothesis to test. Compatible agents and browser/model
availability still gate these paths. The observed browse/detail counts differ;
completeness was not established, and its MCP endpoint was not invoked.

## Current Cabinet and gaps

The merged implementation provides `cabinet_find`, `cabinet_inspect`,
`cabinet_arrange` and `cabinet_compare`. Humans and tools share an ordered selection
of at most six distinct canonical IDs, a selection revision and the latest 20
operation names, actors and outcomes in memory. Invalid inputs fail before
mutation; comparisons reject a selection changed during loading.

The [current code](../site/cabinet.js) has two useful starting gaps:

- Find performs AND matching of lowercase substring tokens, capped at 12 results.
  It is literal search. It differs from the Catalog's Unicode/reviewed-alias
  matcher; sharing that matcher should precede natural-language claims.
- Compare labels short descriptions as Function. It does not yet consume reviewed
  Function summaries/features. Those can improve comparisons where available.

Discovery uses the embedded index. Inspect and compare load same-origin
`catalog.json`, rejecting redirects and source-revision mismatch. Shared URLs
serialize ordered IDs and reopen the current published evidence. They do not
freeze a snapshot. Preserve the [evidence meanings](../brand/foundation.md#evidence-contract)
and existing prohibitions on aggregate rankings/recommendations, arbitrary URLs
or code, repository writes, payments and installation requests.

## Proposed package boundaries

| Component | Responsibility |
| --- | --- |
| Deterministic core | Validated catalog, matching, bounded results, ordered selection, revisions and comparisons |
| Application action registry | One allowlisted contract for manual controls, model controller and bridge; application validation remains authoritative |
| Generic panel | Accessible search, selection, reorder/remove, comparison, sources and literal status/error text |
| Awesome Open adapter | Current canonical IDs, reviewed evidence, dates, presentation and existing source-loading safeguards |
| Prompt API controller | Optional bounded interpretation of natural language into registry actions |
| WebMCP bridge | Independently detected registration for a compatible browser agent |

The generic panel must work with keyboard and touch, expose visible shared state,
and keep human override available during model activity. Awesome Open retains its
existing visual/evidence contracts; other lists need no specimen artwork or
Awesome Open branding. Other site surfaces are outside the generic MVP.

### Data contract and integration

Phase 1 must settle and version a minimal schema. Proposed required fields are
stable item ID, name, primary URL, description, category memberships and source
references, plus dataset revision. Empty descriptions/categories may be represented
explicitly for sparse lists; importer review must still establish that the result
is useful. Identity must survive ordering changes and distinguish duplicate names.

Optional typed capability/evidence fields declare their meaning, mapping, source
and observation/review dates. Preserve absent, unknown and stale values; never
coerce unknown to zero or false. Generic lists need not supply metrics, artwork,
reviewed Function summaries or rich evidence. Unsupported comparison fields stay
unavailable. A declared capability must correspond to data the adapter can supply.

Prefer existing structured data, then a Markdown AST, then explicitly configured
DOM extraction. Universal DOM parsing is outside scope. A GitHub README cannot
run this JavaScript: integration requires a maintainer-controlled hosted page,
Pages companion or build step. Drop-in means a small documented integration with
a proven adapter, not automatic compatibility with every list.

## Optional natural-language controller

Use the current `LanguageModel` global, rather than historical `window.ai`
examples. Chrome's [Prompt API documentation](https://developer.chrome.com/docs/ai/prompt-api)
was checked on 2026-11-04 (updated 2026-10-21; web availability listed as Chrome
148). Gemini Nano is a separate download. Link the live browser, OS, hardware and
storage requirements in setup documentation instead of freezing those limits here.

Feature-detect before calling `LanguageModel.availability(options)`. Keep language,
modality and other applicable options consistent across availability, creation and
prompting. Distinguish unavailable, downloadable, downloading and available states.
Require explicit user activation before `LanguageModel.create(...)`; expose
`monitor` / `downloadprogress`, errors and cancellation via an `AbortSignal`.
Missing API or failed setup leaves the full manual panel available. Cancellation
must stop this controller's work; do not promise removal of browser-managed model
files. Session teardown and late-result handling must preserve human edits.

The controller proposes structured actions, validates their schema and semantics,
and dispatches only registered verbs. Set explicit turn, result and context limits
before implementation; reject malformed JSON, unsupported actions and oversized
requests. Re-read selection revisions before mutations. Source prose is untrusted
data, including instruction-like text. Never execute model-generated code or use
model claims as evidence. Answers cite returned catalog fields and sources; missing
predicates produce an explicit unknown or a request to narrow the query.

The [WebMCP draft](https://webmachinelearning.github.io/webmcp/), dated 2026-11-02,
uses `document.modelContext` and remains a Community Group draft, not a W3C
standard. Detect the installed bridge independently, retain secure-context and
same-origin constraints, and test actual argument behavior for supported browser
versions. Native bridge execution tests and natural-language end-to-end evaluation
are separate: the existing pilot establishes only the former.

## Use cases for tests and documentation

The supplied assessment contributes the following scenarios and candidate additions.
They are requirements for evaluation, not claims of model reliability.

| Visitor request | Expected behavior and evidence boundary |
| --- | --- |
| Find tools for a task, shortlist, then compare | Match declared fields, show bounded results, preserve chosen IDs and compare supported facts |
| Compare named A, B and C | Resolve identities, clarify ambiguity, retain the requested order |
| Is this still alive? | Show dated push/release observations and unknowns; do not infer maintenance, health or security verdicts |
| Find substitutes / open-source options | Use reviewed alternatives or evidenced capability fields; apply “open-source” only with a verified license predicate |
| Share this shortlist | Reopen ordered IDs against current evidence; disclose current-evidence semantics |
| Let me make the choice | Show state and sources, support human edits and reject stale model mutations |

### Candidate additions

Prioritize these after reviewing their cost and evidence coverage. The assessment's
“easy things to add” label is not an effort estimate.

1. Bootstrap/status action returning selection, selection revision, dataset
   revision, count and declared capabilities.
2. Richer comparison using reviewed Function summaries/features and optional mapped
   fields, with evidence dates and sources.
3. Atomic add/remove operations using the same identity, limit and revision rules.
4. Declared filters and bounded pagination beyond the first 12 matches.
5. Stronger tool descriptions and examples for ordering, unknowns and recovery.

Optional later work: seeded random selection and Markdown/JSON selection export.
Retain the existing bounded in-memory activity in Awesome Open; decide whether the
generic panel needs the same optional surface. **Assessment item #7, History and
renames, is excluded by the owner.** It is neither MVP nor committed later scope.
This exclusion is distinct from browser Back/Forward and share-URL restoration.

## Discovering showcase lists

Scan [sindresorhus/awesome](https://github.com/sindresorhus/awesome) for candidate
hosted lists. GitHub Pages is a useful discovery cohort; custom domains and other
hosts remain eligible. `has_pages` alone establishes neither the canonical host
nor compatibility.

### Preliminary pilot, 2026-11-04

The supplied scan pinned root README Git blob
`0acaa99d5f45582ecf70f987213f59ae1855226f` and found 674 distinct direct GitHub
repository links, including links that are not lists. A purposeful sample of 14
repositories had seven with `has_pages=true`. This was a pilot, not a census or
prevalence estimate. The Pages endpoint was inaccessible; actual Pages hosting,
live reachability and integration compatibility remain unverified. Several hosted
lists had `has_pages=false`.

| Candidate | Pilot finding | Follow-up before selection |
| --- | --- | --- |
| [awesome-python](https://github.com/vinta/awesome-python), [site](https://awesome-python.com/) | Pages enabled; 528 projects / 74 categories extracted; existing Markdown AST parser | Reproduce extraction at a recorded source revision; inspect representative entries |
| [awesome-go](https://github.com/avelino/awesome-go), [site](https://awesome-go.com/) | Pages enabled; conventional nested lists; Netlify configuration present | Establish canonical hosting and category/link mapping |
| [awesome-mac](https://github.com/jaywcjlove/awesome-mac), [site](https://wangchujiang.com/awesome-mac/) | Pages enabled; multiple links and badges; source CC0 versus site-footer CC BY 4.0 conflict | Resolve rights and primary-link selection before reuse |
| [free-for-dev](https://github.com/ripienaar/free-for-dev), [site](https://free-for.dev/) | Pages enabled; dynamic Docsify shell | Use source adapter; inspect descriptions and section structure |

These are leads for extraction tests; they carry no maintainer endorsement.

### Reproducible scanner plan

1. Pin the root repository revision and README blob. Use Markdown AST extraction
   to classify actual list links and separate navigation, tooling and incidental
   repositories. Deduplicate redirects/canonical names by numeric repository ID.
2. Record `has_pages`, homepage and default branch. Independently record verified
   Pages hosting, canonical destination, live reachability and structural
   suitability, including unknown/denied states.
3. Inspect structured sources or Markdown without executing candidate scripts.
   Record source revisions, extracted counts, unique identities, categories,
   descriptions, primary/source links, rights, checked dates and unknowns.
4. Manually review bounded samples for false positives, multi-link choices,
   duplicate names, missing descriptions and usefulness for the use cases above.
   Publish the sample selection and observed error counts with the report.
5. Choose two or three contrasting candidates only after useful extraction is
   demonstrated: Go/Python conventional lists and a Docsify source are potential
   choices. Keep fixtures pinned and rights-reviewed; re-run deterministically.

Honor access denials, quotas and `Retry-After`; record unresolved checks. Do not
deploy to others' sites, contact maintainers or imply endorsement. Full-census
coverage is outside this first scan.

## Phases and acceptance

| Phase | Deliverable | Acceptance gate |
| --- | --- | --- |
| 1. Shared foundation | Core, schema, action registry and reconciled search | Manual and action paths return identical IDs/order/unknowns; existing evidence safeguards pass |
| 2. Optional Prompt API showcase | Explicit activation, bounded controller, evaluation corpus | All availability/error paths preserve manual use; held-out natural-language results and failures are recorded separately from bridge tests |
| 3. Portable panel | Generic panel plus JSON adapter and genuinely different fixture | Both catalogs search/select/compare/share with no Awesome Open metrics or artwork dependency; keyboard/touch checks pass |
| 4. Proven importers | Two or three source structures and reproducible scan report | Every sampled imported record has verified identity/link mapping; omissions and unresolved rights are explicit; reruns preserve identities |
| 5. Packaging | Versioned assets/schema, integration instructions and examples | A maintainer can reproduce the fixture integration from documented inputs and run the acceptance suite |

For each use case, maintain expected IDs, permissible actions, evidence fields and
order. Record browser/model versions, fixture revisions, repeated-run outcomes,
completion rate, corrections and failures. Set a numerical natural-language release
threshold after baseline measurement and before promotion; this PRD invents no
latency, reach or reliability promises. Deterministic invariants must pass every
run. A failing scenario remains documented and blocks its supported-use-case claim.

Required edge/adversarial coverage: empty query and no results; more than 12
matches with bounded pagination; more than six selections; duplicate/unknown IDs;
stale selection revision; cancellation; invalid model JSON; unsupported action;
source-revision mismatch; unknown fields; concurrent human/model edits;
unavailable/download/error states; and instruction-like text embedded in sources.
Test manual fallback with both APIs absent. Inspect visible status, keyboard focus,
mobile comparison and cancellation. Never infer natural-language success from
native bridge discovery/execution alone.

## Risks and unresolved decisions

- Browser/API evolution and model/device availability limit reach. Keep support
  checks isolated and publish the tested version matrix.
- Thin descriptions may support discovery but weak comparisons. Capability
  declarations and explicit unknowns bound the answer; evaluate usefulness before
  choosing a showcase list.
- Source structure, identity and licensing can change. Pin fixtures, retain
  provenance and review rights before redistribution.
- Local inference covers model processing; ordinary site requests and analytics
  retain their own privacy behavior. Document the actual data flow.
- Final schema details, controller budgets, package format and release thresholds
  require phase-specific review. This proposal does not activate new collectors,
  schedules, publication targets or brand rules.

Contribution by Junge (AI)
