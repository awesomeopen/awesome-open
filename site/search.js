/* One search for the Catalog's filters and the Cabinet's tools: predicate, match order and unknowns. */
(function (root, factory) {
  "use strict";
  var search = factory();
  if (typeof module === "object" && module.exports) module.exports = search;
  else root.OpenSearch = search;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  // Strongest first. Function summaries and feature notes load separately from
  // the embedded index, so `text` holds them once search-text.json has arrived.
  var FIELDS = ["name", "alias", "description", "alternative", "summary", "feature"];

  function fold(value) {
    return String(value == null ? "" : value).normalize("NFKD")
      .replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function words(query) {
    return fold(query).split(/\s+/).filter(Boolean);
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

  function fieldText(project, text) {
    var extra = (text && text[project.id]) || {};
    return {
      name: fold(project.name),
      description: fold(project.description),
      alternative: fold((project.alternatives || []).map(function (item) { return item.name; }).join(" ")),
      summary: fold(extra.summary),
      feature: fold((extra.features || []).join(" "))
    };
  }

  // Every word must appear somewhere. Returns the fields that matched and the
  // rank, which is the weakest field any word needed; null when a word is absent.
  function match(project, tokens, shortAliases, text) {
    var fields = fieldText(project, text), aliases = aliasNames(project), hit = {}, rank = 0;
    var complete = tokens.every(function (token) {
      var best = -1;
      FIELDS.forEach(function (field, index) {
        // Preserve ordinary substring search; an exact reviewed short name such
        // as OBS must not match incidental prose like "obsolete". Alias-only
        // terms always use word boundaries, including Unicode letters/numbers.
        var found = field === "alias"
          ? aliases.some(function (alias) { return boundaryMatch(alias, token); })
          : shortAliases.has(token) ? boundaryMatch(fields[field], token) : fields[field].indexOf(token) !== -1;
        if (!found) return;
        hit[field] = true;
        if (best === -1) best = index;
      });
      rank = Math.max(rank, best);
      return best !== -1;
    });
    return complete ? { rank: rank, fields: FIELDS.filter(function (field) { return hit[field]; }) } : null;
  }

  // A map of project ID to match, or null when the query has no words.
  function find(projects, query, text) {
    var tokens = words(query);
    if (!tokens.length) return null;
    var shortAliases = shortAliasNames(projects), hits = new Map();
    projects.forEach(function (project) {
      var result = match(project, tokens, shortAliases, text);
      if (result) hits.set(project.id, result);
    });
    return hits;
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

  // A search orders by match rank, then name. With no query there is nothing to
  // rank, so the ledger keeps its star order.
  function compareMatch(hits) {
    if (!hits) return function (a, b) { return compareDescending(starsOf(a), starsOf(b)) || compareName(a, b); };
    function rank(project) {
      var result = hits.get(project.id);
      return result ? result.rank : FIELDS.length;
    }
    return function (a, b) { return rank(a) - rank(b) || compareName(a, b); };
  }

  // The ordered results of a query, each with the fields that matched.
  function results(projects, query, text) {
    var hits = find(projects, query, text);
    return projects.filter(function (project) { return !hits || hits.has(project.id); })
      .sort(compareMatch(hits))
      .map(function (project) {
        return { project: project, fields: hits ? hits.get(project.id).fields : [] };
      });
  }

  function noMatch(count) {
    return "No match in this catalog of " + count + " Open*-named projects.";
  }

  var pending = null;

  // Function summaries and feature notes for one published revision. Concurrent
  // callers share a request; a failure clears it so that the next search retries.
  function loadText(window, url, sourceSha) {
    if (pending) return pending;
    pending = Promise.resolve().then(function () {
      var target = new URL(url, window.location.href);
      if (target.origin !== window.location.origin) throw new Error("Search text must be same-origin");
      return window.fetch(target.href, { redirect: "error", credentials: "omit" });
    }).then(function (response) {
      if (!response.ok) throw new Error("Search text request failed");
      return response.json();
    }).then(function (document) {
      if ((document.source_sha || "") !== (sourceSha || "") || !document.projects ||
          typeof document.projects !== "object") throw new Error("Search text revision mismatch");
      return document.projects;
    }).catch(function (error) {
      pending = null;
      throw error;
    });
    return pending;
  }

  return {
    FIELDS: FIELDS,
    fold: fold,
    words: words,
    licenseOf: licenseOf,
    starsOf: starsOf,
    shortAliasNames: shortAliasNames,
    match: match,
    find: find,
    compareText: compareText,
    compareName: compareName,
    compareDescending: compareDescending,
    compareMatch: compareMatch,
    results: results,
    noMatch: noMatch,
    loadText: loadText
  };
});
