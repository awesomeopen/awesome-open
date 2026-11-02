# Experimental specimen cabinet

Catalog visitors can collect up to six canonical projects, reorder them and
compare cached evidence in one visible cabinet. Native WebMCP tools and human
controls share the ordered selection, comparison and activity display.

## Tools and state

- `cabinet_find`: literal word matching across names, descriptions and reviewed
  aliases; at most 12 results, plus the current selection revision.
- `cabinet_inspect`: display one project's cached evidence and source links.
- `cabinet_arrange`: replace the ordered selection atomically with zero to six
  distinct canonical IDs, using the current revision. Stale revisions fail.
- `cabinet_compare`: display the current selection's evidence in its saved order.

Arguments are checked in application code as well as JSON Schema. Unknown IDs,
duplicates, extra keys, oversized queries and oversized selections fail before a
state change. Only one tool operation runs at a time. Cancellation aborts pending
fetches and is checked before committing a change. A comparison whose selection
changed during loading fails; human selection changes remain available.

The page retains the latest 20 operation names, actors and outcomes in memory.
It records executed operations, without generated reasoning. The agent/client
provides its own model and connection; the site supplies native tools only.

## Evidence and URLs

Search uses the embedded catalog index. Inspect and compare lazily load the one
same-origin generated `catalog.json`, rejecting redirects and a source-revision
mismatch. The comparison presents Function, GitHub stars, detected license,
repository push, cache status, observation/attempt dates and reviewed alternatives
with their scope, checked date and source. Full records link to the remaining
evidence. Unknown measurements remain null in tool results and read Unknown in
the interface. The cabinet makes no aggregate ranking or recommendations.

The `cabinet` query parameter contains ordered canonical IDs. Reload and browser
history restore the selection. Invalid URLs restore an empty selection with a
notice. Copy URL strips unrelated filters; ordinary selection changes preserve
them. A shared URL reads the published evidence at opening time, rather than
freezing a snapshot. Activity and search text stay out of shared URLs.

Visitor tools accept no URLs, code, repository writes, payments or installation
requests. External source prose is rendered as text and marked untrusted in tool
annotations. Only human-activated source links leave the site. Tools register on
`document.modelContext` in secure contexts, with no cross-origin exposure.
Unsupported browsers show an experimental support notice and retain human controls.

## Design and validation

The cabinet is a folded Catalog instrument with the existing white/Prussian
palette and typography, ordered ruled rows and a labeled horizontally scrollable
evidence table. Reorder/remove controls are keyboard and touch accessible; empty,
loading, cancelled and error states use literal text. Existing artwork is unchanged.

Run `node --test site/test_cabinet.js`, the Python suite and existing builds, then
serve the generated site and run `node scripts/check_cabinet_browser.cjs`.
Use `CHROMIUM_PATH` for an installed browser and `CHROMIUM_NO_SANDBOX=1` only when
required by the execution environment. The dedicated check enables the native
WebMCP feature and verifies discovery/execution, state sharing, invalid inputs,
URL restoration, cancellation and desktop/mobile pixels. Report native bridge
coverage separately from a full natural-language agent/client test.

References checked 2026-11-02: [Chrome imperative API](https://developer.chrome.com/docs/ai/webmcp/imperative-api),
[tool security](https://developer.chrome.com/docs/ai/webmcp/secure-tools), and
[WebMCP draft](https://webmachinelearning.github.io/webmcp/).
Chrome 154 execution takes JSON-string arguments; Chrome's documentation describes
object arguments from 155. Registration uses the actual installed document API.
