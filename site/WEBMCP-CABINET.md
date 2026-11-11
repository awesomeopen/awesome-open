# Experimental specimen cabinet

Catalog visitors can collect up to six canonical projects, reorder them and
compare cached evidence in one visible cabinet. Native WebMCP tools and human
controls share the ordered selection, comparison and activity display.

## Tools and state

- `cabinet_find`: the Catalog's search, through the [shared matcher](#search).
  Returns 12 results from `offset`, the `total`, each result's `matched_fields`
  and the current selection revision. Zero matches return a `message` naming this
  catalog.
- `cabinet_inspect`: display one project's cached evidence and source links.
- `cabinet_arrange`: replace the ordered selection atomically with zero to six
  distinct canonical IDs, using the current revision. Stale revisions fail.
- `cabinet_compare`: display the current selection's evidence in its saved order.

While a selection exists, `cabinet_find`, `cabinet_arrange` and `cabinet_compare`
return `cabinet_url`, the [shared URL](#evidence-and-urls) for that selection, and the
compare description asks the caller to give it to the person. A person using an
agent's cloud browser never sees the page, so the link is how they open the comparison.
The page's assistant gets neither the field nor those sentences, because its visitor is
already on the page.

Arguments are checked in application code as well as JSON Schema. Unknown IDs,
duplicates, extra keys, oversized queries and oversized selections fail before a
state change. Only one tool operation runs at a time. Cancellation aborts pending
fetches and is checked before committing a change. A comparison whose selection
changed during loading fails; human selection changes remain available.

Successful tool results carry `ok: true`. Failures return
`{ok: false, code, message}`, because Chrome replaces a thrown error with a generic
failure and the caller would lose the recovery instruction. The codes are
`invalid_arguments`, `invalid_query`, `invalid_offset`, `invalid_ids`,
`stale_revision`, `selection_changed`, `empty_selection`, `busy`, `cancelled`,
`search_unavailable`, `evidence_unavailable` and `catalog_changed`.

An agent's `empty_selection` names the next step: "Call cabinet_arrange with ids from
cabinet_find and its revision, then call cabinet_compare." In the
[Prompt API test](../experiments/prompt-api-m5/README.md) the on-device model recovered
with that message and not with "Select at least one project first.", which the page's
own Compare button still shows.

The page also hands the four tools to [WebMCPlet](../webmcplet/README.md) through
`window.webmcpletTools`, so its opt-in assistant can operate the same selection; its
calls appear as "Assistant" in the activity log. The page registers WebMCPlet's
`list_sections`, `list_find` and `list_get` beside these tools, from the same catalog.

The page retains the latest 20 operation names, actors and outcomes in memory.
It records executed operations, without generated reasoning. The agent/client
provides its own model and connection.

## Search

`site/search.js` is the one matcher behind the Catalog's search box, the Cabinet's
form and `cabinet_find`, so they return the same IDs, order and unknown values.

- **Fields:** name, reviewed aliases, description, reviewed alternatives, function
  summary and feature notes. Every query word must appear in at least one of them.
- **Order:** the rank is the weakest field any word needed, in the order above; ties
  go by name. With no query, the order is GitHub stars. Other orders are the Catalog's
  explicit sort choices.
- **Loading:** names, aliases, descriptions and alternatives are in the embedded
  index. Summaries and notes are in `search-text.json`, fetched at the first search,
  because embedding them would nearly double `index.html`'s gzip size. Until it
  arrives the Catalog searches the embedded fields, then renders again. If it fails,
  the Catalog says what it covered and `cabinet_find` returns `search_unavailable`.

## Evidence and URLs

Inspect and compare lazily load the one
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
When the publish build has `GOOGLE_ORIGIN_TRIAL_TOKEN`, the Catalog carries Chrome's
WebMCP origin-trial token for `awesomeopen.github.io`, which turns the API on for
visitors' Chrome without a flag.
Unsupported browsers show an experimental support notice and retain human controls.

## Design and validation

The cabinet is a folded Catalog instrument ([B-PR304-01](../brand/decisions/B-PR304-01.md)).
Its mist heading names it and states its purpose, "Compare up to six projects side by
side", with the selection count. Opened, it reads as three numbered steps: Find,
Arrange and Compare, followed by the cabinet URL. Native WebMCP status, the activity log
and the method sit in "Agents, activity & method". Selection rows are ruled; the evidence
table scrolls horizontally in a labeled region. Compare is disabled with no selection.
Controls are keyboard and touch accessible; empty, loading, cancelled and error states
use literal text. Existing artwork is unchanged.

Run `node --test site/test_search.js site/test_cabinet.js`, the Python suite and existing builds, then
serve the generated site and run `node scripts/check_cabinet_browser.cjs`; CI runs
it as the `cabinet` suite of `scripts/run_browser_checks.py`.
Use `CHROMIUM_PATH` for an installed browser and `CHROMIUM_NO_SANDBOX=1` only when
required by the execution environment. The dedicated check enables the native
WebMCP feature and verifies discovery/execution, state sharing, structured errors,
identical results between the Catalog and `cabinet_find`, the PRD's search journeys,
a failed `search-text.json`, URL restoration, cancellation and desktop/mobile pixels. Report native bridge
coverage separately from a full natural-language agent/client test.

References checked 2026-11-02: [Chrome imperative API](https://developer.chrome.com/docs/ai/webmcp/imperative-api),
[tool security](https://developer.chrome.com/docs/ai/webmcp/secure-tools), and
[WebMCP draft](https://webmachinelearning.github.io/webmcp/).
Chrome 154 execution takes JSON-string arguments; Chrome's documentation describes
object arguments from 155. Registration uses the actual installed document API.
