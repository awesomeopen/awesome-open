# Awesome Open* brand reference

Version 0.1 · consolidated 2026-10-13 · review baseline

This is the entry point for brand work in this repository. It joins existing
rules, implementation and provenance; it does not restart the identity or make
every historical proposal binding. The new organization and maintenance process
are proposed by this PR. Existing merged behavior is identified separately.

## Read by task

| Need | Authoritative reference |
| --- | --- |
| Purpose, naming, voice and evidence limits | [Foundation](foundation.md), [contribution policy](../CONTRIBUTING.md) |
| Write or simplify reader-facing documentation and help | [Curb your verbosiasm](../.agents/skills/curb-your-verbosiasm/SKILL.md), [writing contract](../site/RETRO-SCRAPERISM.md#writing-style-and-voice) |
| Palette, type, UI, motion | [Visual system](visual-system.md), detailed [Retro-Scraperism guide](../site/RETRO-SCRAPERISM.md), [tokens](../site/design/tokens.css) |
| Design a new page or route | In order: [visual system](visual-system.md), [Retro-Scraperism guide](../site/RETRO-SCRAPERISM.md) including its [route shell](../site/RETRO-SCRAPERISM.md#route-shell-for-sibling-pages-b42), [tokens](../site/design/tokens.css), [visual reference](../site/design/index.html); then open the built `/observatory/` page and `site/observatory.css` as the working model for the frame. Check [decisions](decisions.md) before changing a rule. The Observatory's *data* contract ([OBSERVATORY.md](../site/OBSERVATORY.md)) applies only when the page uses its data; its *shell* applies to every sibling route. [Archive](archive/README.md), [design plan](../site/design_plan.md) and the historical part of [DESIGN.md](../site/DESIGN.md) are background, not instructions |
| Change the specimen plate or ledger record | [Visual system](visual-system.md#specimen-plate-for-every-record-b29), guide section B29, [specimen handoff](../site/SPECIMEN-ART.md) for artwork, then `site/styles.css` and the generator |
| Icons (status, links, controls, setup) | [Icon map](icons.md) and its [manifest](../site/brand/icons.json); proposed (B-PR101-01), no artwork yet |
| Illustration and brand assets | [Illustration](illustration.md), [asset index](assets.md), existing per-family provenance |
| Decisions and unresolved questions | [Authoring guide and generated overview](DECISION-GUIDE.md), [individual records](decisions/), [legacy register and open questions](decisions.md) |
| Skills and editing authority | [Skill policy](skills.md), [pinned files](skills.lock.json) |
| Updating this reference | [Maintenance](maintenance.md), root [agent instructions](../AGENTS.md) |
| Source history and scope of this audit | [Sources](sources.md), [historical documents](archive/README.md) |
| Build, preview and release | [Preview workflow](../site/PREVIEW.md), [contribution/build instructions](../CONTRIBUTING.md) |

Keep detailed implementation rules in their existing guide and tokens; do not
copy their full contents into another editable document. Brand documents link to
those sources and record their role, status and exceptions.

## Authority and status

An explicit current user decision governs the requested change. For established
brand work use the project reference over generic skills or old briefs. Tokens
and source code establish what is implemented. If code and documented intent disagree, record
the discrepancy and fix it through review rather than quietly choosing a winner.

Status vocabulary:

- **User-directed:** explicit decision captured in the project record.
- **Implemented:** present in the audited merged source.
- **Proposed:** awaits review, including new editorial or workflow policy.
- **Historical / superseded:** retained to explain evolution; not instructions.
- **Unresolved:** missing evidence, conflicting sources or a pending decision.

Source baseline: main commit `0be9592` (consolidation); re-audited against
`5b0a7d2` on 2026-10-16 for the specimen plate, Observatory and route shell (B42). Production promotion is recorded in PR
[#26](https://github.com/awesomeopen/awesome-open/pull/26); medium-width corrections
in PR [#27](https://github.com/awesomeopen/awesome-open/pull/27). The private Sites
wrapper is a review output, not the canonical GitHub source.
