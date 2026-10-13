# Disposable design previews

Codex owns the active design branch `design/exhibition-preview-1`; dot remains repository administrator and merge coordinator. Keep catalog/source updates with their existing workflow. Each design proposal is reviewed in a draft PR before a production merge.

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

## Exhibition preview 01

Open `/exhibition.html` for Infrastructure & DevOps: three illustrated category leaders, the complete category ledger, and expandable evidence records. `/` remains the complete directory for comparison. Only the preview builder and PR checks include this route; the production publisher does not. The proposed design is not approved for production.

## Jar study / preview 02

Active branch: `design/jar-preview-2`. Review `/jars/jars.html` on the private host. The bundle's `preview.json` identifies the exact source SHA. `jars.html` adds the three-vessel hero above the full current ledger; `index.html` remains the production-shaped control. Use Shadows/Baseline to compare ground treatments. Preview #1 and the ledger review remain at their previous URLs. The jar builder is called only by design-preview builds and PR CI.

## Photographic jar study / preview 03

Active branch: `design/photographic-jars`. Review `/jars-03/jars.html` on the private host. Seven independent photographic glass assets surround replaceable original specimens, tallest centered, shadow-only ground. Hover/focus annotations overlap neighbors; tapping selects before navigation. The previous three-jar study remains at `/jars/jars.html`. Verify `preview.json` for the GitHub SHA.

## Depth motion / preview 04

Active branch: `design/jar-depth-motion`. Review `/jars-04/jars.html`. Pointer proximity and selection bring photographic jars forward from 82% to 110% scale, with shared scene movement, vertical tilt and specimen/reflection depth. Preview 03 remains at `/jars-03/jars.html` for comparison. Native record links, touch/keyboard controls and reduced-motion fallback remain available.


## Underlight and life / preview 05

Active branch: `design/jar-depth-motion`. Review `/jars-05/jars.html`. Hover/focus/tap adds underlighting, limited opening of removable lids and a brief vapor release. Contents make small staggered movements while idle. Pause motion and reduced-motion settings stop decorative animation. Preview 04 remains available for comparison.
