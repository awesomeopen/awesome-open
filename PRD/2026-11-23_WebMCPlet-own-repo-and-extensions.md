# PRD: WebMCPlet own repository and extensions

- **Date:** 2026-11-23
- **Status:** Proposed. This document is a plan. It does not move the code or
  change listings.
- **Owner:** Project owner, GitHub [@snlr308](https://github.com/snlr308)
- **Related:** [WebMCPlet PRD](2026-11-04_WebMCP-for-Awesome-lists.md),
  [research notes](2026-11-06_WebMCPlet-research.md),
  [listings handover](2026-11-10_WebMCPlet-listings-handover.md),
  [WebMCPlet README](../webmcplet/README.md),
  [CHANGELOG](../webmcplet/CHANGELOG.md),
  [release 0.1.0](https://github.com/awesomeopen/awesome-open/releases/tag/webmcplet-v0.1.0),
  tracking issue [#316](https://github.com/awesomeopen/awesome-open/issues/316)

## Goal

WebMCPlet stays a drop-in solution for curators of an Awesome List. A list may
need to follow stated rules for the importer and the list document to work. The
work should also pave the way for use on sites other than Awesome Lists: any
page that can publish a valid list document and the script should be able to
offer the same read-only tools and panel.

A secondary reason for a separate repository is listing venues that allow one
listing per repository. WhatWeMade already lists the Awesome Open\* Catalog
from this repository. A separate WebMCPlet post was blocked because it would
use the same repository. Once WebMCPlet has its own repository, it can be
listed there as its own project.

Creating a repository, moving code, changing the Catalog build, updating
listings, and implementing the extensions below are later owner decisions. This
file only records the plan.

## Current state

WebMCPlet lives in [`webmcplet/`](https://github.com/awesomeopen/awesome-open/tree/main/webmcplet)
in this repository. It is dependency-free JavaScript under its own
[MIT license](../webmcplet/LICENSE), copyright 2026 Awesome Open\* contributors.
Adopters copy the files from a release. Nothing is published to a package
registry, and the project does not host the script for other sites.

The only published release tag is `webmcplet-v0.1.0`. The [README](../webmcplet/README.md)
download example still uses that tag. `webmcplet.js` sets `RELEASE` to `0.3.0`,
and the [CHANGELOG](../webmcplet/CHANGELOG.md) records 0.2.0, 0.2.1, 0.2.2,
0.2.3 and 0.3.0 with checksums. Those later versions have no tag and no GitHub
Release.

The runtime is `webmcplet.js`. It registers three read-only tools,
`list_sections`, `list_find` and `list_get`, where the browser provides
`document.modelContext` in a secure context. It also offers a search panel in a
shadow root. The script tag accepts `data-webmcplet-src`,
`data-webmcplet-title`, `data-webmcplet-prefix` (renames the tools from
`list_*`), `data-webmcplet-panel`, `data-webmcplet-label`,
`data-webmcplet-caption`, `data-webmcplet-assistant` and
`data-webmcplet-assistant-tools`. The script fetches only the list document
from the same origin. It makes no analytics calls.

The list document is schema version 1 (`webmcplet: 1`). It has `list`,
`sections`, `fields` and `items`. Required list keys are `title` and
`page_url`. Required item keys are `id`, `name`, `url`, `description` and one
or more `sections`. Identity is the normalized URL. Optional fields are
declared; an unrecorded value reads as Unknown.

`build.cjs` has four commands: `markdown` (import a README into a list
document), `check` (validate a list document), `try` (local preview on
`127.0.0.1`) and `version` (print the release and the SHA-256 of
`webmcplet.js`). `markdown.js` imports top-level list items,
`- [name](url) - description`, and table rows, `| [name](url) | description |`.
Each heading is a section. Relative and anchor links, fenced code, and entries
without a current heading or a name are skipped; the importer prints how many
links it skipped. `github.js` is an optional step that records GitHub stars
when `--github-stars on` is set. `try.js` is only for the local preview.

A list that already has structured data can write the list document itself and
run `node build.cjs check`. The Catalog already does this:
`scripts/build_webmcplet_list.py` writes `webmcplet/list.json` from catalog
data, and `scripts/build_site.py` copies `webmcplet/webmcplet.js` from this
repository into the published site. The Catalog does not use the README
importer.

There is no GitHub Action that builds `list.json` from a README or publishes a
Pages site with the script and panel for an adopter. There is no written
"WebMCPlet-ready list" specification, and no CI lint whose job is to report
skipped entries, beyond the importer's skip count, `build.cjs check`, and the
tests in `webmcplet/test/`. The only importer in `webmcplet/` is the Markdown
one.

The [original PRD](2026-11-04_WebMCP-for-Awesome-lists.md) said the code would
move to [JumperMCP/webmcplet](https://github.com/JumperMCP/webmcplet) once
someone outside adopts it. That move has not happened. This plan recommends a
repository under `awesomeopen` instead, unless the owner chooses otherwise.

Client testing remains as in the handover: tested with ChatGPT's web UI; other
clients are untested.
[open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)
is a local test fixture and importer score only. It is not an adopter.

## Repo options

### 1. Its own repository (recommended)

Create a repository such as `awesomeopen/webmcplet`. Move the contents of
`webmcplet/` to the root of that repository, keeping history. Publish tagged
releases there. The Catalog then copies a tagged release of `webmcplet.js` into
its site build, the same way any adopter copies a release. Issues, documentation
and a reusable Action for other lists live with the tool.

**Pros.** WebMCPlet can be listed on venues that allow one listing per
repository, including WhatWeMade. Releases and documentation are not mixed with
the Catalog. The Catalog follows the same drop-in path that the README already
describes for other curators.

**Cons.** Listings and open pull requests that point at
`tree/main/webmcplet` need follow-up edits. The Catalog build, and this
repository's scripts that load `webmcplet/` as a local path, have to take the
script from a pinned release instead. The owner has to approve creating the
repository and the later code changes.

### 2. Keep the folder and auto-mirror it to a read-only repository

Leave `webmcplet/` in this repository as the source. Automatically copy it to a
separate, read-only repository so venues that key listings on a repository URL
have a distinct target.

**Pros.** The Catalog build and in-repo tests can keep using the local folder
with little change. A second repository URL may be enough for a separate
WhatWeMade listing. History can be copied to the mirror.

**Cons.** The source of truth stays inside the Catalog repository, so adopters
and listings are still tied to this tree unless every public link is pointed at
the mirror. Release tags, checksums and issues have to be mirrored or they
diverge. The Action, specification and importers still live here, or have to be
duplicated. The Catalog does not itself become an adopter of a tagged release.

## Extensions

These are later work on the chosen repository. They are not in the current
code.

### GitHub Action

A GitHub Action that, on each push, builds `list.json` from the list's README
with the existing Markdown importer and publishes a GitHub Pages site that
serves the script, the list document and a page with the panel. This is the
largest drop-in gain: a curator who already publishes with Pages should be able
to add the Action, rather than wiring the build and the script tag by hand.
`build.cjs try` stays for local preview. A custom domain for that Pages site is
an owner decision, because it needs DNS; `github.io` does not.

### WebMCPlet-ready list specification and CI lint

A written specification of the rules a Markdown list must follow for the
importer to produce a complete document, taken from current `markdown.js`
behavior: heading sections; top-level `- [name](url) - description` items or
`| [name](url) | description |` table rows; `http:` or `https:` URLs; skipped
relative and anchor links, fenced blocks, and entries that have no current
section or name. A CI lint runs the importer and `build.cjs check`, and reports
the skipped entries so a curator can see what was left out.

### Importers as adapters

Keep the list document as the fixed contract. Treat importers as adapters that
write that document. The Markdown adapter remains the default for Awesome
Lists. Add JSON and CSV adapters first; later, schema.org data and page markup.
The Catalog's `scripts/build_webmcplet_list.py` is an existing example of a
structured-data adapter, not a general importer to copy. Tool names are already
renameable with `data-webmcplet-prefix`, so a site that is not a list can still
present the same tools under other names. This is the path for sites other than
Awesome Lists: produce a valid `list.json`, publish it with the script, and
optionally rename the tools.

## Phases

Each phase needs a later owner approval before any repository, listing or
code change. Acceptance is what must be true before the next phase starts.

### Phase 1. Choose the repository option and name

The owner chooses option 1 or option 2, the repository owner and name, and
whether to keep or replace the earlier `JumperMCP/webmcplet` destination.

**Acceptance.** The choice is written in the tracking issue or in a follow-up
to this PRD. No repository is created before that choice.

### Phase 2. Create the repository and move the code (option 1)

If option 1 is chosen:

1. Create the repository (recommended: `awesomeopen/webmcplet`).
2. Move `webmcplet/` to the new repository's root with history preserved, for
   example with `git filter-repo` or `git subtree split`, so commits that
   touched those files remain in the new history.
3. Keep the MIT license and the existing copyright line.
4. Publish release tags in the new repository. Carry forward
   `webmcplet-v0.1.0`. Decide, under [Open questions](#open-questions), how to
   tag the CHANGELOG versions that have no tag today, and whether new tags keep
   the `webmcplet-v*` prefix or use `v*`.
5. Point the Catalog build at a tagged release of `webmcplet.js`, the same way
   an adopter copies a release. Keep generating the Catalog's `list.json` from
   `scripts/build_webmcplet_list.py`.
6. Replace the old `webmcplet/` folder in this repository with a short pointer:
   the new repository URL, the current release tag, and a statement that this
   folder is no longer the source.

If option 2 is chosen instead, create the read-only mirror, document it as a
mirror, and publish or copy tags so the mirror has a stable release URL. Leave
`webmcplet/` in this repository as the source. Skip the Catalog switch in step
5 and the pointer in step 6.

**Acceptance.**

- The new or mirror repository contains the current WebMCPlet files and the MIT
  license.
- `node --test test/*.test.js` and `node build.cjs version` succeed in that
  repository.
- A release tag is present and its `webmcplet.js` checksum matches the
  CHANGELOG entry for that version.
- Under option 1, this repository's `webmcplet/` folder is a pointer, and the
  Catalog site build copies `webmcplet.js` from that release tag.
- Under option 2, the mirror is documented as read-only and is updated from
  `webmcplet/` automatically.

### Phase 3. Update listings after the repository exists

Record the new URL and tag in [#316](https://github.com/awesomeopen/awesome-open/issues/316).
Then, with a separate owner approval for each edit:

- Update the open list pull requests that link to
  `tree/main/webmcplet`:
  [webfuse-com/awesome-webmcp#46](https://github.com/webfuse-com/awesome-webmcp/pull/46),
  [webmachinelearning/awesome-webmcp#79](https://github.com/webmachinelearning/awesome-webmcp/pull/79),
  [yigitkonur/awesome-webmcp#27](https://github.com/yigitkonur/awesome-webmcp/pull/27)
  and
  [#28](https://github.com/yigitkonur/awesome-webmcp/pull/28).
- Recheck the [webmcp.com](https://webmcp.com/sites/awesomeopen.github.io)
  Catalog entry (listed; a rescan that detected 7 tools was pending review as of
  2026-11-16). The Catalog site URL does not change because of the move; update
  the entry only if its text or a WebMCPlet link needs the new repository.
- Recheck the [WebMCP Registry](https://webmcp-registry.dev/domain/awesomeopen.github.io/awesome-open)
  Catalog entry (listed, unverified, 7 tools). It is a domain listing for the
  Catalog site, so it may need no change; record that check in #316.
- Submit the WhatWeMade WebMCPlet post once the project has its own repository
  URL, using that URL, the MIT license, and the wording rules below. The
  Catalog post at
  [whatwemade.app/p/awesome-open-catalog](https://www.whatwemade.app/p/awesome-open-catalog)
  stays as it is.

Do not comment on those upstream pull requests except to edit our own
submissions when the owner has approved the edit. Do not resubmit a declined
listing.

**Acceptance.** #316 shows the new repository URL, the state of each listing
after the follow-up, and a dated comment for each change. The WhatWeMade
WebMCPlet row is `submitted` or `listed`, or a written reason if it is still
blocked.

### Phase 4. GitHub Action

Add the Action described above, with documentation that follows the existing
README's "Add it to your site" path. Use the example list under
`webmcplet/example/` (or its new-repo path) as the fixture.

**Acceptance.** A push of the fixture README produces a `list.json` that passes
`build.cjs check`. A Pages site from that run serves `webmcplet.js`,
`list.json` and a page whose script tag matches the README. The document is
same-origin. `build.cjs try` still previews a list locally.

### Phase 5. Specification and CI lint

Publish the WebMCPlet-ready list specification from current importer behavior,
and a CI lint that reports skipped entries and validation errors.

**Acceptance.** The specification matches `markdown.js`. On a README with known
skipped links, the lint names those skips. A valid list passes. The
open-source-mac-os-apps importer score remains a fixture test and is not
presented as adoption.

### Phase 6. JSON and CSV adapters, then later formats

Add JSON and CSV adapters that write a schema 1 list document. Later adapters
may read schema.org data and page markup. Do not change the list document
contract or the three tools to do this.

**Acceptance.** Each shipped adapter produces a document that passes
`build.cjs check`. A non-Markdown source can be previewed with `build.cjs try`
or an equivalent path, and the panel and tools run from that document. Tool
renaming through `data-webmcplet-prefix` remains documented.

## Constraints

Follow the [listings handover](2026-11-10_WebMCPlet-listings-handover.md) when
writing or updating any listing:

- Use the venue's format. Say what the thing is and does. No superlatives,
  rankings or comparisons.
- Keep labels literal. Say "tested with ChatGPT's web UI". Other clients are
  untested; describe them as untested, or leave them out.
- Name the license: MIT for WebMCPlet; Catalog content is CC0-1.0.
- Never present open-source-mac-os-apps as an adopter, user or endorser.
- Where a venue asks who submits, say an AI agent submits on the owner's behalf.

Ask the owner first, in #316 mentioning @snlr308, for repository creation,
code or Catalog changes, DNS or a custom domain, accounts in his name, payment
or binding terms, identity verification, disputes, and contact beyond a
listing.

## Open questions

1. Confirm the repository owner and name: `awesomeopen/webmcplet` as
   recommended here, the earlier PRD destination `JumperMCP/webmcplet`, or
   another name.
2. Confirm option 1 (own repository and a history-preserving move) over option
   2 (keep the folder and auto-mirror it to a read-only repository).
3. How should the untagged CHANGELOG versions 0.2.0 through 0.3.0 be handled in
   the new repository, and should new tags keep the `webmcplet-v*` prefix or
   use `v*`?
4. For the Action's Pages site, is `github.io` enough, or is a custom domain
   wanted (that needs a DNS decision)?
5. Should the WhatWeMade WebMCPlet post go up as soon as the new repository
   exists, or only after the Action and specification land?
6. Should the Catalog pin one release tag of `webmcplet.js`, or follow the
   latest release?

Contribution by WebMCPlet Brücke (AI)
