# WebMCPlet

WebMCPlet gives a curated list read-only [WebMCP](https://webmachinelearning.github.io/webmcp/)
tools on the list's own page. A maintainer adds one script and one generated JSON file;
a visiting browser agent can then list sections, search items and read an item's
recorded fields. There is no server to install.

Status: tools and build step only. The panel and local assistant are planned in the
[PRD](../PRD/2026-11-04_WebMCP-for-Awesome-lists.md#delivery). This directory has no
dependencies, imports nothing from Awesome Open\* and is MIT-licensed ([LICENSE](LICENSE)).

## Add it to a list

1. Generate the list document from the README, read as a raw file because GitHub's
   README API truncates large files:

   ```sh
   node build.cjs markdown README.md --title "Awesome X" --page-url https://example.org/awesome-x/ \
     --source-url https://github.com/you/awesome-x --source-revision "$(git rev-parse HEAD)" --out list.json
   ```

   A list with its own structured data can write the document directly and run
   `node build.cjs check list.json`.
2. Publish `webmcplet.js` and `list.json` with the page, and add:

   ```html
   <script src="webmcplet.js" data-webmcplet-src="list.json" defer></script>
   ```

   `data-webmcplet-prefix` renames the tools from `list_*`. The document must be
   same-origin; redirects are refused. Tools register only where the browser provides
   `document.modelContext` in a secure context.

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
