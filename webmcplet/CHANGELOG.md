# Changelog

Each release names the SHA-256 of `webmcplet.js`. Compare it with
`shasum -a 256 webmcplet.js` after copying, or run `node build.cjs version`.

## 0.1.0

`webmcplet.js` SHA-256 `2f0533e87f8c75587a19d648c945e1b0d3272fe29a0f5b65f34db212d8459c46`

- Read-only tools `list_sections`, `list_find` and `list_get`, with structured errors.
- List document schema 1, the README importer and `build.cjs check`.
- The search panel, and the opt-in assistant on Chrome's on-device model.
- `build.cjs try`, a local preview of a list from its README.
