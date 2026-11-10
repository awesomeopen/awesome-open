/* Imports a list README into a WebMCPlet document. MIT License; see LICENSE. */
"use strict";
const { normalizeUrl, VERSION } = require("./webmcplet.js");

// Plain text from inline Markdown: images and HTML go, links keep their text.
function plain(text) {
  return text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/(\*\*|__|`)/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

// A heading's title without leading symbols such as emoji or a trailing count "(72)".
function headingTitle(text) {
  return plain(text).replace(/^[^\p{L}\p{N}]+/u, "").replace(/\s*\(\d+\)\s*$/, "").trim();
}

function slug(text) {
  return text.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-+|-+$/g, "") || "section";
}

// The link at the start of text, allowing brackets in its name ("[Un]MuteMic").
function leadingLink(text) {
  const start = text.replace(/^(\*\*|__)/, "");
  const offset = text.length - start.length;
  if (start[0] !== "[") return null;
  let depth = 0, end = -1;
  for (let i = 0; i < start.length; i++) {
    if (start[i] === "[") depth++;
    else if (start[i] === "]" && --depth === 0) { end = i; break; }
  }
  if (end === -1 || start[end + 1] !== "(") return null;
  const close = start.indexOf(")", end + 2);
  if (close === -1) return null;
  const url = start.slice(end + 2, close).trim().split(/\s+/)[0].replace(/^<|>$/g, "");
  return { name: plain(start.slice(1, end)), url, rest: start.slice(close + 1).replace(/^(\*\*|__)/, ""), length: offset + close + 1 };
}

function isWebUrl(url) {
  return /^https?:\/\//i.test(url);
}

// Entries are top-level list items, "- [name](url) - description", and table
// rows, "| [name](url) | description |". Sections come from headings; an item
// belongs to the deepest heading above it. Relative and anchor links, such as a
// table of contents, are skipped.
function importMarkdown(markdown, list) {
  const sections = [], items = new Map(), stack = [];
  const counts = { entries: 0, skipped: 0 };
  let fenced = false;
  for (const line of markdown.split(/\r?\n/)) {
    if (/^\s*(```|~~~)/.test(line)) { fenced = !fenced; continue; }
    if (fenced) continue;
    const heading = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
    if (heading) {
      const level = heading[1].length, title = headingTitle(heading[2]);
      while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
      if (!title) continue;
      const parent = stack.length ? stack[stack.length - 1].section : null;
      let id = (parent ? parent.id + "/" : "") + slug(title);
      for (let n = 2; sections.some(s => s.id === id); n++) id = id.replace(/~\d+$/, "") + "~" + n;
      const section = { id, title, parent, used: false };
      sections.push(section);
      stack.push({ level, section });
      continue;
    }
    let body = null, description = "";
    const bullet = /^ {0,3}[-*+]\s+(.*)$/.exec(line);
    const row = /^\s*\|(.*)\|\s*$/.exec(line);
    if (bullet) body = bullet[1];
    else if (row) {
      const cells = row[1].split("|").map(c => c.trim());
      body = cells[0];
      description = cells.slice(1).filter(c => !/^:?-+:?$/.test(c)).join(" ");
    }
    if (body === null) continue;
    const link = leadingLink(body);
    if (!link) continue;
    if (!isWebUrl(link.url)) { counts.skipped++; continue; }
    // Badges and HTML may sit between the link and its separator.
    if (bullet) description = link.rest.replace(/^(?:\s*(?:!\[[^\]]*\]\([^)]*\)|<[^>]+>))*/, "")
      .replace(/^\s*(?:[-–—:]\s*)?/, "");
    const current = stack.length ? stack[stack.length - 1].section : null;
    if (!current || !link.name) { counts.skipped++; continue; }
    counts.entries++;
    let id;
    try { id = normalizeUrl(link.url); } catch (_) { counts.skipped++; continue; }
    current.used = true;
    const item = items.get(id);
    if (item) { if (!item.sections.includes(current.id)) item.sections.push(current.id); continue; }
    items.set(id, { id, name: link.name, url: link.url, description: plain(description), sections: [current.id] });
  }
  // Keep sections that hold items, and the ancestors of those sections.
  const kept = new Set();
  for (const section of sections) {
    if (!section.used) continue;
    for (let s = section; s; s = s.parent) kept.add(s);
  }
  return {
    doc: {
      webmcplet: VERSION,
      list: list,
      sections: sections.filter(s => kept.has(s)).map(s => {
        const out = { id: s.id, title: s.title };
        if (s.parent) out.parent = s.parent.id;
        return out;
      }),
      fields: {},
      items: [...items.values()]
    },
    counts: { entries: counts.entries, items: items.size, skipped: counts.skipped }
  };
}

module.exports = { importMarkdown, leadingLink, headingTitle, plain };
