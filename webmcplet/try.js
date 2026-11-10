/* Previews WebMCPlet on a list without touching its site. MIT License; see LICENSE.
 * Adopters need only webmcplet.js, build.cjs and markdown.js; this file serves `build.cjs try`. */
"use strict";
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { validate, RELEASE } = require("./webmcplet.js");
const { importMarkdown } = require("./markdown.js");

const README_NAMES = ["README.md", "readme.md", "Readme.md", "README.markdown"];

// Raw-file URLs to try for a GitHub repository URL, or null for anything else.
// Raw files, because GitHub's README API truncates large ones.
function readmeUrls(input) {
  const match = /^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/i.exec(input);
  if (!match) return null;
  return README_NAMES.map(name => "https://raw.githubusercontent.com/" + match[1] + "/" + match[2] + "/HEAD/" + name);
}

async function readReadme(input) {
  const urls = readmeUrls(input);
  if (!urls) return { markdown: fs.readFileSync(input, "utf8"), source: path.resolve(input) };
  for (const url of urls) {
    const response = await fetch(url);
    if (response.ok) return { markdown: await response.text(), source: url, repository: input.replace(/\/$/, "") };
    if (response.status !== 404) throw new Error(url + " returned " + response.status);
  }
  throw new Error("No README found in " + input);
}

// The README's first top-level heading, without inline Markdown.
function titleOf(markdown, fallback) {
  const heading = /^#\s+(.+?)\s*#*\s*$/m.exec(markdown);
  return heading ? heading[1].replace(/!\[[^\]]*\]\([^)]*\)|<[^>]+>/g, "").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").trim() || fallback : fallback;
}

function escape(text) {
  return String(text).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

// A plain page of the list's sections and entries, carrying the same tag an adopter adds.
function page(doc, options = {}) {
  const depth = new Map();
  const body = doc.sections.map(section => {
    const level = Math.min((section.parent ? depth.get(section.parent) : 1) + 1, 6);
    depth.set(section.id, level);
    const entries = doc.items.filter(item => item.sections.includes(section.id)).map(item =>
      "<li><a href=\"" + escape(item.url) + "\">" + escape(item.name) + "</a>" + (item.description ? " - " + escape(item.description) : "") + "</li>");
    return "<h" + level + ">" + escape(section.title) + "</h" + level + ">" + (entries.length ? "\n<ul>\n" + entries.join("\n") + "\n</ul>" : "");
  }).join("\n");
  const assistant = options.assistant ? " data-webmcplet-assistant=\"on\"" : "";
  return "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n" +
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" +
    "<title>" + escape(doc.list.title) + " - WebMCPlet preview</title>\n" +
    "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:48rem;margin:0 auto;padding:1rem}</style>\n" +
    "<script src=\"webmcplet.js\" data-webmcplet-src=\"list.json\" data-webmcplet-title=\"" + escape(doc.list.title) + "\"" + assistant + " defer></script>\n" +
    "</head>\n<body>\n<h1>" + escape(doc.list.title) + "</h1>\n" +
    "<p>Local preview of WebMCPlet " + RELEASE + " on " + doc.items.length + " items imported from " +
    (doc.list.source_url ? "<a href=\"" + escape(doc.list.source_url) + "\">" + escape(doc.list.source_url) + "</a>" : "a local README") +
    ". Open the panel with the corner button.</p>\n" + body + "\n</body>\n</html>\n";
}

// Serves the preview page, the script and the list document from memory on 127.0.0.1.
function serve(files, port) {
  const server = http.createServer((request, response) => {
    const name = new URL(request.url, "http://127.0.0.1").pathname;
    const file = files[name === "/" ? "/index.html" : name];
    if (!file) { response.writeHead(404); response.end("Not found"); return; }
    response.writeHead(200, { "content-type": file.type, "cache-control": "no-store" });
    response.end(file.body);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

async function tryList(input, options = {}) {
  const { markdown, source, repository } = await readReadme(input);
  const title = options.title || titleOf(markdown, repository ? repository.split("/").pop() : path.basename(input));
  const files = {};
  const server = await serve(files, options.port || 0);
  const url = "http://127.0.0.1:" + server.address().port + "/";
  const list = { title, page_url: repository || url, generated_at: new Date().toISOString() };
  if (repository) list.source_url = repository;
  const { doc, counts } = importMarkdown(markdown, list);
  const problems = validate(doc);
  if (problems.length) { server.close(); throw new Error("The imported list is invalid:\n  " + problems.join("\n  ")); }
  files["/index.html"] = { type: "text/html; charset=utf-8", body: page(doc, options) };
  files["/webmcplet.js"] = { type: "text/javascript; charset=utf-8", body: fs.readFileSync(path.join(__dirname, "webmcplet.js")) };
  files["/list.json"] = { type: "application/json", body: JSON.stringify(doc) };
  return { server, url, source, counts, sections: doc.sections.length };
}

module.exports = { readmeUrls, titleOf, page, serve, tryList };
