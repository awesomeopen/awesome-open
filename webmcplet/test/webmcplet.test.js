"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const W = require("../webmcplet.js");

function fixture() {
  return {
    webmcplet: 1,
    list: { title: "Awesome Test", page_url: "https://example.org/list/" },
    sections: [{ id: "media", title: "Media" }, { id: "media/video", title: "Video", parent: "media" }, { id: "tools", title: "Tools" }],
    fields: {
      stars: { label: "GitHub stars", type: "number", meaning: "Stargazer count.", observed_at: "2026-11-01" },
      modes: { label: "run mode", type: "list", meaning: "Ways it runs.", filter: true, values: { server: "Self-hosted server" } },
      summary: { label: "Summary", type: "text", meaning: "Reviewed prose.", search: true }
    },
    items: [
      { id: "a", name: "Zebra Cut", url: "https://a.example/", description: "A video editor.", sections: ["media/video"], fields: { stars: 5 } },
      { id: "b", name: "Video Editor", url: "https://b.example/", description: "Trims clips.", sections: ["media/video", "tools"], fields: { stars: 0, modes: ["server"] } },
      { id: "c", name: "Apple", url: "https://c.example/", description: "Signage.", sections: ["tools"], fields: { summary: "Plays video on screens with a layout editor." } },
      { id: "d", name: "Broadcaster", url: "https://d.example/", description: "Obsolete recorder.", sections: ["media"], aliases: ["OBS"] }
    ]
  };
}
const names = result => result.items.map(i => i.name);

test("normalizeUrl gives cross-listed entries one identity", () => {
  assert.equal(W.normalizeUrl("https://www.GitHub.com/Owner/Repo.git/"), "github.com/owner/repo");
  assert.equal(W.normalizeUrl("http://github.com/owner/repo#readme"), "github.com/owner/repo");
  assert.throws(() => W.normalizeUrl("mailto:a@example.org"));
});

test("validate names each problem and accepts the fixture", () => {
  assert.deepEqual(W.validate(fixture()), []);
  const doc = fixture();
  doc.items[0].sections = ["missing"];
  doc.items[1].fields.stars = "many";
  doc.items[2].fields.unknown = 1;
  doc.fields.modes.search = true;
  doc.fields.modes.type = "number";
  assert.deepEqual(W.validate(doc), [
    "fields.modes.search: applies to string, list and text fields",
    "fields.modes.filter: applies to string and list fields",
    "items[0].sections: must name one or more declared sections",
    "items[1].fields.stars: must be a number",
    "items[1].fields.modes: must be a number",
    "items[2].fields.unknown: is not declared"
  ]);
  assert.throws(() => W.create({}), { code: "list_invalid" });
});

test("every word must match; order is the weakest field needed, then name", () => {
  const list = W.create(fixture());
  assert.deepEqual(names(list.find({ query: "video editor" })), ["Video Editor", "Zebra Cut", "Apple"]);
  assert.deepEqual(list.find({ query: "video editor" }).items[2].matched_fields, ["summary"]);
  assert.deepEqual(names(list.find({ query: "family photos" })), []);
  assert.equal(list.find({ query: "family photos" }).message, "No match in Awesome Test (4 items).");
});

test("an exact short alias uses word boundaries in every field", () => {
  const list = W.create(fixture());
  assert.deepEqual(names(list.find({ query: "obs" })), ["Broadcaster"]);
  assert.deepEqual(list.find({ query: "obs" }).items[0].matched_fields, ["aliases"]);
});

test("an empty query lists items in list order, twelve at a time", () => {
  const doc = fixture();
  doc.items = Array.from({ length: 30 }, (_, i) => ({ id: "i" + i, name: "Item " + i, url: "https://x.example/" + i, description: "", sections: ["tools"] }));
  const list = W.create(doc), first = list.find({}), last = list.find({ offset: 24 });
  assert.deepEqual([first.total, first.items.length, last.items.length, last.items[0].id], [30, 12, 6, "i24"]);
});

test("section scope includes subsections", () => {
  const list = W.create(fixture());
  assert.deepEqual(names(list.find({ section: "media" })), ["Zebra Cut", "Video Editor", "Broadcaster"]);
  assert.deepEqual(names(list.find({ section: "media/video", query: "clips" })), ["Video Editor"]);
});

test("a filter keeps recorded matches and reports coverage", () => {
  const result = W.create(fixture()).find({ filters: { modes: "server" } });
  assert.deepEqual(names(result), ["Video Editor"]);
  assert.deepEqual(result.coverage, [{ field: "modes", recorded: 1, total: 4, note: "1 of 4 items have a recorded run mode." }]);
});

test("unrecorded values are null; zero survives; text waits for get", () => {
  const list = W.create(fixture());
  const [zebra, editor] = list.find({ query: "video", section: "media/video" }).items.sort((a, b) => a.id.localeCompare(b.id));
  assert.deepEqual(zebra.fields, { stars: 5, modes: null });
  assert.equal(editor.fields.stars, 0);
  assert.equal(list.get({ id: "c" }).fields.summary, "Plays video on screens with a layout editor.");
  assert.equal(list.get({ id: "a" }).fields.summary, null);
});

test("rejections carry a stable code and name the tool to use", () => {
  const list = W.create(fixture(), { prefix: "mac" });
  for (const [args, code] of [[{ query: 1 }, "invalid_query"], [{ query: "x".repeat(161) }, "invalid_query"], [{ offset: -1 }, "invalid_offset"],
    [{ section: "nope" }, "invalid_section"], [{ filters: { stars: "5" } }, "invalid_filter"], [{ filters: { modes: ["server"] } }, "invalid_filter"],
    [{ fetch: "x" }, "invalid_arguments"]]) assert.throws(() => list.find(args), { code });
  assert.throws(() => list.get({ id: "zz" }), { code: "unknown_id", message: /mac_find/ });
});

test("overview counts each item once per containing section", () => {
  const overview = W.create(fixture()).overview({});
  assert.deepEqual(overview.sections.map(s => [s.id, s.items]), [["media", 3], ["media/video", 2], ["tools", 2]]);
  assert.deepEqual(overview.searched_fields, ["name", "aliases", "description", "summary"]);
  assert.equal(overview.fields.stars.recorded, 2);
  assert.equal(overview.fields.stars.observed_at, "2026-11-01");
});

test("registered tools return results and failures as data", async () => {
  const registered = new Map();
  const doc = { modelContext: { registerTool: async tool => { registered.set(tool.name, tool); } } };
  const result = await W.register(fixture(), { document: doc });
  assert.deepEqual(result.registered, ["list_sections", "list_find", "list_get"]);
  const find = registered.get("list_find"), get = registered.get("list_get");
  assert.equal(find.annotations.readOnlyHint, true);
  assert.deepEqual((await find.execute({ query: "obs" })).items.map(i => i.id), ["d"]);
  assert.equal((await find.execute('{"query":"obs"}')).ok, true);
  assert.deepEqual(await get.execute({ id: "zz" }), { ok: false, code: "unknown_id", message: "id must be an id returned by list_find." });
  assert.equal((await find.execute("{")).code, "invalid_arguments");
  assert.deepEqual((await W.register(fixture(), { document: {} })).registered, []);
});

test("a lazy list loads once, at the first call, and retries after a failure", async () => {
  let loads = 0, fail = true;
  const tools = W.tools(async () => { loads++; if (fail) throw new Error("offline"); return fixture(); }, { title: "Awesome Test" });
  assert.equal(loads, 0);
  assert.match(tools[1].description, /^Search Awesome Test\./);
  assert.equal((await tools[1].execute({ query: "obs" })).code, "list_unavailable");
  fail = false;
  await tools[1].execute({ query: "obs" }); await tools[2].execute({ id: "a" });
  assert.equal(loads, 2);
});

// A scripted stand-in for a LanguageModel session.
function session(replies) {
  const prompts = [];
  return { prompts, prompt: async (input, options) => {
    prompts.push({ input, options });
    const next = replies.shift();
    if (next instanceof Error) throw next;
    return JSON.stringify(next);
  } };
}

test("the assistant sees refs, calls tools with real IDs and shows rows from results", async () => {
  const tools = W.tools(fixture(), {});
  const model = session([{ action: "call", tool: "list_find", args: { query: "video editor" } },
    { action: "call", tool: "list_get", args: { id: "r2" } },
    { action: "answer", text: "Video Editor trims clips.", ids: ["r1", "r9"] }]);
  const outcome = await W.assistant.ask({ session: model, tools, request: "Find a video editor.", names: fixture().items.map(i => i.name) });
  assert.match(model.prompts[1].input, /"id":"r1"/);
  assert.doesNotMatch(model.prompts[1].input, /"id":"b"/);
  assert.deepEqual(outcome.trace[1].args, { id: "a" });
  assert.equal(outcome.status, "answered");
  assert.deepEqual(outcome.rows.map(r => [r.id, r.name, r.href]), [["b", "Video Editor", "https://b.example/"]]);
  assert.equal(outcome.removed, 1);
  assert.equal(outcome.text, "Video Editor trims clips.");
});

test("the assistant withholds text naming an item the tools did not return", async () => {
  const model = session([{ action: "call", tool: "list_find", args: { query: "family photos" } },
    { action: "answer", text: "Try Broadcaster, or see https://apple.example/Apple.", ids: [] }]);
  const outcome = await W.assistant.ask({ session: model, tools: W.tools(fixture(), {}), request: "Manage family photos.", names: fixture().items.map(i => i.name) });
  assert.deepEqual([outcome.rows, outcome.text, outcome.withheld], [[], null, ["Broadcaster"]]);
});

test("the assistant retries UnknownError once and stops at its limits", async () => {
  const unknown = () => Object.assign(new Error("kErrorUnknown"), { name: "UnknownError" });
  const tools = W.tools(fixture(), {});
  const retried = await W.assistant.ask({ session: session([unknown(), { action: "answer", text: "No match.", ids: [] }]), tools, request: "x" });
  assert.equal(retried.status, "answered");
  assert.equal((await W.assistant.ask({ session: session([unknown(), unknown()]), tools, request: "x" })).status, "error");
  const loop = session(Array.from({ length: 9 }, () => ({ action: "call", tool: "list_sections", args: {} })));
  assert.equal((await W.assistant.ask({ session: loop, tools, request: "x", maxTurns: 3 })).status, "turn_limit");
  const stop = new AbortController(); stop.abort();
  assert.equal((await W.assistant.ask({ session: session([]), tools, request: "x", signal: stop.signal })).status, "cancelled");
});

test("the model schema uses refs for IDs and drops uniqueItems", () => {
  const schema = W.assistant.modelSchema({ type: "object", properties: { ids: { type: "array", uniqueItems: true, maxItems: 6, items: { type: "string", pattern: "^[a-f0-9]{64}$" } }, id: { type: "string" } } });
  assert.deepEqual(schema.properties, { ids: { type: "array", maxItems: 6, items: { type: "string", pattern: "^r[0-9]{1,3}$" } }, id: { type: "string", pattern: "^r[0-9]{1,3}$" } });
  assert.deepEqual(W.assistant.namesIn("Use Apple-tools or Apple. See github.com/x/Apple", ["Apple", "Pear"]), ["Apple"]);
});
