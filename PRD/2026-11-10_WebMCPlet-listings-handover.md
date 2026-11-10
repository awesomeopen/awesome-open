# Handover: WebMCPlet and Awesome Open\* listings

- **Date:** 2026-11-10
- **Owner:** Project owner, GitHub [@snlr308](https://github.com/snlr308)
- **Agent:** a personal-assistant agent, such as Muse, working on the owner's behalf
- **Related:** [WebMCPlet PRD](2026-11-04_WebMCP-for-Awesome-lists.md),
  [research notes](2026-11-06_WebMCPlet-research.md), [WebMCPlet README](../webmcplet/README.md),
  [CHANGELOG](../webmcplet/CHANGELOG.md), [release 0.1.0](https://github.com/awesomeopen/awesome-open/releases/tag/webmcplet-v0.1.0)

Your job is to get WebMCPlet and the Awesome Open\* Catalog listed in the directories
and curated lists where people look for WebMCP tools, to keep those listings accurate,
and to find new places to list them. The owner delegates this work to you: within the
limits below, you submit, update and follow up without asking. Record everything in one
tracking issue so the owner can read the state at any time.

## What you list

| Subject | What it is | Link | Where it fits |
| --- | --- | --- | --- |
| WebMCPlet | An MIT-licensed, dependency-free script that gives a curated list read-only WebMCP tools and a search panel on the list's own page, from one generated JSON file | [webmcplet/](https://github.com/awesomeopen/awesome-open/tree/main/webmcplet) | Curated lists of WebMCP libraries and tools |
| Awesome Open\* Catalog | A catalog of software named Open; its page exposes WebMCP tools for searching, inspecting and comparing projects | [awesomeopen.github.io/awesome-open](https://awesomeopen.github.io/awesome-open/) | Directories of sites with live WebMCP tools; curated lists' demo sections |

Take every claim from these sources, in this order: the [WebMCPlet README](../webmcplet/README.md),
the [CHANGELOG](../webmcplet/CHANGELOG.md), the [Cabinet contract](../site/WEBMCP-CABINET.md)
and the [research notes](2026-11-06_WebMCPlet-research.md). Re-read them before each
submission or update, because they change.

Facts as of 2026-11-10, for orientation:

- Latest release: 0.1.0, tag `webmcplet-v0.1.0`. Adopters copy the files; nothing is
  hosted or published to a package registry.
- Tools on the Catalog page: `cabinet_find`, `cabinet_inspect`, `cabinet_arrange`,
  `cabinet_compare`, plus WebMCPlet's `list_sections`, `list_find` and `list_get`.
- Client tested by this project: ChatGPT's web UI cloud browser, which called the Catalog's
  tools on 2026-11-06 and 2026-11-10. Other clients are untested; the research notes say which.
- The built-in assistant on Chrome's on-device model is opt-in and off on the Catalog.
- The page carries a WebMCP origin-trial token for `awesomeopen.github.io`.

## How to write a listing

- Follow the venue's own format, category names and length limits exactly.
- Say what the thing is and does, in the venue's register. Use the one-line description
  in the table above, shortened if needed. No superlatives, rankings or comparisons with
  other projects.
- Keep labels literal: "read-only tools", "tested with ChatGPT's web UI", "opt-in
  assistant". Describe untested clients as untested, or leave them out.
- Name the license (MIT for WebMCPlet; the catalog content is CC0-1.0, see
  [LICENSE.md](../LICENSE.md)).
- [open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)
  was a local test fixture only. Never present it as an adopter, user or endorser.
- Where a venue asks who submits, say an AI agent submits on the owner's behalf. Follow
  any venue rule on AI-generated contributions; if a venue forbids them, skip it and
  record why.

## Venues found so far

Checked 2026-11-06; verify each before acting. Details are in the
[research notes](2026-11-06_WebMCPlet-research.md#alternatives-and-adjacent-resources).

| Venue | Subject | Route | Starting state |
| --- | --- | --- | --- |
| [WebMCP Directory](https://webmcp.com) | Catalog | URL and email form; it scans live tools and reviews sites | To submit |
| [Browser Use directory](https://browser-use.com/webmcp) | Catalog | None stated; built from scans | Check whether the Catalog is listed; find a route if one exists |
| WebMCP Registry (`webmcp-registry.dev`) | Catalog | DNS TXT verification, then a sync CLI | Blocked: a `github.io` project site has no DNS control. Record and skip |
| [webfuse-com/awesome-webmcp](https://github.com/webfuse-com/awesome-webmcp) | Both | Pull request | To submit |
| [webmachinelearning/awesome-webmcp](https://github.com/webmachinelearning/awesome-webmcp) | Both | Pull request | To submit |
| [yigitkonur/awesome-webmcp](https://github.com/yigitkonur/awesome-webmcp) | Both | Pull request | To submit |
| [Leanmcp/awesome-webmcp](https://github.com/Leanmcp/awesome-webmcp) | Both | Pull request | To submit |
| [ilkerulusoy/awesome-webmcp](https://github.com/ilkerulusoy/awesome-webmcp) | Both | Pull request | Low priority: 2 stars on 2026-11-06 |

For a curated list on GitHub: read its README and CONTRIBUTING, pick the section that
matches the subject, add one entry per subject in the list's format, and open one pull
request. Check that the list is active (a push or merged pull request in the last six
months) before spending effort on it.

## The tracking issue

Open one issue in [awesomeopen/awesome-open](https://github.com/awesomeopen/awesome-open/issues)
titled "WebMCPlet listings", and keep its first comment as the current table:

| Venue | Subject | State | Link | Last checked | Next action |
| --- | --- | --- | --- | --- | --- |

States: `to submit`, `submitted`, `changes requested`, `listed`, `declined`, `skipped`,
`blocked`. Add a dated comment for each action: what you submitted, the reply you got,
what you changed. Write in the same literal style as the listings. The issue is your
memory between runs; read it first every time.

## Schedule

- **Weekly:** check every `submitted` and `changes requested` entry. Answer reviewer
  questions and make requested edits within these rules.
- **On a new release** (a new `webmcplet-v*` tag): update listings that name a version,
  and recheck facts against the CHANGELOG.
- **Monthly:** confirm each `listed` entry is still present, links resolve and the text
  still matches the sources; fix drift. Then search for new venues.
- **When WebMCPlet moves** to [JumperMCP/webmcplet](https://github.com/JumperMCP/webmcplet),
  as the PRD plans once someone outside adopts it: update every listing's link.

## Finding new venues

Look for curated lists, directories and registries of WebMCP tools, libraries, demos or
sites with live tools, and for awesome lists on browser agents or MCP with a WebMCP
section. Add a venue to the issue when it is active, accepts submissions, and a
WebMCPlet or Catalog entry fits its stated scope. Record rejected candidates with the
reason, so they are not reconsidered every month.

## Ask the owner first

Comment in the tracking issue and mention @snlr308, then wait, when a venue or reply:

- asks for payment, a paid tier, a contract or terms that bind the owner;
- needs an account in the owner's name, identity verification, DNS changes or a domain;
- asks for changes to WebMCPlet's code, the Catalog or this repository;
- disputes a claim, reports a bug or security problem, or raises a rights question;
- offers a partnership, interview, feature or other contact beyond the listing.

## Never

- Change files, settings, secrets or pull requests in this repository; your only write
  here is the tracking issue.
- Ask other list maintainers to adopt WebMCPlet, or deploy it to anyone's site; the PRD
  keeps that with the owner.
- Resubmit to a venue that declined, open duplicate submissions, or chase reviewers more
  than once a week.
- Post on social media, forums or chat, or send email beyond a venue's own submission
  form, unless the owner adds that to this document.
- Share the owner's personal details beyond what a venue's form requires.

## Getting started

1. Read this document, the WebMCPlet README and the research notes' alternatives section.
2. Open the tracking issue with every venue above in its starting state.
3. Verify each venue: active, open to submissions, AI policy, and whether the subject is
   already listed.
4. Submit to the active venues, one pull request or form per venue, and record each.
5. Continue on the schedule above.

Contribution by Claude Code (AI)
