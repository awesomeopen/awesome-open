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
      this.textContent = "";
      this.isConnected = true;
    }
    addEventListener(type, listener) {
      (this.listeners[type] ||= []).push(listener);
    }
    removeEventListener(type, listener) {
      this.listeners[type] = (this.listeners[type] || []).filter(item => item !== listener);
    }
    fire(type, extra = {}) {
      const event = { target: this, button: 0, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...extra };
      (this.listeners[type] || []).slice().forEach(listener => listener(event));
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
    scrollIntoView() { this.scrolled += 1; }
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
    removeAttribute(key) { delete this.attributes[key]; }
    cloneNode(deep) {
      const clone = new Element(this.name);
      Object.assign(clone.dataset, this.dataset);
      Object.assign(clone.attributes, this.attributes);
      for (const key of ["className", "id", "textContent", "open", "src", "complete"]) clone[key] = this[key];
      if (deep) this.children.forEach(child => clone.appendChild(child.cloneNode(true)));
      return clone;
    }
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
  const alphabeticalIds = fixtureData.projects.slice().sort(catalog.comparator("name")).map(project => project.id);
  fixtureData.projects.forEach(project => {
    const card = new Element(options.detailsCard ? "details" : "article");
    card.className = "project-card";
    card.dataset.projectId = project.id;
    card.id = "project-" + project.id;
    ids[card.id] = card;
    if (options.drawers !== false) {
      const drawer = options.detailsCard ? card : new Element("details");
      drawer.classList.add("specimen-drawer");
      const summary = new Element("summary");
      const folio = String(alphabeticalIds.indexOf(project.id) + 1).padStart(3, "0");
      const addText = (parent, className, text) => {
        const node = new Element("span");
        node.className = className;
        node.textContent = text;
        parent.appendChild(node);
        return node;
      };
      addText(summary, "folio", folio);
      drawer.appendChild(summary);
      addText(drawer, "sheet-folio", "Folio " + folio);
      addText(drawer, "plate-index", "Field notes / " + folio);
      addText(drawer, "registry", "OP-" + project.id.slice(0, 8).toUpperCase());
      const permalink = addText(drawer, "permalink", "Permalink");
      permalink.setAttribute("href", "#project-" + project.id);
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
      return ids["project-list"].querySelectorAll(selector);
    },
    querySelector(selector) { return selector === ".category-panel" ? panel : ids["project-list"].querySelector(selector); },
    createElement(name) { return new Element(name); },
    createElementNS(_namespace, name) { return new Element(name); },
    importNode(node, deep) { return node.cloneNode(deep); },
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
    document, window, ids, entries, timers, categoryLinks, panel, mobile, diagnostics, Element, events,
    fire: events.fire.bind(events),
    flush() { const callbacks = Array.from(timers.values()); timers.clear(); callbacks.forEach(callback => callback()); },
    visible() { return ids["project-list"].children.filter(card => !card.hidden).map(card => card.dataset.projectId); }
  };
}

function assertVisiblePositions(ui, expectedIds) {
  assert.deepEqual(ui.visible(), expectedIds);
  assert.deepEqual(expectedIds.map(id => ui.ids["project-" + id].querySelector(".folio").textContent),
    expectedIds.map((_, index) => String(index + 1).padStart(3, "0")));
}

function recordIdentities(ui) {
  return Object.fromEntries(projects.map(project => {
    const card = ui.ids["project-" + project.id];
    return [project.id, {
      id: card.id, projectId: card.dataset.projectId,
      folio: card.querySelector(".sheet-folio").textContent,
      notes: card.querySelector(".plate-index").textContent,
      registry: card.querySelector(".registry").textContent,
      permalink: card.querySelector(".permalink").attributes.href
    }];
  }));
}

test("visible positions follow default stars, name and latest-push sort without changing record identity", () => {
  const ui = fixture();
  const original = recordIdentities(ui);
  catalog.init(ui.document, ui.window);
  assertVisiblePositions(ui, ids({}));
  assert.equal(ui.ids["project-open-beta"].querySelector(".folio").textContent, "001");
  assert.equal(ui.ids["project-open-beta"].querySelector(".sheet-folio").textContent, "Folio 003");
  for (const sort of ["name", "pushed", "stars"]) {
    ui.ids["sort-order"].value = sort;
    ui.ids["sort-order"].fire("change");
    assertVisiblePositions(ui, ids({ sort }));
    assert.deepEqual(recordIdentities(ui), original);
  }
});

test("visible positions restart after filtering, clear and history, including zero results", () => {
  const ui = fixture();
  const original = recordIdentities(ui);
  catalog.init(ui.document, ui.window);
  ui.ids["category-filter"].value = "tools";
  ui.ids["category-filter"].fire("change");
  assertVisiblePositions(ui, ["open-alpha", "open-zero", "open-empty"]);
  ui.ids.search.value = "unfindable";
  ui.ids.search.fire("change");
  assertVisiblePositions(ui, []);
  assert.equal(ui.ids["empty-state"].hidden, false);
  ui.ids["clear-filters"].fire("click");
  assertVisiblePositions(ui, ids({}));
  ui.window.history.go(-1);
  assertVisiblePositions(ui, []);
  ui.window.history.go(-1);
  assertVisiblePositions(ui, ["open-alpha", "open-zero", "open-empty"]);
  ui.window.history.go(1);
  assertVisiblePositions(ui, []);
  ui.window.history.go(1);
  assertVisiblePositions(ui, ids({}));
  assert.deepEqual(recordIdentities(ui), original);
});

test("progressive enhancement reveals controls, enables sorting and leaves category disclosure closed", () => {
  const ui = fixture();
  assert.equal(catalog.init(ui.document, ui.window), true);
  assert.equal(ui.ids.filters.hidden, false);
  assert.equal(ui.ids["sort-order"].disabled, false);
  assert.equal(ui.ids["result-count"].textContent, "5 projects");
  assert.equal(ui.panel.open, false);
  ui.mobile.matches = false;
  ui.mobile.fire("change");
  assert.equal(ui.panel.open, false);
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
  assert.deepEqual(ui.visible(), ["open-alpha", "open-zero", "open-empty"]);
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
  assert.equal(ui.ids["empty-state"].scrolled, 1);
  ui.ids["clear-filters"].fire("click");
  assert.equal(ui.ids["empty-state"].hidden, true);
});

test("unavailable history APIs do not break local-file filtering", () => {
  const ui = fixture("file:///tmp/catalog/index.html");
  ui.window.history.pushState = () => { throw new Error("History unavailable"); };
  catalog.init(ui.document, ui.window);
  ui.ids["category-filter"].value = "tools";
  assert.doesNotThrow(() => ui.ids["category-filter"].fire("change"));
  assert.deepEqual(ui.visible(), ["open-alpha", "open-zero", "open-empty"]);
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
  assert.equal(catalog.matchesProject(unrelated, state({ alternative: "Microsoft Word" }), data), false);
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
  assert.equal(catalog.stateToURL(input, legacyState).searchParams.get("sort"), "name");
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

test("typing stays in place; submit jumps to the first rendered match", () => {
  const ui = fixture();
  catalog.init(ui.document, ui.window);
  ui.ids.search.value = "alpha";
  ui.ids.search.fire("input");
  assert.equal(ui.ids["project-list"].children.reduce((n,c)=>n+c.scrolled,0), 0);
  ui.ids.filters.fire("submit");
  const first = ui.ids["project-list"].children.find(c=>!c.hidden);
  assert.equal(first.scrolled, 1);
  assert.equal(ui.document.activeElement, first.querySelector("summary"));
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

test("explicit name sorting survives URL changes while reset uses stars", () => {
  const explicit = state(new URLSearchParams("sort=name&category=writing"));
  assert.equal(explicit.sort, "name");
  assert.deepEqual(ids({ sort: "name" }), ["open-alpha", "open-alpha-2", "open-beta", "open-empty", "open-zero"]);
  const url = catalog.stateToURL("https://example.org/?sort=name", explicit);
  assert.equal(state(url.searchParams).sort, "name");
  assert.equal(catalog.stateToURL(url, state({})).searchParams.has("sort"), false);
  assert.equal(state({}).sort, "stars");
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

// Fetch and parsing are injected browser interfaces. The fixture models the
// generated static-record DOM; integration/browser checks exercise real HTML.
function detailFixture(options = {}) {
  const detailProjects = Array.from({ length: options.count || 5 }, (_, index) => ({
    ...projects[index % projects.length], id: (index + 1).toString(16).repeat(64), name: 'Record ' + index
  }));
  const detailData = { ...data, projects: detailProjects };
  const ui = fixture(options.url, { data: detailData });
  const { Element } = ui;
  ui.calls = [];
  ui.parseCount = 0;
  ui.records = detailProjects.map(project => {
    const card = ui.ids['project-' + project.id], drawer = card.querySelector('details.specimen-drawer');
    drawer.children.slice(1).forEach(child => child.remove());
    const label = new Element('span');
    label.id = 'name-' + project.id;
    drawer.querySelector('summary').appendChild(label);
    const host = new Element();
    host.className = 'specimen-detail-host';
    host.dataset.projectId = project.id;
    host.dataset.detailUrl = 'records/' + project.id + '.html';
    const fallback = new Element('p');
    fallback.className = 'detail-fallback';
    const link = new Element('a');
    link.setAttribute('href', host.dataset.detailUrl);
    fallback.appendChild(link);
    host.appendChild(fallback);
    drawer.appendChild(host);
    return { project, card, drawer, host, fallback, summary: drawer.querySelector('summary') };
  });
  function createRecord(spec) {
    const record = new Element('html');
    record.getElementById = id => record.querySelectorAll('*').find(node => node.id === id) || null;
    const base = new Element('base');
    base.setAttribute('href', spec.base || '../');
    if (!spec.noBase) record.appendChild(base);
    const card = new Element('article');
    card.className = 'project-card';
    card.dataset.projectId = spec.wrongIdentity ? 'other' : spec.projectId;
    card.id = 'project-' + card.dataset.projectId;
    const label = new Element('summary');
    label.id = 'name-' + spec.projectId;
    if (!spec.noLabel) card.appendChild(label);
    const plate = new Element();
    plate.className = 'specimen-interior specimen-plate';
    plate.setAttribute('aria-labelledby', spec.wrongLabel ? 'name-other' : label.id);
    const field = new Element();
    field.className = 'plate-field';
    field.dataset.seed = spec.projectId.slice(0, 16);
    const img = new Element('img');
    img.setAttribute('src', spec.imageURL || 'specimens/drawing.webp');
    img.complete = false;
    field.appendChild(img);
    plate.appendChild(field);
    const crop = new Element();
    crop.className = 'plate-crop';
    crop.clientWidth = 50;
    plate.appendChild(crop);
    const departure = new Element('nav');
    departure.className = 'plate-departure';
    plate.appendChild(departure);
    for (const [index, value] of [false, true, false].entries()) {
      const detail = new Element('details');
      detail.id = 'evidence-' + index;
      detail.open = value;
      plate.appendChild(detail);
    }
    const category = new Element('a');
    category.dataset.category = 'tools';
    category.setAttribute('href', 'https://example.org/source#tools');
    plate.appendChild(category);
    const permalink = new Element('a');
    permalink.className = 'permalink';
    permalink.setAttribute('href', '#project-' + spec.projectId);
    plate.appendChild(permalink);
    const evidence = new Element('a');
    evidence.className = 'evidence-download';
    evidence.setAttribute('href', 'catalog.json');
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
  ui.window.AbortController = AbortController;
  ui.window.DOMParser = class {
    parseFromString(body, mime) {
      assert.equal(mime, 'text/html');
      ui.parseCount += 1;
      return createRecord(JSON.parse(body));
    }
  };
  ui.window.fetch = (url, init) => new Promise((resolve, reject) => {
    ui.calls.push({ url, init, resolve, reject });
  });
  ui.respond = (index, spec = {}, overrides = {}) => {
    const call = ui.calls[index];
    const projectId = /\/([a-f0-9]{64})\.html$/.exec(call.url)[1];
    call.resolve({ ok: true, url: call.url, headers: { get: () => 'text/html; charset=utf-8' },
      text: async () => JSON.stringify({ projectId, ...spec }), ...overrides });
  };
  ui.toggle = (index, open) => {
    ui.records[index].drawer.open = open;
    ui.records[index].drawer.fire('toggle');
  };
  ui.plate = index => ui.records[index].host.querySelector('.specimen-plate');
  ui.settle = () => new Promise(resolve => setImmediate(resolve));
  ui.createRecord = createRecord;
  return ui;
}

test('deferred records allocate no plate, requests or loading UI until a native drawer opens', () => {
  const ui = detailFixture();
  assert.equal(catalog.init(ui.document, ui.window), true);
  assert.equal(ui.calls.length, 0);
  assert.equal(ui.document.querySelectorAll('.specimen-plate').length, 0);
  for (const { host, drawer, fallback } of ui.records) {
    assert.equal(host.children.length, 1);
    assert.equal(fallback.hidden, false);
    assert.equal(drawer.listeners.toggle.length, 1);
  }
  catalog.init(ui.document, ui.window);
  assert.equal(ui.events.listeners.resize.length, 1);
  assert.equal(ui.events.listeners.pagehide.length, 1);
  assert.equal(ui.records[0].drawer.listeners.toggle.length, 1);
  assert.equal(ui.ids['project-list'].listeners.click.length, 1);
});

test('opening fetches one same-origin record, imports only its matching plate and rebases assets', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.records[0].summary.focus();
  ui.toggle(0, true);
  const { host, fallback, summary } = ui.records[0];
  assert.equal(ui.calls.length, 1);
  assert.equal(host.dataset.detailState, 'loading');
  assert.equal(host.getAttribute('aria-busy'), 'true');
  assert.equal(host.querySelector('.detail-status').getAttribute('role'), 'status');
  assert.equal(fallback.hidden, true, 'Loading hides the fallback before the response settles');
  assert.equal(ui.calls[0].url, 'https://example.org/catalog/records/' + ui.records[0].project.id + '.html');
  assert.equal(ui.calls[0].init.mode, 'same-origin');
  assert.equal(ui.calls[0].init.redirect, 'error');
  ui.toggle(0, true);
  catalog.init(ui.document, ui.window);
  assert.equal(ui.calls.length, 1);
  ui.respond(0);
  await ui.settle();
  const plate = ui.plate(0);
  assert.ok(plate);
  assert.equal(plate.querySelector('img').getAttribute('src'), 'https://example.org/catalog/specimens/drawing.webp');
  assert.equal(plate.querySelector('.evidence-download').getAttribute('href'), 'https://example.org/catalog/catalog.json');
  assert.equal(plate.querySelector('.permalink').getAttribute('href'), '#project-' + ui.records[0].project.id);
  assert.equal(host.querySelector('base'), null);
  assert.equal(host.querySelector('.project-card'), null);
  assert.equal(host.dataset.detailState, 'loaded');
  assert.equal(host.getAttribute('aria-busy'), null);
  assert.equal(host.querySelector('.detail-status').hidden, true);
  assert.equal(fallback.hidden, true, 'Loaded plates hide the fallback from display and keyboard access');
  assert.equal(ui.document.activeElement, summary);
  assert.equal(plate.querySelectorAll('.plate-lens').length, 1);
  assert.equal(plate.querySelectorAll('.plate-wild-terrain').length, 1);
  ui.toggle(0, false);
  ui.toggle(0, true);
  catalog.init(ui.document, ui.window);
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.plate(0), plate);
  assert.equal(plate.querySelectorAll('.plate-lens').length, 1);
  assert.equal(plate.querySelector('.plate-field').listeners.pointermove.length, 1);
});

test('record URLs without base tags resolve relative to the static file', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  ui.respond(0, { noBase: true, imageURL: '../specimens/drawing.webp' });
  await ui.settle();
  assert.equal(ui.plate(0).querySelector('img').getAttribute('src'), 'https://example.org/catalog/specimens/drawing.webp');
});

test('closing aborts and stale responses cannot mount, overwrite or duplicate a newer request', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  ui.toggle(0, false);
  assert.equal(ui.calls[0].init.signal.aborted, true);
  assert.equal(ui.records[0].host.dataset.detailState, 'idle');
  assert.equal(ui.records[0].fallback.hidden, false, 'Idle restores fallback after cancellation or eviction');
  ui.toggle(0, true);
  assert.equal(ui.calls.length, 2);
  ui.respond(0);
  await ui.settle();
  assert.equal(ui.parseCount, 0);
  assert.equal(ui.plate(0), null);
  assert.equal(ui.records[0].host.dataset.detailState, 'loading');
  ui.respond(1);
  await ui.settle();
  assert.ok(ui.plate(0));
  assert.equal(ui.parseCount, 1);
  assert.equal(ui.document.querySelectorAll('.specimen-plate').length, 1);
});

test('closing during response text and late abort errors are ignored', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  let finishText;
  ui.respond(0, {}, { text: () => new Promise(resolve => { finishText = resolve; }) });
  await ui.settle();
  ui.toggle(0, false);
  finishText(JSON.stringify({ projectId: ui.records[0].project.id }));
  await ui.settle();
  assert.equal(ui.parseCount, 0);
  assert.equal(ui.plate(0), null);
  assert.equal(ui.records[0].host.dataset.detailState, 'idle');
  assert.equal(ui.records[0].fallback.hidden, false, 'Idle restores fallback after cancellation or eviction');
  ui.toggle(0, true);
  ui.toggle(0, false);
  ui.toggle(0, true);
  ui.calls[1].reject(new Error('aborted transfer completed late'));
  await ui.settle();
  assert.equal(ui.records[0].host.dataset.detailState, 'loading');
  ui.respond(2);
  await ui.settle();
  assert.ok(ui.plate(0));
});

test('starting loading returns focus from the disappearing fallback to the summary', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  const { fallback, summary } = ui.records[0];
  assert.equal(fallback.hidden, false, 'Initialized but idle fallback remains available');
  fallback.querySelector('a').focus();
  ui.toggle(0, true);
  assert.equal(fallback.hidden, true);
  assert.equal(ui.document.activeElement, summary);
  ui.respond(0);
  await ui.settle();
  assert.equal(fallback.hidden, true);
  assert.equal(ui.document.activeElement, summary);
});

test('failure exposes a retry and static fallback; repeated retry starts only one request', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  ui.calls[0].reject(new Error('offline'));
  await ui.settle();
  const { host, summary } = ui.records[0];
  const retry = host.querySelector('.detail-retry');
  assert.equal(host.dataset.detailState, 'error');
  assert.equal(retry.hidden, false);
  assert.equal(ui.records[0].fallback.hidden, false);
  retry.focus();
  retry.fire('click');
  retry.fire('click');
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.records[0].fallback.hidden, true, 'Retry hides the fallback again before settling');
  assert.equal(ui.document.activeElement, summary, 'Focus returns to a stable control before retry is hidden');
  ui.respond(1);
  await ui.settle();
  assert.equal(host.dataset.detailState, 'loaded');
  assert.equal(retry.hidden, true);
  assert.equal(ui.records[0].fallback.hidden, true);
  assert.ok(ui.plate(0));
});

test('bad responses, identity mismatches and active or cross-origin payloads leave the fallback intact', async () => {
  const cases = [
    [{}, { ok: false }],
    [{}, { headers: { get: () => 'application/json' } }],
    [{}, { url: 'https://elsewhere.example/record.html' }],
    [{}, { text: async () => 'not a valid record' }],
    [{}, { text: async () => 'x'.repeat(2 * 1024 * 1024 + 1) }],
    [{ wrongIdentity: true }], [{ wrongLabel: true }], [{ noLabel: true }],
    [{ duplicatePlate: true }], [{ duplicateCard: true }], [{ detachedPlate: true }],
    [{ base: 'https://elsewhere.example/' }],
    [{ imageURL: 'https://elsewhere.example/drawing.webp' }],
    [{ imageURL: 'javascript:alert(1)' }],
    [{ activeTag: 'script' }], [{ activeTag: 'iframe' }], [{ activeTag: 'foreignObject' }],
    [{ attribute: ['onclick', 'alert(1)'] }],
    [{ attribute: ['style', 'background:url(https://elsewhere.example/image)'] }],
    [{ attribute: ['srcdoc', '<script></script>'] }],
    [{ attribute: ['href', 'javascript:alert(1)'] }]
  ];
  for (const [spec, overrides] of cases) {
    const ui = detailFixture();
    catalog.init(ui.document, ui.window);
    ui.toggle(0, true);
    ui.respond(0, spec, overrides);
    await ui.settle();
    assert.equal(ui.plate(0), null, JSON.stringify(spec));
    assert.equal(ui.records[0].host.dataset.detailState, 'error');
    assert.equal(ui.records[0].fallback.hidden, false);
    assert.equal(ui.records[0].host.querySelector('.detail-retry').hidden, false);
  }
});

test('invalid destinations, local files and missing APIs never request a record or break filtering', () => {
  const cases = [
    ui => { ui.records[0].host.dataset.detailUrl = 'https://elsewhere.example/records/' + ui.records[0].project.id + '.html'; },
    ui => { ui.records[0].host.dataset.detailUrl = '/records/other.html'; },
    ui => { ui.records[0].host.dataset.projectId = 'invalid'; },
    ui => { ui.window.location.href = 'file:///tmp/site/index.html'; },
    ui => { delete ui.window.fetch; },
    ui => { delete ui.window.DOMParser; }
  ];
  for (const change of cases) {
    const ui = detailFixture();
    change(ui);
    assert.equal(catalog.init(ui.document, ui.window), true);
    ui.toggle(0, true);
    assert.equal(ui.calls.length, 0);
    assert.equal(ui.records[0].fallback.hidden, false);
    assert.equal(ui.records[0].host.dataset.detailState, 'error');
    assert.equal(ui.records[0].host.querySelector('.detail-retry'), null);
    ui.ids['category-filter'].value = 'tools';
    assert.doesNotThrow(() => ui.ids['category-filter'].fire('change'));
  }
});

test('closed-plate LRU keeps three, never evicts an open plate, cleans listeners and restores nested disclosures', async () => {
  const ui = detailFixture({ count: 6 });
  catalog.init(ui.document, ui.window);
  for (let index = 0; index < 6; index += 1) { ui.toggle(index, true); ui.respond(index); }
  await ui.settle();
  assert.equal(ui.document.querySelectorAll('.specimen-plate').length, 6, 'Every intentionally open plate remains mounted');
  const first = ui.plate(0), field = first.querySelector('.plate-field'), img = first.querySelector('img');
  first.querySelectorAll('details').forEach((detail, index) => { detail.open = index !== 1; });
  assert.equal(field.listeners.pointermove.length, 1);
  assert.equal(img.listeners.load.length, 1);
  for (let index = 0; index < 4; index += 1) ui.toggle(index, false);
  assert.equal(ui.plate(0), null);
  assert.ok(ui.plate(4));
  assert.ok(ui.plate(5));
  assert.equal(ui.document.querySelectorAll('.specimen-plate').length, 5);
  assert.deepEqual(field.listeners.pointermove, []);
  assert.deepEqual(field.listeners.pointerleave, []);
  assert.deepEqual(field.listeners.click, []);
  assert.deepEqual(img.listeners.load, []);
  assert.equal(first.plateLayout, undefined);
  assert.equal(first.plateCleanup, undefined);
  assert.equal(ui.records[0].host.dataset.detailState, 'idle');
  assert.equal(ui.records[0].fallback.hidden, false, 'Idle restores fallback after cancellation or eviction');
  // Reusing a cached closed plate moves it to the newest closed position.
  ui.toggle(1, true);
  ui.toggle(1, false);
  ui.toggle(4, false);
  assert.equal(ui.plate(2), null);
  assert.ok(ui.plate(1));
  ui.toggle(0, true);
  assert.equal(ui.calls.length, 7);
  ui.respond(6);
  await ui.settle();
  assert.notEqual(ui.plate(0), first);
  assert.deepEqual(ui.plate(0).querySelectorAll('details').map(detail => detail.open), [true, false, true]);
  assert.equal(ui.plate(0).querySelectorAll('.plate-lens').length, 1);
});

test('an open drawer awaiting its toggle event is protected from closed-cache eviction', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  for (let index = 0; index < 5; index += 1) { ui.toggle(index, true); ui.respond(index); }
  await ui.settle();
  for (let index = 0; index < 3; index += 1) ui.toggle(index, false);
  ui.records[0].drawer.open = true;
  ui.toggle(3, false);
  assert.ok(ui.plate(0));
  assert.ok(ui.plate(1));
  assert.equal(ui.document.querySelectorAll('.specimen-plate').length, 5);
  ui.records[0].drawer.fire('toggle');
  ui.toggle(4, false);
  assert.equal(ui.plate(1), null);
  assert.ok(ui.plate(0));
});

test('deep links open before fetching; filtered links load only when visible, and category links work after mounting', async () => {
  const id = '1'.repeat(64);
  const ui = detailFixture({ url: 'https://example.org/catalog/?metrics=missing#project-' + id });
  catalog.init(ui.document, ui.window);
  assert.equal(ui.calls.length, 0);
  assert.equal(ui.records[0].drawer.open, false);
  assert.equal(ui.ids['project-link-notice'].hidden, false);
  ui.ids['clear-filters'].fire('click');
  assert.equal(ui.records[0].drawer.open, true);
  assert.equal(ui.calls.length, 1, 'Deep links request without waiting for toggle delivery');
  ui.records[0].drawer.fire('toggle');
  assert.equal(ui.calls.length, 1);
  ui.respond(0);
  await ui.settle();
  const category = ui.plate(0).querySelector('a[data-category]');
  const list = ui.ids['project-list'];
  assert.equal(list.fire('click', { target: category, ctrlKey: true }).defaultPrevented, false);
  assert.equal(list.fire('click', { target: category }).defaultPrevented, true);
  assert.equal(ui.ids['category-filter'].value, 'tools');
  assert.equal(ui.document.activeElement, ui.ids.catalog);
  assert.equal(ui.records[0].drawer.open, true);
  assert.ok(ui.plate(0));
  ui.window.location.href = 'https://example.org/catalog/#project-' + ui.records[1].project.id;
  ui.fire('hashchange');
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.records[1].drawer.open, true);
  assert.equal(ui.document.activeElement, ui.records[1].summary);
  ui.respond(1);
  await ui.settle();
  assert.ok(ui.plate(1));
});

test('initial project links fetch their record exactly once and do not refetch on history restoration', async () => {
  const ui = detailFixture({ url: 'https://example.org/catalog/#project-' + '1'.repeat(64) });
  catalog.init(ui.document, ui.window);
  assert.equal(ui.records[0].drawer.open, true);
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.document.activeElement, ui.records[0].summary);
  ui.respond(0);
  await ui.settle();
  ui.fire('popstate');
  ui.fire('pageshow', { persisted: true });
  assert.equal(ui.calls.length, 1);
});

test('pagehide aborts transfers and bfcache restoration retries only still-open drawers', async () => {
  const ui = detailFixture();
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  ui.toggle(1, true);
  ui.toggle(1, false);
  ui.fire('pagehide');
  assert.equal(ui.calls[0].init.signal.aborted, true);
  ui.fire('pageshow', { persisted: false });
  assert.equal(ui.calls.length, 2);
  ui.fire('pageshow', { persisted: true });
  assert.equal(ui.calls.length, 3);
  assert.equal(ui.calls[2].url, ui.calls[0].url);
  ui.respond(0);
  ui.respond(1);
  ui.respond(2);
  await ui.settle();
  assert.ok(ui.plate(0));
  assert.equal(ui.plate(1), null);
  assert.equal(ui.parseCount, 1);
});

test('without AbortController stale protection still works; detached hosts ignore completion', async () => {
  const ui = detailFixture();
  delete ui.window.AbortController;
  catalog.init(ui.document, ui.window);
  ui.toggle(0, true);
  ui.toggle(0, false);
  ui.respond(0);
  await ui.settle();
  assert.equal(ui.plate(0), null);
  ui.toggle(1, true);
  ui.records[1].host.isConnected = false;
  ui.respond(1);
  await ui.settle();
  assert.equal(ui.plate(1), null);
  assert.equal(ui.parseCount, 0);
});

test('legacy fully rendered standalone and single-record pages enhance without fetching or catalog controls', () => {
  for (const single of [false, true]) {
    const ui = detailFixture({ url: 'file:///tmp/site/standalone.html' });
    for (const record of ui.records) {
      record.host.remove();
      const html = ui.createRecord({ projectId: record.project.id });
      record.drawer.appendChild(ui.document.importNode(html.querySelector('.specimen-plate'), true));
    }
    if (single) {
      delete ui.ids['catalog-data'];
      ui.records[0].drawer.open = true;
    }
    assert.equal(catalog.init(ui.document, ui.window), !single);
    if (!single) ui.toggle(0, true);
    const plate = ui.records[0].drawer.querySelector('.specimen-plate');
    assert.equal(plate.dataset.enhanced, 'true');
    ui.toggle(0, false);
    ui.toggle(0, true);
    catalog.init(ui.document, ui.window);
    assert.equal(ui.calls.length, 0);
    assert.equal(plate.querySelectorAll('.plate-lens').length, 1);
    assert.equal(ui.records[0].drawer.listeners.toggle.length, 1);
    assert.equal(ui.events.listeners.resize.length, 1);
    assert.equal(ui.document.querySelectorAll('.specimen-plate').length, ui.records.length);
  }
});
