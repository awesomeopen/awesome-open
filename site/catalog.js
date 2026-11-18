/* Shared catalog state, plate enhancement, and record-plate checks. */
(function (root, factory) {
  "use strict";
  var catalog = factory(typeof module === "object" && module.exports ? require("./search.js") : root.OpenSearch);
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
})(typeof globalThis === "object" ? globalThis : this, function (Search) {
  "use strict";

  var DEFAULTS = Object.freeze({
    q: "", category: "", license: "all", stars: null, pushed: "", sort: "match",
    window: "all", alternative: "", metrics: "all", run_mode: "", install_method: "", language: ""
  });
  var PARAMS = ["q", "category", "license", "stars", "pushed", "sort", "window", "alternative", "metrics", "run_mode", "install_method", "language"];
  var DAY = 24 * 60 * 60 * 1000;

  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    var timestamp = Date.parse(value + "T00:00:00Z");
    return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value
      ? value : "";
  }

  function licenseOf(project) { return Search.licenseOf(project); }

  function starsOf(project) { return Search.starsOf(project); }

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
    }, []))).sort(Search.compareText);
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

  // The summary and filter share these predicates.
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
    if (stars !== null) stars = Math.min(Number.MAX_SAFE_INTEGER, stars);
    return {
      q: String(get("q") || "").trim().replace(/\s+/g, " ").slice(0, 500),
      category: (data.categories || []).some(function (item) { return item.id === category; })
        ? category : "",
      license: ["all", "known", "unknown"].indexOf(license) !== -1 || licenses.has(license)
        ? license : "all",
      stars: stars,
      pushed: validDate(String(get("pushed") || "")),
      sort: ["match", "name", "stars", "pushed"].indexOf(get("sort")) !== -1 ? get("sort") : DEFAULTS.sort,
      window: ["all", "recent", "older", "unknown"].indexOf(get("window")) !== -1 ? get("window") : "all",
      alternative: alternativeNames(data.projects || []).indexOf(alternative) !== -1 ? alternative : "",
      run_mode: setupFilter(String(get("run_mode") || ""), data.projects || [], "run_modes"),
      install_method: setupFilter(String(get("install_method") || ""), data.projects || [], "install_methods"),
      language: Search.normalizeLanguage(get("language"), data.projects || []),
      metrics: ["all", "present", "missing"].indexOf(get("metrics")) !== -1 ? get("metrics") : "all"
    };
  }

  function matchesFilters(project, state, snapshot) {
    if (!Search.matchesLanguage(project, state.language)) return false;
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

  function comparator(sort, hits) {
    if (sort === "match") return Search.compareMatch(hits || null);
    return function (a, b) {
      var result = sort === "stars" ? Search.compareDescending(starsOf(a), starsOf(b))
        : sort === "pushed" ? Search.compareDescending(pushedAt(a), pushedAt(b)) : 0;
      return result || Search.compareName(a, b);
    };
  }

  function selectProjects(projects, state, snapshot) {
    var text = snapshot && snapshot.search_text, hits = Search.find(projects, state.q, text);
    return projects.filter(function (project) {
      return (!hits || hits.has(project.id)) && matchesFilters(project, state, snapshot);
    }).sort(comparator(state.sort, hits));
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

  // Concentric contour rings; deterministic per Registry ID.
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

  // The loupe doubles the drawing, so it uses the widest candidate rather than
  // the one the browser chose for the plate's display size.
  function largestSource(image) {
    var best = null, width = 0;
    (image.getAttribute("srcset") || "").split(",").forEach(function (candidate) {
      var parts = candidate.trim().split(/\s+/), w = parseInt(parts[1], 10);
      if (parts[0] && w > width) { best = parts[0]; width = w; }
    });
    return best || image.currentSrc || image.src;
  }

  function enhancePlate(plate, document, window) {
    if (plate.dataset.enhanced === "true") return;
    plate.dataset.enhanced = "true";
    var field = plate.querySelector(".plate-field");
    var departure = plate.querySelector(".plate-departure");
    if (departure) {
      var seed = (field && field.dataset.seed) || (plate.getAttribute("aria-labelledby") || "").replace("name-", "").slice(0, 16) || "0";
      departure.insertBefore(terrain(document, "plate-wild-terrain", seed, "0 0 1000 400",
        plateRings(seed, 500, 200, 30, 42, 1.9, 0.55), "xMidYMid slice"), departure.firstChild);
    }
    if (!field) return;
    var image = field.querySelector("img");
    if (!image) return;
    if (field.dataset.cutout === "true") {
      var stage = field.querySelector(".plate-stage") || field;
      var stageHeight = Number(stage.dataset.height) * 1000 || 1000;
      var ground = Number(stage.dataset.ground) || .86;
      stage.insertBefore(terrain(document, "plate-terrain", field.dataset.seed, "0 0 1000 " + stageHeight,
        plateRings(field.dataset.seed, 500, ground * stageHeight, 22, 34, 1.55, 0.5), "none"), stage.firstChild);
    }
    var lens = document.createElement("div");
    lens.className = "plate-lens";
    lens.setAttribute("aria-hidden", "true");
    field.appendChild(lens);
    function place(fx, fy) {
      var outer = field.getBoundingClientRect(), art = image.getBoundingClientRect(), size = lens.offsetWidth;
      var src = largestSource(image), scale = art.width * 2, scaleY = art.height * 2;
      lens.style.left = (art.left - outer.left + fx * art.width) + "px";
      lens.style.top = (art.top - outer.top + fy * art.height) + "px";
      lens.style.backgroundImage = 'url("' + src + '")';
      lens.style.backgroundSize = scale + "px " + scaleY + "px";
      lens.style.backgroundPosition = (size / 2 - fx * scale) + "px " + (size / 2 - fy * scaleY) + "px";
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
      var width = crop.clientWidth, zoom = i ? 4.2 : 3, size = width * zoom, sizeY = size * image.naturalHeight / image.naturalWidth, c = centres[i] || centres[0];
      crop.style.backgroundImage = 'url("' + src + '")';
      crop.style.backgroundSize = size + "px " + sizeY + "px";
      crop.style.backgroundPosition = (width / 2 - c[0] * size) + "px " + (width / 2 - c[1] * sizeY) + "px";
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
      // Start just below the same subject baseline as the contour floor.
      var sy = A.top - S.top + A.height * box[3] + 3 + i * 2;
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
        if (/^on/.test(name) || name === "srcdoc" ||
            (name === "srcset" && node.tagName.toLowerCase() !== "img") ||
            (name === "style" && /url\s*\(|@import|expression\s*\(/i.test(value))) {
          throw new Error("Unexpected active record attribute");
        }
        if (name === "srcset") {
          node.setAttribute(attribute.name, value.split(",").map(function (candidate) {
            var parts = candidate.trim().split(/\s+/);
            if (parts.length !== 2 || !/^[1-9][0-9]*w$/.test(parts[1])) throw new Error("Invalid record srcset");
            var resolved = new URL(parts[0], assetBase);
            if (!/^https?:$/.test(resolved.protocol) || resolved.origin !== url.origin) {
              throw new Error("Invalid record resource URL");
            }
            return resolved.href + " " + parts[1];
          }).join(", "));
          return;
        }
        if (["src", "href", "xlink:href"].indexOf(name) === -1 || value.charAt(0) === "#") return;
        // Generated history markers point within this plate. Static record pages
        // need their own path because of <base>; adopted drawers need local fragments.
        var anchor = node.getAttribute("data-record-anchor");
        if (name === "href" && anchor) {
          var anchorNode = record.getElementById(anchor);
          if (!/^history-[a-z0-9-]+$/.test(anchor) || !anchorNode || !plate.contains(anchorNode)) {
            throw new Error("Invalid history anchor");
          }
          node.setAttribute("href", "#" + anchor);
          return;
        }
        var resolved = new URL(value, assetBase);
        if (!/^https?:$/.test(resolved.protocol) ||
            (name === "src" && resolved.origin !== url.origin)) throw new Error("Invalid record resource URL");
        node.setAttribute(attribute.name, resolved.href);
      });
    });
    return document.importNode(plate, true);
  }

  function focusHistory(plate, document, window) {
    var anchor = new URL(window.location.href).hash.slice(1);
    if (!/^history-[a-f0-9]{64}-(?:event|repository)-[a-z0-9-]+$/.test(anchor)) return false;
    var target = document.getElementById(anchor);
    if (!target || !plate.contains(target)) return false;
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "center" });
    return true;
  }

  function enhancePlates(document, window) {
    if (plateManagers.has(document)) return plateManagers.get(document);
    var states = new WeakMap();

    function showPlate(plate) {
      enhancePlate(plate, document, window);
      plate.classList.remove("is-opening");
      void plate.offsetWidth;
      plate.classList.add("is-opening");
      if (plate.plateLayout) plate.plateLayout();
      focusHistory(plate, document, window);
    }

    function open(drawer) {
      var state = states.get(drawer);
      if (!state || !drawer.open) return;
      var plate = drawer.querySelector(".specimen-plate");
      if (!plate || state.shown) return;
      showPlate(plate);
      state.shown = true;
    }

    var drawers = document.querySelectorAll ? document.querySelectorAll("details.specimen-drawer") : [];
    Array.prototype.forEach.call(drawers, function (drawer) {
      var state = { shown: false };
      states.set(drawer, state);
      drawer.addEventListener("toggle", function () {
        if (drawer.open) open(drawer);
        else state.shown = false;
      });
      if (drawer.open) open(drawer);
    });
    if (window.addEventListener) {
      window.addEventListener("resize", function () {
        Array.prototype.forEach.call(document.querySelectorAll(".specimen-drawer[open] .specimen-plate"), function (plate) {
          if (plate.plateLayout) plate.plateLayout();
        });
      });
      window.addEventListener("pageshow", function (event) {
        if (event.persisted) Array.prototype.forEach.call(drawers, function (drawer) { if (drawer.open) open(drawer); });
      });
    }
    var manager = { open: open };
    plateManagers.set(document, manager);
    return manager;
  }

  // Evidence-grid popups: native disclosures; keep one open, close on Escape or outside click.
  function plateInfo(document) {
    if (!document.addEventListener) return;
    function openInfos() {
      return Array.prototype.slice.call(document.querySelectorAll(".pg-info[open]"));
    }
    document.addEventListener("toggle", function (event) {
      var info = event.target;
      if (!info.classList || !info.classList.contains("pg-info") || !info.open) return;
      openInfos().forEach(function (other) { if (other !== info) other.open = false; });
      // Open from the box edge nearest the grid's centre; columns change with width.
      var box = info.parentElement, grid = info.closest(".plate-grid");
      if (grid) {
        var b = box.getBoundingClientRect(), g = grid.getBoundingClientRect();
        box.classList.toggle("is-end", b.left + b.width / 2 > g.left + g.width / 2 + 1);
      }
    }, true);
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      openInfos().forEach(function (info) {
        info.open = false;
        if (info.contains(document.activeElement)) info.querySelector("summary").focus();
      });
    });
    document.addEventListener("click", function (event) {
      openInfos().forEach(function (info) { if (!info.contains(event.target)) info.open = false; });
    });
  }

  function collectionReplay(document, window) {
    if (!window.IntersectionObserver || !window.MutationObserver) return;
    var states = new Map(), reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    function stop(state) { window.clearTimeout(state.timer); state.timer = null; }
    function active(state) {
      var node = state.node, drawer = node.closest('details.specimen-drawer');
      return node.isConnected && state.visible && !document.hidden && !reduced.matches &&
        (!drawer || drawer.open) && !node.matches(':hover') && !node.contains(document.activeElement) &&
        !node.querySelector('details[open]') && state.lines.length > 1;
    }
    function schedule(state) {
      stop(state);
      if (!active(state)) return;
      state.timer = window.setTimeout(function () {
        if (!active(state)) return;
        state.index = (state.index + 1) % state.lines.length;
        var screen = state.node.querySelector('.collection-replay');
        screen.replaceChildren();
        for (var n = Math.min(3, state.index + 1); n > 0; n--) {
          var span = document.createElement('span');
          span.textContent = state.lines[state.index - n + 1]; screen.appendChild(span);
        }
        schedule(state);
      }, 6000);
    }
    var observer = new window.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var state = states.get(entry.target); if (!state) return;
        state.visible = entry.isIntersecting; schedule(state);
      });
    }, {threshold: 0.1});
    function scan() {
      states.forEach(function (state, node) {
        if (!node.isConnected) { stop(state); observer.unobserve(node); states.delete(node); }
      });
      document.querySelectorAll('.pg-collection').forEach(function (node) {
        if (states.has(node)) return;
        var lines = Array.from(node.querySelectorAll('.collection-events li')).map(function (li) {
          return li.querySelector('time').dateTime.slice(0, 10) + ' · ' + li.querySelector('a').textContent;
        });
        var state = {node:node, lines:lines, index:lines.length - 1, visible:false, timer:null};
        states.set(node, state); observer.observe(node);
        ['mouseenter','mouseleave','focusin','focusout'].forEach(function (event) {
          node.addEventListener(event, function () {
            if (event === 'focusout') window.setTimeout(function () { schedule(state); }, 0);
            else schedule(state);
          });
        });
      });
    }
    function refresh() { states.forEach(schedule); }
    document.addEventListener('visibilitychange', refresh);
    document.addEventListener('toggle', refresh, true);
    reduced.addEventListener('change', refresh);
    new window.MutationObserver(scan).observe(document.body, {childList:true, subtree:true});
    scan();
  }

  function init(document, window) {
    plateInfo(document);
    collectionReplay(document, window);
    enhancePlates(document, window);
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
  }

  return {
    DEFAULTS: DEFAULTS,
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
    comparator: comparator,
    selectProjects: selectProjects,
    stateToURL: stateToURL,
    init: init,
    // The one-screen Catalog (app.js) mounts fetched records with the same checks and enhancement.
    recordPlate: recordPlate,
    enhancePlate: enhancePlate
  };
});
