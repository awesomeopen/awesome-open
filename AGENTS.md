# Working in Awesome Open*

Read `CONTRIBUTING.md` for catalog and evidence work. For brand, artwork, copy,
interface or design-system changes, start with `brand/README.md` and
`.agents/skills/awesome-open-brand/SKILL.md`. Read the relevant detailed sources
listed there before editing; do not load every design skill for a small fix.

## Source and meaning

- `README.source.md` is the curated catalog. `README.md` and published site output
  are generated. Follow the existing publisher's ownership of metrics and charts.
- Edit the site generator in `scripts/` and authored files in `site/`; do not fix
  only a built HTML file or the disposable Sites deployment wrapper.
- Keep factual labels literal: each value keeps the meaning in the
  [evidence contract](brand/foundation.md#evidence-contract). Follow the evidence
  contracts in `site/`.
- In copy, docs, comments and PR text, say what a value, label or rule is and
  link its method. Do not define it by what it is not, pre-empt conclusions or
  disclaim claims nobody made; limits that matter go once in the method section
  or the "(i)" disclosure. See the writing style in `site/RETRO-SCRAPERISM.md`.
- Explicit user constraints and the current project guide take precedence over
  optional generic design-skill defaults. Preserve the fixed specimen concept,
  white/Prussian system, existing assets and accessible controls unless the task
  explicitly changes them.
- Icons follow `brand/icons.md` and its twin `site/brand/icons.json`. Add or change
  the row in both before drawing or using an icon. Icons restate evidence labels
  and add no judgment of their own; unknown uses the muted state, and shape or
  text always carries state alongside colour.

## Maintenance in the same PR

- New or changed brand rule: update the relevant reference and add a PR-scoped
  record under `brand/decisions/`, following `brand/DECISION-GUIDE.md`. Open a
  useful early draft to get its number; use `B-PR<number>-<ordinal>` IDs. Keep
  merged IDs/filenames stable and declare replacements explicitly. Preserve the
  legacy IDs and links; never append a shared decision table. Make later status
  or evidence corrections only with review evidence; do not redefine old rules.
- Artwork: update its existing provenance/manifest and `brand/assets.md` when its
  role changes; refresh `brand/assets.lock.json` for intentional byte changes.
- Skill dependency: follow `brand/skills.md`; update the snapshot, its provenance,
  checksum lock and explanation together. Do not edit a pinned dependency silently.
- Implementation-only change: say why brand documentation is unaffected in the PR.
- Run `python3 scripts/check_brand.py` and checks relevant to the code changed.
  `--refresh` updates checksums only; it never grants approval.
- Use a focused branch and draft PR. Follow `site/PREVIEW.md` for a requested
  private preview; preserve the audience. Record the exact source revision and
  verification limits. Never merge or modify repository protections by inference.

Read `brand/maintenance.md` for the operating procedure, including Junge handoffs.
These instructions do not create a scheduled task or trigger another agent.
