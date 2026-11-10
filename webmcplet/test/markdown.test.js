"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { importMarkdown, leadingLink, headingTitle } = require("../markdown.js");
const { validate } = require("../webmcplet.js");

const README = `# Awesome Test

## Contents
- [Editors](#editors)
- [Contributing](CONTRIBUTING.md)

## 📝 Editors (3)
- [[Un]Mute](https://github.com/a/unmute) - Mutes the microphone.
- [Writer](https://github.com/b/writer) ![macOS 14+](https://img.shields.io/badge/x) - A **Markdown** editor with [CommonMark](https://commonmark.org).

  **Website:** [https://writer.example](https://writer.example)

### Markdown
* [MarkIt](https://github.com/c/markit/) – Previews Markdown.

\`\`\`
- [Ignored](https://example.org/ignored) - Inside a code block.
\`\`\`

## Tools
| Name | Description |
| --- | --- |
| [Writer](https://www.github.com/B/Writer.git) | Listed twice. |
| [Shell](https://shell.example) | A shell. |

## License
Text only.
`;

test("headings become nested sections without emoji or counts", () => {
  assert.equal(headingTitle("📝 Editors (3)"), "Editors");
  const { doc } = importMarkdown(README, { title: "Awesome Test", page_url: "https://example.org/" });
  assert.deepEqual(doc.sections, [
    { id: "awesome-test", title: "Awesome Test" },
    { id: "awesome-test/editors", title: "Editors", parent: "awesome-test" },
    { id: "awesome-test/editors/markdown", title: "Markdown", parent: "awesome-test/editors" },
    { id: "awesome-test/tools", title: "Tools", parent: "awesome-test" }
  ]);
  assert.deepEqual(validate(doc), []);
});

test("entries keep bracketed names, plain descriptions and one identity per URL", () => {
  const { doc, counts } = importMarkdown(README, { title: "Awesome Test", page_url: "https://example.org/" });
  assert.deepEqual(doc.items.map(i => [i.id, i.name, i.description, i.sections]), [
    ["github.com/a/unmute", "[Un]Mute", "Mutes the microphone.", ["awesome-test/editors"]],
    ["github.com/b/writer", "Writer", "A Markdown editor with CommonMark.", ["awesome-test/editors", "awesome-test/tools"]],
    ["github.com/c/markit", "MarkIt", "Previews Markdown.", ["awesome-test/editors/markdown"]],
    ["shell.example", "Shell", "A shell.", ["awesome-test/tools"]]
  ]);
  assert.deepEqual(counts, { entries: 5, items: 4, skipped: 2 });
});

test("leadingLink reads bold links and ignores text without one", () => {
  assert.deepEqual(leadingLink("**[Bold](https://x.example)** - d").name, "Bold");
  assert.equal(leadingLink("Plain text"), null);
});
