/* Progressive enhancement for the static catalog. No requests or dependencies. */
(function (root, factory) {
  "use strict";
  var catalog = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = catalog;
  } else {
    root.OpenCatalog = catalog;
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", function () {
        catalog.init(root.document, root);
      }, { once: true });
    } else {
      catalog.init(root.document, root);
    }
  }
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  var DEFAULTS = Object.freeze({
    q: "", category: "", license: "all", stars: null, pushed: "", sort: "name",
    window: "all", alternative: "", metrics: "all"
  });
  var PARAMS = ["q", "category", "license", "stars", "pushed", "sort", "window", "alternative", "metrics"];
  var DAY = 24 * 60 * 60 * 1000;

  function fold(value) {
    return String(value == null ? "" : value).normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    var timestamp = Date.parse(value + "T00:00:00Z");
    return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value
      ? value : "";
  }

  function licenseOf(project) {
    var value = project.github && project.github.license;
    if (typeof value !== "string") return "";
    value = value.trim();
    return value && !/^(NOASSERTION|OTHER|UNKNOWN)$/i.test(value) ? value : "";
  }

  function starsOf(project) {
    var value = project.github && project.github.stars;
    return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
  }

  function pushedAt(project) {
    var value = project.github && project.github.pushed_at;
    if (typeof value !== "string" || !validDate(value.slice(0, 10))) return null;
    var timestamp = Date.parse(value);
    return Number.isFinite(timestamp) ? timestamp : null;
  }

  function metricsPresent(project) {
    return Boolean(project.github && typeof project.github === "object" && !Array.isArray(project.github));
  }

  function alternativeNames(projects) {
    return Array.from(new Set(projects.reduce(function (names, project) {
      return names.concat((project.alternatives || []).map(function (item) { return item.name; })
        .filter(function (name) { return typeof name === "string" && name !== ""; }));
    }, []))).sort(compareText);
  }

  function snapshotDate(snapshot) {
    return validDate(typeof snapshot === "string" ? snapshot : snapshot && snapshot.metrics_as_of);
  }

  function pushWindowBounds(snapshot) {
    var date = snapshotDate(snapshot);
    if (!date) return null;
    var asOf = Date.parse(date + "T00:00:00Z");
    var older = new Date(asOf);
    var month = older.getUTCMonth();
    // Clamp February 29 to February 28 when the anniversary is not a leap year.
    older.setUTCFullYear(older.getUTCFullYear() - 2);
    if (older.getUTCMonth() !== month) older.setUTCDate(0);
    return { recent: asOf - 90 * DAY, older: older.getTime(), end: asOf + DAY };
  }

  function pushWindowOf(project, snapshot) {
    var pushed = pushedAt(project);
    if (pushed === null) return "unknown";
    var bounds = pushWindowBounds(snapshot);
    if (!bounds) return "";
    if (pushed >= bounds.recent && pushed < bounds.end) return "recent";
    if (pushed < bounds.older) return "older";
    return "";
  }

  // The summary and filter share these predicates; no lifecycle judgment is inferred.
  function diagnosticCounts(projects, snapshot) {
    var counts = { recent: 0, older: 0, unknown: 0, "metrics-present": 0, "metrics-missing": 0 };
    projects.forEach(function (project) {
      var window = pushWindowOf(project, snapshot);
      if (window) counts[window] += 1;
      counts[metricsPresent(project) ? "metrics-present" : "metrics-missing"] += 1;
    });
    return counts;
  }

  function normalizeState(input, data) {
    input = input || {};
    data = data || { categories: [], projects: [] };
    var get = typeof input.get === "function"
      ? function (key) { return input.get(key); }
      : function (key) { return input[key]; };
    var category = String(get("category") || "");
    var licenses = new Set((data.projects || []).map(licenseOf).filter(Boolean));
    var license = String(get("license") || "all");
    var alternative = String(get("alternative") || "");
    var starInput = String(get("stars") == null ? "" : get("stars")).trim();
    var stars = /^\d+$/.test(starInput) ? Number(starInput) : null;
    if (stars !== null) {
      if (!Number.isFinite(stars)) stars = Number.MAX_SAFE_INTEGER;
      stars = Math.min(Number.MAX_SAFE_INTEGER, stars);
    }
    return {
      q: String(get("q") || "").trim().replace(/\s+/g, " ").slice(0, 500),
      category: (data.categories || []).some(function (item) { return item.id === category; })
        ? category : "",
      license: ["all", "known", "unknown"].indexOf(license) !== -1 || licenses.has(license)
        ? license : "all",
      stars: stars,
      pushed: validDate(String(get("pushed") || "")),
      sort: ["name", "stars", "pushed"].indexOf(get("sort")) !== -1 ? get("sort") : "name",
      window: ["all", "recent", "older", "unknown"].indexOf(get("window")) !== -1 ? get("window") : "all",
      alternative: alternativeNames(data.projects || []).indexOf(alternative) !== -1 ? alternative : "",
      metrics: ["all", "present", "missing"].indexOf(get("metrics")) !== -1 ? get("metrics") : "all"
    };
  }

  function searchText(project) {
    return fold([project.name, project.description].concat(
      (project.alternatives || []).map(function (item) { return item.name; })
    ).join(" "));
  }

  function matchesProject(project, state, snapshot) {
    var tokens = fold(state.q).split(/\s+/).filter(Boolean);
    if (tokens.length) {
      var text = searchText(project);
      if (!tokens.every(function (token) { return text.indexOf(token) !== -1; })) return false;
    }
    if (state.category && (project.categories || []).indexOf(state.category) === -1) return false;
    if (state.window && state.window !== "all" && pushWindowOf(project, snapshot) !== state.window) return false;
    if (state.metrics === "present" && !metricsPresent(project)) return false;
    if (state.metrics === "missing" && metricsPresent(project)) return false;
    if (state.alternative && !(project.alternatives || []).some(function (item) {
      return item.name === state.alternative;
    })) return false;
    var license = licenseOf(project);
    if (state.license === "known" && !license) return false;
    if (state.license === "unknown" && license) return false;
    if (["all", "known", "unknown"].indexOf(state.license) === -1 && license !== state.license) return false;
    if (state.stars !== null) {
      var stars = starsOf(project);
      if (stars === null || stars < state.stars) return false;
    }
    if (state.pushed) {
      var pushed = pushedAt(project);
      if (pushed === null || pushed < Date.parse(state.pushed + "T00:00:00Z")) return false;
    }
    return true;
  }

  // Lexical comparisons make ordering reproducible across browser locales.
  function compareText(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function compareName(a, b) {
    return compareText(fold(a.name), fold(b.name)) || compareText(String(a.id), String(b.id));
  }

  function compareDescending(a, b) {
    if (a === null && b === null) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    return b - a;
  }

  function comparator(sort) {
    return function (a, b) {
      var result = sort === "stars" ? compareDescending(starsOf(a), starsOf(b))
        : sort === "pushed" ? compareDescending(pushedAt(a), pushedAt(b)) : 0;
      return result || compareName(a, b);
    };
  }

  function selectProjects(projects, state, snapshot) {
    return projects.filter(function (project) { return matchesProject(project, state, snapshot); })
      .sort(comparator(state.sort));
  }

  function stateToURL(currentURL, state) {
    var url = new URL(String(currentURL));
    PARAMS.forEach(function (key) {
      url.searchParams.delete(key);
      if (state[key] !== undefined && state[key] !== DEFAULTS[key]) url.searchParams.set(key, String(state[key]));
    });
    return url;
  }

  function init(document, window) {
    var embedded = document.getElementById("catalog-data");
    var list = document.getElementById("project-list");
    var filters = document.getElementById("filters");
    var count = document.getElementById("result-count");
    var empty = document.getElementById("empty-state");
    var clear = document.getElementById("clear-filters");
    var controls = {
      q: document.getElementById("search"),
      category: document.getElementById("category-filter"),
      license: document.getElementById("license-filter"),
      stars: document.getElementById("min-stars"),
      pushed: document.getElementById("pushed-since"),
      sort: document.getElementById("sort-order")
    };
    if (!embedded || !list || !filters || !count || !empty || !clear ||
        Object.keys(controls).some(function (key) { return !controls[key]; })) return false;
    if (filters.dataset.enhanced === "true") return true;
    // These controls are additive, so older static pages can still be enhanced.
    [["window", "push-window"], ["alternative", "alternative-filter"], ["metrics", "metrics-filter"]]
      .forEach(function (entry) {
        var control = document.getElementById(entry[1]);
        if (control) controls[entry[0]] = control;
      });

    var data;
    try { data = JSON.parse(embedded.textContent); } catch (_) { return false; }
    if (!data || !Array.isArray(data.projects) || !Array.isArray(data.categories)) return false;
    var cards = new Map();
    Array.from(list.querySelectorAll(".project-card[data-project-id]")).forEach(function (card) {
      cards.set(card.dataset.projectId, card);
    });
    // A broken payload must never make the server-rendered directory disappear.
    if (cards.size !== data.projects.length || new Set(data.projects.map(function (p) { return p && p.id; })).size !== data.projects.length ||
        data.projects.some(function (project) { return !project || !cards.has(project.id); })) return false;

    var existingLicenses = new Set(Array.from(controls.license.options).map(function (option) { return option.value; }));
    Array.from(new Set(data.projects.map(licenseOf).filter(Boolean))).sort(compareText).forEach(function (license) {
      if (!existingLicenses.has(license)) {
        var option = document.createElement("option");
        option.value = license;
        option.textContent = license;
        controls.license.appendChild(option);
      }
    });

    if (controls.alternative) {
      var existingAlternatives = new Set(Array.from(controls.alternative.options).map(function (option) { return option.value; }));
      alternativeNames(data.projects).forEach(function (name) {
        if (!existingAlternatives.has(name)) {
          var option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          controls.alternative.appendChild(option);
        }
      });
    }
    var diagnostics = diagnosticCounts(data.projects, data);
    Array.from(document.querySelectorAll("[data-diagnostic]")).forEach(function (node) {
      if (Object.prototype.hasOwnProperty.call(diagnostics, node.dataset.diagnostic)) {
        node.textContent = diagnostics[node.dataset.diagnostic].toLocaleString("en-US");
      }
    });

    var categoryLinks = Array.from(document.querySelectorAll("a[data-category]"));
    var navLinks = Array.from(document.querySelectorAll(".category-nav a[data-category]"));
    var timer = null;
    var currentState = DEFAULTS;
    var linkNotice = document.getElementById("project-link-notice");
    var lastLinkedCard = null;
    var linkedWasHidden = false;

    function linkedProject(focus) {
      var anchor;
      try { anchor = decodeURIComponent(new URL(window.location.href).hash.slice(1)); }
      catch (_) { anchor = ""; }
      var card = anchor.indexOf("project-") === 0 ? cards.get(anchor.slice(8)) : null;
      var becameVisible = card && card === lastLinkedCard && linkedWasHidden && !card.hidden;
      lastLinkedCard = card;
      linkedWasHidden = Boolean(card && card.hidden);
      if (linkNotice) linkNotice.hidden = !card || !card.hidden;
      if (!card) return;
      if (card.hidden) {
        if (!linkNotice) {
          linkNotice = document.createElement("p");
          linkNotice.id = "project-link-notice";
          linkNotice.setAttribute("role", "status");
          filters.appendChild(linkNotice);
        }
        var project = data.projects.find(function (item) { return item.id === card.dataset.projectId; });
        linkNotice.textContent = "The linked project, " + project.name + ", is hidden by your current filters. Clear or change filters to view it.";
        linkNotice.hidden = false;
        return;
      }
      // Preserve a drawer the reader closed while changing unrelated filters.
      if (!focus && !becameVisible) return;
      var drawer = String(card.tagName || "").toLowerCase() === "details" ? card
        : typeof card.querySelector === "function" ? card.querySelector("details.specimen-drawer") : null;
      if (drawer) drawer.open = true;
      if (focus) {
        var target = drawer && typeof drawer.querySelector === "function" ? drawer.querySelector("summary") : null;
        target = target || card;
        if (target === card) card.setAttribute("tabindex", "-1");
        if (typeof target.focus === "function") target.focus({ preventScroll: true });
        if (typeof card.scrollIntoView === "function") card.scrollIntoView({ block: "start" });
      }
    }

    function cancelPending() {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
    }

    function readControls() {
      var input = Object.assign({}, currentState);
      Object.keys(controls).forEach(function (key) { input[key] = controls[key].value; });
      return normalizeState(input, data);
    }

    function setControls(state) {
      currentState = state;
      Object.keys(controls).forEach(function (key) {
        controls[key].value = state[key] === null ? "" : String(state[key]);
      });
    }

    function render(state) {
      currentState = state;
      var total = 0;
      var fragment = document.createDocumentFragment();
      data.projects.slice().sort(comparator(state.sort)).forEach(function (project) {
        var card = cards.get(project.id);
        var visible = matchesProject(project, state, data);
        card.hidden = !visible;
        if (visible) total += 1;
        fragment.appendChild(card);
      });
      list.appendChild(fragment);
      count.textContent = total === data.projects.length
        ? total.toLocaleString("en-US") + " projects"
        : total.toLocaleString("en-US") + " of " + data.projects.length.toLocaleString("en-US") + " projects";
      empty.hidden = total !== 0;
      linkedProject(false);
      navLinks.forEach(function (link) {
        if (link.dataset.category === state.category) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      });
    }

    function writeURL(state, replace) {
      var next = stateToURL(window.location.href, state);
      if (next.href === window.location.href) return;
      // Filtering also works when a local-file preview cannot update its URL.
      try {
        window.history[replace ? "replaceState" : "pushState"](
          replace ? window.history.state : null, "", next.href
        );
      } catch (_) { /* The static directory remains usable without history access. */ }
    }

    function apply() {
      cancelPending();
      var state = readControls();
      Object.keys(controls).forEach(function (key) {
        if (key !== "q" || document.activeElement !== controls.q) {
          controls[key].value = state[key] === null ? "" : String(state[key]);
        }
      });
      render(state);
      writeURL(state, false);
    }

    function restore() {
      cancelPending();
      var state = normalizeState(new URL(window.location.href).searchParams, data);
      setControls(state);
      render(state);
      writeURL(state, true);
      linkedProject(true);
    }

    controls.q.addEventListener("input", function () {
      cancelPending();
      timer = window.setTimeout(apply, 250);
    });
    Object.keys(controls).forEach(function (key) {
      controls[key].addEventListener("change", apply);
    });
    filters.addEventListener("submit", function (event) {
      event.preventDefault();
      apply();
    });
    clear.addEventListener("click", function (event) {
      event.preventDefault();
      cancelPending();
      setControls(DEFAULTS);
      apply();
    });
    categoryLinks.forEach(function (link) {
      link.addEventListener("click", function (event) {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        var category = link.dataset.category;
        if (category && !data.categories.some(function (item) { return item.id === category; })) return;
        event.preventDefault();
        cancelPending();
        controls.category.value = category;
        apply();
        var catalogMain = document.getElementById("catalog");
        if (catalogMain && typeof catalogMain.focus === "function") catalogMain.focus();
      });
    });
    window.addEventListener("popstate", restore);
    window.addEventListener("hashchange", restore);
    // A page restored from the back/forward cache may have stale field values.
    window.addEventListener("pageshow", function (event) { if (event.persisted) restore(); });

    restore();
    controls.sort.disabled = false;
    controls.q.maxLength = 500;
    var categoryPanel = document.querySelector(".category-panel");
    if (categoryPanel && typeof window.matchMedia === "function") {
      var mobile = window.matchMedia("(max-width: 900px)");
      var setPanel = function () { categoryPanel.open = !mobile.matches; };
      setPanel();
      if (typeof mobile.addEventListener === "function") mobile.addEventListener("change", setPanel);
      else if (typeof mobile.addListener === "function") mobile.addListener(setPanel);
    }
    filters.dataset.enhanced = "true";
    filters.hidden = false;
    document.documentElement.classList.add("catalog-enhanced");
    return true;
  }

  return {
    DEFAULTS: DEFAULTS,
    fold: fold,
    validDate: validDate,
    licenseOf: licenseOf,
    starsOf: starsOf,
    pushedAt: pushedAt,
    metricsPresent: metricsPresent,
    alternativeNames: alternativeNames,
    pushWindowBounds: pushWindowBounds,
    pushWindowOf: pushWindowOf,
    diagnosticCounts: diagnosticCounts,
    normalizeState: normalizeState,
    matchesProject: matchesProject,
    comparator: comparator,
    selectProjects: selectProjects,
    stateToURL: stateToURL,
    init: init
  };
});
