# Skills and ownership

| Skill | Role | Editing authority | Repository treatment |
| --- | --- | --- | --- |
| `awesome-open-brand` | Read/update the current project contract | This repository | `.agents/skills/awesome-open-brand/`; installed routing mirror for cross-chat use |
| `retro-scraperism` | Reusable interface/graphic language | Owner's reusable Skills workspace | Exact pinned snapshot including references and UI assets |
| `speculative-fossoligy` | Reusable drawing language | Owner's reusable Skills workspace | Exact pinned snapshot including style atlas and UI assets |
| `gpt-taste` | Optional composition/refinement aid | Upstream/installed skill | Not a project dependency; no automatic theme/font/motion substitution |
| `imagegen-frontend-web` | Optional section reference-image workflow | Owner's installed skill | Not a project dependency; one image per requested section when invoked |
| `redesign-existing-projects` | Optional audit aid | Upstream/installed skill | Installed separately from taste-skill; no automatic project-wide redesign |
| `brandkit` | Optional future visual summary | Upstream if adopted | Evaluated, not installed; no dependency or new identity implied |

[skills.lock.json](skills.lock.json) pins every bundled reusable-skill file by
SHA-256, along with its source name and captured Skills commit. The originals are
owner-maintained project-authored instructions, not copied third-party images.
Their reference files contain external links; those links grant no rights to
reproduce the referenced artwork. Existing repository licensing applies subject
to the notices in [assets.md](assets.md).

## Update a reusable skill

1. Make general-purpose changes in the owner's Skills workspace; validate and
   persist them using its normal Git-backed save procedure.
2. Read the new version and all referenced resources. Compare it with the pinned
   repository copy. Import the complete skill folder intentionally in a focused PR.
3. Update source revision/date in the lock, then refresh checksums. Explain what
   changed and whether the Awesome Open project overrides still apply.
4. Review and merge using the normal process. Until then the old pin remains the
   project's baseline. A newer installed skill never silently changes the project.

For Awesome Open-specific changes, edit project rules rather than changing the
portable skill just to create an exception. The portable Retro-Scraperism snapshot
already delegates to the current project guide.

## Update the project router

Edit `.agents/skills/awesome-open-brand/` in a PR. After acceptance, copy its exact
files into the installed skill, validate, and commit/push the Skills workspace.
Report the synced repository commit. Do not create two independent copies of the
brand facts inside both skill files and documentation.

The initial installed router is draft-aware: it checks for the consolidation
branch when the reference is absent on main. Installation does not mark the PR
merged. Future syncs follow merged project revisions.

## Agent compatibility

`.agents/skills/` provides repository-local skill files; loading behavior varies
by agent. `AGENTS.md` and explicit file paths supply the fallback. An agent that
cannot load skills can still read the Markdown instructions. Do not invent a CLI
command or claim a skill was invoked merely because its name appears in a prompt.

No scheduled updater, automatic upstream pull, or third-party skill installer is
added. Skill pins change through review.
