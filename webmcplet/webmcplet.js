/* WebMCPlet: read-only WebMCP tools for one curated list, from one generated JSON document.
 * MIT License; see LICENSE in this directory. No dependencies. */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else { root.WebMCPlet = api; api.autostart(root); }
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  var RELEASE = "0.1.0"; // This script's version; CHANGELOG.md records each with its SHA-256.
  var VERSION = 1; // The list document schema.
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


  function failure(code, message) {
    return { ok: false, code: code, message: message };
  }

  // The three read-only tools. `source` is a list document or a function that
  // loads one; the document loads at the first call, so a page pays for it only
  // when a tool or the panel is used. Chrome replaces a thrown error with a
  // generic failure, so every tool returns {ok:false, code, message}.
  function tools(source, options) {
    var prefix = options.prefix || "list", title = options.title || (source && source.list && source.list.title);
    var pending = null;
    function list() {
      if (!pending) {
        pending = Promise.resolve(typeof source === "function" ? source() : source)
          .then(function (doc) { return { doc: doc, list: create(doc, { prefix: prefix }) }; });
        pending.catch(function () { pending = null; });
      }
      return pending;
    }
    function tool(suffix, description, properties, required, method, modelProperties) {
      return {
        name: prefix + suffix, description: description,
        inputSchema: { type: "object", properties: properties, required: required, additionalProperties: false },
        // The on-device model fills optional arguments with invented values, such as
        // a section name, so the assistant sees only the arguments it needs.
        modelSchema: modelProperties && { type: "object", properties: modelProperties, required: required, additionalProperties: false },
        annotations: { readOnlyHint: true, untrustedContentHint: true },
        execute: async function (args) {
          var parsed;
          try { parsed = typeof args === "string" ? JSON.parse(args || "{}") : args || {}; }
          catch (_) { return failure("invalid_arguments", "Arguments must be a JSON object."); }
          var loaded;
          try { loaded = await list(); }
          catch (error) { return failure("list_unavailable", "The list could not load. Retry later."); }
          try { return Object.assign({ ok: true }, loaded.list[method](parsed)); }
          catch (error) { return error.code ? failure(error.code, error.message) : failure("invalid_arguments", "Arguments must be a JSON object."); }
        }
      };
    }
    var defined = [
      tool("_sections", "Describe " + title + ": its sections with item counts, and its declared fields with their meaning, source, observation date and how many items record them. Unknown values are null.",
        {}, [], "overview"),
      tool("_find", "Search " + title + ". Every word of query must appear in an item’s name, aliases, description or a searched field. Returns 12 items from offset, strongest matching field first, with matched_fields and total; an empty query lists items in list order. section limits results to a section and its subsections. filters maps a filterable field to one value and reports how many items record it. total 0 means no item in this list matches.",
        { query: { type: "string", maxLength: MAX_QUERY }, offset: { type: "integer", minimum: 0 },
          section: { type: "string" }, filters: { type: "object", additionalProperties: { type: "string" } } }, [], "find",
        { query: { type: "string", maxLength: MAX_QUERY }, offset: { type: "integer", minimum: 0 } }),
      tool("_get", "Return one item from " + title + " with every recorded field, including text fields. Unknown values are null.",
        { id: { type: "string" } }, ["id"], "get")
    ];
    defined.document = function () { return list().then(function (loaded) { return loaded.doc; }); };
    return defined;
  }

  // Registers the tools on document.modelContext where the browser provides it.
  async function register(source, options) {
    options = options || {};
    var defined = tools(source, options), context = options.document || document;
    var bridge = context.modelContext, names = [];
    if (bridge && typeof bridge.registerTool === "function") {
      for (var tool of defined) {
        await bridge.registerTool(tool, options.signal ? { signal: options.signal } : undefined);
        names.push(tool.name);
      }
    }
    return { registered: names, tools: defined };
  }

  // Loads one same-origin document. Redirects and credentials are refused.
  async function load(url, win) {
    var target = new URL(url, win.location.href);
    if (target.origin !== win.location.origin) throw ListError("list_unavailable", "The list document must be same-origin.");
    var response = await win.fetch(target.href, { redirect: "error", credentials: "omit" });
    if (!response.ok) throw ListError("list_unavailable", "The list document returned HTTP " + response.status + ".");
    return response.json();
  }

  // ---- Assistant: Chrome's Prompt API driving the same tools ----
  //
  // Measured in experiments/prompt-api-m5: the model copies short refs reliably
  // and 64-character IDs poorly, needs recovery messages that name the next tool,
  // and occasionally fails with UnknownError or generates without end.

  var LANG = { expectedInputs: [{ type: "text", languages: ["en"] }], expectedOutputs: [{ type: "text", languages: ["en"] }] };
  var REF = { type: "string", pattern: "^r[0-9]{1,3}$" };
  var MAX_TURNS = 8, TURN_MS = 30000, MAX_REQUEST = 500;

  function Refs() {
    var toRef = new Map(), toId = new Map();
    function ref(id) {
      if (!toRef.has(id)) { var r = "r" + (toRef.size + 1); toRef.set(id, r); toId.set(r, id); }
      return toRef.get(id);
    }
    function id(r) { return toId.has(r) ? toId.get(r) : r; }
    function hide(value, key) {
      if (key === "id" && typeof value === "string") return ref(value);
      if (key === "ids" && Array.isArray(value)) return value.map(function (v) { return typeof v === "string" ? ref(v) : v; });
      if (Array.isArray(value)) return value.map(function (v) { return hide(v); });
      if (isObject(value)) {
        var out = {};
        Object.keys(value).forEach(function (k) { out[k] = hide(value[k], k); });
        return out;
      }
      return value;
    }
    // Unknown refs pass through unchanged, so the tool rejects them.
    function reveal(args) {
      var out = Object.assign({}, args);
      if (typeof out.id === "string") out.id = id(out.id);
      if (Array.isArray(out.ids)) out.ids = out.ids.map(id);
      return out;
    }
    return { hide: hide, reveal: reveal, id: id };
  }

  function schemaOf(tool) {
    if (tool.modelSchema) return tool.modelSchema;
    return typeof tool.inputSchema === "string" ? JSON.parse(tool.inputSchema) : tool.inputSchema;
  }

  // Item IDs become refs in the schema the model sees. Chrome 156 rejects a
  // responseConstraint containing uniqueItems; the tools enforce it themselves.
  function modelSchema(schema) {
    if (Array.isArray(schema)) return schema.map(modelSchema);
    if (!isObject(schema)) return schema;
    var out = {};
    Object.keys(schema).forEach(function (key) {
      if (key === "uniqueItems") return;
      out[key] = key === "properties" ? refProperties(schema[key]) : modelSchema(schema[key]);
    });
    return out;
  }

  function refProperties(properties) {
    var out = {};
    Object.keys(properties).forEach(function (key) {
      if (key === "id") out[key] = REF;
      else if (key === "ids") out[key] = Object.assign(modelSchema(properties[key]), { items: REF });
      else out[key] = modelSchema(properties[key]);
    });
    return out;
  }

  function actionSchema(tools) {
    return { anyOf: tools.map(function (tool) {
      return { type: "object", additionalProperties: false, required: ["action", "tool", "args"],
        properties: { action: { type: "string", enum: ["call"] }, tool: { type: "string", enum: [tool.name] }, args: modelSchema(schemaOf(tool)) } };
    }).concat([{ type: "object", additionalProperties: false, required: ["action", "text", "ids"],
      properties: { action: { type: "string", enum: ["answer"] }, text: { type: "string" }, ids: { type: "array", items: REF } } }]) };
  }

  // Wording measured in experiments/prompt-api-m5; small changes moved pass rates.
  function instructions(title, tools) {
    return [
      "You help a visitor find items in " + title + ". You can only read this page through its tools.",
      "Each turn, reply with one JSON action.",
      "Items are identified by short refs such as r1. Use these refs in tool arguments and in ids.",
      "To call a tool: {\"action\":\"call\",\"tool\":\"<name>\",\"args\":{...}}. The next message gives its result.",
      "To finish: {\"action\":\"answer\",\"text\":\"<answer for the visitor>\",\"ids\":[\"<id>\", ...]}.",
      "Rules:",
      "- Search with short keyword queries. A result must contain every word of the query, so long phrases often find nothing; try fewer or simpler words.",
      "- State only facts from tool results. A null value is Unknown.",
      "- ids lists the items your answer presents as fitting the request, copied exactly from tool results.",
      "- If no item fits, say that this list has no match, leave ids empty and name no item.",
      "- If a tool returns ok:false, follow its message.",
      "Tools:"
    ].concat(tools.map(function (tool) {
      return "- " + tool.name + ": " + tool.description + " Arguments: " + JSON.stringify(modelSchema(schemaOf(tool)));
    })).join("\n");
  }

  // Every object with a string id and name in a tool result, as a display row.
  function collectRows(value, rows) {
    if (Array.isArray(value)) value.forEach(function (v) { collectRows(v, rows); });
    else if (isObject(value)) {
      if (typeof value.id === "string" && typeof value.name === "string") {
        var row = rows.get(value.id) || { id: value.id, name: value.name };
        if (!row.description && typeof value.description === "string") row.description = value.description;
        if (!row.href) row.href = value.link || value.record || value.url || null;
        rows.set(value.id, row);
      }
      Object.keys(value).forEach(function (k) { collectRows(value[k], rows); });
    }
    return rows;
  }

  // Names of list items written in text, as whole words of four or more
  // characters outside URLs; hyphens join words.
  function namesIn(text, names) {
    var plainText = text.replace(/\b(?:https?:\/\/|[\w.-]+\.\w+\/)\S*/g, " ");
    return names.filter(function (name) {
      if (name.length < 4) return false;
      var literal = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp("(^|[^\\p{L}\\p{N}-])" + literal + "(?![\\p{L}\\p{N}-])", "u").test(plainText);
    });
  }

  // Runs one request to an answer, the turn limit or cancellation. The answer's
  // rows come from tool results; the model's text is returned separately, and is
  // withheld when it names an item the tools did not return.
  async function ask(options) {
    var session = options.session, available = options.tools, refs = Refs(), rows = new Map();
    var constraint = actionSchema(available), maxTurns = options.maxTurns || MAX_TURNS, turnMs = options.turnMs || TURN_MS;
    var trace = [], input = options.request, retried = false;
    function report(entry) { trace.push(entry); if (options.onStep) options.onStep(entry); }
    for (var turn = 0; turn < maxTurns; turn++) {
      if (options.signal && options.signal.aborted) return { status: "cancelled", rows: [], trace: trace };
      var raw;
      try {
        var signals = [AbortSignal.timeout(turnMs)];
        if (options.signal) signals.push(options.signal);
        raw = await session.prompt(input, { responseConstraint: constraint, signal: AbortSignal.any(signals) });
      } catch (error) {
        if (options.signal && options.signal.aborted) return { status: "cancelled", rows: [], trace: trace };
        // UnknownError was transient in testing; retry the same prompt once.
        if (error && error.name === "UnknownError" && !retried) { retried = true; turn--; continue; }
        return { status: error && error.name === "TimeoutError" ? "timeout" : "error",
          message: error && error.message, rows: [], trace: trace };
      }
      var action;
      try { action = JSON.parse(raw); } catch (_) { report({ invalid: "malformed_json" }); input = "That was not valid JSON. Reply with one JSON action."; continue; }
      if (action.action === "answer") {
        var ids = (action.ids || []).map(refs.id);
        var shown = ids.filter(function (id) { return rows.has(id); }).map(function (id) { return rows.get(id); });
        var returnedNames = new Set(Array.from(rows.values()).map(function (r) { return r.name; }));
        var unreturned = namesIn(action.text || "", options.names || []).filter(function (n) { return !returnedNames.has(n); });
        report({ answer: true, ids: ids });
        return { status: "answered", rows: shown, removed: ids.length - shown.length,
          text: unreturned.length ? null : action.text, withheld: unreturned, trace: trace };
      }
      var tool = available.find(function (t) { return t.name === action.tool; });
      if (action.action !== "call" || !tool) { report({ invalid: "unsupported_action" }); input = "Unsupported action. Call one of the listed tools or answer."; continue; }
      var args = refs.reveal(action.args || {});
      var result = await tool.execute(args, options.signal ? { signal: options.signal } : {});
      if (typeof result === "string") result = JSON.parse(result);
      if (result && result.ok) collectRows(result, rows);
      report({ tool: tool.name, args: args, ok: Boolean(result && result.ok), code: result && result.code, prompt: input });
      input = "Result of " + tool.name + ": " + JSON.stringify(refs.hide(result));
    }
    return { status: "turn_limit", rows: [], trace: trace };
  }

  // ---- Panel ----

  var STYLE = [
    ":host{all:initial;--wm-bg:var(--webmcplet-bg,#fff);--wm-fg:var(--webmcplet-fg,#1b1b1b);--wm-accent:var(--webmcplet-accent,#1d4ed8);",
    "--wm-muted:var(--webmcplet-muted,#555);--wm-rule:var(--webmcplet-rule,#c8c8c8);--wm-focus:var(--webmcplet-focus,#c2410c);",
    "--wm-font:var(--webmcplet-font,system-ui,sans-serif);--wm-heading:var(--webmcplet-heading-font,var(--wm-font));--wm-radius:var(--webmcplet-radius,4px)}",
    "*{box-sizing:border-box}",
    ".trigger{display:block;font:14px/1.2 var(--wm-font);min-height:44px;padding:12px 16px;",
    "border:1px solid var(--wm-accent);border-radius:var(--wm-radius);background:var(--wm-accent);color:var(--wm-bg);cursor:pointer}",
    ".banner .trigger{width:100%;text-align:left}",
    "button,input,select,textarea{font:inherit;color:inherit}",
    ":focus-visible{outline:3px solid var(--wm-focus);outline-offset:2px}",
    "dialog{width:min(880px,calc(100vw - 32px));max-height:calc(100vh - 32px);padding:0;border:1px solid var(--wm-accent);",
    "border-radius:var(--wm-radius);background:var(--wm-bg);color:var(--wm-fg);font:14px/1.6 var(--wm-font)}",
    "dialog::backdrop{background:rgba(0,0,0,.45)}",
    ".frame{padding:24px}header{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}",
    "h2{margin:0;font:400 28px/1.2 var(--wm-heading)}h3{margin:32px 0 8px;font:400 22px/1.2 var(--wm-heading)}",
    "h4{margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--wm-muted)}",
    "label{display:block;margin:16px 0 4px}.row{display:flex;gap:8px;flex-wrap:wrap}",
    "input,select,textarea{min-height:44px;padding:8px 12px;border:1px solid var(--wm-accent);border-radius:var(--wm-radius);background:var(--wm-bg)}",
    "input,textarea{flex:1;min-width:0;width:100%}select{width:100%}textarea{resize:vertical}",
    ".frame button{min-height:44px;padding:8px 16px;border:1px solid var(--wm-accent);border-radius:var(--wm-radius);background:var(--wm-bg);color:var(--wm-accent);cursor:pointer}",
    ".frame button.primary{background:var(--wm-accent);color:var(--wm-bg)}.frame button:disabled{opacity:.45;cursor:default}",
    "ol{list-style:none;margin:8px 0;padding:0}li{padding:12px 0;border-bottom:1px solid var(--wm-rule)}",
    "li a{color:var(--wm-accent);font:400 18px/1.3 var(--wm-heading)}li p{margin:4px 0 0}.meta,.note,.state{color:var(--wm-muted);font-size:13px}",
    ".status{min-height:1.6em}footer{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-top:32px;",
    "padding-top:16px;border-top:1px solid var(--wm-rule);font-size:13px}footer a{color:var(--wm-muted)}",
    "progress{width:100%}[hidden]{display:none!important}",
    "@media(max-width:560px){.frame{padding:16px}h2{font-size:24px}dialog{width:calc(100vw - 16px);max-height:calc(100vh - 16px)}}"
  ].join("");

  function element(doc, tag, attrs, parent, text) {
    var el = doc.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "class") el.className = attrs[key]; else el.setAttribute(key, attrs[key]);
    });
    if (text !== undefined) el.textContent = text;
    if (parent) parent.append(el);
    return el;
  }

  function hiddenKey(win) { return "webmcplet-hidden:" + win.location.pathname; }

  function readHidden(win) {
    try { return win.localStorage.getItem(hiddenKey(win)) === "1"; } catch (_) { return false; }
  }

  // A labelled corner button that opens the list's search, browsing and, where
  // Chrome offers its model, the assistant. It never opens or moves by itself.
  function mount(win, options) {
    var doc = win.document, title = options.title, coreTools = options.tools;
    if (readHidden(win)) return null;
    var host = element(doc, "div", { "data-webmcplet-host": "" });
    // The host carries its own placement so that page CSS on divs, such as a
    // transform, cannot move the corner button into the page's flow.
    var place = options.mode === "banner"
      ? { display: "block", position: "static", transform: "none" }
      : { display: "block", position: "fixed", right: "16px", bottom: "16px", left: "auto", top: "auto",
          "z-index": "2147483000", transform: "none", margin: "0", width: "auto", height: "auto" };
    Object.keys(place).forEach(function (key) { host.style.setProperty(key, place[key], "important"); });
    if (options.mode === "banner") doc.body.prepend(host); else doc.body.append(host);
    var root = host.attachShadow({ mode: "open" });
    element(doc, "style", {}, root, STYLE);
    var wrap = element(doc, "div", { class: options.mode === "banner" ? "banner" : "corner" }, root);
    var trigger = element(doc, "button", { class: "trigger", type: "button", "aria-haspopup": "dialog" }, wrap, options.label || "Search this list");
    var dialog = element(doc, "dialog", { "aria-labelledby": "wm-title" }, wrap);
    var frame = element(doc, "div", { class: "frame" }, dialog);
    var head = element(doc, "header", {}, frame);
    element(doc, "h2", { id: "wm-title" }, head, title);
    var close = element(doc, "button", { type: "button" }, head, "Close");
    var form = element(doc, "form", { role: "search" }, frame);
    element(doc, "label", { for: "wm-query" }, form, "Search " + title);
    var row = element(doc, "div", { class: "row" }, form);
    var query = element(doc, "input", { id: "wm-query", type: "search", maxlength: String(MAX_QUERY), autocomplete: "off" }, row);
    element(doc, "button", { type: "submit", class: "primary" }, row, "Search");
    element(doc, "label", { for: "wm-section" }, form, "Section");
    var section = element(doc, "select", { id: "wm-section" }, form);
    element(doc, "option", { value: "" }, section, "All sections");
    var status = element(doc, "p", { class: "status", role: "status", "aria-live": "polite" }, frame);
    var results = element(doc, "ol", { "aria-label": "Results" }, frame);
    var more = element(doc, "button", { type: "button", hidden: "" }, frame, "Show 12 more");
    var assistant = element(doc, "section", { "aria-labelledby": "wm-ask-title", hidden: "" }, frame);
    element(doc, "h3", { id: "wm-ask-title" }, assistant, "Ask Chrome’s on-device model");
    element(doc, "p", { class: "note" }, assistant, "The model runs in this browser and uses the same tools. Rows come from the list; the text below them is generated.");
    var modelState = element(doc, "p", { class: "state", role: "status", "aria-live": "polite" }, assistant);
    var download = element(doc, "button", { type: "button", hidden: "" }, assistant, "Download the model");
    var progress = element(doc, "progress", { max: "1", value: "0", hidden: "", "aria-label": "Model download" }, assistant);
    var askForm = element(doc, "form", { hidden: "" }, assistant);
    element(doc, "label", { for: "wm-question" }, askForm, "Question");
    var question = element(doc, "textarea", { id: "wm-question", rows: "3", maxlength: String(MAX_REQUEST) }, askForm);
    var askRow = element(doc, "div", { class: "row" }, askForm);
    var askButton = element(doc, "button", { type: "submit", class: "primary" }, askRow, "Ask");
    var stop = element(doc, "button", { type: "button", disabled: "" }, askRow, "Stop");
    var answer = element(doc, "div", { hidden: "" }, assistant);
    element(doc, "h4", {}, answer, "From the list");
    var answerRows = element(doc, "ol", { "aria-label": "Items in the answer" }, answer);
    element(doc, "h4", {}, answer, "Generated text");
    var generated = element(doc, "p", { class: "generated" }, answer);
    var foot = element(doc, "footer", {}, frame);
    var hide = element(doc, "button", { type: "button" }, foot, "Hide this button");
    element(doc, "span", { class: "note" }, foot, "Hidden in this browser until its site data is cleared.");
    element(doc, "a", { href: "https://github.com/awesomeopen/awesome-open/tree/main/webmcplet" }, foot, "WebMCPlet");

    var find = coreTools.find(function (t) { return /_find$/.test(t.name); });
    var listDoc = null, current = { query: "", section: "", offset: 0 }, running = null;

    function link(item) { return item.link || item.url; }
    function sectionTitle(id) {
      var s = listDoc && listDoc.sections.find(function (x) { return x.id === id; });
      return s ? s.title : id;
    }
    function renderRow(list, item) {
      var li = element(doc, "li", {}, list);
      var href = item.href || link(item);
      if (href) element(doc, "a", { href: href }, li, item.name); else element(doc, "strong", {}, li, item.name);
      if (item.description) element(doc, "p", {}, li, item.description);
      if (item.sections) element(doc, "p", { class: "meta" }, li, item.sections.map(sectionTitle).join(" · "));
    }
    async function run(append) {
      if (!append) current.offset = 0;
      var args = { query: current.query, offset: current.offset };
      if (current.section) args.section = current.section;
      status.textContent = "Searching…";
      var result = await find.execute(args);
      if (!result.ok) { status.textContent = result.message; return; }
      if (!append) results.replaceChildren();
      result.items.forEach(function (item) { renderRow(results, item); });
      current.offset += result.items.length;
      var shown = current.offset;
      status.textContent = result.total ? (result.total === 1 ? "1 item" : result.total + " items") +
        (shown < result.total ? "; showing " + shown + "." : ".") : result.message;
      more.hidden = shown >= result.total;
    }
    async function prepare() {
      if (listDoc) return;
      status.textContent = "Loading the list…";
      try { listDoc = await coreTools.document(); }
      catch (_) { status.textContent = "The list could not load. Close and retry."; return; }
      listDoc.sections.forEach(function (s) {
        var depth = 0;
        for (var p = s.parent; p; p = (listDoc.sections.find(function (x) { return x.id === p; }) || {}).parent) depth++;
        element(doc, "option", { value: s.id }, section, " ".repeat(depth) + s.title);
      });
      status.textContent = listDoc.items.length + " items in " + listDoc.sections.length + " sections.";
      refreshModel();
    }

    // Assistant availability: hidden where Chrome has no model for this device.
    // The assistant is opt-in: it missed the pass threshold on one PRD journey
    // (webmcplet/README.md#assistant).
    var model = options.assistant ? win.LanguageModel : null;
    async function refreshModel() {
      if (!model || typeof model.availability !== "function") return;
      var state;
      try { state = await model.availability(LANG); } catch (_) { state = "unavailable"; }
      assistant.hidden = state === "unavailable";
      download.hidden = state !== "downloadable";
      askForm.hidden = state !== "available";
      progress.hidden = state !== "downloading";
      modelState.textContent = {
        downloadable: "Chrome can download its on-device model to answer here. The download is several gigabytes and happens once per browser.",
        downloading: "Chrome is downloading its on-device model.",
        available: "The model is ready."
      }[state] || "";
    }
    download.addEventListener("click", async function () {
      download.disabled = true; progress.hidden = false;
      modelState.textContent = "Downloading the model…";
      try {
        var created = await model.create(Object.assign({}, LANG, { monitor: function (m) {
          m.addEventListener("downloadprogress", function (e) { progress.value = e.loaded; });
        } }));
        created.destroy();
      } catch (error) {
        modelState.textContent = "The download stopped: " + (error && error.message) + " Retry when ready.";
        download.disabled = false; return;
      }
      download.disabled = false;
      refreshModel();
    });

    function assistantTools() {
      var names = options.assistantTools;
      var extra = (win.webmcpletTools || []);
      var all = coreTools.concat(extra);
      // By default the measured set: search and retrieval, plus the page's own tools.
      var chosen = !names ? all.filter(function (t) { return !/_sections$/.test(t.name); })
        : names.map(function (n) { return all.find(function (t) { return t.name === n; }); }).filter(Boolean);
      // In name order, as Chrome lists tools: with cabinet_arrange listed first the
      // model recovered from an empty selection; in registration order it did not.
      return chosen.slice().sort(function (a, b) { return compareText(a.name, b.name); });
    }
    askForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      var request = question.value.trim();
      if (!request || running) return;
      running = new AbortController();
      askButton.disabled = true; stop.disabled = false; answer.hidden = true;
      modelState.textContent = "Working…";
      var session;
      try {
        var available = assistantTools();
        // The list's description names what its items are, as in the measured wording.
        var about = listDoc && listDoc.list.description ? title + ", " + listDoc.list.description.charAt(0).toLowerCase() + listDoc.list.description.slice(1).replace(/\.$/, "") : title;
        session = await model.create(Object.assign({}, LANG, { initialPrompts: [{ role: "system", content: instructions(about, available) }], signal: running.signal }));
        var outcome = await ask({ session: session, tools: available, request: request, signal: running.signal,
          names: listDoc ? listDoc.items.map(function (i) { return i.name; }) : [],
          onStep: function (step) { if (step.tool) modelState.textContent = "Called " + step.tool + (step.ok ? "." : ": " + step.code + "."); } });
        // The last outcome, with its tool trace, for the page's developer tools.
        if (win.WebMCPlet) win.WebMCPlet.lastAnswer = outcome;
        showAnswer(outcome);
      } catch (error) {
        modelState.textContent = running.signal.aborted ? "Stopped." : "The model stopped: " + (error && error.message);
      } finally {
        if (session) session.destroy();
        running = null; askButton.disabled = false; stop.disabled = true;
      }
    });
    function showAnswer(outcome) {
      if (outcome.status !== "answered") {
        modelState.textContent = {
          cancelled: "Stopped.", timeout: "The model took longer than 30 seconds for one step. Ask again.",
          turn_limit: "The model did not finish within " + MAX_TURNS + " steps. Ask again or search above.",
          error: "The model stopped: " + outcome.message
        }[outcome.status];
        return;
      }
      answer.hidden = false;
      answerRows.replaceChildren();
      outcome.rows.forEach(function (r) { renderRow(answerRows, r); });
      if (!outcome.rows.length) element(doc, "li", {}, answerRows, "No items.");
      generated.textContent = outcome.text !== null ? outcome.text
        : "The generated text named items the tools did not return, so it is withheld.";
      modelState.textContent = outcome.removed ? "The model listed " + outcome.removed + " item(s) the tools did not return; they are omitted." : "Answered.";
    }
    stop.addEventListener("click", function () { if (running) running.abort(); });

    // Fixed elements follow the layout viewport. On a page wider than the screen,
    // or when zoomed, that differs from what the visitor sees, so place the button
    // and dialog in the visual viewport instead.
    function follow() {
      var vv = win.visualViewport;
      var offset = vv && (Math.abs(vv.width - win.innerWidth) > 1 || Math.abs(vv.height - win.innerHeight) > 1 || vv.offsetLeft || vv.offsetTop);
      if (options.mode !== "banner") {
        if (offset) {
          host.style.setProperty("left", (vv.offsetLeft + vv.width - host.offsetWidth - 16) + "px", "important");
          host.style.setProperty("top", (vv.offsetTop + vv.height - host.offsetHeight - 16) + "px", "important");
          host.style.setProperty("right", "auto", "important"); host.style.setProperty("bottom", "auto", "important");
        } else {
          host.style.setProperty("left", "auto", "important"); host.style.setProperty("top", "auto", "important");
          host.style.setProperty("right", "16px", "important"); host.style.setProperty("bottom", "16px", "important");
        }
      }
      if (offset) {
        dialog.style.margin = "0"; dialog.style.position = "fixed";
        dialog.style.width = Math.min(880, vv.width - 16) + "px"; dialog.style.maxHeight = (vv.height - 16) + "px";
        dialog.style.left = (vv.offsetLeft + (vv.width - Math.min(880, vv.width - 16)) / 2) + "px";
        dialog.style.top = (vv.offsetTop + 8) + "px";
      } else ["margin", "position", "width", "maxHeight", "left", "top"].forEach(function (k) { dialog.style[k] = ""; });
    }
    if (win.visualViewport) {
      win.visualViewport.addEventListener("resize", follow);
      win.visualViewport.addEventListener("scroll", follow);
    }
    win.requestAnimationFrame(follow);

    trigger.addEventListener("click", function () { dialog.showModal(); follow(); query.focus(); prepare(); });
    close.addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("close", function () { if (running) running.abort(); trigger.focus(); });
    form.addEventListener("submit", function (event) {
      event.preventDefault(); current.query = query.value; current.section = section.value; run(false);
    });
    section.addEventListener("change", function () { current.query = query.value; current.section = section.value; run(false); });
    more.addEventListener("click", function () { run(true); });
    hide.addEventListener("click", function () {
      try { win.localStorage.setItem(hiddenKey(win), "1"); } catch (_) { /* Hidden for this page view only. */ }
      dialog.close(); host.remove();
    });
    return host;
  }

  // <script src="webmcplet.js" data-webmcplet-src="list.json" data-webmcplet-title="Awesome X"
  //   data-webmcplet-prefix="list" data-webmcplet-panel="button|banner|off" data-webmcplet-assistant="on">
  // With a title, the document loads at the first tool call or panel use.
  function autostart(win) {
    var script = win.document && win.document.currentScript;
    if (!script || !script.dataset || !script.dataset.webmcpletSrc) return;
    var data = script.dataset, options = { prefix: data.webmcpletPrefix || "list", title: data.webmcpletTitle };
    var loader = function () { return load(data.webmcpletSrc, win); };
    var source = options.title ? Promise.resolve(loader) : loader().then(function (doc) {
      options.title = doc.list.title; return doc;
    });
    win.WebMCPlet.ready = source.then(function (src) { return register(src, options); }).then(function (result) {
      var mode = data.webmcpletPanel || "button";
      if (mode !== "off") {
        var start = function () {
          result.panel = mount(win, { title: options.title, tools: result.tools, mode: mode, label: data.webmcpletLabel,
            assistant: data.webmcpletAssistant === "on",
            assistantTools: data.webmcpletAssistantTools ? data.webmcpletAssistantTools.split(/[\s,]+/).filter(Boolean) : null });
        };
        if (win.document.body) start(); else win.document.addEventListener("DOMContentLoaded", start);
      }
      return result;
    }).catch(function (error) {
      if (win.console) win.console.warn("WebMCPlet: " + error.message);
      return { registered: [], error: error.code || "list_unavailable" };
    });
  }

  return { RELEASE: RELEASE, VERSION: VERSION, PAGE: PAGE, normalizeUrl: normalizeUrl, validate: validate, create: create,
    tools: tools, register: register, load: load, autostart: autostart, fold: fold,
    assistant: { ask: ask, actionSchema: actionSchema, instructions: instructions, modelSchema: modelSchema, Refs: Refs, namesIn: namesIn },
    mount: mount };
});
