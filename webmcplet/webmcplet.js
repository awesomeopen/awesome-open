/* WebMCPlet: read-only WebMCP tools for one curated list, from one generated JSON document.
 * MIT License; see LICENSE in this directory. No dependencies. */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.WebMCPlet = api; api.autostart(root); }
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  var VERSION = 1;
  var PAGE = 12;
  var MAX_QUERY = 160;
  var TYPES = ["number", "string", "date", "list", "text"];
  var SEARCHABLE = ["string", "list", "text"];
  var FILTERABLE = ["string", "list"];

  function ListError(code, message) {
    var error = new Error(message);
    error.code = code;
    return error;
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function isText(value) {
    return typeof value === "string" && value.trim() !== "";
  }

  // The identity of an entry: its URL without scheme, "www.", fragment, trailing
  // slash or ".git", in lowercase. Cross-listed entries share it.
  function normalizeUrl(url) {
    var parsed = new URL(url);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") throw new Error("Not a web URL: " + url);
    var path = parsed.pathname.replace(/\/+$/, "").replace(/\.git$/i, "").replace(/\/+$/, "");
    return (parsed.host.replace(/^www\./i, "") + path + parsed.search).toLowerCase();
  }

  function checkValue(type, value) {
    if (type === "number") return typeof value === "number" && Number.isFinite(value);
    if (type === "date") return typeof value === "string" && !Number.isNaN(Date.parse(value));
    if (type === "list") return Array.isArray(value) && value.every(isText);
    // Text is prose: one string, or several such as feature notes.
    if (type === "text") return isText(value) || (Array.isArray(value) && value.every(isText));
    return isText(value);
  }

  // Returns a list of problems; an empty list means the document is usable.
  function validate(doc) {
    var problems = [];
    function problem(path, text) { if (problems.length < 50) problems.push(path + ": " + text); }
    if (!isObject(doc)) return ["document: must be a JSON object"];
    if (doc.webmcplet !== VERSION) problem("webmcplet", "must be " + VERSION);
    var list = doc.list;
    if (!isObject(list)) problem("list", "must be an object");
    else {
      ["title", "page_url"].forEach(function (key) { if (!isText(list[key])) problem("list." + key, "is required"); });
    }
    var sections = Array.isArray(doc.sections) ? doc.sections : [];
    if (!Array.isArray(doc.sections) || !sections.length) problem("sections", "must be a non-empty array");
    var sectionIds = new Set();
    sections.forEach(function (section, i) {
      var path = "sections[" + i + "]";
      if (!isObject(section) || !isText(section.id) || !isText(section.title)) return problem(path, "needs id and title");
      if (sectionIds.has(section.id)) problem(path + ".id", "duplicates " + section.id);
      if (section.parent !== undefined && !sectionIds.has(section.parent)) problem(path + ".parent", "must name an earlier section");
      sectionIds.add(section.id);
    });
    var fields = doc.fields === undefined ? {} : doc.fields;
    if (!isObject(fields)) { problem("fields", "must be an object"); fields = {}; }
    Object.keys(fields).forEach(function (name) {
      var field = fields[name], path = "fields." + name;
      if (["id", "name", "url", "description", "sections", "aliases", "link"].indexOf(name) !== -1) return problem(path, "uses a reserved name");
      if (!isObject(field) || !isText(field.label) || !isText(field.meaning)) return problem(path, "needs label and meaning");
      if (TYPES.indexOf(field.type) === -1) problem(path + ".type", "must be one of " + TYPES.join(", "));
      if (field.search && SEARCHABLE.indexOf(field.type) === -1) problem(path + ".search", "applies to string, list and text fields");
      if (field.filter && FILTERABLE.indexOf(field.type) === -1) problem(path + ".filter", "applies to string and list fields");
      if (field.values !== undefined && !isObject(field.values)) problem(path + ".values", "must map values to labels");
      if (field.observed_at !== undefined && !checkValue("date", field.observed_at)) problem(path + ".observed_at", "must be a date");
    });
    var items = Array.isArray(doc.items) ? doc.items : [];
    if (!Array.isArray(doc.items)) problem("items", "must be an array");
    var ids = new Set();
    items.forEach(function (item, i) {
      var path = "items[" + i + "]";
      if (!isObject(item)) return problem(path, "must be an object");
      ["id", "name", "url"].forEach(function (key) { if (!isText(item[key])) problem(path + "." + key, "is required"); });
      if (typeof item.description !== "string") problem(path + ".description", "must be a string");
      if (ids.has(item.id)) problem(path + ".id", "duplicates " + item.id);
      ids.add(item.id);
      if (!Array.isArray(item.sections) || !item.sections.length || !item.sections.every(function (s) { return sectionIds.has(s); }))
        problem(path + ".sections", "must name one or more declared sections");
      if (item.aliases !== undefined && !(Array.isArray(item.aliases) && item.aliases.every(isText))) problem(path + ".aliases", "must be strings");
      if (item.link !== undefined && !isText(item.link)) problem(path + ".link", "must be a URL");
      var values = item.fields === undefined ? {} : item.fields;
      if (!isObject(values)) return problem(path + ".fields", "must be an object");
      Object.keys(values).forEach(function (name) {
        if (!fields[name]) return problem(path + ".fields." + name, "is not declared");
        if (!checkValue(fields[name].type, values[name])) problem(path + ".fields." + name, "must be a " + fields[name].type);
      });
    });
    return problems;
  }

  // Matching: every query word must appear in a searched field. Fields rank in
  // order: name, aliases, description, then declared search fields in document
  // order. A result's rank is the weakest field any word needed; ties go by
  // name, then list order.
  function fold(value) {
    return String(value == null ? "" : value).normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function words(query) {
    return fold(query).split(/\s+/).filter(Boolean);
  }

  function boundaryMatch(text, token) {
    var literal = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp("(^|[^\\p{L}\\p{N}\\p{M}_])" + literal + "(?=$|[^\\p{L}\\p{N}\\p{M}_])", "u").test(text);
  }

  function compareText(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  // options.prefix names the tools in recovery messages, default "list".
  function create(doc, options) {
    var hint = ((options && options.prefix) || "list") + "_";
    var problems = validate(doc);
    if (problems.length) throw ListError("list_invalid", "The list document is invalid: " + problems.slice(0, 3).join("; "));
    var fields = doc.fields || {};
    var searched = Object.keys(fields).filter(function (name) { return fields[name].search; });
    var ranks = ["name", "aliases", "description"].concat(searched);
    var sections = doc.sections.map(function (s) { return { id: s.id, title: s.title, parent: s.parent || null }; });
    var children = new Map(sections.map(function (s) { return [s.id, []]; }));
    var parentOf = new Map(sections.map(function (s) { return [s.id, s.parent]; }));
    sections.forEach(function (s) { if (s.parent) children.get(s.parent).push(s.id); });
    var byId = new Map(), position = new Map();
    var index = doc.items.map(function (item, i) {
      byId.set(item.id, item); position.set(item.id, i);
      var values = item.fields || {}, text = { name: fold(item.name), description: fold(item.description) };
      searched.forEach(function (name) {
        var value = values[name];
        text[name] = fold(Array.isArray(value) ? value.join(" ") : value);
      });
      return { item: item, text: text, aliases: (item.aliases || []).map(fold), name: fold(item.name) };
    });
    // An exact reviewed short alias such as OBS must not match "obsolete".
    var shortAliases = new Set();
    index.forEach(function (entry) {
      entry.aliases.forEach(function (alias) { if (/^[\p{L}\p{N}_]{1,4}$/u.test(alias)) shortAliases.add(alias); });
    });

    function within(sectionId) {
      var all = new Set(), stack = [sectionId];
      while (stack.length) { var id = stack.pop(); all.add(id); stack.push.apply(stack, children.get(id)); }
      return all;
    }

    function matchEntry(entry, tokens) {
      var hit = {}, rank = 0;
      var complete = tokens.every(function (token) {
        var best = -1;
        ranks.forEach(function (field, i) {
          var found = field === "aliases"
            ? entry.aliases.some(function (alias) { return boundaryMatch(alias, token); })
            : shortAliases.has(token) ? boundaryMatch(entry.text[field], token) : entry.text[field].indexOf(token) !== -1;
          if (!found) return;
          hit[field] = true;
          if (best === -1) best = i;
        });
        rank = Math.max(rank, best);
        return best !== -1;
      });
      return complete ? { rank: rank, fields: ranks.filter(function (f) { return hit[f]; }) } : null;
    }

    // Values of declared non-text fields; unrecorded values are null (Unknown).
    // Text fields are long, so only get returns them.
    function summary(item) {
      var values = item.fields || {}, out = {};
      Object.keys(fields).forEach(function (name) {
        if (fields[name].type !== "text") out[name] = values[name] === undefined ? null : values[name];
      });
      return out;
    }

    function row(item, fieldsMatched) {
      var out = { id: item.id, name: item.name, description: item.description, url: item.url, sections: item.sections.slice() };
      if (item.link) out.link = item.link;
      if (fieldsMatched) out.matched_fields = fieldsMatched;
      out.fields = summary(item);
      return out;
    }

    function checkKeys(args, allowed) {
      if (!isObject(args) || Object.keys(args).some(function (key) { return allowed.indexOf(key) === -1; }))
        throw ListError("invalid_arguments", "Send an object with only: " + allowed.join(", ") + ".");
    }

    function find(args) {
      checkKeys(args, ["query", "offset", "section", "filters"]);
      var query = args.query === undefined ? "" : args.query;
      if (typeof query !== "string" || query.length > MAX_QUERY)
        throw ListError("invalid_query", "query must be a string of at most " + MAX_QUERY + " characters.");
      var offset = args.offset === undefined ? 0 : args.offset;
      if (!Number.isInteger(offset) || offset < 0) throw ListError("invalid_offset", "offset must be a whole number from 0.");
      var scope = null;
      if (args.section !== undefined) {
        if (!children.has(args.section)) throw ListError("invalid_section", "section must be an id from " + hint + "sections.");
        scope = within(args.section);
      }
      var filters = args.filters === undefined ? {} : args.filters;
      if (!isObject(filters)) throw ListError("invalid_filter", "filters must map a filterable field to one value.");
      var applied = Object.keys(filters).map(function (name) {
        var field = fields[name], value = filters[name];
        if (!field || !field.filter || !isText(value))
          throw ListError("invalid_filter", "filters must map a filterable field to one value; " + hint + "sections lists them.");
        return { name: name, value: value, type: field.type };
      });
      var tokens = words(query), hits = [];
      var order = function (a, b) { return position.get(a.entry.item.id) - position.get(b.entry.item.id); };
      index.forEach(function (entry) {
        var item = entry.item, values = item.fields || {};
        if (scope && !item.sections.some(function (s) { return scope.has(s); })) return;
        var kept = applied.every(function (f) {
          var value = values[f.name];
          return f.type === "list" ? Array.isArray(value) && value.indexOf(f.value) !== -1 : value === f.value;
        });
        if (!kept) return;
        var match = tokens.length ? matchEntry(entry, tokens) : { rank: 0, fields: null };
        if (match) hits.push({ entry: entry, rank: match.rank, fields: match.fields });
      });
      hits.sort(tokens.length
        ? function (a, b) { return a.rank - b.rank || compareText(a.entry.name, b.entry.name) || order(a, b); }
        : order);
      var result = { query: query, offset: offset, total: hits.length,
        items: hits.slice(offset, offset + PAGE).map(function (hit) { return row(hit.entry.item, hit.fields); }),
        page_url: doc.list.page_url };
      if (args.section !== undefined) result.section = args.section;
      if (applied.length) {
        // Unrecorded items cannot match a filter, so say how many have a record.
        result.coverage = applied.map(function (f) {
          var recorded = doc.items.filter(function (item) { return (item.fields || {})[f.name] !== undefined; }).length;
          return { field: f.name, recorded: recorded, total: doc.items.length,
            note: recorded + " of " + doc.items.length + " items have a recorded " + fields[f.name].label + "." };
        });
      }
      if (!hits.length) result.message = "No match in " + doc.list.title + " (" + doc.items.length + " items).";
      return result;
    }

    function get(args) {
      checkKeys(args, ["id"]);
      var item = typeof args.id === "string" && byId.get(args.id);
      if (!item) throw ListError("unknown_id", "id must be an id returned by " + hint + "find.");
      var out = row(item);
      if (item.aliases) out.aliases = item.aliases.slice();
      var values = item.fields || {};
      Object.keys(fields).forEach(function (name) {
        if (fields[name].type === "text") out.fields[name] = values[name] === undefined ? null : values[name];
      });
      out.page_url = doc.list.page_url;
      return out;
    }

    function overview(args) {
      checkKeys(args, []);
      var counts = new Map(sections.map(function (s) { return [s.id, 0]; }));
      // An item counts once in each section that contains it, at any depth.
      doc.items.forEach(function (item) {
        var seen = new Set();
        item.sections.forEach(function (id) { for (; id; id = parentOf.get(id)) seen.add(id); });
        seen.forEach(function (id) { counts.set(id, counts.get(id) + 1); });
      });
      var declared = {};
      Object.keys(fields).forEach(function (name) {
        var field = fields[name], out = { label: field.label, type: field.type, meaning: field.meaning,
          recorded: doc.items.filter(function (item) { return (item.fields || {})[name] !== undefined; }).length };
        ["source", "observed_at", "values"].forEach(function (key) { if (field[key] !== undefined) out[key] = field[key]; });
        if (field.search) out.searched = true;
        if (field.filter) out.filter = true;
        declared[name] = out;
      });
      var list = { title: doc.list.title, page_url: doc.list.page_url, items: doc.items.length };
      ["description", "source_url", "source_revision", "license", "generated_at"].forEach(function (key) {
        if (doc.list[key] !== undefined) list[key] = doc.list[key];
      });
      return { list: list, sections: sections.map(function (s) { return { id: s.id, title: s.title, parent: s.parent, items: counts.get(s.id) }; }),
        fields: declared, searched_fields: ranks };
    }

    return { find: find, get: get, overview: overview };
  }

  function definitions(prefix, doc) {
    var title = doc.list.title;
    return [
      [prefix + "_sections", "Describe " + title + ": its sections with item counts, and its declared fields with their meaning, source, observation date and how many items record them. Unknown values are null.",
        {}, []],
      [prefix + "_find", "Search " + title + ". Every word of query must appear in an item’s name, aliases, description or a searched field. Returns 12 items from offset, strongest matching field first, with matched_fields and total; an empty query lists items in list order. section limits results to a section and its subsections. filters maps a filterable field to one value and reports how many items record it. total 0 means no item in this list matches.",
        { query: { type: "string", maxLength: MAX_QUERY }, offset: { type: "integer", minimum: 0 },
          section: { type: "string" }, filters: { type: "object", additionalProperties: { type: "string" } } }, []],
      [prefix + "_get", "Return one item from " + title + " with every recorded field, including text fields. Unknown values are null.",
        { id: { type: "string" } }, ["id"]]
    ];
  }

  function failure(code, message) {
    return { ok: false, code: code, message: message };
  }

  // Registers the tools on document.modelContext. Chrome replaces a thrown error
  // with a generic failure, so every tool returns {ok:false, code, message}.
  async function register(doc, options) {
    options = options || {};
    var prefix = options.prefix || "list", context = options.document || document;
    var bridge = context.modelContext;
    if (!bridge || typeof bridge.registerTool !== "function") return { registered: [] };
    var list = create(doc, { prefix: prefix });
    var run = { _sections: list.overview, _find: list.find, _get: list.get };
    var names = [];
    for (var entry of definitions(prefix, doc)) {
      var name = entry[0], handler = run[name.slice(prefix.length)];
      await bridge.registerTool({
        name: name, description: entry[1],
        inputSchema: { type: "object", properties: entry[2], required: entry[3], additionalProperties: false },
        annotations: { readOnlyHint: true, untrustedContentHint: true },
        execute: (function (handler) {
          return function (args) {
            try {
              var parsed = typeof args === "string" ? JSON.parse(args || "{}") : args || {};
              return Object.assign({ ok: true }, handler(parsed));
            } catch (error) {
              return error.code ? failure(error.code, error.message) : failure("invalid_arguments", "Arguments must be a JSON object.");
            }
          };
        })(handler)
      }, options.signal ? { signal: options.signal } : undefined);
      names.push(name);
    }
    return { registered: names };
  }

  // Loads one same-origin document. Redirects and credentials are refused.
  async function load(url, win) {
    var target = new URL(url, win.location.href);
    if (target.origin !== win.location.origin) throw ListError("list_unavailable", "The list document must be same-origin.");
    var response = await win.fetch(target.href, { redirect: "error", credentials: "omit" });
    if (!response.ok) throw ListError("list_unavailable", "The list document returned HTTP " + response.status + ".");
    return response.json();
  }

  // <script src="webmcplet.js" data-webmcplet-src="list.json" data-webmcplet-prefix="list">
  function autostart(win) {
    var script = win.document && win.document.currentScript;
    if (!script || !script.dataset || !script.dataset.webmcpletSrc) return;
    var options = { prefix: script.dataset.webmcpletPrefix || "list" };
    win.WebMCPlet.ready = load(script.dataset.webmcpletSrc, win)
      .then(function (doc) { return register(doc, options); })
      .catch(function (error) {
        if (win.console) win.console.warn("WebMCPlet: " + error.message);
        return { registered: [], error: error.code || "list_unavailable" };
      });
  }

  return { VERSION: VERSION, PAGE: PAGE, normalizeUrl: normalizeUrl, validate: validate, create: create,
    register: register, load: load, autostart: autostart, fold: fold };
});
