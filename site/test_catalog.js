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
const data = { categories: [{ id: "writing" }, { id: "tools" }], projects };
const state = input => catalog.normalizeState(input, data);
const ids = input => catalog.selectProjects(projects, state(input)).map(p => p.id);

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
function fixture(initialURL = "https://example.org/catalog/?utm_source=test#catalog") {
  class Element {
    constructor(name = "div") {
      this.name = name;
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
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
  }
  const ids = {};
  for (const id of ["catalog", "catalog-data", "project-list", "filters", "result-count", "empty-state", "clear-filters", "search", "category-filter", "license-filter", "min-stars", "pushed-since", "sort-order"]) ids[id] = new Element();
  ids["catalog-data"].textContent = JSON.stringify(data);
  ids.filters.hidden = true;
  ids["empty-state"].hidden = true;
  ids["sort-order"].disabled = true;
  Object.defineProperty(ids["license-filter"], "options", { get() { return this.children; } });
  ["all", "known", "unknown", "MIT", "Apache-2.0"].forEach(value => {
    const option = new Element("option");
    option.value = value;
    ids["license-filter"].appendChild(option);
  });
  projects.forEach(project => {
    const card = new Element("article");
    card.dataset.projectId = project.id;
    ids["project-list"].appendChild(card);
  });
  const categoryLinks = ["", "writing", "tools"].map(category => {
    const link = new Element("a");
    link.dataset.category = category;
    return link;
  });
  const panel = new Element("details");
  const document = {
    activeElement: null,
    documentElement: new Element("html"),
    getElementById(id) { return ids[id]; },
    querySelectorAll() { return categoryLinks; },
    querySelector() { return panel; },
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
    document, window, ids, entries, timers, categoryLinks, panel, mobile,
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
