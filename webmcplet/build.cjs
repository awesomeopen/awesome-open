#!/usr/bin/env node
/* WebMCPlet build step. MIT License; see LICENSE.
 *
 *   node build.cjs markdown README.md --title "Awesome X" --page-url https://example.org/awesome-x/ \
 *     [--source-url URL] [--source-revision SHA] [--license SPDX] [--out list.json]
 *   node build.cjs check list.json
 *
 * Read the README from a raw file: GitHub's README API truncates large files.
 */
"use strict";
const fs = require("node:fs");
const { validate } = require("./webmcplet.js");
const { importMarkdown } = require("./markdown.js");

function options(args) {
  const out = { positional: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) out[args[i].slice(2)] = args[++i];
    else out.positional.push(args[i]);
  }
  return out;
}

function fail(message) {
  process.stderr.write(message + "\n");
  process.exit(1);
}

function check(doc, label) {
  const problems = validate(doc);
  if (problems.length) fail(label + " is invalid:\n  " + problems.join("\n  "));
}

const [command, ...rest] = process.argv.slice(2);
const opts = options(rest);
if (command === "markdown") {
  const [source] = opts.positional;
  if (!source || !opts.title || !opts["page-url"]) fail("Usage: build.cjs markdown README.md --title TITLE --page-url URL [--out list.json]");
  const list = { title: opts.title, page_url: opts["page-url"], generated_at: new Date().toISOString() };
  if (opts["source-url"]) list.source_url = opts["source-url"];
  if (opts["source-revision"]) list.source_revision = opts["source-revision"];
  if (opts.license) list.license = opts.license;
  const { doc, counts } = importMarkdown(fs.readFileSync(source, "utf8"), list);
  check(doc, "The imported list");
  const json = JSON.stringify(doc) + "\n";
  if (opts.out) fs.writeFileSync(opts.out, json); else process.stdout.write(json);
  process.stderr.write(counts.items + " items from " + counts.entries + " entries in " + doc.sections.length +
    " sections; " + counts.skipped + " links skipped.\n");
} else if (command === "check") {
  const [file] = opts.positional;
  if (!file) fail("Usage: build.cjs check list.json");
  const doc = JSON.parse(fs.readFileSync(file, "utf8"));
  check(doc, file);
  process.stderr.write(file + ": " + doc.items.length + " items in " + doc.sections.length + " sections.\n");
} else {
  fail("Commands: markdown, check. See the header of build.cjs.");
}
