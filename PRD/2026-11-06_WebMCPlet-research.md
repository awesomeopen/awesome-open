# WebMCPlet research notes

Evidence and implementation constraints behind the [WebMCPlet PRD](2026-11-04_WebMCP-for-Awesome-lists.md).
This record grows as the work finds resources. Entries are dated; counts are as each
source reports them unless a project test is named.

## Client support

The [WebMCP Directory FAQ](https://webmcp.com) reports the state as of October 2026,
from one source run by a vendor in this space. The test column records what this
project has run.

| Client | Reported state | Project test |
| --- | --- | --- |
| ChatGPT web UI, cloud browser | Not covered by the FAQ | **Worked**, 2026-11-06, owner's run (below) |
| ChatGPT desktop | Uses WebMCP tools in its built-in browser since 2026-08-25 | Not tested |
| Brave Leo | Available in Brave Nightly behind a flag | Not tested |
| Gemini in Chrome | Cannot use WebMCP tools yet | Not tested |
| Claude for Chrome | Does not use WebMCP tools | Not tested |
| Stagehand, Vercel agent-browser | Supported | Not tested |
| [chrome-devtools-mcp](https://developer.chrome.com/docs/devtools/agents/webmcp-debugging) | Chrome's docs: `list_webmcp_tools` and `execute_webmcp_tool` behind `--categoryExperimentalWebmcp`, "a debugging feature targeted at developers" | Page tools called through script evaluation, 2026-11-06; the two named tools not yet run |

### ChatGPT web UI test

Prompt: "Open https://awesomeopen.github.io/awesome-open/, use the page's tools to
find video editors, and compare two." The interface showed GPT-6.1 Terra Light.

- It reported calling `cabinet_find`, `cabinet_arrange` and `cabinet_compare`, and
  named all six matches.
- Licenses, stars and push dates for OpenCut and OpenReel Video match the catalog's
  values: 97,430 and 5,593 stars, MIT for both, pushes on 2026-09-24 and 2026-10-17.
- Its prose reflects OpenCut's function summary, a field `cabinet_compare` does not
  return, so it read beyond the tool results. Which source it read was not observed.
- It called OpenReel "the more immediately informative choice", which is the model's
  own judgment.
- The no-match journey and ChatGPT desktop have not been run.

### Local checks, 2026-11-06

- With Chrome 156 and no flag, the live page reports "Native WebMCP is unavailable".
  With `--enable-blink-features=WebMCP`, it registers all four tools.
- `scripts/check_cabinet_browser.cjs` passes on `alder` using system Chrome through
  `CHROMIUM_PATH`. It covers the tools only, and CI does not run it yet.
- Through `chrome-devtools-mcp`, a stale revision was rejected and the selection was
  preserved. The caller received "Tool was executed but the invocation failed", while
  the page showed "Selection changed. Read the current revision and retry."

## Browser APIs

**WebMCP** is a [Community Group draft](https://webmachinelearning.github.io/webmcp/)
using `document.modelContext`. [Chrome Status](https://chromestatus.com/api/v0/features?q=webmcp)
lists its origin trial as Chrome 149–156, extended to 162, whose
[stable date](https://chromiumdash.appspot.com/fetch_milestone_schedule?mstone=162)
is 2027-02-02. Chrome's [API page](https://developer.chrome.com/docs/ai/webmcp/imperative-api)
deprecates JSON-string arguments from Chrome 155. A third-party
[support guide](https://www.mcpbundles.com/guides/webmcp-browser-support) lists an Edge
trial expiring 2027-03-30 and no Firefox or Safari implementation.

**Prompt API**, per [Chrome's docs](https://developer.chrome.com/docs/ai/prompt-api)
updated 2026-10-21:

- Web availability from Chrome 148, with no flag or token.
- Windows 10/11, macOS 13+, Linux, and ChromeOS on Chromebook Plus. Android and iOS
  are unsupported.
- At least 22 GB free. Either more than 4 GB VRAM, or 16 GB RAM and 4 cores.
- English, Japanese, Spanish, German and French.
- The docs give no context-window size; `session.contextWindow` reports it at runtime.
- `responseConstraint` provides structured output. Native tool use needs
  `chrome://flags/#prompt-api-tool-use`, per the
  [tool-use demo](https://chrome.dev/web-ai-demos/prompt-api-tool-use/).

**Machines, 2026-11-06:**

| Machine | Hardware | Chrome | Model state |
| --- | --- | --- | --- |
| `m5` | M5 Max, 18 cores, 128 GB, 1.1 TB free | 156.0.8078.76 | Not on disk |
| `alder` | About 15 GB RAM, 4 cores, integrated graphics, 40 GB free | 156.0.8078.47 | `downloadable` in the owner's Chrome; `unavailable` in a clean headless profile |

## Catalog evidence

Live catalog, 2026-11-06, 555 projects: 503 have GitHub stars, 419 function summaries,
390 detected licenses, 33 deployment records and 31 reviewed alternatives. The embedded
index is 254 KB and the summaries total 165,000 characters, so search has to narrow the
results before a model reads them.

## List scan

Scan of the root README of `sindresorhus/awesome`, blob
`0acaa99d5f45582ecf70f987213f59ae1855226f`, on 2026-11-06: 674 linked repositories,
673 resolved, 3 archived.

| Measure | Lists |
| --- | --- |
| At least 70% of entries are `- [name](url) - description` | 456 of 673 (68%) |
| `has_pages` true | 110 of 673 (16%), 70 of them in that format |
| Homepage set, Pages off | 93 |
| At least half of entries carry stars, by badge or text | 5 of 586 with 20+ entries |
| Any star marking on at least 10% of entries | 11 of 586 |
| At least half of entries link to GitHub | 255 of 586 |

Classification used line regexes, with no manual review or live-site checks. GitHub's
README API truncated content at about 512 KB, which undercounts four large lists.
`has_pages` establishes neither the canonical host nor whether a maintainer can add a
script. A later scan should use a Markdown AST and raw files, and should record hosting
type, reachability and a reviewed sample.

Structured, Pages-enabled candidates by stars include
[awesome-python](https://github.com/vinta/awesome-python),
[awesome-go](https://github.com/avelino/awesome-go),
[free-for-dev](https://github.com/ripienaar/free-for-dev),
[awesome-mac](https://github.com/jaywcjlove/awesome-mac) and
[awesome-nix](https://github.com/nix-community/awesome-nix). These are extraction leads
and carry no maintainer endorsement. awesome-mac has a rights conflict to resolve:
CC0 source and a CC BY 4.0 site footer.

### Acceptance list

[open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps) is
CC0, with Pages built from its `github-pages-redesign` branch.

- `applications.json` holds 988 apps, with 984 distinct normalized repository URLs, 972
  of the apps on GitHub, and 4 duplicated titles.
- `categories.json` holds 49 categories, and 336 apps sit in more than one.
- The site's `assets/app.js` loads both JSON files, so the HTML contains no listings.
- The README has 1,421 entries and 977 distinct URLs. All 977 are in the JSON, and 7
  JSON URLs are absent from the regex match.

`awesome-go`, with about 3,167 entries, is the size test.

**Importer score, 2026-11-09,** at `23b6184`: `webmcplet/build.cjs markdown` found 978 of
the JSON's 984 items by normalized URL and no others. Names and plain-text descriptions
are equal for all 978, and section sets for 975. The 6 missing items are absent from the
README; the 3 section differences are JSON categories with no README heading. Firefox and
Thunderbird share one repository URL and merge. Method: [WebMCPlet importer](../webmcplet/README.md#importer).

## Alternatives and adjacent resources

### Context Awesome

[Context Awesome](https://www.context-awesome.com/) is a hosted MCP service reporting
8,500+ lists and 1M+ items. Its [tools](https://github.com/bh-rat/context-awesome) are
`find_awesome_section`, `search_awesome_items` and `get_awesome_items`. Using it means
adding its URL to an MCP client; local installation is a development option. It offers
cross-list discovery, while WebMCPlet offers per-list tools on the list's own page. The
trade-off is client setup against compatible clients and browser or model availability.

Its demo was described in the earlier PRD as a roughly 90-second Cursor journey on
resources for authoring technical books, with an initial generic answer, then section
and item calls, then a categorized answer. Its endpoint was not invoked here.

### Cloudflare

[Cloudflare's preview](https://blog.cloudflare.com/webmcp) (2026-08-06) injects a
same-origin bridge at the edge, with packs for reading C2PA metadata and proxying a
site's MCP server. [Browser Run](https://developers.cloudflare.com/browser-run/features/webmcp/)
(updated 2026-09-28) discovers and runs page tools through experimental backends, and
is a possible interoperability-testing route. Neither generates catalog tools, and
neither is a dependency.

### Site directories

These index sites that expose WebMCP tools, which makes them listing channels for
adopters with live tools.

| Resource | What it records | Listing route |
| --- | --- | --- |
| [WebMCP Directory](https://webmcp.com), maintained by nekuda | 8,572 verified sites, 52,659 tools, 23 platform pages and some developer links | URL and email form; scans live tools and reviews sites before listing |
| [Browser Use directory](https://browser-use.com/webmcp) | 13,352 sites and 45,763 distinct tools from a scan finished 2026-10-19 on Chrome 154, plus 22 platforms that add tools for their customers | None stated; sources are the Tranco list, public lists and its own searches |
| [WebMCP Registry](https://dev.to/jeffsalive/we-built-a-public-registry-and-sdk-for-webmcp-tools-heres-why-it-matters-43lf) (`webmcp-registry.dev`), read from its announcement | Site domains and their tool contracts, searchable by keyword, category or domain | DNS TXT verification, then a sync CLI; a `github.io` project site has no DNS control |

### Curated resource lists

These catalog reusable libraries, extensions and demos, and are possible listing routes
after a public release. Checked 2026-11-06.

| List | Stars | License | Last push |
| --- | --- | --- | --- |
| [webfuse-com/awesome-webmcp](https://github.com/webfuse-com/awesome-webmcp) | 173 | None detected | 2026-10-09 |
| [webmachinelearning/awesome-webmcp](https://github.com/webmachinelearning/awesome-webmcp) | 62 | CC0-1.0 | 2026-10-08 |
| [yigitkonur/awesome-webmcp](https://github.com/yigitkonur/awesome-webmcp) | 31 | CC0-1.0 | 2026-06-07 |
| [Leanmcp/awesome-webmcp](https://github.com/Leanmcp/awesome-webmcp) | 23 | None detected | 2026-03-10 |
| [ilkerulusoy/awesome-webmcp](https://github.com/ilkerulusoy/awesome-webmcp) | 2 | None detected | 2026-08-01 |

### Libraries and embeds

Each helps a site define or proxy its own tools. WebMCPlet supplies a list schema, an
importer, ready-made list tools and a visitor panel; these remain references for API
behavior and interface patterns. Summaries come from registry metadata and documentation,
checked 2026-11-06; their code was not reviewed.

| Resource | Latest | License | What it does |
| --- | --- | --- | --- |
| [@mcp-use/webmcp](https://www.npmjs.com/package/@mcp-use/webmcp) | 0.1.0, 2026-03-06 | MIT | Script-tag proxy for a remote MCP server, with a live inspector overlay |
| [webmcp-tools](https://www.npmjs.com/package/webmcp-tools) | 0.1.2, 2026-06-13 | MIT | Typed SDK and `document.modelContext` ponyfill |
| [@mcp-b/global](https://www.npmjs.com/package/@mcp-b/global) | 6.0.3, 2026-10-14 | MIT | WebMCP API polyfill |
| [@webmcp-registry/kit](https://www.npmjs.com/package/@webmcp-registry/kit) | 0.1.2, 2026-06-08 | MIT | Tool definitions with Zod, React hooks and a registry sync CLI |
| [@nekuda/webmcp-sdk](https://www.npmjs.com/package/@nekuda/webmcp-sdk) | 0.9.0, 2026-11-02 | MIT | Tool SDK used by the [WebMCP Kit](https://webmcp-kit-docs.onrender.com/) coding-agent plugin, which generates tools in a site's repository |
| [webmcp](https://www.npmjs.com/package/webmcp) | 0.0.2, 2026-11-05 | AGPL-3.0-only | One tool definition for the page, an MCP server and a published manifest |
| [Legalese embed](https://legalese.com/l4/tutorials/legalese-cloud/webmcp-embed.md) | Unversioned | Not checked | Script tag exposing Legalese rules, configured with an API key |
| [TYPO3 extension](https://docs.typo3.org/p/neoblack/webmcp/0.2/en-us/singlehtml/Index.html) | 0.2 docs | Not checked | WebMCP integration for TYPO3 sites |

## Constraints for phase specs

These carry forward from the earlier PRD. Each phase spec adopts the ones it needs.

### Current Cabinet

- `cabinet_find` ANDs lowercase substring tokens, capped at 12 results. The Catalog
  uses a Unicode and reviewed-alias matcher.
- Comparison labels the short description as Function and does not read function
  summaries or feature notes.
- Inspect and compare load same-origin `catalog.json`, rejecting redirects and
  source-revision mismatch. Shared URLs carry ordered IDs and reopen current evidence.

### Natural-language controller

- Use the `LanguageModel` global, and feature-detect before calling `availability(options)`.
  Keep language and modality options consistent across availability, creation and prompting.
- Distinguish unavailable, downloadable, downloading and available states.
- Require explicit user activation before `create()`. Expose `monitor`/`downloadprogress`,
  errors and cancellation through an `AbortSignal`.
- Set turn, result and context limits before implementation. Reject malformed JSON,
  unsupported actions and oversized requests.
- Dispatch only registered actions, and re-read selection revisions before mutations.
- Treat source prose as untrusted data, including instruction-like text. Never execute
  model-generated code or use model claims as evidence.
- Teardown and late results must preserve human edits. Cancellation stops this
  controller's work; browser-managed model files stay under the browser's control.

### Data

- Importers prefer existing structured data, then Markdown. Configured DOM extraction
  is a last resort.
- Optional fields declare meaning, mapping, source and observation or review dates.
  Absent, unknown and stale values stay distinct, and unknown never becomes zero or false.
- Declared capabilities must correspond to data the adapter can supply.
- Fixtures are pinned and rights-reviewed, and reruns preserve identities.

### Test coverage

For each journey, keep expected IDs, permissible actions, evidence fields and order.
Record browser and model versions, fixture revisions, repeated-run outcomes, completion
rate, corrections and failures. Deterministic invariants pass on every run.

Required edge cases:

- Empty query and no results; more than 12 matches with bounded pagination.
- More than six selections; duplicate and unknown IDs; stale selection revision.
- Cancellation; invalid model JSON; unsupported action.
- Source-revision mismatch; unknown fields; concurrent human and model edits.
- Unavailable, download and error states; instruction-like text in sources.
- Manual fallback with both APIs absent.

Inspect visible status, keyboard focus, mobile comparison and cancellation. Report
native tool execution and natural-language success separately.

### Further scenarios and candidates

| Visitor request | Expected behavior |
| --- | --- |
| Compare named A, B and C | Resolve identities, clarify ambiguity, keep the requested order |
| Is this still alive? | Show dated push and release observations and unknowns; infer no maintenance, health or security verdict |
| Find substitutes or open-source options | Use reviewed alternatives or evidenced fields; apply "open-source" only with a verified license predicate |
| Share this shortlist | Reopen ordered IDs against current evidence, and disclose that |
| Let me make the choice | Show state and sources, support human edits, reject stale model mutations |

Candidate tool additions, to review for cost and coverage: a status action returning
selection, revisions, count and capabilities; richer comparison from function summaries
and mapped fields; atomic add and remove; bounded pagination beyond 12 matches; seeded
random selection; Markdown or JSON export of a selection.

Contribution by Junge (AI) and Claude Code (AI)
