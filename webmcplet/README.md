# WebMCPlet

WebMCPlet gives a curated list read-only [WebMCP](https://webmachinelearning.github.io/webmcp/)
tools and a search panel on the list's own page. A maintainer adds one script and one
generated JSON file; a visiting browser agent can then list sections, search items and
read an item's recorded fields, and a visitor can search and browse from a corner button.
There is no server to install.

This directory has no dependencies, imports nothing from Awesome Open\* and is
MIT-licensed ([LICENSE](LICENSE)). Releases and their checksums are in the
[CHANGELOG](CHANGELOG.md).

## Try it on your list

With Node.js 18 or later, download a release into an empty folder and preview your list
from its README:

```sh
v=webmcplet-v0.1.0
for f in webmcplet.js build.cjs markdown.js try.js LICENSE; do
  curl -fsSLO "https://raw.githubusercontent.com/awesomeopen/awesome-open/$v/webmcplet/$f"
done
node build.cjs try https://github.com/you/awesome-x
```

It reads the README as a raw file, imports it, and serves a plain page of your entries
with the panel at the printed `127.0.0.1` address until you press Ctrl+C. Your site and
repository stay untouched. A local `README.md` path works too; `--assistant on` adds the
[assistant](#assistant). The visitor tools appear in a browser that provides WebMCP, such
as Chrome started with `--enable-blink-features=WebMCP`, as this repository's checks do.

## Add it to your site

WebMCPlet runs on a page you publish, such as a GitHub Pages site; GitHub's README view
runs no scripts.

1. Put `webmcplet.js`, `build.cjs`, `markdown.js` and `LICENSE` from that download in a
   `webmcplet/` folder in your repository; `try.js` serves only the preview. Check that
   the SHA-256 that `node build.cjs version` prints matches the release in the
   [CHANGELOG](CHANGELOG.md).
2. Generate the list document from the README in your site's build. Read the README as a
   raw file, because GitHub's README API truncates large files:

   ```sh
   node build.cjs markdown README.md --title "Awesome X" --page-url https://example.org/awesome-x/ \
     --source-url https://github.com/you/awesome-x --source-revision "$(git rev-parse HEAD)" --out list.json
   ```

   A list with its own structured data can write the [list document](#list-document)
   directly and run `node build.cjs check list.json`.
3. Publish `webmcplet.js` and `list.json` with the page, and add:

   ```html
   <script src="webmcplet.js" data-webmcplet-src="list.json" data-webmcplet-title="Awesome X" defer></script>
   ```

   With `data-webmcplet-title`, `list.json` loads at the first tool call or panel use;
   without it, at page load. The document must be same-origin; redirects are refused.
   Tools register only where the browser provides `document.modelContext` in a secure
   context; the panel works in every browser.

On your page, the script fetches only `list.json` from your origin, makes no analytics
calls, and adds one element whose panel sits in a shadow root, so your styles and markup
stay as they are. When a visitor hides the button, that browser stores one
`localStorage` key. To update, copy a later release and compare its checksum the same way.

| Attribute | Effect |
| --- | --- |
| `data-webmcplet-prefix` | Renames the tools from `list_*` |
| `data-webmcplet-panel` | `button` (default) is a corner button; `banner` is a full-width bar at the top of the page; `off` removes the panel and keeps the tools |
| `data-webmcplet-label` | The button's text, default "Search this list" |
| `data-webmcplet-assistant` | `on` adds the [assistant](#assistant) to the panel |
| `data-webmcplet-assistant-tools` | Tool names the assistant uses, such as the page's own tools (below) |

**Origin-trial token:** Chrome turns WebMCP on for visitors without a flag when the page
carries a token for its origin from [Chrome Origin Trials](https://developer.chrome.com/origintrials/):
`<meta http-equiv="origin-trial" content="TOKEN">`. Visiting agents such as ChatGPT's
browser use the tools without one.

## Tools

| Tool | Returns |
| --- | --- |
| `list_sections` | The list's title and page URL, its sections with item counts, and each declared field with its meaning, source, observation date and how many items record it |
| `list_find` | 12 items from `offset`, with `total`, `matched_fields` and the list's `page_url`. `query`, `section` and `filters` narrow the results |
| `list_get` | One item with every recorded field |

**Search:** every word of `query` must appear in an item's name, aliases, description
or a field declared with `search`. Results rank by the weakest field any word needed,
in that order, then by name, then list order. An exact short alias, such as OBS, matches
whole words only. An empty query lists items in list order.

**Filters:** `filters` maps a field declared with `filter` to one value, such as
`{"run_modes": "server"}`. Items without a recorded value cannot match, so the result
carries `coverage`, for example "33 of 569 items have a recorded run mode."

**Values:** an unrecorded field reads `null`, which means Unknown; `0` stays `0`. Text
fields such as summaries are long, so only `list_get` returns them.

**Errors:** tools return `{ok: false, code, message}`, because Chrome replaces a thrown
error with a generic failure and the agent would lose the recovery instruction. Codes:
`invalid_arguments`, `invalid_query`, `invalid_offset`, `invalid_section`,
`invalid_filter` and `unknown_id`.

## Panel

The corner button opens a modal dialog with search, a section filter and results that
link to each item. The button never opens or moves by itself. Escape or Close returns
focus to the button. A visitor can hide the button with "Hide this button"; the choice is
stored in that browser only and the tools stay registered. The panel loads no other
files and makes no analytics calls.

The panel sits in a shadow root. A page themes it by setting these custom properties on
`[data-webmcplet-host]`: `--webmcplet-bg`, `--webmcplet-fg`, `--webmcplet-accent`,
`--webmcplet-muted`, `--webmcplet-rule`, `--webmcplet-focus`, `--webmcplet-font`,
`--webmcplet-heading-font` and `--webmcplet-radius`. On a page wider than the screen,
or when zoomed, the button and dialog follow the visible part of the page.

## Assistant

With `data-webmcplet-assistant="on"`, the panel offers Chrome's on-device model
([Prompt API](https://developer.chrome.com/docs/ai/prompt-api)) where Chrome reports it
available or downloadable. Downloading needs a click. The model calls the same tools,
one JSON action per turn, at most 8 turns and 30 seconds per turn, and sees short refs
such as `r1` in place of item IDs. The answer's rows come from tool results; the model's
text is labelled as generated and withheld when it names an item the tools did not return.

A page can give the assistant its own tools by pushing definitions shaped like
`registerTool`'s argument onto `window.webmcpletTools` and naming them in
`data-webmcplet-assistant-tools`.

**Status: opt-in.** Measured on 2026-11-10 with Chrome 156 and on-device model
2025.8.8.1141, 20 runs per journey, it passed the family-photo journey (no match)
20 of 20 and the Markdown-editor journey 20 of 20, and selected the requested two
projects for the video-editor comparison in 8 of 20 runs; the other 12 selected three. The pass threshold is 17 of 20
for each journey, so it stays off by default. Method and earlier results:
[experiments/prompt-api-m5](../experiments/prompt-api-m5/README.md),
`scripts/check_webmcplet_assistant.cjs`.

## List document

An example with one hypothetical item:

```json
{
  "webmcplet": 1,
  "list": { "title": "Awesome X", "page_url": "https://example.org/awesome-x/" },
  "sections": [{ "id": "editors", "title": "Editors" }, { "id": "editors/markdown", "title": "Markdown", "parent": "editors" }],
  "fields": {
    "github_stars": { "label": "GitHub stars", "type": "number", "meaning": "Stargazer count of the GitHub repository.",
                      "source": "GitHub REST API", "observed_at": "2026-11-09" }
  },
  "items": [{ "id": "github.com/example/editor", "name": "Example Editor", "url": "https://github.com/example/editor",
              "description": "A Markdown editor.", "sections": ["editors/markdown"], "fields": { "github_stars": 120 } }]
}
```

- **Required:** `list.title`, `list.page_url`, and for each item `id`, `name`, `url`,
  `description` and one or more `sections`. Optional list keys: `description`,
  `source_url`, `source_revision`, `license`, `generated_at`.
- **Identity:** the importer sets `id` to the item's URL without scheme, `www.`,
  fragment, trailing slash or `.git`, in lowercase. An entry listed in several
  sections is one item with several `sections`, so entries that share a URL merge.
- **Optional item keys:** `aliases`, a list of other names, and `link`, the item's
  own page on the list.
- **Fields:** each declares `label`, `meaning` and a `type`: `number`, `string`, `date`,
  `list` (of strings) or `text` (one string or several). `search` applies to string,
  list and text fields; `filter` to string and list fields. `source`, `observed_at`
  and `values` (labels for filter values) are optional.

## Importer

`build.cjs markdown` reads top-level list items, `- [name](url) - description`, and table
rows, `| [name](url) | description |`. Each heading is a section, nested by level, with
leading emoji and a trailing count such as "(72)" removed. Relative and anchor links,
such as a table of contents, are skipped, as are fenced code blocks and indented detail
under an entry. Descriptions become plain text.

Scored on [open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)
`23b6184`, against that list's own `applications.json`: 978 of its 984 items found and
no others; names and descriptions equal for all 978; section sets equal for 975. The 6
missing items do not appear in the README, and the 3 section differences are JSON
categories the README has no heading for. Two apps that share the repository URL
`hg.mozilla.org/mozilla-central`, Firefox and Thunderbird, become one item. Rerun the
score with `scripts/score_webmcplet_importer.cjs`.

## Tests

```sh
node --test test/*.test.js
```

`scripts/check_webmcplet_adoption.cjs` follows [Try it](#try-it-on-your-list) and
[Add it to your site](#add-it-to-your-site) on [a hypothetical list](example/README.md)
in Chromium.
