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
  assert.deepEqual(ids({}), ["open-alpha", "open-alpha-2", "open-beta", "open-empty", "open-zero"]);
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
  assert.deepEqual(ids({ category: "writing", license: "known" }), ["open-alpha", "open-beta"]);
  assert.deepEqual(ids({ category: "writing", license: "unknown" }), ["open-alpha-2"]);
  assert.deepEqual(ids({ category: "writing", license: "Apache-2.0" }), ["open-beta"]);
});

test("blank threshold includes unknowns; explicit zero excludes them", () => {
  assert.deepEqual(ids({ stars: "" }), ids({}));
  assert.deepEqual(ids({ stars: "0" }), ["open-alpha", "open-alpha-2", "open-beta", "open-zero"]);
  assert.equal(state({ stars: 0 }).stars, 0);
  assert.deepEqual(ids({ stars: "25" }), ["open-alpha", "open-alpha-2", "open-beta"]);
  assert.deepEqual(ids({ stars: "26" }), ["open-beta"]);
});

test("date threshold is exact and inclusive in UTC; unknown date fails", () => {
  assert.deepEqual(ids({ pushed: "2026-10-09" }), ["open-alpha", "open-alpha-2"]);
  assert.deepEqual(ids({ pushed: "2026-10-08" }), ["open-alpha", "open-alpha-2", "open-beta"]);
  assert.deepEqual(ids({ pushed: "2026-10-10" }), []);
  assert.equal(catalog.pushedAt({ github: { pushed_at: "2026-02-30T01:00:00Z" } }), null);
  assert.equal(catalog.pushedAt({ github: { pushed_at: "invalid" } }), null);
});

test("unknown, NOASSERTION and OTHER licenses remain unknown", () => {
  assert.deepEqual(ids({ license: "unknown" }), ["open-alpha-2", "open-empty", "open-zero"]);
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

// A tiny DOM/history fixture exercises event wiring without jsdom or packages.
function fixture(initialURL = "https://example.org/catalog/?utm_source=test#catalog", options = {}) {
  const fixtureData = options.data || data;
  class Element {
    constructor(name = "div") {
      this.name = name;
      this.tagName = name.toUpperCase();
      this.open = false;
      this.scrolled = 0;
      this.value = "";
      this.hidden = false;
      this.disabled = false;
      this.children = [];
      this.dataset = {};
      this.attributes = {};
      this.listeners = {};
      this.classList = { add() {} };
      this.textContent = "";
    }
    addEventListener(type, listener) {
      (this.listeners[type] ||= []).push(listener);
    }
    fire(type, extra = {}) {
      const event = { button: 0, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...extra };
      (this.listeners[type] || []).forEach(listener => listener(event));
      return event;
    }
    appendChild(child) {
      if (child.name === "fragment") {
        child.children.slice().forEach(node => this.appendChild(node));
        return child;
      }
      if (child.parent) child.parent.children = child.parent.children.filter(node => node !== child);
      this.children.push(child);
      child.parent = this;
      return child;
    }
    querySelectorAll() { return this.children.slice(); }
    querySelector(selector) {
      if (selector === "details.specimen-drawer") return this.children.find(child => child.name === "details") || null;
      if (selector === "summary") return this.children.find(child => child.name === "summary") || null;
      return null;
    }
    focus() { document.activeElement = this; }
    scrollIntoView() { this.scrolled += 1; }
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
  }
  const ids = {};
  for (const id of ["catalog", "catalog-data", "project-list", "filters", "result-count", "empty-state", "clear-filters", "search", "category-filter", "license-filter", "min-stars", "pushed-since", "sort-order"]) ids[id] = new Element();
  if (options.optional !== false) {
    for (const id of ["push-window", "alternative-filter", "metrics-filter", "project-link-notice"]) ids[id] = new Element();
    ids["project-link-notice"].hidden = true;
    Object.defineProperty(ids["alternative-filter"], "options", { get() { return this.children; } });
    const allAlternatives = new Element("option");
    ids["alternative-filter"].appendChild(allAlternatives);
  }
  ids["catalog-data"].textContent = JSON.stringify(fixtureData);
  ids.filters.hidden = true;
  ids["empty-state"].hidden = true;
  ids["sort-order"].disabled = true;
  Object.defineProperty(ids["license-filter"], "options", { get() { return this.children; } });
  ["all", "known", "unknown", "MIT", "Apache-2.0"].forEach(value => {
    const option = new Element("option");
    option.value = value;
    ids["license-filter"].appendChild(option);
  });
  fixtureData.projects.forEach(project => {
    const card = new Element(options.detailsCard ? "details" : "article");
    card.dataset.projectId = project.id;
    card.id = "project-" + project.id;
    ids[card.id] = card;
    if (options.drawers !== false) {
      const drawer = options.detailsCard ? card : new Element("details");
      drawer.appendChild(new Element("summary"));
      if (drawer !== card) card.appendChild(drawer);
    }
    ids["project-list"].appendChild(card);
  });
  const categoryLinks = ["", "writing", "tools"].map(category => {
    const link = new Element("a");
    link.dataset.category = category;
    return link;
  });
  const panel = new Element("details");
  const diagnostics = ["recent", "older", "unknown", "metrics-present", "metrics-missing"].map(key => {
    const node = new Element("span");
    node.dataset.diagnostic = key;
    return node;
  });
  const document = {
    activeElement: null,
    documentElement: new Element("html"),
    getElementById(id) { return ids[id]; },
    querySelectorAll(selector) {
      if (selector === "[data-diagnostic]") return diagnostics;
      if (selector === "a[data-category]" || selector === ".category-nav a[data-category]") return categoryLinks;
      return [];
    },
    querySelector(selector) { return selector === ".category-panel" ? panel : null; },
    createElement(name) { return new Element(name); },
    createDocumentFragment() { return new Element("fragment"); }
  };
  ids.catalog.focus = () => { document.activeElement = ids.catalog; };
  const events = new Element();
  const location = { href: initialURL };
  const entries = [initialURL];
  let cursor = 0;
  const history = {
    state: null,
    pushState(_state, _title, url) {
      entries.splice(cursor + 1, entries.length, url);
      cursor += 1;
      location.href = url;
    },
    replaceState(_state, _title, url) {
      entries[cursor] = url;
      location.href = url;
    },
    go(delta) {
      cursor += delta;
      location.href = entries[cursor];
      events.fire("popstate");
    }
  };
  const timers = new Map();
  let nextTimer = 0;
  const mobile = new Element();
  mobile.matches = true;
  const window = {
    location, history,
    addEventListener: events.addEventListener.bind(events),
    setTimeout(callback) { timers.set(++nextTimer, callback); return nextTimer; },
    clearTimeout(id) { timers.delete(id); },
    matchMedia() { return mobile; }
  };
  return {
    document, window, ids, entries, timers, categoryLinks, panel, mobile, diagnostics,
    fire: events.fire.bind(events),
    flush() { const callbacks = Array.from(timers.values()); timers.clear(); callbacks.forEach(callback => callback()); },
    visible() { return ids["project-list"].children.filter(card => !card.hidden).map(card => card.dataset.projectId); }
  };
}

test("progressive enhancement reveals controls, enables sorting and sizes category panel", () => {
  const ui = fixture();
  assert.equal(catalog.init(ui.document, ui.window), true);
  assert.equal(ui.ids.filters.hidden, false);
  assert.equal(ui.ids["sort-order"].disabled, false);
  assert.equal(ui.ids["result-count"].textContent, "5 projects");
  assert.equal(ui.panel.open, false);
  ui.mobile.matches = false;
  ui.mobile.fire("change");
  assert.equal(ui.panel.open, true);
  assert.equal(catalog.init(ui.document, ui.window), true);
  assert.equal(ui.ids.search.listeners.input.length, 1);
});

test("invalid or mismatched embedded data leaves the complete static fallback intact", () => {
  for (const payload of ["not json", "{}", JSON.stringify({ ...data, projects: projects.slice(1) })]) {
    const ui = fixture();
    ui.ids["catalog-data"].textContent = payload;
    assert.equal(catalog.init(ui.document, ui.window), false);
    assert.equal(ui.ids.filters.hidden, true);
    assert.equal(ui.ids["sort-order"].disabled, true);
    assert.equal(ui.visible().length, projects.length);
  }
});

test("Back and Forward cancel stale search debounce and restore URL, controls and results", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  ui.document.activeElement = ui.ids.search;
  ui.ids.search.value = "Microsoft";
  ui.ids.search.fire("input");
  assert.equal(ui.visible().length, 5);
  ui.flush();
  assert.deepEqual(ui.visible(), ["open-alpha"]);
  assert.equal(ui.document.activeElement, ui.ids.search);
  assert.equal(ui.ids["result-count"].textContent, "1 of 5 projects");
  assert.equal(new URL(ui.window.location.href).searchParams.get("q"), "Microsoft");
  ui.ids.search.value = "Google";
  ui.ids.search.fire("input");
  assert.equal(ui.timers.size, 1);
  ui.window.history.go(-1);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.ids.search.value, "");
  assert.equal(ui.visible().length, 5);
  ui.flush();
  assert.equal(ui.visible().length, 5);
  assert.equal(new URL(ui.window.location.href).searchParams.get("q"), null);
  ui.window.history.go(1);
  assert.equal(ui.ids.search.value, "Microsoft");
  assert.deepEqual(ui.visible(), ["open-alpha"]);
});

test("repeated clear is idempotent and history restores an explicit zero threshold", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  ui.ids["min-stars"].value = "0";
  ui.ids["min-stars"].fire("change");
  assert.equal(ui.ids["min-stars"].value, "0");
  assert.equal(ui.visible().length, 4);
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.ids["min-stars"].value, "");
  assert.equal(ui.visible().length, 5);
  const entries = ui.entries.length;
  ui.ids["clear-filters"].fire("click");
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.entries.length, entries);
  assert.equal(new URL(ui.window.location.href).hash, "#catalog");
  assert.equal(new URL(ui.window.location.href).searchParams.get("utm_source"), "test");
  ui.window.history.go(-1);
  assert.equal(ui.ids["min-stars"].value, "0");
  assert.equal(ui.visible().length, 4);
});

test("sidebar category links filter in place, mark current category and respect modified clicks", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  assert.equal(ui.categoryLinks[0].attributes["aria-current"], "true");
  const modified = ui.categoryLinks[2].fire("click", { ctrlKey: true });
  assert.equal(modified.defaultPrevented, false);
  assert.equal(ui.ids["category-filter"].value, "");
  const plain = ui.categoryLinks[2].fire("click");
  assert.equal(plain.defaultPrevented, true);
  assert.equal(ui.document.activeElement, ui.ids.catalog);
  assert.equal(ui.ids["category-filter"].value, "tools");
  assert.equal(ui.categoryLinks[0].attributes["aria-current"], undefined);
  assert.equal(ui.categoryLinks[2].attributes["aria-current"], "true");
  assert.deepEqual(ui.visible(), ["open-alpha", "open-empty", "open-zero"]);
  assert.equal(new URL(ui.window.location.href).hash, "#catalog");
});

test("submit cancels debounce, applies current controls, prevents navigation and shows empty state", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  ui.ids.search.value = "missing";
  ui.ids.search.fire("input");
  assert.equal(ui.ids.filters.fire("submit").defaultPrevented, true);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.ids["empty-state"].hidden, false);
  assert.equal(ui.ids["result-count"].textContent, "0 of 5 projects");
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.ids["empty-state"].hidden, true);
});

test("unavailable history APIs do not break local-file filtering", () => {
  const ui = fixture("file:///tmp/catalog/index.html");
  ui.window.history.pushState = () => { throw new Error("History unavailable"); };
  catalog.init(ui.document, ui.window);
  ui.ids["category-filter"].value = "tools";
  assert.doesNotThrow(() => ui.ids["category-filter"].fire("change"));
  assert.deepEqual(ui.visible(), ["open-alpha", "open-empty", "open-zero"]);
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
  assert.deepEqual(ids({ window: "recent" }), ["open-alpha", "open-alpha-2", "open-beta"]);
  assert.deepEqual(ids({ window: "older" }), []);
  assert.deepEqual(ids({ window: "unknown" }), ["open-empty", "open-zero"]);
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
  assert.equal(catalog.matchesProject(unrelated, state({ alternative: "Microsoft Word" }), data), false);
  assert.deepEqual(catalog.alternativeNames(projects), ["Google Docs", "Microsoft Word"]);
});

test("metrics presence means a cached GitHub record, not known license, stars or push date", () => {
  assert.deepEqual(ids({ metrics: "present" }), ["open-alpha", "open-alpha-2", "open-beta", "open-zero"]);
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
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  ui.diagnostics.forEach(node => assert.equal(node.textContent, String(counts[node.dataset.diagnostic])));
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
  assert.equal(catalog.stateToURL(input, legacyState).href, input);
});

test("older markup works without optional controls and retains URL-only optional state until clear", () => {
  const legacy = fixture(undefined, { optional: false, drawers: false });
  assert.equal(catalog.init(legacy.document, legacy.window), true);
  assert.equal(legacy.visible().length, 5);
  const ui = fixture("https://example.org/?metrics=present&window=unknown", { optional: false });
  assert.equal(catalog.init(ui.document, ui.window), true);
  assert.deepEqual(ui.visible(), ["open-zero"]);
  ui.ids["min-stars"].value = "0";
  ui.ids["min-stars"].fire("change");
  assert.deepEqual(ui.visible(), ["open-zero"]);
  assert.equal(new URL(ui.window.location.href).searchParams.get("metrics"), "present");
  assert.equal(new URL(ui.window.location.href).searchParams.get("window"), "unknown");
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.visible().length, 5);
  assert.equal(new URL(ui.window.location.href).search, "");
});

test("optional controls populate reviewed alternatives and restore without stale search on Back, Forward and bfcache", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  assert.deepEqual(ui.ids["alternative-filter"].options.map(option => option.value), ["", "Google Docs", "Microsoft Word"]);
  ui.ids["push-window"].value = "recent";
  ui.ids["alternative-filter"].value = "Microsoft Word";
  ui.ids["metrics-filter"].value = "present";
  ui.ids["alternative-filter"].fire("change");
  assert.deepEqual(ui.visible(), ["open-alpha"]);
  ui.ids.search.value = "stale query";
  ui.ids.search.fire("input");
  ui.window.history.go(-1);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.ids["push-window"].value, "all");
  assert.equal(ui.ids["alternative-filter"].value, "");
  assert.equal(ui.ids["metrics-filter"].value, "all");
  assert.equal(ui.visible().length, 5);
  ui.flush();
  ui.window.history.go(1);
  assert.equal(ui.ids["push-window"].value, "recent");
  assert.equal(ui.ids["alternative-filter"].value, "Microsoft Word");
  assert.equal(ui.ids["metrics-filter"].value, "present");
  assert.deepEqual(ui.visible(), ["open-alpha"]);
  ui.ids.search.value = "another stale query";
  ui.ids.search.fire("input");
  ui.ids["metrics-filter"].value = "missing";
  ui.fire("pageshow", { persisted: true });
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.ids.search.value, "");
  assert.equal(ui.ids["metrics-filter"].value, "present");
  assert.deepEqual(ui.visible(), ["open-alpha"]);
});

test("project hash opens its specimen drawer and focuses the linked project on initial load and hash navigation", () => {
  const ui = fixture("https://example.org/#project-open-alpha");
  catalog.init(ui.document, ui.window);
  const alpha = ui.ids["project-open-alpha"];
  assert.equal(alpha.children[0].open, true);
  assert.equal(ui.document.activeElement, alpha.children[0].children[0]);
  assert.equal(alpha.scrolled, 1);
  const beta = ui.ids["project-open-beta"];
  assert.equal(beta.children[0].open, false);
  ui.window.location.href = "https://example.org/#project-open-beta";
  ui.fire("hashchange");
  assert.equal(beta.children[0].open, true);
  assert.equal(ui.document.activeElement, beta.children[0].children[0]);
  assert.equal(beta.scrolled, 1);
  assert.equal(ui.ids["project-link-notice"].hidden, true);
  // A project's card may itself be the disclosure; legacy articles still focus.
  for (const options of [{ detailsCard: true }, { drawers: false }]) {
    const layout = fixture("https://example.org/#project-open-alpha", options);
    assert.equal(catalog.init(layout.document, layout.window), true);
    const card = layout.ids["project-open-alpha"];
    if (options.detailsCard) assert.equal(card.open, true);
    else assert.equal(layout.document.activeElement, card);
    assert.equal(card.scrolled, 1);
  }
});

test("filtered-out project hashes keep filters and show a notice, then reveal the project when filters clear", () => {
  const ui = fixture("https://example.org/?metrics=missing#project-open-alpha");
  catalog.init(ui.document, ui.window);
  assert.deepEqual(ui.visible(), ["open-empty"]);
  const alpha = ui.ids["project-open-alpha"];
  assert.equal(alpha.children[0].open, false);
  assert.equal(alpha.scrolled, 0);
  assert.equal(ui.ids["metrics-filter"].value, "missing");
  assert.equal(ui.ids["project-link-notice"].hidden, false);
  assert.match(ui.ids["project-link-notice"].textContent, /Open Alpha.*hidden by your current filters/);
  assert.equal(new URL(ui.window.location.href).searchParams.get("metrics"), "missing");
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.ids["project-link-notice"].hidden, true);
  assert.equal(alpha.children[0].open, true);
  assert.equal(new URL(ui.window.location.href).hash, "#project-open-alpha");
  const legacy = fixture("https://example.org/?metrics=missing#project-open-alpha", { optional: false });
  assert.equal(catalog.init(legacy.document, legacy.window), true);
  const notice = legacy.ids.filters.children.find(child => child.id === "project-link-notice");
  assert.ok(notice);
  assert.equal(notice.hidden, false);
  assert.equal(notice.attributes.role, "status");
});

test("Back and Forward restore linked drawers and filters together, canceling pending input", () => {
  const ui = fixture("https://example.org/#project-open-alpha");
  catalog.init(ui.document, ui.window);
  ui.window.history.pushState(null, "", "https://example.org/?alternative=Google+Docs#project-open-beta");
  ui.fire("hashchange");
  assert.deepEqual(ui.visible(), ["open-beta"]);
  ui.ids.search.value = "stale";
  ui.ids.search.fire("input");
  ui.window.history.go(-1);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.visible().length, 5);
  assert.equal(ui.ids["alternative-filter"].value, "");
  assert.equal(ui.document.activeElement, ui.ids["project-open-alpha"].children[0].children[0]);
  ui.flush();
  ui.window.history.go(1);
  assert.deepEqual(ui.visible(), ["open-beta"]);
  assert.equal(ui.ids["alternative-filter"].value, "Google Docs");
  assert.equal(ui.document.activeElement, ui.ids["project-open-beta"].children[0].children[0]);
});

test("unknown, malformed and ordinary section hashes do not open projects or steal focus", () => {
  for (const hash of ["#project-missing", "#project-%E0%A4%A", "#catalog", "#methodology"]) {
    const ui = fixture("https://example.org/" + hash);
    ui.document.activeElement = ui.ids.search;
    assert.equal(catalog.init(ui.document, ui.window), true);
    assert.equal(ui.document.activeElement, ui.ids.search);
    assert.equal(ui.visible().length, 5);
    assert.equal(ui.ids["project-link-notice"].hidden, true);
    projects.forEach(project => assert.equal(ui.ids["project-" + project.id].children[0].open, false));
  }
});


test("changing filters preserves a manually closed linked drawer and does not steal search focus", () => {
  const ui = fixture("https://example.org/#project-open-alpha");
  catalog.init(ui.document, ui.window);
  const alpha = ui.ids["project-open-alpha"];
  alpha.children[0].open = false;
  ui.document.activeElement = ui.ids.search;
  ui.ids.search.value = "editor";
  ui.ids.search.fire("input");
  ui.flush();
  assert.equal(alpha.hidden, false);
  assert.equal(alpha.children[0].open, false);
  assert.equal(ui.document.activeElement, ui.ids.search);
  assert.equal(alpha.scrolled, 1);
});
