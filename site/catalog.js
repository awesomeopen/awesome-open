/* Progressive enhancement for the static catalog. Same-origin records load on demand. */
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
    q: "", category: "", license: "all", stars: null, pushed: "", sort: "stars",
    window: "all", alternative: "", metrics: "all", run_mode: "", install_method: ""
  });
  var PARAMS = ["q", "category", "license", "stars", "pushed", "sort", "window", "alternative", "metrics", "run_mode", "install_method"];
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
    return Boolean(project.github && project.github.status !== "unavailable" && typeof project.github === "object" && !Array.isArray(project.github));
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

  function setupValues(project, field) {
    return ((project.deployment || {})[field] || []).map(function (fact) { return fact.value; });
  }

  function setupFilter(value, projects, field) {
    return value === "unknown" || projects.some(function (p) { return setupValues(p, field).includes(value); }) ? value : "";
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
      sort: ["name", "stars", "pushed"].indexOf(get("sort")) !== -1 ? get("sort") : DEFAULTS.sort,
      window: ["all", "recent", "older", "unknown"].indexOf(get("window")) !== -1 ? get("window") : "all",
      alternative: alternativeNames(data.projects || []).indexOf(alternative) !== -1 ? alternative : "",
      run_mode: setupFilter(String(get("run_mode") || ""), data.projects || [], "run_modes"),
      install_method: setupFilter(String(get("install_method") || ""), data.projects || [], "install_methods"),
      metrics: ["all", "present", "missing"].indexOf(get("metrics")) !== -1 ? get("metrics") : "all"
    };
  }

  function searchText(project) {
    return fold([project.name, project.description].concat(
      (project.alternatives || []).map(function (item) { return item.name; })
    ).join(" "));
  }

  function aliasNames(project) {
    return (project.aliases || []).map(function (alias) { return fold(alias.name); });
  }

  function shortAliasNames(projects) {
    return new Set(projects.reduce(function (names, project) {
      return names.concat(aliasNames(project).filter(function (name) {
        return /^[\p{L}\p{N}_]{1,4}$/u.test(name);
      }));
    }, []));
  }

  function boundaryMatch(text, token) {
    var literal = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp("(^|[^\\p{L}\\p{N}\\p{M}_])" + literal + "(?=$|[^\\p{L}\\p{N}\\p{M}_])", "u").test(text);
  }

  function matchesProject(project, state, snapshot, shortAliases) {
    var tokens = fold(state.q).split(/\s+/).filter(Boolean);
    if (tokens.length) {
      var text = searchText(project);
      var aliases = aliasNames(project);
      shortAliases = shortAliases || shortAliasNames((snapshot && snapshot.projects) || [project]);
      if (!tokens.every(function (token) {
        // Preserve ordinary substring search; an exact reviewed short name such
        // as OBS must not match incidental prose like "obsolete". Alias-only
        // terms always use word boundaries, including Unicode letters/numbers.
        return (shortAliases.has(token) ? boundaryMatch(text, token) : text.indexOf(token) !== -1) ||
          aliases.some(function (alias) { return boundaryMatch(alias, token); });
      })) return false;
    }
    if (state.category && (project.categories || []).indexOf(state.category) === -1) return false;
    if (state.window && state.window !== "all" && pushWindowOf(project, snapshot) !== state.window) return false;
    if (state.metrics === "present" && !metricsPresent(project)) return false;
    if (state.metrics === "missing" && metricsPresent(project)) return false;
    if (state.alternative && !(project.alternatives || []).some(function (item) {
      return item.name === state.alternative;
    })) return false;
    if (![["run_mode", "run_modes"], ["install_method", "install_methods"]].every(function (pair) {
      var selected = state[pair[0]], values = setupValues(project, pair[1]);
      return !selected || (selected === "unknown" ? values.length === 0 : values.includes(selected));
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
    var shortAliases = shortAliasNames(projects);
    return projects.filter(function (project) { return matchesProject(project, state, snapshot, shortAliases); })
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

  /* Specimen plates: decorative enhancement only. Content and links render without JavaScript. */
  var SVG_NS = "http://www.w3.org/2000/svg";

  function seededRandom(hex) {
    var a = parseInt(String(hex).slice(0, 8), 16) >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Concentric contour rings; deterministic per Registry ID and encoding no data.
  function plateRings(seed, cx, cy, count, step, sx, sy) {
    var random = seededRandom(seed);
    var phase = [random() * 6.28, random() * 6.28, random() * 6.28];
    var amp = [0.07 + random() * 0.05, 0.04 + random() * 0.03, 0.02 + random() * 0.015];
    var rings = [];
    for (var k = 1; k <= count; k++) {
      var radius = k * step, d = "";
      for (var j = 0; j <= 72; j++) {
        var th = j / 72 * Math.PI * 2;
        var f = 1 + amp[0] * Math.sin(2 * th + phase[0] + k * 0.11) + amp[1] * Math.sin(5 * th + phase[1] - k * 0.07) +
          amp[2] * Math.sin(9 * th + phase[2] + k * 0.05);
        d += (j ? "L" : "M") + (cx + Math.cos(th) * radius * f * sx).toFixed(1) + " " + (cy + Math.sin(th) * radius * f * sy).toFixed(1);
      }
      rings.push({ d: d + "Z", index: k % 5 === 0 });
    }
    return rings;
  }

  function terrain(document, className, seed, box, rings, preserve) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", className);
    svg.setAttribute("viewBox", box);
    svg.setAttribute("preserveAspectRatio", preserve);
    svg.setAttribute("aria-hidden", "true");
    rings.forEach(function (ring, i) {
      var path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", ring.d);
      path.setAttribute("pathLength", "1");
      if (ring.index) path.setAttribute("class", "is-index");
      path.style.setProperty("--i", i);
      svg.appendChild(path);
    });
    return svg;
  }

  function enhancePlate(plate, document, window) {
    if (plate.dataset.enhanced === "true") return;
    plate.dataset.enhanced = "true";
    var field = plate.querySelector(".plate-field");
    var departure = plate.querySelector(".plate-departure");
    if (departure) {
      var seed = (field && field.dataset.seed) || (plate.getAttribute("aria-labelledby") || "").replace("name-", "").slice(0, 16) || "0";
      departure.insertBefore(terrain(document, "plate-wild-terrain", seed, "0 0 1000 400",
        plateRings(seed, 500, 1150, 30, 42, 1.9, 0.55), "xMidYMid slice"), departure.firstChild);
    }
    if (!field) return;
    var image = field.querySelector("img");
    if (!image) return;
    if (field.dataset.cutout === "true") {
      field.insertBefore(terrain(document, "plate-terrain", field.dataset.seed, "0 0 1000 1000",
        plateRings(field.dataset.seed, 500, 860, 22, 34, 1.55, 0.5), "none"), field.firstChild);
    }
    var lens = document.createElement("div");
    lens.className = "plate-lens";
    lens.setAttribute("aria-hidden", "true");
    field.appendChild(lens);
    function place(fx, fy) {
      var outer = field.getBoundingClientRect(), art = image.getBoundingClientRect(), size = lens.offsetWidth;
      var src = image.currentSrc || image.src, scale = art.width * 2;
      lens.style.left = (art.left - outer.left + fx * art.width) + "px";
      lens.style.top = (art.top - outer.top + fy * art.height) + "px";
      lens.style.backgroundImage = 'url("' + src + '")';
      lens.style.backgroundSize = scale + "px " + scale + "px";
      lens.style.backgroundPosition = (size / 2 - fx * scale) + "px " + (size / 2 - fy * scale) + "px";
      lens.classList.add("is-on");
    }
    function fraction(event) {
      var art = image.getBoundingClientRect();
      return [Math.min(1, Math.max(0, (event.clientX - art.left) / art.width)), Math.min(1, Math.max(0, (event.clientY - art.top) / art.height))];
    }
    function move(event) { if (event.pointerType === "mouse") place.apply(null, fraction(event)); }
    function leave(event) { if (event.pointerType === "mouse") lens.classList.remove("is-on"); }
    function click(event) {
      if (event.pointerType === "mouse") return;
      if (lens.classList.contains("is-on")) lens.classList.remove("is-on"); else place.apply(null, fraction(event));
    }
    field.addEventListener("pointermove", move);
    field.addEventListener("pointerleave", leave);
    field.addEventListener("click", click);
    plate.plateLayout = function () { layoutPlate(plate, field, image, window); };
    plate.plateCleanup = function () {
      field.removeEventListener("pointermove", move);
      field.removeEventListener("pointerleave", leave);
      field.removeEventListener("click", click);
      image.removeEventListener("load", plate.plateLayout);
      delete plate.plateLayout;
      delete plate.plateCleanup;
    };
    if (image.complete) plate.plateLayout(); else image.addEventListener("load", plate.plateLayout, { once: true });
  }

  function layoutPlate(plate, field, image, window) {
    var box = (field.dataset.bbox || "0 0 1 1").split(" ").map(Number);
    var src = image.currentSrc || image.src;
    // Detail crops: enlarged windows of the same drawing, placed inside the subject's bounding box.
    var centres = [[box[0] + (box[2] - box[0]) * 0.5, box[1] + (box[3] - box[1]) * 0.3],
                   [box[0] + (box[2] - box[0]) * 0.62, box[1] + (box[3] - box[1]) * 0.66]];
    Array.prototype.forEach.call(plate.querySelectorAll(".plate-crop"), function (crop, i) {
      var width = crop.clientWidth, zoom = i ? 4.2 : 3, size = width * zoom, c = centres[i] || centres[0];
      crop.style.backgroundImage = 'url("' + src + '")';
      crop.style.backgroundSize = size + "px " + size + "px";
      crop.style.backgroundPosition = (width / 2 - c[0] * size) + "px " + (width / 2 - c[1] * size) + "px";
      crop.classList.add("is-ready");
    });
    var svg = plate.querySelector(".plate-leaders"), study = plate.querySelector(".plate-study");
    var crops = plate.querySelectorAll(".plate-crop");
    if (!svg || !study || !crops.length) return;
    var S = study.getBoundingClientRect(), A = image.getBoundingClientRect();
    if (!A.width) return;
    var stacked = window.matchMedia && window.matchMedia("(max-width: 900px)").matches;
    var d = "", dots = "";
    Array.prototype.forEach.call(crops, function (crop, i) {
      var C = crop.getBoundingClientRect();
      var sx = A.left - S.left + A.width * (box[0] + (box[2] - box[0]) * (0.62 + i * 0.12));
      var sy = A.top - S.top + A.height * Math.min(0.98, box[3] + 0.02 + i * 0.025);
      var cy = C.top - S.top + C.height / 2;
      if (!stacked) {
        var ex = C.left - S.left, mx = ex - 30 + i * 12;
        d += "M" + sx + " " + sy + "H" + mx + "V" + cy + "H" + ex;
      } else {
        var gx = C.left - S.left - 6 - i * 5;
        d += "M" + sx + " " + sy + "H" + gx + "V" + cy + "H" + (C.left - S.left);
      }
      dots += '<circle cx="' + sx + '" cy="' + sy + '" r="2.5"/>';
    });
    svg.innerHTML = '<path d="' + d + '"/>' + dots;
  }

  var plateManagers = new WeakMap();
  var CLOSED_PLATE_LIMIT = 3;

  // Generated record pages are the no-JS fallback and the fetch payload. Never
  // insert their outer document, script, style or navigation into the ledger.
  function recordPlate(html, url, projectId, document, window) {
    if (html.length > 2 * 1024 * 1024) throw new Error("Record is too large");
    var record = new window.DOMParser().parseFromString(html, "text/html");
    var cards = record.querySelectorAll(".project-card[data-project-id]");
    var plates = record.querySelectorAll(".specimen-plate");
    if (cards.length !== 1 || cards[0].dataset.projectId !== projectId ||
        cards[0].id !== "project-" + projectId || plates.length !== 1 ||
        !cards[0].contains(plates[0]) || !record.getElementById("name-" + projectId) ||
        plates[0].getAttribute("aria-labelledby") !== "name-" + projectId) {
      throw new Error("Record identity does not match");
    }
    var base = record.querySelector("base[href]");
    var assetBase = new URL(base ? base.getAttribute("href") : url.href, url);
    if (assetBase.origin !== url.origin || !/^https?:$/.test(assetBase.protocol)) {
      throw new Error("Invalid record base URL");
    }
    var plate = plates[0];
    Array.from(plate.querySelectorAll("*")).concat(plate).forEach(function (node) {
      if (/^(script|style|iframe|frame|frameset|object|embed|base|link|meta|form|foreignobject|animate|animatemotion|animatetransform|set)$/i.test(node.tagName)) {
        throw new Error("Unexpected active record content");
      }
      Array.from(node.attributes).forEach(function (attribute) {
        var name = attribute.name.toLowerCase(), value = attribute.value.trim();
        if (/^on/.test(name) || name === "srcdoc" || name === "srcset" ||
            (name === "style" && /url\s*\(|@import|expression\s*\(/i.test(value))) {
          throw new Error("Unexpected active record attribute");
        }
        if (["src", "href", "xlink:href"].indexOf(name) === -1 || value.charAt(0) === "#") return;
        var resolved = new URL(value, assetBase);
        if (!/^https?:$/.test(resolved.protocol) ||
            (name === "src" && resolved.origin !== url.origin)) throw new Error("Invalid record resource URL");
        node.setAttribute(attribute.name, resolved.href);
      });
    });
    return document.importNode(plate, true);
  }

  function enhancePlates(document, window) {
    if (plateManagers.has(document)) return plateManagers.get(document);
    var states = new WeakMap(), closed = [];

    function showPlate(plate) {
      enhancePlate(plate, document, window);
      plate.classList.remove("is-opening");
      void plate.offsetWidth;
      plate.classList.add("is-opening");
      if (plate.plateLayout) plate.plateLayout();
    }

    function forgetClosed(state) {
      var index = closed.indexOf(state);
      if (index !== -1) closed.splice(index, 1);
    }

    function trimClosed() {
      // Open drawers are never evicted, even when a native toggle event has not
      // reached us yet. Keep only small disclosure booleans after an eviction.
      closed = closed.filter(function (state) { return !state.drawer.open; });
      while (closed.length > CLOSED_PLATE_LIMIT) {
        var state = closed.shift(), plate = state.host.querySelector(".specimen-plate");
        if (!plate) continue;
        state.disclosures = Array.from(plate.querySelectorAll("details")).map(function (detail) { return detail.open; });
        if (plate.plateCleanup) plate.plateCleanup();
        plate.remove();
        state.shown = false;
        status(state, "idle");
      }
    }

    function status(state, value, message, retry) {
      state.host.dataset.detailState = value;
      if (value === "loading") state.host.setAttribute("aria-busy", "true");
      else state.host.removeAttribute("aria-busy");
      // The static link is a fallback, not an extra heading above a loaded plate.
      if (state.fallback) {
        if (value === "loaded" && state.fallback.contains(document.activeElement)) {
          var fallbackSummary = state.drawer.querySelector("summary");
          if (fallbackSummary) fallbackSummary.focus({ preventScroll: true });
        }
        state.fallback.hidden = value === "loaded";
      }
      if (message && !state.status) {
        state.status = document.createElement("p");
        state.status.className = "detail-status";
        state.status.setAttribute("role", "status");
        state.host.appendChild(state.status);
      }
      if (state.status) {
        state.status.textContent = message || "";
        state.status.hidden = !message;
      }
      if (retry && !state.retry) {
        state.retry = document.createElement("button");
        state.retry.type = "button";
        state.retry.className = "detail-retry";
        state.retry.textContent = "Retry loading record";
        state.retry.addEventListener("click", function () { if (state.drawer.open) open(state.drawer); });
        state.host.appendChild(state.retry);
      }
      if (state.retry) {
        if (!retry && document.activeElement === state.retry) {
          var summary = state.drawer.querySelector("summary");
          if (summary) summary.focus({ preventScroll: true });
        }
        state.retry.hidden = !retry;
      }
    }

    function cancel(state) {
      state.sequence += 1;
      if (state.request) state.request.abort();
      state.request = null;
      if (state.host && state.host.dataset.detailState === "loading") status(state, "idle");
    }

    async function load(state) {
      var url, projectId = state.host.dataset.projectId;
      try {
        var pageURL = new URL(window.location.href);
        url = new URL(state.host.dataset.detailUrl, document.baseURI || pageURL.href);
        if (!/^[a-f0-9]{64}$/.test(projectId) || !/^https?:$/.test(url.protocol) ||
            url.origin !== pageURL.origin || url.username || url.password ||
            !url.pathname.endsWith("/records/" + projectId + ".html")) throw new Error("Invalid record URL");
        if (typeof window.fetch !== "function" || typeof window.DOMParser !== "function") throw new Error("Fetch unavailable");
      } catch (_) {
        status(state, "error", "Open the full record using the record link.", false);
        return;
      }
      var sequence = ++state.sequence;
      var request = typeof window.AbortController === "function" ? new window.AbortController() : { abort: function () {} };
      state.request = request;
      status(state, "loading", "Loading record…");
      function current() {
        return state.sequence === sequence && state.drawer.open && state.host.isConnected !== false;
      }
      try {
        var response = await window.fetch(url.href, { signal: request.signal, credentials: "same-origin", mode: "same-origin", redirect: "error" });
        if (!current()) return;
        if (!response.ok || (response.url && new URL(response.url).origin !== url.origin)) throw new Error("Record request failed");
        var type = response.headers && response.headers.get("content-type");
        if (type && !/^(text\/html|application\/xhtml\+xml)(?:;|$)/i.test(type)) throw new Error("Unexpected record type");
        var html = await response.text();
        if (!current()) return;
        var plate = recordPlate(html, url, projectId, document, window);
        if (!current()) return;
        if (state.disclosures) Array.from(plate.querySelectorAll("details")).forEach(function (detail, index) {
          if (index < state.disclosures.length) detail.open = state.disclosures[index];
        });
        state.host.appendChild(plate);
        status(state, "loaded");
        state.shown = true;
        showPlate(plate);
      } catch (_) {
        if (current()) status(state, "error", "The record couldn’t load. Retry or use the full record link.", true);
      } finally {
        if (state.sequence === sequence) state.request = null;
      }
    }

    function open(drawer) {
      var state = states.get(drawer);
      if (!state || !drawer.open) return;
      forgetClosed(state);
      var plate = drawer.querySelector(".specimen-plate");
      if (plate) {
        if (!state.shown) showPlate(plate);
        state.shown = true;
      } else if (state.host && !state.request) {
        load(state);
      }
    }

    var drawers = document.querySelectorAll ? document.querySelectorAll("details.specimen-drawer") : [];
    Array.prototype.forEach.call(drawers, function (drawer) {
      var host = drawer.querySelector(".specimen-detail-host");
      var state = { drawer: drawer, host: host, sequence: 0, request: null, shown: false,
        fallback: host && host.querySelector(".detail-fallback") };
      states.set(drawer, state);
      drawer.addEventListener("toggle", function () {
        if (drawer.open) open(drawer);
        else {
          cancel(state);
          state.shown = false;
          if (host && host.querySelector(".specimen-plate")) {
            forgetClosed(state);
            closed.push(state);
            trimClosed();
          }
        }
      });
      if (drawer.open) open(drawer);
    });
    if (window.addEventListener) {
      window.addEventListener("resize", function () {
        Array.prototype.forEach.call(document.querySelectorAll(".specimen-drawer[open] .specimen-plate"), function (plate) {
          if (plate.plateLayout) plate.plateLayout();
        });
      });
      // Abort pending transfers on real navigation. Keep mounted records and
      // listeners intact so a back/forward-cache restore stays usable.
      window.addEventListener("pagehide", function () {
        Array.prototype.forEach.call(drawers, function (drawer) { cancel(states.get(drawer)); });
      });
      window.addEventListener("pageshow", function (event) {
        if (event.persisted) Array.prototype.forEach.call(drawers, function (drawer) { if (drawer.open) open(drawer); });
      });
    }
    var manager = { open: open };
    plateManagers.set(document, manager);
    return manager;
  }

  function init(document, window) {
    var plates = enhancePlates(document, window);
    var footerArt = document.querySelector('[data-footer-background]');
    if (footerArt) {
      var backgrounds = JSON.parse(footerArt.dataset.backgrounds);
      if (backgrounds.length) {
        var selected = Math.floor(Math.random() * backgrounds.length);
        var sizes = JSON.parse(footerArt.dataset.backgroundSizes || '[]');
        if (sizes[selected]) {
          footerArt.width = sizes[selected][0];
          footerArt.height = sizes[selected][1];
        }
        footerArt.src = backgrounds[selected];
      }
    }
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
    [["window", "push-window"], ["alternative", "alternative-filter"], ["metrics", "metrics-filter"], ["run_mode", "run-mode-filter"], ["install_method", "install-method-filter"]]
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
    var endMark = document.querySelector(".page-end img");
    var defaultEndSrc = endMark && endMark.getAttribute("src");
    var navLinks = Array.from(document.querySelectorAll(".category-nav a[data-category]"));
    var timer = null;
    var currentState = DEFAULTS;
    var renderedSort = null;
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
      if (drawer) {
        drawer.open = true;
        plates.open(drawer);
      }
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
      // Keep rows attached on filter-only changes. Reparenting a summary during
      // input blur can cancel the native disclosure click that follows.
      var reorder = renderedSort !== state.sort;
      var fragment = reorder ? document.createDocumentFragment() : null;
      data.projects.slice().sort(comparator(state.sort)).forEach(function (project) {
        var card = cards.get(project.id);
        var visible = matchesProject(project, state, data);
        card.hidden = !visible;
        var leaders = project.leader_categories || [];
        var selectedLeaders = state.category ? leaders.filter(function (id) { return id === state.category; }) : leaders;
        card.dataset.leader = selectedLeaders.length ? 'true' : 'false';
        var label = typeof card.querySelector === 'function' ? card.querySelector('.leader-label') : null;
        if (label) {
          label.hidden = !selectedLeaders.length;
          label.textContent = selectedLeaders.length ? selectedLeaders.map(function (id) {
            return data.categories.find(function (category) { return category.id === id; }).name;
          }).join(' / ') : '';
        }
        if (visible) {
          total += 1;
          var position = typeof card.querySelector === "function" ? card.querySelector(".folio") : null;
          if (position) position.textContent = String(total).padStart(3, "0");
        }
        if (reorder) fragment.appendChild(card);
      });
      if (reorder) list.appendChild(fragment);
      renderedSort = state.sort;
      count.textContent = total === data.projects.length
        ? total.toLocaleString("en-US") + " projects"
        : total.toLocaleString("en-US") + " of " + data.projects.length.toLocaleString("en-US") + " projects";
      empty.hidden = total !== 0;
      linkedProject(false);
      if (endMark) {
        var selectedLink = navLinks.find(function (link) { return link.dataset.category === state.category; });
        var art = selectedLink && selectedLink.querySelector(".category-art");
        var endSrc = art ? art.dataset.endSrc : defaultEndSrc;
        if (endMark.getAttribute("src") !== endSrc) endMark.setAttribute("src", endSrc);
        endMark.width = art ? Number(art.dataset.endWidth) : 96;
        endMark.height = art ? Number(art.dataset.endHeight) : 96;
      }
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
      cancelPending();
      apply();
      var result = Array.from(list.children).find(function (card) { return !card.hidden; });
      var target = result || empty;
      var summary = result && result.querySelector("summary");
      if (summary) summary.focus({ preventScroll: true });
      target.scrollIntoView({ block: "start", behavior: "instant" });
    });
    clear.addEventListener("click", function (event) {
      event.preventDefault();
      cancelPending();
      setControls(DEFAULTS);
      apply();
    });
    function followCategory(event, link) {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var category = link.dataset.category;
      if (category && !data.categories.some(function (item) { return item.id === category; })) return;
      event.preventDefault();
      cancelPending();
      controls.category.value = category;
      apply();
      var catalogMain = document.getElementById("catalog");
      if (catalogMain && typeof catalogMain.focus === "function") catalogMain.focus();
    }
    categoryLinks.forEach(function (link) {
      if (!list.contains(link)) link.addEventListener("click", function (event) { followCategory(event, link); });
    });
    // Delegate record links so newly mounted plates work without per-plate
    // listeners or a closure retaining an evicted record.
    list.addEventListener("click", function (event) {
      var link = event.target && event.target.closest("a[data-category]");
      if (link && list.contains(link)) followCategory(event, link);
    });
    window.addEventListener("popstate", restore);
    window.addEventListener("hashchange", restore);
    // A page restored from the back/forward cache may have stale field values.
    window.addEventListener("pageshow", function (event) { if (event.persisted) restore(); });

    restore();
    controls.sort.disabled = false;
    clear.disabled = false;
    controls.q.maxLength = 500;
    var headerSearch = document.getElementById('header-search');
    if (headerSearch) headerSearch.hidden = false;
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
    plateRings: plateRings,
    init: init
  };
});
