---
name: awesome-open-brand
description: Apply and maintain Awesome Open* brand decisions, design documentation, skills and asset provenance alongside changes to its website or catalog interface. Use for Awesome Open* design work, brand consolidation, artwork handoffs or drift audits; not for unrelated brands or routine catalog metadata refreshes.
---

# Awesome Open* brand maintenance

## Resolve the working source

Use the `awesomeopen/awesome-open` repository. Read its root `AGENTS.md`, `brand/README.md`, `brand/DECISION-GUIDE.md`, relevant individual records in `brand/decisions/`, the legacy `brand/decisions.md`, and the relevant references from that index. Check the current branch and working tree before editing. Use a focused branch from the current base and preserve other work.

This installed skill is a routing workflow; the brand rules live in the repository. In a repository checkout, prefer the matching `.agents/skills/awesome-open-brand/SKILL.md`. If the brand reference is absent on the selected revision, check whether the consolidation PR is still pending; do not pretend its contents are merged. Resolve the intended branch or report the limitation. Do not guess current colors, approval status, asset selections or branch names from chat memory.

## Apply the project contract

1. Establish the bounded task and which existing decisions it affects.
2. Read `brand/visual-system.md` and the detailed guide it points to for interface work. For a new page, follow the route shell in that guide and open the built Observatory and `site/observatory.css` as the working model; a heading and paragraphs on the ledger stylesheet is not a finished page. For the expanded record, read the specimen plate rules (B29). Read any feature contract the change touches (`site/OBSERVATORY.md`, `site/WEEKLY-DRAWS.md`, `site/SPECIMEN-ART.md`). For artwork, read `brand/illustration.md` and the repository's pinned FOSSoligy skill. Compare the result with `site/design/index.html` and its retired-patterns list; if that reference is out of date, fix it in the same PR.
3. Preserve explicit user constraints and approved project choices over generic design-skill defaults. Distinguish implemented behavior from newly proposed policy. Keep evidence labels factual and sources traceable.
4. Edit source files, not generated HTML or the disposable Sites wrapper alone. For source-only copy edits, update the generator. Follow `site/PREVIEW.md` for any preview and publication workflow.
5. Update the affected brand rule, decision entry, asset provenance or skill pin in the same PR. For implementation-only changes, record why no brand rule changed in the PR body. Never invent an approval to close an unresolved decision. When implementing an approved prototype or mock, compare it with the result section by section and list each prototype element left out or changed, with the reason, in the PR body and the decision entry.
6. Run `python3 scripts/check_brand.py`. If asset bytes or a pinned skill changed intentionally, update their source provenance and run `python3 scripts/check_brand.py --refresh` before checking again. A checksum refresh does not constitute design approval.
7. Run the checks appropriate to the actual code/art change. State unavailable visual checks honestly. Submit a draft PR identifying the exact source revision; do not merge or change hosting access merely because this skill was invoked.

## Maintain skills without drift

For a new decision, open a useful early draft PR to obtain its number, then add
`brand/decisions/B-PR<number>-<ordinal>.md` using the authoring guide's metadata.
Each PR owns its namespace; do not reserve a global counter or append the legacy
table. Keep merged IDs and filenames stable. Declare full replacements in the
new record's `supersedes` list; explain partial changes with ordinary citations.
Generate the combined overview into ignored output, not a shared tracked table.
Run the decision checks with the real base SHA and PR number before review.

Read `brand/skills.md` and `brand/skills.lock.json`. This workflow's authority is the project repository; an installed copy is a convenience mirror. Reusable Retro-Scraperism and Speculative FOSSoligy originals remain owner-maintained Skills; their repository copies are pinned dependencies, updated deliberately with a reviewed diff and all referenced files. General design tools are optional and never supersede the project contract.

After an approved workflow change, sync this skill and its agent metadata from the merged repository revision to the installed Skills workspace, validate, commit and push that workspace through the available skill persistence mechanism. Record or report the synced repository revision. Do not silently promote an unmerged workflow proposal to the installed copy.

## Junge and automation

An agent must actually read the repository instructions to follow them. When handing work to Junge or a new agent, explicitly direct it to `AGENTS.md` and `brand/README.md`, then give the concrete task. Skills and CI do not initiate work by themselves. Routine evidence refreshes retain their existing workflow; no new schedule is implied. A requested periodic audit should propose fixes in a draft PR, never rewrite accepted design or merge automatically.
