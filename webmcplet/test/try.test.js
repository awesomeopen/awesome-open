"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { readmeUrls, titleOf, page, tryList } = require("../try.js");
const { RELEASE } = require("../webmcplet.js");

const DIR = path.join(__dirname, "..");

test("readmeUrls reads raw files from a GitHub repository URL only", () => {
  assert.equal(readmeUrls("https://github.com/o/awesome-x.git/")[0], "https://raw.githubusercontent.com/o/awesome-x/HEAD/README.md");
  assert.equal(readmeUrls("README.md"), null);
  assert.equal(readmeUrls("https://gitlab.com/o/r"), null);
});

test("titleOf takes the first top-level heading as plain text", () => {
  assert.equal(titleOf("Intro\n## Two\n# Awesome [X](https://x.example) ![b](b.svg)\n", "f"), "Awesome X");
  assert.equal(titleOf("## Only sections\n", "fallback"), "fallback");
});

test("page escapes list text and carries the adopter's tag", () => {
  const html = page({ list: { title: "A \"<b>\" list", page_url: "https://e.example/" },
    sections: [{ id: "s", title: "S&T" }, { id: "s/t", title: "Sub", parent: "s" }],
    items: [{ id: "i", name: "<i>", url: "https://i.example/?a=1&b=2", description: "D", sections: ["s/t"] }] });
  assert.match(html, /<script src="webmcplet.js" data-webmcplet-src="list.json" data-webmcplet-title="A &quot;&lt;b&gt;&quot; list" defer>/);
  assert.match(html, /<h2>S&amp;T<\/h2>\n<h3>Sub<\/h3>/);
  assert.match(html, /<a href="https:\/\/i.example\/\?a=1&amp;b=2">&lt;i&gt;<\/a> - D/);
  assert.match(page({ list: { title: "T" }, sections: [], items: [] }, { assistant: true }), /data-webmcplet-assistant="on"/);
});

test("tryList serves a local README with its own page URL", async () => {
  const result = await tryList(path.join(DIR, "example/README.md"));
  try {
    const doc = await (await fetch(result.url + "list.json")).json();
    assert.equal(doc.list.title, "Awesome Example");
    assert.equal(doc.list.page_url, result.url);
    assert.equal(doc.items.length, 5);
    assert.equal((await fetch(result.url + "webmcplet.js")).headers.get("content-type"), "text/javascript; charset=utf-8");
    assert.equal((await fetch(result.url + "other")).status, 404);
  } finally {
    result.server.close();
  }
});

test("CHANGELOG records this release with the script's SHA-256", () => {
  const changelog = fs.readFileSync(path.join(DIR, "CHANGELOG.md"), "utf8");
  const latest = /^## (\S+)[^\n]*\n[\s\S]*?SHA-256 `([0-9a-f]{64})`/m.exec(changelog);
  assert.ok(latest, "CHANGELOG.md needs a release heading and a SHA-256");
  assert.equal(latest[1], RELEASE);
  const hash = crypto.createHash("sha256").update(fs.readFileSync(path.join(DIR, "webmcplet.js"))).digest("hex");
  assert.equal(latest[2], hash, "webmcplet.js changed: bump RELEASE and add a CHANGELOG entry with `node build.cjs version`");
});
