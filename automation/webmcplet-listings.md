# WebMCPlet listings

Status: Version 1, 2026-11-10. The owner assigned this job to the agent on
2026-11-10. Tracking issue [#316](https://github.com/awesomeopen/awesome-open/issues/316)
is open. A weekly routine in the assistant (Mondays around 9:00 America/New_York)
runs the cadence below; the monthly pass runs in the first week of each month.
Editing, cloning or merging this file does not register a schedule.

Signing: contributions prepared by the assistant for this job are signed
"WebMCPlet Brücke (AI)" in pull request and commit descriptions and in the
tracking issue. WebMCPlet Brücke is the Grok Bot assistant working for the
repository owner. Owner review and merge remain separate and are not signed by
the assistant.

## The job in one paragraph

List [WebMCPlet](../webmcplet/README.md) and the
[Awesome Open\* Catalog](https://awesomeopen.github.io/awesome-open/) in the
directories and curated lists where people look for WebMCP tools, keep those
listings accurate, answer reviewers, and find new venues. The
[listings handover](../PRD/2026-11-10_WebMCPlet-listings-handover.md) is the
contract: what is listed, how a listing is written, the venues, the schedule,
and what needs the owner. This file records how the job runs; it does not
repeat the handover's rules.

## Runner and authority

| Item | Value |
| --- | --- |
| Job owner | Repository owner (GitHub `snlr308`) |
| Runner | WebMCPlet Brücke, a Grok Bot assistant for the owner |
| Writes in this repository | Tracking issue #316 through the GitHub API, and owner-authorized changes to this file through a draft PR |
| Writes elsewhere | Pull requests to external lists, from the owner's GitHub account; venue forms where the handover allows them |
| Credentials | None new. No token, secret or account is added to this repository |
| Reporting | The owner's WebMCPlet Brücke conversation and issue #316 |
| Merge authority | Owner only, for this repository. External merges belong to each list's maintainers |

## Sources of truth

Re-read before each submission or update, in this order, as the handover sets:
[WebMCPlet README](../webmcplet/README.md), [CHANGELOG](../webmcplet/CHANGELOG.md),
[Cabinet contract](../site/WEBMCP-CABINET.md),
[research notes](../PRD/2026-11-06_WebMCPlet-research.md) and
[LICENSE.md](../LICENSE.md). Facts that a listing states (release, tool names,
tested client, licenses) come from these files on fresh `main`, never from an
earlier listing or from chat history.

## State

Issue [#316](https://github.com/awesomeopen/awesome-open/issues/316), "WebMCPlet
listings", is the job's memory. Its top post holds the current table (venue,
subject, state, link, last checked, next action); each action gets a dated
comment with what was submitted, the reply and what changed. States are those
in the handover. Read the issue first on every run. Rejected venue candidates
are recorded there with the reason, so they are not reconsidered each month.

## Cadence

| Trigger | Work |
| --- | --- |
| Weekly | Check every `submitted` and `changes requested` entry; answer reviewers and make requested edits within the handover's rules. At most one follow-up per venue per week |
| New `webmcplet-v*` tag | Recheck facts against the CHANGELOG; update listings that name a version or a tool |
| Monthly | Confirm each `listed` entry is present, its links resolve and its text matches the sources; fix drift. Recheck `skipped` venues for activity. Then search for new venues |
| WebMCPlet moves to [JumperMCP/webmcplet](https://github.com/JumperMCP/webmcplet) | Update every listing's link |

## Run

1. Read issue #316, then the sources of truth on fresh `main`.
2. Verify each venue in scope for this run: active (a push to the default
   branch or a merged pull request in the last six months), how it accepts
   submissions, any rule on AI-generated contributions, and whether the
   subject is already listed.
3. Write the entry in the venue's own format and section, from the sources.
   Follow the venue's rule on pull request count (for example, one link per
   pull request) over the handover's one-per-venue default.
4. Submit through the venue's own route. Every pull request body says an AI
   agent submits on the owner's behalf.
5. Update the table in #316 and add a dated comment with links.
6. Report new submissions, replies and blockers to the owner. Runs with no
   change stay quiet.

## Boundaries

The handover's [Ask the owner first](../PRD/2026-11-10_WebMCPlet-listings-handover.md#ask-the-owner-first)
and [Never](../PRD/2026-11-10_WebMCPlet-listings-handover.md#never) lists
govern. In short: payment, binding terms, accounts or identity in the owner's
name, DNS, code changes, disputes, bug or security reports and offers beyond a
listing go to @snlr308 in #316 first. No resubmission after a decline, no
duplicate submissions, no social media, forums, chat or email beyond a venue's
own form, and no owner details beyond what a form requires. In this
repository, the job writes only issue #316 and, when the owner asks, this file.

## Verification

Before each submission, check the entry against the sources and the listing
rules: literal labels, no superlatives or comparisons, MIT for WebMCPlet,
CC0-1.0 for catalog content, "tested with ChatGPT's web UI", untested clients
called untested or left out, and
[open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)
never named as an adopter. After submitting, confirm the pull request or form
receipt exists and link it in #316. A missing tool, access failure or block is
reported, not routed around.

## Current state, 2026-11-10

From the first verification on 2026-11-10; #316 holds the live table.

| Venue | Subject | State | Note |
| --- | --- | --- | --- |
| [WebMCP Directory](https://webmcp.com) | Catalog | listed | [Site page](https://webmcp.com/sites/awesomeopen.github.io), tools verified 2026-11-06 with the four `cabinet_*` tools. A rescan to add `list_*` needs a report email from the owner |
| [Browser Use directory](https://browser-use.com/webmcp) | Catalog | skipped | Not found; built from scans, no submission route |
| WebMCP Registry (`webmcp-registry.dev`) | Catalog | blocked | Accepts unverified entries, but needs an account in the owner's name and an ownership statement in its terms; owner decision needed |
| [webfuse-com/awesome-webmcp](https://github.com/webfuse-com/awesome-webmcp) | Both | to submit | One pull request |
| [webmachinelearning/awesome-webmcp](https://github.com/webmachinelearning/awesome-webmcp) | Both | to submit | One pull request |
| [yigitkonur/awesome-webmcp](https://github.com/yigitkonur/awesome-webmcp) | Both | to submit | Two pull requests, one link each; no merge since 2026-03-18 |
| [Leanmcp/awesome-webmcp](https://github.com/Leanmcp/awesome-webmcp) | Both | skipped | No push since 2026-03-10 and no merged pull request |
| [ilkerulusoy/awesome-webmcp](https://github.com/ilkerulusoy/awesome-webmcp) | Both | skipped | No merge or default-branch push since 2026-04-28 |

## Changelog

| Date | Version | Change | By |
| --- | --- | --- | --- |
| 2026-11-10 | 1 | Initial job description: runner, sources, state in #316, cadence, boundaries, and the first venue verification | WebMCPlet Brücke (AI) |
