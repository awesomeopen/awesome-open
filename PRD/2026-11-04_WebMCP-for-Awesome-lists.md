# PRD: WebMCPlet

- **Date:** 2026-11-04; revised 2026-11-06 after the owner's design review
- **Status:** Proposed. The merged Cabinet is the only implementation so far
- **Owner:** Project owner
- **Baseline:** main `b8e27f5`
- **Related:** [research notes](2026-11-06_WebMCPlet-research.md),
  [Cabinet contract](../site/WEBMCP-CABINET.md), [reuse proposal](../CLONE.md),
  future home [JumperMCP/webmcplet](https://github.com/JumperMCP/webmcplet)

## Purpose

WebMCPlet lets people ask an AI about a curated list from the list's own page,
with no MCP server to install. A maintainer adds one script and one generated JSON
file; the page then offers a search panel, a local assistant where the browser
supports one, and tools for visiting agents.

The target experience is the [Context Awesome demo](https://github.com/bh-rat/context-awesome):
an agent finds the relevant section, retrieves its items and writes a detailed
answer. WebMCPlet brings that journey to one list at a time, on that list's page.

Awesome Open\* is the rich example. [open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)
is the outside proof, because the showcase is only useful if a similar site can
adopt it like a product.

**Audience:** developers, list maintainers and people following WebMCP. Limited
browser and hardware support is accepted. Search in the panel works for everyone.

## Evidence so far

| Finding | Result | Consequence |
| --- | --- | --- |
| ChatGPT's web UI on the live Catalog, 2026-11-06 | Its cloud browser called `cabinet_find`, `cabinet_arrange` and `cabinet_compare`. The live site has no origin-trial token | The no-install journey works today for this client |
| Current search on the PRD's first example | "manage family photos on my own server" returns 0 of 555 projects; "video editor" returns 6 | Search comes first; no-match is a required outcome |
| Scan of 673 lists in `sindresorhus/awesome` | 68% use `- [name](url) - description`; 16% have Pages on; 5 of 586 carry star counts on most entries | Structure is common. Hosting and page control decide adoption |
| Quick importer on the Mac list's full README | Found 977 distinct URLs, all in the list's JSON; missed 7 | The list's JSON can score the importer automatically |

Methods and limits are in the [research notes](2026-11-06_WebMCPlet-research.md).

## Journeys

Every journey answers: **what in this list fits my need, and what's missing?**

| Request | List | Required behavior |
| --- | --- | --- |
| Find a video editor and compare two | Awesome Open\* | Returns matches, compares recorded fields with their dates and sources |
| Find a Markdown editor | Mac list | Same script and tools, with fields limited to what the list supplies |
| Manage family photos on my own server | Awesome Open\* | Reports no match in this Open\*-named catalog and names no unrelated project |

## Decisions

### Adoption

- **Delivery:** adopters copy a versioned script into their site and run a pinned
  build step that generates the JSON. We serve no script. `build.cjs try` previews a list
  from its README before any change to the site.
- **Input:** the build step reads README Markdown; a list with good JSON can use
  that. Importers read raw files, because GitHub's README API truncated large files
  at about 512 KB.
- **Schema:** stable ID, section, name, URL and description are required. Identity
  is the normalized URL, so cross-listed entries merge into one item with several
  sections. Other fields are declared and optional, and missing values read Unknown.
- **GitHub stars:** an optional field fetched at build time and labelled "GitHub
  stars, observed on [date]". Results default to match order; sorting by stars
  happens only on request.
- **Code home and license:** a self-contained directory in this repository with no
  Awesome Open imports, in dependency-free JavaScript, under its own MIT license.
  `LICENSE.md` and `CONTRIBUTING.md` record that exception when the directory is
  created, since this repository's contributions are CC0. It moves to
  `JumperMCP/webmcplet` once someone outside adopts it.

### Tools

- **Core tools:** read-only section listing, item search and item retrieval.
- **Optional module:** ordered selection and comparison, which Awesome Open enables.
- **Search:** one shared matcher across names, descriptions, aliases, function
  summaries and feature notes, reporting which field matched.
- **Run modes:** a declared filter on recorded run modes that reports coverage, for
  example "33 of 555 have a recorded run mode". Records are read at build time, so
  coverage grows as the [deployment-evidence job](../automation/backfill-deployment-evidence.md)
  adds them. Unrecorded projects stay Unknown and remain searchable.
- **Errors:** tools return `{ok: false, code, message}`. In testing, Chrome replaced
  a thrown error with a generic failure, and the agent lost the recovery instruction.
- **Links back:** results include the list's page URL and, when a selection exists,
  its shareable URL. A person using an agent's cloud browser never sees the page, so
  these give the agent something to cite.

### Two ways to use the tools

- **WebMCP** serves visiting agents, starting with ChatGPT's browser. Other clients
  are listed in the [research notes](2026-11-06_WebMCPlet-research.md#client-support).
- **The Prompt API** serves visitors with no agent, on capable desktop Chrome. It
  stays in only if the model test passes. There is no cloud fallback.

### Panel

- **Default:** a small labelled corner button that never opens by itself or
  animates. It opens a large overlay. A banner is an opt-in style.
- **Contents:** search and browsing for everyone. The assistant appears when the
  model is available or downloadable, and any download needs an explicit click.
- **Silencing:** maintainers set `data-webmcplet-panel="off"`, which keeps the tools
  registered. Visitors can dismiss the button, stored only in their browser.
- **Credit:** a small "WebMCPlet" link in the overlay footer, plus directory and
  list submissions that the owner controls. The script makes no analytics calls.
- **Awesome Open:** shows the same button in its white/Prussian theme, and the
  assistant operates one shared selection. The Cabinet keeps its name. Its current
  interface is uninviting and makes its purpose hard to understand, so this work
  redesigns the interface.

### Answers and copy

- **Assistant answers** show rows and links from tool results separately from model
  prose, which is labelled as generated. A deterministic check rejects any project
  the tools did not return. Missing facts read Unknown.
- **Visiting agents** write their own prose. In the ChatGPT test, recorded values
  were correct and the model added its own judgment that one project was "the more
  immediately informative choice". Tool descriptions state what each field means;
  the page's own answer rules cover only the built-in assistant.
- **Copy:** panel text, tool descriptions and the assistant's instructions follow
  [curb-your-verbosiasm](../.agents/skills/curb-your-verbosiasm/SKILL.md) and its
  sister skill `straightforward`. Say what a thing is and does.

### Origin-trial token

Tokens are optional for adopters. ChatGPT's browser worked without one; a token
turns the API on for visitors' Chrome without a flag. Register ours at release. It
needs attention by Chrome 162, stable on 2027-02-02.

## Delivery

| PR | Deliverable | Acceptance |
| --- | --- | --- |
| 1 | This PRD split into decisions and research notes | Links and brand checks pass |
| 2 | Shared search, structured errors and the Cabinet check in CI, on Awesome Open | Manual and tool paths return identical IDs, order and unknowns; the Journeys table's Awesome Open searches behave as specified |
| 3 | Throwaway model test on the M5, unmerged | Context window, speed and valid-action rate recorded for the journeys on both lists. Set a threshold after the first baseline. A failure drops the Prompt API and leaves search plus WebMCP |
| 4 | Core, schema, read-only tools and importer | The importer is scored against the Mac list's JSON; the same script runs on Awesome Open and on the Mac list, injected only in our own browser |
| 5 | Panel, assistant if it passed, and the Cabinet redesign, with a brand decision record | Keyboard, touch, focus and silencing checks pass on both lists |
| 6 | Packaging, adopter docs and token | A maintainer can reproduce the fixture integration from the docs |
| 7 | Demo recording | The owner reviews the recording before anything is published |

**Demo recording,** deferred by the owner on 2026-11-10 until every segment runs reliably; about 90 seconds on the M5: the local assistant on Awesome Open
with "video editor"; the family-photo query returning a clear no-match; the same
script on the Mac list, labelled as a local demo with no affiliation; then an agent
calling the same tools.

**Test machines:** the M5 (`ssh m5`) runs model and browser work. `alder` has about
15 GB of RAM and reports the model as `downloadable`, so it serves as the low-end
reference. On `alder`, browser checks need system Chrome through `CHROMIUM_PATH`,
because Playwright's bundled Chromium can't start there.

## Out of scope

- Hosted scripts, backends, provider keys, automatic model downloads and analytics.
- Deploying to other people's sites, or contacting maintainers without the owner.
- Implying endorsement by any list used as a fixture.
- Universal DOM parsing.
- Aggregate rankings or recommendations; arbitrary URLs or code; repository writes,
  payments and installation requests.
- Assessment item #7, History and renames, excluded by the owner. Browser Back/Forward
  and share-URL restoration stay in scope.

Contribution by Junge (AI) and Claude Code (AI)
