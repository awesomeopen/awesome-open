"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { repositoryOf, addGithubStars, describe } = require("../github.js");
const { validate } = require("../webmcplet.js");

const response = (status, body, headers = {}) => ({
  status, ok: status >= 200 && status < 300, json: async () => body,
  headers: { get: name => headers[name.toLowerCase()] ?? null }
});

const doc = urls => ({
  webmcplet: 1, list: { title: "X", page_url: "https://e.example/" }, sections: [{ id: "s", title: "S" }],
  items: urls.map((url, i) => ({ id: "i" + i, name: "I" + i, url, description: "", sections: ["s"] }))
});

test("repositoryOf accepts GitHub repository URLs only", () => {
  assert.equal(repositoryOf("https://github.com/o/r.git/"), "o/r");
  assert.equal(repositoryOf("https://www.github.com/o/r#readme"), "o/r");
  assert.equal(repositoryOf("https://github.com/o/r/tree/main"), null);
  assert.equal(repositoryOf("https://gitlab.com/o/r"), null);
});

test("addGithubStars records stars, leaves failures unrecorded and declares the field", async () => {
  const list = doc(["https://github.com/o/a", "https://github.com/o/gone", "https://example.org/"]);
  const seen = [];
  const counts = await addGithubStars(list, { token: "t", fetch: async (url, init) => {
    seen.push([url, init.headers.authorization]);
    return url.endsWith("/o/a") ? response(200, { stargazers_count: 42 }) : response(404, {});
  } });
  assert.deepEqual(counts, { repositories: 2, recorded: 1, unavailable: 1, notChecked: 0 });
  assert.deepEqual(list.items.map(item => item.fields), [{ github_stars: 42 }, undefined, undefined]);
  assert.deepEqual(seen.map(s => s[1]), ["Bearer t", "Bearer t"]);
  assert.equal(list.fields.github_stars.type, "number");
  assert.ok(!Number.isNaN(Date.parse(list.fields.github_stars.observed_at)));
  assert.deepEqual(validate(list), []);
});

test("addGithubStars stops at the rate limit and counts what it did not check", async () => {
  const list = doc(["https://github.com/o/a", "https://github.com/o/b", "https://github.com/o/c"]);
  const counts = await addGithubStars(list, { token: "", concurrency: 1, fetch: async url =>
    url.endsWith("/o/a") ? response(200, { stargazers_count: 1 }) : response(403, {}, { "x-ratelimit-remaining": "0" }) });
  assert.deepEqual(counts, { repositories: 3, recorded: 1, unavailable: 0, notChecked: 2 });
  assert.match(describe(counts), /2 not checked after the rate limit/);
});
