# Changelog

Each release names the SHA-256 of `webmcplet.js`. Compare it with
`shasum -a 256 webmcplet.js` after copying, or run `node build.cjs version`.

## 0.2.3

`webmcplet.js` SHA-256 `66a0d1e9fddaf8bda26ab9dea5791e3775c5afb41520a808ccf6c7c1d6560708`

- The assistant keeps to the number of items a request names ("two video editors"):
  the response schema caps the answer's items and any tool's `ids` at that number.
- Refs such as `R1` are replaced in either case, and a name the model repeated next to
  its ref ("OpenReel Video: OpenReel Video") appears once.
- Answers show as plain text with their line breaks: Markdown emphasis and link marks
  are removed and list markers become bullets.
- The instructions ask the model to compare recorded values when asked to compare, and
  to answer instead of describing its next steps.

## 0.2.2

`webmcplet.js` SHA-256 `606dfa9038f68d266be71164702a00d114957c703c93c2d732643ab38a1e7086`

- The model download bar takes the panel's accent colour (`--webmcplet-accent`) instead of
  the browser's default.
- Optional `github.js` and `--github-stars on` for `build.cjs markdown` and `try`: a
  `github_stars` field from the GitHub REST API, with `observed_at`; `GITHUB_TOKEN` raises
  the rate limit.

## 0.2.1

`webmcplet.js` SHA-256 `9bedf98b77df038cfd37b45ed0b40e34d7e780438916fd602040b2b92f205e9d`

- Assistant answers read "List result:" and "AI response:", with refs such as `r1` replaced
  by item names. The form's button reads "Send"; the model notes above it are gone.
- A page tool's result can carry `view: {label, href}`; the answer links to it, and the
  link closes the panel and dispatches `webmcplet:view`.

## 0.2.0

`webmcplet.js` SHA-256 `00d5a8baf6317649a6cefc4970fcaf644e740cedeae7b7c4c44550d230b599b6`

- The corner button reads "Search" over a smaller "WebMCPlet" (`data-webmcplet-caption`).
  Pages restyle it through `::part(trigger)`, `::part(label)` and `::part(caption)`.
- The dialog's footer says what WebMCPlet is, offers "Hide the Search button" as a link,
  and names `data-webmcplet-panel="off"` for list admins.

## 0.1.0

`webmcplet.js` SHA-256 `2f0533e87f8c75587a19d648c945e1b0d3272fe29a0f5b65f34db212d8459c46`

- Read-only tools `list_sections`, `list_find` and `list_get`, with structured errors.
- List document schema 1, the README importer and `build.cjs check`.
- The search panel, and the opt-in assistant on Chrome's on-device model.
- `build.cjs try`, a local preview of a list from its README.
