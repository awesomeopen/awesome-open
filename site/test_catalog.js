/* Run with: node --test site/test_catalog.js */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const catalog = require("./catalog.js");

const projects = [
  {
    id: "open-alpha", name: "Open Alpha", description: "A café-friendly writing editor",
    url: "https://example.org/alpha", categories: ["writing", "tools"],
    github: { stars: 25, license: "MIT", pushed_at: "2026-10-09T00:00:00Z" },
    alternatives: [{ name: "Microsoft Word" }]
  },
  {
    id: "open-beta", name: "Open Beta", description: "Collaborative documents",
    url: "https://example.org/beta", categories: ["writing"],
    github: { stars: 100, license: "Apache-2.0", pushed_at: "2026-10-08T23:59:59Z" },
    alternatives: [{ name: "Google Docs" }]
  },
  {
    id: "open-empty", name: "Open Empty", description: "Unmeasured tools",
    url: "https://example.org/empty", categories: ["tools"], github: null, alternatives: []
  },
  {
    id: "open-zero", name: "Open Zero", description: "Repository without a license or push date",
    url: "https://example.org/zero", categories: ["tools"],
    github: { stars: 0, license: null, pushed_at: null }, alternatives: []
  },
  {
    id: "open-alpha-2", name: "Open Alpha", description: "Another editor",
    url: "https://example.org/alpha-2", categories: ["writing"],
    github: { stars: 25, license: "NOASSERTION", pushed_at: "2026-10-09T00:00:00Z" },
    alternatives: []
  }
];
const data = { metrics_as_of: "2026-10-10", categories: [{ id: "writing" }, { id: "tools" }], projects };
const state = input => catalog.normalizeState(input, data);
const ids = input => catalog.selectProjects(projects, state(input), data).map(p => p.id);

test("defaults keep every project, including unknown metrics", () => {
  assert.deepEqual(state({}), catalog.DEFAULTS);
  assert.deepEqual(ids({}), ["open-beta", "open-alpha", "open-alpha-2", "open-zero", "open-empty"]);
});

test("search matches names, descriptions and reviewed alternatives", () => {
  assert.deepEqual(ids({ q: "  MICROSOFT   word  " }), ["open-alpha"]);
  assert.deepEqual(ids({ q: "cafe" }), ["open-alpha"]);
  assert.deepEqual(ids({ q: "Google" }), ["open-beta"]);
  assert.deepEqual(ids({ q: "Open Beta" }), ["open-beta"]);
  assert.deepEqual(ids({ q: "alpha editor" }), ["open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ q: "unfindable" }), []);
});

test("all filters combine; cross-listed projects are not duplicated", () => {
  assert.deepEqual(ids({ q: "editor", category: "tools", license: "MIT", stars: "25", pushed: "2026-10-09" }), ["open-alpha"]);
  assert.deepEqual(ids({ q: "editor", category: "tools", stars: "26" }), []);
  assert.deepEqual(ids({ category: "writing", license: "known" }), ["open-beta", "open-alpha"]);
  assert.deepEqual(ids({ category: "writing", license: "unknown" }), ["open-alpha-2"]);
  assert.deepEqual(ids({ category: "writing", license: "Apache-2.0" }), ["open-beta"]);
});

test("blank threshold includes unknowns; explicit zero excludes them", () => {
  assert.deepEqual(ids({ stars: "" }), ids({}));
  assert.deepEqual(ids({ stars: "0" }), ["open-beta", "open-alpha", "open-alpha-2", "open-zero"]);
  assert.equal(state({ stars: 0 }).stars, 0);
  assert.deepEqual(ids({ stars: "25" }), ["open-beta", "open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ stars: "26" }), ["open-beta"]);
});

test("date threshold is exact and inclusive in UTC; unknown date fails", () => {
  assert.deepEqual(ids({ pushed: "2026-10-09" }), ["open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ pushed: "2026-10-08" }), ["open-beta", "open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ pushed: "2026-10-10" }), []);
  assert.equal(catalog.pushedAt({ github: { pushed_at: "2026-02-30T01:00:00Z" } }), null);
  assert.equal(catalog.pushedAt({ github: { pushed_at: "invalid" } }), null);
});

test("unknown, NOASSERTION and OTHER licenses remain unknown", () => {
  assert.deepEqual(ids({ license: "unknown" }), ["open-alpha-2", "open-zero", "open-empty"]);
  for (const license of [null, "", "OTHER", "NOASSERTION", "unknown", 7]) {
    assert.equal(catalog.licenseOf({ github: { license } }), "");
  }
});

test("stars sort is descending with unknowns last and deterministic ties", () => {
  assert.deepEqual(ids({ sort: "stars" }), ["open-beta", "open-alpha", "open-alpha-2", "open-zero", "open-empty"]);
  assert.deepEqual(ids({ sort: "pushed" }), ["open-alpha", "open-alpha-2", "open-beta", "open-empty", "open-zero"]);
  const original = projects.map(p => p.id);
  catalog.selectProjects(projects, state({ sort: "stars" }));
  assert.deepEqual(projects.map(p => p.id), original);
});

test("unknown metrics sort last even when a real star count is zero", () => {
  const fixture = [
    { id: "x", name: "X", github: { stars: -1, pushed_at: "bad" } },
    { id: "a", name: "A", github: { stars: 0, pushed_at: "2020-01-01T00:00:00Z" } },
    { id: "y", name: "Y", github: { stars: null, pushed_at: null } }
  ];
  assert.deepEqual(fixture.slice().sort(catalog.comparator("stars")).map(p => p.id), ["a", "x", "y"]);
  assert.deepEqual(fixture.slice().sort(catalog.comparator("pushed")).map(p => p.id), ["a", "x", "y"]);
});

test("malformed URL values become safe defaults and huge stars clamp", () => {
  assert.deepEqual(state(new URLSearchParams("category=oops&license=Proprietary&stars=-1&pushed=2026-02-30&sort=random")), catalog.DEFAULTS);
  for (const value of ["NaN", "Infinity", "-1", "1.5", "2e3", "abc", ""]) {
    assert.equal(state({ stars: value }).stars, null);
  }
  assert.equal(state({ stars: "9999999999999999999999999999999999999999" }).stars, Number.MAX_SAFE_INTEGER);
  assert.equal(state({ q: "a".repeat(600) }).q.length, 500);
  assert.equal(catalog.validDate("2024-02-29"), "2024-02-29");
  assert.equal(catalog.validDate("2023-02-29"), "");
  assert.equal(catalog.validDate("2026-13-01"), "");
  assert.equal(catalog.validDate("2026-1-01"), "");
});

test("URL state is shareable and preserves unrelated params and project hash", () => {
  const input = "https://example.org/catalog/?utm_source=test&debug=1#project-open-alpha";
  const selected = state({ q: "Microsoft Word", category: "tools", license: "MIT", stars: "0", pushed: "2026-10-09", sort: "pushed" });
  const url = catalog.stateToURL(input, selected);
  assert.equal(url.searchParams.get("utm_source"), "test");
  assert.equal(url.searchParams.get("debug"), "1");
  assert.equal(url.hash, "#project-open-alpha");
  assert.equal(url.searchParams.get("stars"), "0");
  assert.deepEqual(state(url.searchParams), selected);
  const cleared = catalog.stateToURL(url.href, state({}));
  assert.equal(cleared.href, input);
  assert.equal(catalog.stateToURL(cleared.href, state({})).href, input);
});

test("duplicate filter URL params are canonicalized without touching unrelated duplicates", () => {
  const input = new URL("https://example.org/?q=alpha&q=beta&tag=a&tag=b#catalog");
  const output = catalog.stateToURL(input.href, state(input.searchParams));
  assert.deepEqual(output.searchParams.getAll("q"), ["alpha"]);
  assert.deepEqual(output.searchParams.getAll("tag"), ["a", "b"]);
  assert.equal(output.hash, "#catalog");
});

test("local file URLs need no fetch or server to serialize state", () => {
  const url = catalog.stateToURL("file:///tmp/site/index.html#catalog", state({ q: "office" }));
  assert.equal(url.href, "file:///tmp/site/index.html?q=office#catalog");
});

test("push windows are anchored to the cached snapshot and use exact inclusive UTC day boundaries", () => {
  const window = pushed_at => catalog.pushWindowOf({ github: { pushed_at } }, data);
  assert.equal(window("2026-07-11T23:59:59.999Z"), "");
  assert.equal(window("2026-07-12T00:00:00Z"), "recent");
  assert.equal(window("2026-10-10T23:59:59.999Z"), "recent");
  assert.equal(window("2026-10-11T00:00:00Z"), "");
  assert.equal(window("2024-10-09T23:59:59.999Z"), "older");
  assert.equal(window("2024-10-10T00:00:00Z"), "");
  assert.equal(window("2025-10-10T00:00:00Z"), "");
  for (const value of [null, undefined, "", "not-a-date", "2026-02-30T00:00:00Z"]) {
    assert.equal(window(value), "unknown");
  }
  assert.equal(catalog.pushWindowOf({ github: null }, data), "unknown");
  assert.equal(catalog.pushWindowOf(projects[0], "2026-10-10"), "recent");
  assert.equal(catalog.pushWindowOf(projects[0], { metrics_as_of: "invalid" }), "");
  assert.equal(catalog.pushWindowBounds(null), null);
  assert.deepEqual(ids({ window: "recent" }), ["open-beta", "open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ window: "older" }), []);
  assert.deepEqual(ids({ window: "unknown" }), ["open-zero", "open-empty"]);
});

test("two-calendar-year cutoff clamps leap-day anniversaries without overflowing into March", () => {
  const bounds = catalog.pushWindowBounds("2024-02-29");
  assert.equal(new Date(bounds.older).toISOString(), "2022-02-28T00:00:00.000Z");
  assert.equal(catalog.pushWindowOf({ github: { pushed_at: "2022-02-27T23:59:59Z" } }, "2024-02-29"), "older");
  assert.equal(catalog.pushWindowOf({ github: { pushed_at: "2022-02-28T00:00:00Z" } }, "2024-02-29"), "");
  assert.equal(new Date(catalog.pushWindowBounds("2026-02-28").older).toISOString(), "2024-02-28T00:00:00.000Z");
  assert.equal(new Date(catalog.pushWindowBounds("2024-03-01").older).toISOString(), "2022-03-01T00:00:00.000Z");
});

test("reviewed alternative filter uses exact names, independent of description, ancestry and search", () => {
  assert.deepEqual(ids({ alternative: "Microsoft Word" }), ["open-alpha"]);
  assert.deepEqual(ids({ alternative: "Google Docs" }), ["open-beta"]);
  assert.deepEqual(ids({ q: "editor", alternative: "Microsoft Word", metrics: "present", window: "recent", category: "tools" }), ["open-alpha"]);
  assert.deepEqual(ids({ q: "Google", alternative: "Microsoft Word" }), []);
  for (const alternative of ["Word", "microsoft word", " Microsoft Word ", "Unreviewed"]) {
    assert.equal(state({ alternative }).alternative, "");
  }
  const unrelated = { ...projects[0], alternatives: [], ancestry: [{ name: "Microsoft Word" }] };
  assert.deepEqual(catalog.selectProjects([unrelated], state({ alternative: "Microsoft Word" }), data), []);
  assert.deepEqual(catalog.alternativeNames(projects), ["Google Docs", "Microsoft Word"]);
});

test("metrics presence means a cached GitHub record, not known license, stars or push date", () => {
  assert.deepEqual(ids({ metrics: "present" }), ["open-beta", "open-alpha", "open-alpha-2", "open-zero"]);
  assert.deepEqual(ids({ metrics: "missing" }), ["open-empty"]);
  assert.deepEqual(ids({ metrics: "present", window: "unknown" }), ["open-zero"]);
  assert.deepEqual(ids({ metrics: "missing", license: "known" }), []);
  assert.equal(catalog.metricsPresent({ github: {} }), true);
  for (const github of [null, undefined, false, "unknown", []]) {
    assert.equal(catalog.metricsPresent({ github }), false);
  }
});

test("diagnostic counts are the same predicates used by each diagnostic filter", () => {
  const counts = catalog.diagnosticCounts(projects, data);
  assert.deepEqual(counts, { recent: 3, older: 0, unknown: 2, "metrics-present": 4, "metrics-missing": 1 });
  for (const window of ["recent", "older", "unknown"]) assert.equal(counts[window], ids({ window }).length);
  for (const metrics of ["present", "missing"]) assert.equal(counts["metrics-" + metrics], ids({ metrics }).length);
});

test("new URL filters normalize, round-trip, canonicalize duplicates and clear independently of unrelated params", () => {
  const selected = state({ window: "recent", alternative: "Microsoft Word", metrics: "present" });
  const input = "https://example.org/?tag=a&tag=b#project-open-alpha";
  const url = catalog.stateToURL(input, selected);
  assert.deepEqual(state(url.searchParams), selected);
  assert.equal(url.searchParams.get("window"), "recent");
  assert.equal(url.searchParams.get("alternative"), "Microsoft Word");
  assert.equal(url.searchParams.get("metrics"), "present");
  assert.equal(catalog.stateToURL(url.href, state({})).href, input);
  assert.deepEqual(state({ window: "active", metrics: "yes", alternative: "Unreviewed" }), catalog.DEFAULTS);
  const duplicated = new URL("https://example.org/?window=older&window=unknown&metrics=missing&metrics=present&alternative=Google+Docs&alternative=Microsoft+Word");
  const canonical = catalog.stateToURL(duplicated.href, state(duplicated.searchParams));
  assert.deepEqual(canonical.searchParams.getAll("window"), ["older"]);
  assert.deepEqual(canonical.searchParams.getAll("metrics"), ["missing"]);
  assert.deepEqual(canonical.searchParams.getAll("alternative"), ["Google Docs"]);
  const legacyState = { q: "", category: "", license: "all", stars: null, pushed: "", sort: "name" };
  assert.equal(catalog.stateToURL(input, legacyState).searchParams.get("sort"), "name");
});

test("reviewed setup filters are multivalued, combinable, unknown-safe and URL-restorable", () => {
  const sample = { categories: [], projects: [
    { ...projects[0], deployment: { run_modes: [{ value: 'desktop' }, { value: 'cli' }], install_methods: [{ value: 'binary' }] } },
    { ...projects[1], deployment: { run_modes: [{ value: 'server' }], install_methods: [{ value: 'container' }] } },
    projects[2]
  ] };
  const select = input => catalog.selectProjects(sample.projects, catalog.normalizeState(input, sample)).map(p => p.id);
  assert.deepEqual(select({ run_mode: 'cli', install_method: 'binary' }), ['open-alpha']);
  assert.deepEqual(select({ run_mode: 'desktop', install_method: 'container' }), []);
  assert.deepEqual(select({ run_mode: 'unknown' }), ['open-empty']);
  assert.deepEqual(select({ install_method: 'unknown' }), ['open-empty']);
  assert.equal(catalog.normalizeState({ run_mode: 'invented', install_method: 'invented' }, sample).run_mode, '');
  const wanted = catalog.normalizeState({ run_mode: 'server', install_method: 'container' }, sample);
  const url = catalog.stateToURL('https://example.org/?other=keep#anchor', wanted);
  assert.deepEqual(catalog.normalizeState(url.searchParams, sample), wanted);
  const reset = catalog.stateToURL(url, catalog.DEFAULTS);
  assert.equal(reset.searchParams.has('run_mode'), false);
  assert.equal(reset.searchParams.get('other'), 'keep');
  assert.equal(reset.hash, '#anchor');
});


test("setup unknown filters are field-specific for sparse approved records", () => {
  const sample = { categories: [], projects: [
    { ...projects[0], deployment: { run_modes: [{ value: 'cli' }] } },
    { ...projects[1], deployment: { install_methods: [{ value: 'binary' }] } }
  ] };
  const select = input => catalog.selectProjects(sample.projects, catalog.normalizeState(input, sample)).map(p => p.id);
  assert.deepEqual(select({ run_mode: 'unknown' }), ['open-beta']);
  assert.deepEqual(select({ install_method: 'unknown' }), ['open-alpha']);
  assert.deepEqual(select({ run_mode: 'cli', install_method: 'unknown' }), ['open-alpha']);
});

test('unavailable records are unknown while stale zero remains measurable', () => {
  const unavailable = { id: 'unavailable', name: 'Unavailable', github: { status: 'unavailable', stars: null, pushed_at: null } };
  const stale = { id: 'stale', name: 'Stale', github: { status: 'stale', stars: 0, pushed_at: '2020-01-01T00:00:00Z' } };
  assert.equal(catalog.metricsPresent(unavailable), false);
  assert.equal(catalog.metricsPresent(stale), true);
  assert.equal(catalog.starsOf(unavailable), null);
  assert.equal(catalog.starsOf(stale), 0);
  assert.deepEqual(catalog.selectProjects([unavailable, stale], state({ stars: '0' })).map(p => p.id), ['stale']);
});

test("explicit name sorting survives URL changes while reset uses match order", () => {
  const explicit = state(new URLSearchParams("sort=name&category=writing"));
  assert.equal(explicit.sort, "name");
  assert.deepEqual(ids({ sort: "name" }), ["open-alpha", "open-alpha-2", "open-beta", "open-empty", "open-zero"]);
  const url = catalog.stateToURL("https://example.org/?sort=name", explicit);
  assert.equal(state(url.searchParams).sort, "name");
  assert.equal(catalog.stateToURL(url, state({})).searchParams.has("sort"), false);
  assert.equal(state({}).sort, "match");
  assert.deepEqual(ids({}), ids({ sort: "stars" })); // No query: match order is the ledger's star order
  assert.equal(state(new URLSearchParams("sort=stars")).sort, "stars");
  assert.equal(catalog.stateToURL("https://example.org/", state({ sort: "stars" })).searchParams.get("sort"), "stars");
});

test("reviewed aliases match on boundaries and short names do not leak into prose", () => {
  const fixtures = [
    {id: 'obs', name: 'OBS Studio', description: 'Streaming and recording', categories: ['media'],
      github: {stars: 10}, aliases: [{name: 'Open Broadcaster Software'}, {name: 'OBS'}]},
    {id: 'other', name: 'Open Other', description: 'Observatory for obsolete jobs', github: {stars: 100}},
    {id: 'unicode', name: 'Open Unicode', description: 'éOBS OBSé OBS2 OBS_name', github: null},
    {id: 'another', name: 'Another OBS tool', description: 'A distinct project', github: {stars: 20}},
    {id: 'accent', name: 'Open Accent', description: '', aliases: [{name: 'Café Editor'}, {name: 'C++'}]}
  ];
  const snapshot = {projects: fixtures, categories: [{id: 'media'}]};
  const find = input => catalog.selectProjects(fixtures, catalog.normalizeState(input, snapshot), snapshot).map(p => p.id);
  assert.deepEqual(find({q: 'OBS'}), ['another', 'obs']);
  assert.deepEqual(find({q: 'obs streaming'}), ['obs']);
  assert.deepEqual(find({q: 'Open Broadcaster Software'}), ['obs']);
  assert.deepEqual(find({q: 'broadcaster recording', category: 'media'}), ['obs']);
  assert.deepEqual(find({q: 'broadcast'}), []);
  assert.deepEqual(find({q: 'obso'}), ['other']); // ordinary non-alias substring behavior
  assert.deepEqual(find({q: 'cafe'}), ['accent']);
  assert.deepEqual(find({q: 'C++'}), ['accent']); // escaped literal, never a regex
  assert.deepEqual(find({q: 'OBS', sort: 'name'}), ['another', 'obs']);
  assert.equal(catalog.stateToURL('https://example.org/', catalog.normalizeState({q:'OBS'}, snapshot)).searchParams.get('q'), 'OBS');
});


// Adopted plates and in-page drawers. The one-screen catalog calls recordPlate;
// record pages call init, which enhances plates already in the document.
function plateDom() {
  class Element {
    constructor(name = "div") {
      this.name = name;
      this.tagName = name.toUpperCase();
      this.open = false;
      this.children = [];
      this.dataset = {};
      this.attributes = {};
      Object.defineProperty(this.attributes, Symbol.iterator, { value: function* () {
        for (const [name, value] of Object.entries(this)) yield { name, value };
      } });
      this.listeners = {};
      this.className = "";
      this.classList = {
        add: (...names) => { this.className = [...new Set(this.className.split(/\s+/).filter(Boolean).concat(names))].join(" "); },
        remove: (...names) => { this.className = this.className.split(/\s+/).filter(name => !names.includes(name)).join(" "); },
        contains: name => this.className.split(/\s+/).includes(name)
      };
      this.style = { setProperty(key, value) { this[key] = value; } };
      this.isConnected = true;
    }
    addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
    fire(type, extra = {}) {
      const event = { target: this, button: 0, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...extra };
      (this.listeners[type] || []).slice().forEach(listener => listener(event));
      return event;
    }
    appendChild(child) {
      if (child.parent) child.parent.children = child.parent.children.filter(node => node !== child);
      this.children.push(child);
      child.parent = this;
      return child;
    }
    insertBefore(child, before) {
      this.appendChild(child);
      if (before) {
        this.children.splice(this.children.indexOf(child), 1);
        this.children.splice(this.children.indexOf(before), 0, child);
      }
      return child;
    }
    get firstChild() { return this.children[0] || null; }
    remove() {
      if (this.parent) this.parent.children = this.parent.children.filter(node => node !== this);
      this.parent = null;
      this.isConnected = false;
    }
    contains(node) { return node === this || this.children.some(child => child.contains(node)); }
    matches(selector) {
      if (selector.includes(" ")) {
        const parts = selector.split(/\s+/), last = parts.pop();
        if (!this.matches(last)) return false;
        let parent = this.parent;
        while (parent) { if (parent.matches(parts.join(" "))) return true; parent = parent.parent; }
        return false;
      }
      const tag = selector.match(/^[a-z][a-z0-9-]*/i);
      if (tag && this.tagName !== tag[0].toUpperCase()) return false;
      for (const [, name] of selector.matchAll(/\.([a-z0-9_-]+)/gi)) if (!this.classList.contains(name)) return false;
      for (const [, name, expected] of selector.matchAll(/\[([a-z0-9_-]+)(?:="([^"]*)")?\]/gi)) {
        const actual = this.getAttribute(name);
        if (actual === null || (expected !== undefined && actual !== expected)) return false;
      }
      return true;
    }
    closest(selector) { return this.matches(selector) ? this : this.parent && this.parent.closest(selector); }
    querySelectorAll(selector) {
      const found = [];
      for (const child of this.children) {
        if (child.matches(selector)) found.push(child);
        found.push(...child.querySelectorAll(selector));
      }
      return found;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    focus() { document.activeElement = this; }
    getBoundingClientRect() { return { left: 0, top: 0, width: 100, height: 100 }; }
    setAttribute(key, value) {
      this.attributes[key] = String(value);
      if (key === "class") this.className = String(value);
      if (key === "id") this.id = String(value);
      if (key.startsWith("data-")) this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
      if (key === "src") this.src = String(value);
    }
    getAttribute(key) {
      if (key === "class") return this.className || null;
      if (key === "id") return this.id || null;
      if (key === "open") return this.open ? "" : null;
      if (key.startsWith("data-")) return this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] ?? null;
      return this.attributes[key] ?? null;
    }
    cloneNode(deep) {
      const clone = new Element(this.name);
      Object.assign(clone.dataset, this.dataset);
      Object.assign(clone.attributes, this.attributes);
      for (const key of ["className", "id", "textContent", "open", "src", "complete"]) clone[key] = this[key];
      if (deep) this.children.forEach(child => clone.appendChild(child.cloneNode(true)));
      return clone;
    }
  }
  function createRecord(spec) {
    const record = new Element("html");
    record.getElementById = id => record.querySelectorAll("*").find(node => node.id === id) || null;
    const base = new Element("base");
    base.setAttribute("href", spec.base || "../");
    if (!spec.noBase) record.appendChild(base);
    const card = new Element("article");
    card.className = "project-card";
    card.dataset.projectId = spec.wrongIdentity ? "other" : spec.projectId;
    card.id = "project-" + card.dataset.projectId;
    const label = new Element("summary");
    label.id = "name-" + spec.projectId;
    if (!spec.noLabel) card.appendChild(label);
    const plate = new Element();
    plate.className = "specimen-interior specimen-plate";
    plate.setAttribute("aria-labelledby", spec.wrongLabel ? "name-other" : label.id);
    const field = new Element();
    field.className = "plate-field";
    field.dataset.seed = spec.projectId.slice(0, 16);
    const img = new Element("img");
    img.setAttribute("src", spec.imageURL || "specimens/drawing.webp");
    if (spec.srcset) img.setAttribute("srcset", spec.srcset);
    img.complete = false;
    field.appendChild(img);
    plate.appendChild(field);
    const departure = new Element("nav");
    departure.className = "plate-departure";
    plate.appendChild(departure);
    const category = new Element("a");
    category.setAttribute("href", "https://example.org/source#tools");
    plate.appendChild(category);
    const permalink = new Element("a");
    permalink.className = "permalink";
    permalink.setAttribute("href", "#project-" + spec.projectId);
    plate.appendChild(permalink);
    const evidence = new Element("a");
    evidence.className = "evidence-download";
    evidence.setAttribute("href", "catalog.json");
    plate.appendChild(evidence);
    if (spec.activeTag) plate.appendChild(new Element(spec.activeTag));
    if (spec.attribute) field.setAttribute(spec.attribute[0], spec.attribute[1]);
    card.appendChild(plate);
    if (spec.duplicatePlate) card.appendChild(plate.cloneNode(true));
    record.appendChild(card);
    if (spec.duplicateCard) record.appendChild(card.cloneNode(true));
    if (spec.detachedPlate) { plate.remove(); record.appendChild(plate); }
    return record;
  }
  const root = new Element("div");
  const document = {
    activeElement: null,
    addEventListener() {},
    querySelector(selector) { return root.querySelector(selector); },
    querySelectorAll(selector) { return root.querySelectorAll(selector); },
    getElementById(id) { return root.querySelectorAll("*").find(node => node.id === id) || null; },
    createElement(name) { return new Element(name); },
    createElementNS(_namespace, name) { return new Element(name); },
    importNode(node, deep) { return node.cloneNode(deep); }
  };
  const listeners = {};
  const window = {
    location: { href: "https://example.org/catalog/" },
    addEventListener(type, listener) { (listeners[type] ||= []).push(listener); },
    matchMedia() { return { matches: false }; },
    DOMParser: class {
      parseFromString(body) { return createRecord(JSON.parse(body)); }
    }
  };
  const id = "ab".repeat(32);
  const url = new URL("https://example.org/catalog/records/" + id + ".html");
  return { Element, document, window, root, listeners, id, url, createRecord };
}

test("recordPlate keeps one matching plate and rebases same-origin assets", () => {
  const ui = plateDom();
  const plate = catalog.recordPlate(JSON.stringify({ projectId: ui.id }), ui.url, ui.id, ui.document, ui.window);
  assert.equal(plate.querySelector("img").getAttribute("src"), "https://example.org/catalog/specimens/drawing.webp");
  assert.equal(plate.querySelector(".evidence-download").getAttribute("href"), "https://example.org/catalog/catalog.json");
  assert.equal(plate.querySelector(".permalink").getAttribute("href"), "#project-" + ui.id);
  assert.equal(plate.querySelector("base"), null);
  catalog.enhancePlate(plate, ui.document, ui.window);
  assert.equal(plate.dataset.enhanced, "true");
  assert.equal(plate.querySelectorAll(".plate-lens").length, 1);
  const points = [...plate.querySelector(".plate-wild-terrain").querySelector("path").getAttribute("d").matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)]
    .map(match => ({ x: Number(match[1]), y: Number(match[2]) }));
  assert.ok(points.length > 0);
  assert.ok(points.every(point => point.x > 0 && point.x < 1000 && point.y > 100 && point.y < 300));
});

test("recordPlate resolves a missing base against the record URL", () => {
  const ui = plateDom();
  const plate = catalog.recordPlate(JSON.stringify({ projectId: ui.id, noBase: true, imageURL: "../specimens/drawing.webp" }), ui.url, ui.id, ui.document, ui.window);
  assert.equal(plate.querySelector("img").getAttribute("src"), "https://example.org/catalog/specimens/drawing.webp");
});

test("recordPlate srcset stays same-origin and the loupe uses the widest candidate", () => {
  const ui = plateDom();
  const plate = catalog.recordPlate(JSON.stringify({
    projectId: ui.id,
    srcset: "specimens/responsive/a-512.webp 512w, specimens/responsive/a-768.webp 768w,specimens/a.webp 1254w"
  }), ui.url, ui.id, ui.document, ui.window);
  const img = plate.querySelector("img");
  assert.equal(img.getAttribute("srcset"), "https://example.org/catalog/specimens/responsive/a-512.webp 512w, " +
    "https://example.org/catalog/specimens/responsive/a-768.webp 768w, https://example.org/catalog/specimens/a.webp 1254w");
  catalog.enhancePlate(plate, ui.document, ui.window);
  const field = plate.querySelector(".plate-field"), lens = plate.querySelector(".plate-lens");
  field.fire("pointermove", { pointerType: "mouse", clientX: 0, clientY: 0 });
  assert.equal(lens.style.backgroundImage, 'url("https://example.org/catalog/specimens/a.webp")');
});

test("recordPlate rejects oversized, mismatched, and active records", () => {
  const ui = plateDom();
  const adopt = spec => catalog.recordPlate(JSON.stringify({ projectId: ui.id, ...spec }), ui.url, ui.id, ui.document, ui.window);
  assert.throws(() => catalog.recordPlate("x".repeat(2 * 1024 * 1024 + 1), ui.url, ui.id, ui.document, ui.window));
  assert.throws(() => catalog.recordPlate("not a valid record", ui.url, ui.id, ui.document, ui.window));
  for (const spec of [
    { wrongIdentity: true }, { wrongLabel: true }, { noLabel: true },
    { duplicatePlate: true }, { duplicateCard: true }, { detachedPlate: true },
    { base: "https://elsewhere.example/" },
    { imageURL: "https://elsewhere.example/drawing.webp" },
    { imageURL: "javascript:alert(1)" },
    { srcset: "specimens/a-512.webp 512w, https://elsewhere.example/a.webp 1254w" },
    { srcset: "javascript:alert(1) 512w" },
    { srcset: "specimens/a-512.webp 2x" },
    { srcset: "specimens/a-512.webp" },
    { activeTag: "script" }, { activeTag: "iframe" }, { activeTag: "foreignObject" },
    { attribute: ["onclick", "alert(1)"] },
    { attribute: ["style", "background:url(https://elsewhere.example/image)"] },
    { attribute: ["srcdoc", "<script></script>"] },
    { attribute: ["href", "javascript:alert(1)"] }
  ]) assert.throws(() => adopt(spec), JSON.stringify(spec));
});

test("init enhances a plate already in the drawer and picks one About panorama", () => {
  const ui = plateDom();
  const plate = catalog.recordPlate(JSON.stringify({ projectId: ui.id }), ui.url, ui.id, ui.document, ui.window);
  const drawer = new ui.Element("details");
  drawer.className = "specimen-drawer";
  drawer.appendChild(plate);
  ui.root.appendChild(drawer);
  const art = new ui.Element("img");
  art.dataset.backgrounds = JSON.stringify(["footer-backgrounds/a.webp", "footer-backgrounds/b.webp"]);
  art.dataset.backgroundSizes = JSON.stringify([[10, 20], [30, 40]]);
  art.setAttribute("data-footer-background", "");
  ui.root.appendChild(art);
  catalog.init(ui.document, ui.window);
  assert.equal(plate.dataset.enhanced, undefined);
  assert.equal(drawer.listeners.toggle.length, 1);
  drawer.open = true;
  drawer.fire("toggle");
  assert.equal(plate.dataset.enhanced, "true");
  assert.equal(plate.querySelectorAll(".plate-lens").length, 1);
  catalog.init(ui.document, ui.window);
  assert.equal(drawer.listeners.toggle.length, 1);
  assert.equal(ui.listeners.resize.length, 1);
  const index = art.src.endsWith("b.webp") ? 1 : 0;
  assert.equal(art.src, JSON.parse(art.dataset.backgrounds)[index]);
  assert.equal(art.width, JSON.parse(art.dataset.backgroundSizes)[index][0]);
  assert.equal(art.height, JSON.parse(art.dataset.backgroundSizes)[index][1]);
});
