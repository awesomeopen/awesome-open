# Disposable design previews

Codex owns the active design branch `design/compact-ledger`; dot remains repository administrator and merge coordinator. Keep catalog/source updates with their existing workflow. Each design proposal is reviewed in a draft PR before a production merge.

## Build a reviewable revision

From a clean checkout of the PR head, using an empty output directory:

```sh
python3 scripts/build_design_preview.py --output tmp/design-preview
```

This uses cached repository evidence, runs the existing static builder, copies the style reference and guide, and writes `preview.json` with the full GitHub source SHA. Open `/design/` in the hosted build to review the proposed system; `/` is the current field-guide implementation from that same revision. The reference is not automatically included in the production publisher.

The command requires a clean tracked working tree and no untracked source files. Commit first; do not stamp a dirty build with a clean SHA. Build outside the source tree or under ignored `tmp/`. To inspect locally, serve the output over HTTP rather than opening individual files with `file://`.

## Publish the private disposable preview

1. Build the exact PR head using the command above; retain `preview.json`.
2. Use the owner's private ChatGPT Site as a disposable review host. Open its source through the Sites workflow, then replace its static output with this build. Preserve its hosting manifest and owner-only access.
3. Package, push the Site source, and deploy the saved Site version through Sites. The Site's Git commit is a deployment wrapper; `preview.json` identifies the authoritative GitHub commit.
4. Put the clickable `/design/` URL and GitHub source SHA in the PR description. Review at desktop and narrow widths, including keyboard focus. Record any verification limits.
5. New revisions replace the disposable preview. Update the PR's preview SHA before asking for approval. A URL by itself does not identify a revision.
6. After approval, dot merges through the repository's normal process; the existing main-only publisher remains the production path. The preview can then be reused for the next design branch.

This is an operator-driven publishing workflow, not an automatic GitHub-to-Sites integration. Existing CI still uploads its offline `field-guide-preview` artifact. No Sites credentials belong in this public repository or its artifacts. A preview host may be reused, so check its displayed SHA before approving a PR. Do not publish the private preview to GitHub Pages or change its sharing to make review easier.

## Ledger-first review

The current branch migrates the working catalog. Review `/` for the ledger, `/design/` for the system reference, and the three illustrated records (OpenTofu, OpenRefine, OpenSCAD). Missing artwork must leave no placeholder. Check category changes against the top-three labels. Production remains the main-only publisher after PR approval. See `SPECIMEN-ART.md` for Junge's asset handoff.
