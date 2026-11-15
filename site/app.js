/* The Catalog as one screen: category rail, filtered list and one pane for a plate, the jars or a sheet.
   Filtering, search and the record loader's checks come from the site's own catalog.js and search.js. */
(function () {
  "use strict";
  var C = window.OpenCatalog, S = window.OpenSearch;
  var $ = function (id) { return document.getElementById(id); };
  var embedded = $("catalog-data"), data;
  // Without the runtime or its data the page stays a static list of record links.
  if (!C || !S || !embedded || !C.recordPlate) return;
  try { data = JSON.parse(embedded.textContent); } catch (_) { return; }
  var NAMES = Object.fromEntries(data.categories.map(function (c) { return [c.id, c.name]; }));
  var byId = new Map(data.projects.map(function (p) { return [p.id, p]; }));
  var list = $("rows"), rows = new Map();
  Array.prototype.forEach.call(list.querySelectorAll(".row[data-id]"), function (row) { rows.set(row.dataset.id, row); });

  var controls = {
    q: $("search"), sort: $("f-sort"), window: $("f-window"), alternative: $("f-alternative"), license: $("f-license"),
    run_mode: $("f-run"), install_method: $("f-install"), metrics: $("f-metrics"), stars: $("f-stars"), pushed: $("f-pushed")
  };
  var selects = Array.prototype.slice.call(document.querySelectorAll(".rail-filters select"));
  var railLinks = Array.prototype.slice.call(document.querySelectorAll("#rail-cats a[data-category]"));
  var pane = $("pane"), rest = $("pane-rest"), plateBox = $("pane-plate"), scroll = $("pane-scroll"), about = $("pane-about");
  var cabinet = $("specimen-cabinet");

  var state = C.normalizeState(new URL(window.location.href).searchParams, data);
  var order = [], current = null, sequence = 0, request = null, textState = "idle", timer = null, stepTimer = null;
  var cache = new Map();

  // A select's first option carries its title; a chosen option takes the title while it is selected.
  selects.forEach(function (select) {
    Array.prototype.forEach.call(select.options, function (option, i) {
      option.dataset.label = i ? option.textContent : option.textContent.replace(select.dataset.title + ": ", "");
    });
  });
  function syncSelects() {
    selects.forEach(function (select) {
      Array.prototype.forEach.call(select.options, function (option, i) {
        option.textContent = (i === 0 || option.selected ? select.dataset.title + ": " : "") + option.dataset.label;
      });
      select.classList.toggle("is-set", select.selectedIndex > 0 && select.id !== "f-sort");
    });
    controls.stars.classList.toggle("is-set", controls.stars.value !== "");
  }

  function setControls() {
    Object.keys(controls).forEach(function (key) { controls[key].value = state[key] === null ? "" : String(state[key]); });
    syncSelects();
  }
  function readControls() {
    var input = Object.assign({}, state);
    Object.keys(controls).forEach(function (key) { input[key] = controls[key].value; });
    return C.normalizeState(input, data);
  }

  function loadText() {
    textState = "loading";
    S.loadText(window, embedded.dataset.searchText, embedded.dataset.sourceSha).then(function (text) {
      data.search_text = text; textState = "ready"; render();
    }).catch(function () { textState = "failed"; });
  }

  function render() {
    if (state.q && textState === "idle") loadText();
    var visible = C.selectProjects(data.projects, state, data);
    var shown = new Set(), fragment = document.createDocumentFragment();
    order = visible.map(function (p) { return p.id; });
    visible.forEach(function (project, i) {
      var row = rows.get(project.id), leaders = project.leader_categories || [];
      shown.add(project.id);
      row.hidden = false;
      row.querySelector(".row-n").textContent = String(i + 1).padStart(3, "0");
      row.dataset.leader = (state.category ? leaders.indexOf(state.category) !== -1 : leaders.length > 0) ? "true" : "false";
      var tag = row.querySelector(".row-cat");
      if (!state.category) {
        if (!tag) {
          tag = document.createElement("span"); tag.className = "row-cat";
          var desc = row.querySelector(".row-desc");
          desc.insertBefore(tag, desc.firstChild);
        }
        tag.textContent = NAMES[project.categories[0]] || "";
        tag.hidden = false;
      } else if (tag) tag.hidden = true;
      fragment.appendChild(row);
    });
    rows.forEach(function (row, id) { if (!shown.has(id)) row.hidden = true; });
    list.insertBefore(fragment, list.firstChild);

    // Rail counts follow search and the other filters, so a count is what its category will list.
    var others = Object.assign({}, state, { category: "" });
    var pool = C.selectProjects(data.projects, others, data), tally = {};
    pool.forEach(function (p) { p.categories.forEach(function (id) { tally[id] = (tally[id] || 0) + 1; }); });
    railLinks.forEach(function (link) {
      var id = link.dataset.category, n = id ? (tally[id] || 0) : pool.length;
      link.querySelector(".n").textContent = String(n).padStart(2, "0");
      link.classList.toggle("is-empty", n === 0);
      if (id === state.category) link.setAttribute("aria-current", "true"); else link.removeAttribute("aria-current");
      link.href = C.stateToURL(window.location.href.split("#")[0], Object.assign({}, state, { category: id })).href;
    });

    var total = state.category ? data.projects.filter(function (p) { return p.categories.indexOf(state.category) !== -1; }).length : data.projects.length;
    $("list-count").textContent = (visible.length === total ? total.toLocaleString("en-US") : visible.length.toLocaleString("en-US") + " of " + total.toLocaleString("en-US")) +
      " projects" + (state.q ? " match “" + state.q + "”" : "");
    var mark = $("end-mark");
    if (state.category) {
      mark.src = "domains/" + state.category + "-m.webp"; mark.width = 207; mark.height = 207;
    } else { mark.src = mark.dataset.default; mark.width = 96; mark.height = 96; }

    var empty = $("empty"), filtered = Object.keys(C.DEFAULTS).some(function (key) {
      return key !== "sort" && key !== "category" && state[key] !== C.DEFAULTS[key];
    });
    empty.hidden = visible.length > 0;
    list.querySelector(".rows-end").hidden = !visible.length;
    empty.textContent = filtered ? "No matches found. Reset the filters or clear the search." : S.noMatch(data.projects.length);
    if (!visible.length && state.category && pool.length) {
      empty.textContent = "No matches in " + NAMES[state.category] + ". ";
      var all = document.createElement("a");
      all.href = "#"; all.textContent = "Show the " + pool.length + " in all categories";
      all.addEventListener("click", function (event) { event.preventDefault(); state = Object.assign({}, state, { category: "" }); render(); });
      empty.appendChild(all);
    }
    $("reset").disabled = !Object.keys(C.DEFAULTS).some(function (key) {
      return key !== "q" && key !== "category" && state[key] !== C.DEFAULTS[key];
    });
    try { window.history.replaceState(null, "", C.stateToURL(window.location.href, state)); } catch (_) {}
    syncBar();
  }

  function apply() { state = readControls(); syncSelects(); render(); }

  /* Plate pane */
  var shim = { matchMedia: function () { return { matches: scroll.clientWidth < 760 }; } };
  function fetchRecord(id, signal) {
    if (cache.has(id)) return Promise.resolve(cache.get(id));
    var url = new URL("records/" + id + ".html", window.location.href);
    return window.fetch(url.href, { signal: signal, credentials: "same-origin", mode: "same-origin", redirect: "error" })
      .then(function (response) { if (!response.ok) throw new Error("Record unavailable"); return response.text(); })
      .then(function (html) {
        cache.set(id, html);
        if (cache.size > 12) cache.delete(cache.keys().next().value);
        return html;
      });
  }
  function mountedPlate() { return scroll.querySelector(".specimen-plate"); }
  function syncBar() {
    if (!current) return;
    var project = byId.get(current), at = order.indexOf(current);
    $("plate-position").textContent = (at === -1 ? "—" : String(at + 1).padStart(3, "0")) + " / " + String(order.length).padStart(3, "0");
    $("plate-name").textContent = project.name;
    rows.forEach(function (row, id) {
      var on = id === current;
      row.classList.toggle("is-current", on);
      var link = row.firstElementChild;
      if (on) link.setAttribute("aria-current", "true"); else link.removeAttribute("aria-current");
    });
    syncCabinetButton();
  }
  function setHash(id) {
    var url = new URL(window.location.href);
    url.hash = SHEETS.test(id || "") ? id : id ? "project-" + id : "";
    try { window.history.replaceState(null, "", url); } catch (_) {}
  }
  function open(id, options) {
    if (!byId.has(id)) return;
    options = options || {};
    var mine = ++sequence;
    if (request) request.abort();
    request = typeof AbortController === "function" ? new AbortController() : { abort: function () {} };
    current = id;
    rest.hidden = true; about.hidden = true; plateBox.hidden = false; $("rail-about").removeAttribute("aria-current");
    syncBar(); setHash(id);
    var row = rows.get(id);
    if (row && !row.hidden) row.scrollIntoView({ block: "nearest" });
    $("plate-status").textContent = cache.has(id) ? "" : "Loading…";
    fetchRecord(id, request.signal).then(function (html) {
      if (mine !== sequence) return;
      var plate = C.recordPlate(html, new URL("records/" + id + ".html", window.location.href), id, document, window);
      var old = mountedPlate();
      if (old && old.plateCleanup) old.plateCleanup();
      var image = plate.querySelector(".plate-art img");
      if (image) image.sizes = "440px";
      scroll.replaceChildren(plate);
      scroll.scrollTop = 0;
      C.enhancePlate(plate, document, shim);
      plate.classList.add("is-opening");
      $("plate-status").textContent = "";
      window.setTimeout(function () { if (plate.plateLayout) plate.plateLayout(); }, 350);
      // Neighbours are fetched ahead so stepping swaps without a wait.
      var at = order.indexOf(id);
      if (at !== -1) [order[(at + 1) % order.length], order[(at - 1 + order.length) % order.length]].forEach(function (near) {
        if (near && near !== id) fetchRecord(near).catch(function () {});
      });
    }).catch(function (error) {
      if (mine !== sequence || (error && error.name === "AbortError")) return;
      $("plate-status").textContent = "";
      var box = document.createElement("div"); box.className = "pane-error";
      box.innerHTML = '<p>This record could not load. <a href="records/' + id + '.html">Open the full record</a>.</p>';
      var retry = document.createElement("button"); retry.type = "button"; retry.textContent = "Try again";
      retry.addEventListener("click", function () { open(id); });
      box.appendChild(retry);
      scroll.replaceChildren(box);
    });
  }
  function unmount() {
    sequence += 1;
    if (request) request.abort();
    window.clearTimeout(stepTimer);
    var old = mountedPlate();
    if (old && old.plateCleanup) old.plateCleanup();
    scroll.replaceChildren();
    var row = current && rows.get(current);
    current = null;
    plateBox.hidden = true;
    rows.forEach(function (r) { r.classList.remove("is-current"); r.firstElementChild.removeAttribute("aria-current"); });
    return row;
  }
  function close() {
    var row = unmount(), wasAbout = !about.hidden;
    about.hidden = true; rest.hidden = false;
    $("rail-about").removeAttribute("aria-current");
    setHash("");
    if (wasAbout) $("rail-about").focus({ preventScroll: true });
    else if (row && !row.hidden) row.firstElementChild.focus({ preventScroll: true });
  }

  /* About: everything that is not the catalog, shown in the plate's place. */
  var aboutArt = about.querySelector("[data-footer-background]");
  if (aboutArt) {
    var backgrounds = JSON.parse(aboutArt.dataset.backgrounds), sizes = JSON.parse(aboutArt.dataset.backgroundSizes || "[]");
    var pick = Math.floor(Math.random() * backgrounds.length);
    if (sizes[pick]) { aboutArt.width = sizes[pick][0]; aboutArt.height = sizes[pick][1]; }
    aboutArt.src = backgrounds[pick];
  }
  /* Sheets: About and the three field-guide pages share the About pane; a rider picks one.
     The pages load in a frame and hide their own navigation there; their catalog links act here. */
  var SHEETS = /^(about|observatory|scoreboard|spotlight)$/, frame = $("pane-frame"), sheet = "";
  var riders = Array.prototype.slice.call(about.querySelectorAll(".riders a[data-sheet]"));
  function showAbout(name) {
    name = name || "about";
    if (current) unmount();
    rest.hidden = true; about.hidden = false; plateBox.hidden = true;
    $("rail-about").setAttribute("aria-current", "page");
    riders.forEach(function (rider) {
      var on = rider.dataset.sheet === name;
      if (on) rider.setAttribute("aria-current", "page"); else rider.removeAttribute("aria-current");
    });
    $("about-scroll").hidden = name !== "about";
    frame.hidden = name === "about";
    if (name !== "about" && name !== sheet) {
      frame.title = name.charAt(0).toUpperCase() + name.slice(1);
      frame.src = name + "/";
    }
    if (name === "about") $("about-scroll").scrollTop = 0;
    sheet = name;
    setHash(name);
  }
  frame.addEventListener("load", function () {
    var doc;
    try { doc = frame.contentDocument; } catch (_) { return; }
    if (!doc || !doc.head) return;
    // Esc inside the page returns to the jars, as it does from the rest of the app.
    doc.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !event.defaultPrevented && !/^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) close();
    });
    doc.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest("a[href]");
      if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var url = new URL(link.href), home = new URL("./", window.location.href);
      if (url.origin !== home.origin) { link.target = "_blank"; link.rel = "noopener"; return; }
      var path = url.pathname.slice(home.pathname.length).replace(/index\.html$/, "");
      var project = /^#project-([a-f0-9]{64})$/.exec(url.hash);
      if (path === "" && project && byId.has(project[1])) { event.preventDefault(); open(project[1]); }
      else if (path === "") { event.preventDefault(); close(); }
      else if (SHEETS.test(path.replace(/\/$/, "")) && url.pathname !== new URL(frame.src).pathname) { event.preventDefault(); showAbout(path.replace(/\/$/, "")); }
    });
  });
  function step(delta, focusRow) {
    if (!order.length) return;
    var at = order.indexOf(current);
    var next = at === -1 ? (delta > 0 ? 0 : order.length - 1) : (at + delta + order.length) % order.length;
    var id = order[next], row = rows.get(id);
    if (focusRow && row) row.firstElementChild.focus({ preventScroll: true });
    // Mark the row at once; a held key loads only where it stops.
    current = id; rest.hidden = true; about.hidden = true; plateBox.hidden = false; $("rail-about").removeAttribute("aria-current"); syncBar();
    if (row) row.scrollIntoView({ block: "nearest" });
    window.clearTimeout(stepTimer);
    stepTimer = window.setTimeout(function () { open(id); }, cache.has(id) ? 0 : 90);
  }
  function fromHash() {
    var named = window.location.hash.slice(1);
    // Older pages link the ledger and its method notes; they now mean the list and the About sheet.
    if (named === "catalog") { if (current || !about.hidden) close(); return; }
    if (named === "method") { showAbout("about"); var notes = $("method"); if (notes) notes.scrollIntoView(); return; }
    if (SHEETS.test(named)) { if (about.hidden || named !== sheet) showAbout(named); return; }
    var match = /^#project-([a-f0-9]{64})$/.exec(window.location.hash);
    if (match && byId.has(match[1]) && match[1] !== current) open(match[1]);
  }

  /* Cabinet: the pane's button edits the same URL parameter the cabinet restores from. */
  function cabinetIds() {
    var value = new URL(window.location.href).searchParams.get("cabinet");
    return value ? value.split(",") : [];
  }
  function syncCabinetButton() {
    var button = $("plate-cabinet"), inside = current && cabinetIds().indexOf(current) !== -1;
    button.textContent = inside ? "Added to Cabinet" : "Compare";
    button.title = inside ? "Remove from the cabinet" : "Add to the cabinet to compare side by side";
    button.classList.toggle("is-in", Boolean(inside));
    button.setAttribute("aria-pressed", String(Boolean(inside)));
  }
  function toggleCabinet() {
    if (!current) return;
    var ids = cabinetIds(), at = ids.indexOf(current);
    if (at !== -1) ids.splice(at, 1);
    else if (ids.length >= 6) { $("plate-status").textContent = "The cabinet holds six projects."; return; }
    else ids.push(current);
    var url = new URL(window.location.href), wasOpen = cabinet.open;
    url.searchParams.delete("cabinet");
    if (ids.length) url.searchParams.set("cabinet", ids.join(","));
    window.history.replaceState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
    cabinet.open = wasOpen;
    cabinet.classList.remove("is-bumped"); void cabinet.offsetWidth; cabinet.classList.add("is-bumped");
    syncCabinetButton();
  }
  new MutationObserver(syncCabinetButton).observe($("cabinet-count"), { childList: true, characterData: true, subtree: true });

  /* Events */
  list.addEventListener("click", function (event) {
    var link = event.target.closest(".row > a");
    if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    open(link.parentElement.dataset.id);
  });
  $("rail-cats").addEventListener("click", function (event) {
    var link = event.target.closest("a[data-category]");
    if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    state = Object.assign({}, state, { category: link.dataset.category });
    render();
    list.scrollTop = 0;
  });
  $("filters").addEventListener("change", apply);
  $("filters").addEventListener("submit", function (event) { event.preventDefault(); apply(); });
  controls.stars.addEventListener("input", apply);
  controls.q.addEventListener("input", function () {
    window.clearTimeout(timer);
    // A new search covers every category; the rail counts then show where its matches are.
    timer = window.setTimeout(function () {
      state = readControls();
      if (state.q) state = Object.assign({}, state, { category: "" });
      syncSelects(); render(); list.scrollTop = 0;
    }, 120);
  });
  $("search-form").addEventListener("submit", function (event) {
    event.preventDefault();
    window.clearTimeout(timer); apply();
    if (order.length) open(order[0]);
  });
  $("reset").addEventListener("click", function () {
    state = Object.assign({}, C.DEFAULTS, { q: state.q, category: state.category });
    setControls(); render();
  });
  $("plate-prev").addEventListener("click", function () { step(-1); });
  $("plate-next").addEventListener("click", function () { step(1); });
  $("plate-close").addEventListener("click", close);
  $("rail-about").addEventListener("click", function (event) {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (about.hidden) showAbout(); else close();
  });
  riders.forEach(function (rider) {
    rider.addEventListener("click", function (event) {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      showAbout(rider.dataset.sheet);
    });
  });
  $("plate-cabinet").addEventListener("click", toggleCabinet);

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
    var target = event.target;
    var typing = target && (/^(INPUT|SELECT|TEXTAREA)$/.test(target.tagName) || target.isContentEditable);
    if (event.key === "Escape") {
      if (document.querySelector(".pg-info[open],.timeline-info[open]")) return;
      if (cabinet.open) { cabinet.open = false; cabinet.querySelector("summary").focus(); return; }
      if ((current || !about.hidden) && !typing) close();
      return;
    }
    if (typing || cabinet.contains(target) || (rest.contains(target) && !rest.hidden) || about.contains(target)) return;
    if ((event.key === "ArrowRight" || event.key === "ArrowLeft") && current) {
      event.preventDefault(); step(event.key === "ArrowRight" ? 1 : -1, list.contains(target));
    } else if ((event.key === "ArrowDown" || event.key === "ArrowUp") && (target === document.body || list.contains(target))) {
      event.preventDefault(); step(event.key === "ArrowDown" ? 1 : -1, true);
    }
  });
  document.addEventListener("click", function (event) {
    if (cabinet.open && !cabinet.contains(event.target) && !event.target.closest("#plate-cabinet")) cabinet.open = false;
  });
  window.addEventListener("hashchange", fromHash);
  window.addEventListener("popstate", function () {
    state = C.normalizeState(new URL(window.location.href).searchParams, data);
    setControls(); render(); fromHash();
  });
  if (typeof ResizeObserver === "function") new ResizeObserver(function () {
    var plate = mountedPlate();
    if (plate && plate.plateLayout) plate.plateLayout();
  }).observe(scroll);

  // Search and filters need this script; without it the page is a static list of record links.
  $("filters").hidden = false; $("search-form").hidden = false;
  setControls();
  render();
  fromHash();
})();
