/* Throwaway WebMCP tools over the Mac list's applications.json, shaped like cabinet_find. */
(async function () {
  "use strict";
  const PAGE = 12;
  const status = document.getElementById('status');
  const [apps, categories] = await Promise.all(['applications.json', 'categories.json']
    .map(file => fetch(file).then(response => response.json())));
  const titles = new Map(categories.categories.map(c => [c.id, c.title]));
  // Identity is the normalized repository URL, so cross-listed entries are one item.
  const items = new Map();
  for (const app of apps.applications) {
    const id = app.repo_url.trim().replace(/^https?:\/\//, '').replace(/\/+$/, '').toLowerCase();
    const sections = (app.categories || []).map(c => titles.get(c) || c);
    const item = items.get(id);
    if (item) { item.sections = [...new Set([...item.sections, ...sections])]; continue; }
    items.set(id, { id, name: app.title, description: app.short_description || '', sections,
      url: app.repo_url, official_site: app.official_site || null, languages: app.languages || [] });
  }
  const all = [...items.values()];
  window.__listItems = all.map(i => ({ id: i.id, name: i.name }));
  const failure = (code, message) => ({ ok: false, code, message });
  function parse(args) { return typeof args === 'string' ? JSON.parse(args) : (args || {}); }
  function find(args) {
    const keys = Object.keys(args);
    if (keys.some(k => !['query', 'offset'].includes(k)) || typeof args.query !== 'string' || args.query.length > 160)
      return failure('invalid_arguments', 'Send {query, offset}: query is a string of at most 160 characters.');
    const offset = args.offset === undefined ? 0 : args.offset;
    if (!Number.isInteger(offset) || offset < 0) return failure('invalid_offset', 'offset must be a whole number from 0.');
    const rows = OpenSearch.results(all, args.query);
    const page = rows.slice(offset, offset + PAGE).map(r => ({ id: r.project.id, name: r.project.name,
      description: r.project.description, sections: r.project.sections, matched_fields: r.fields }));
    const result = { ok: true, query: args.query, offset, total: rows.length, items: page };
    if (!rows.length) result.message = 'No match in this list of ' + all.length + ' macOS apps.';
    return result;
  }
  function get(args) {
    if (Object.keys(args).join() !== 'id' || !items.has(args.id))
      return failure('invalid_id', 'Send {id} with an id returned by list_find.');
    return { ok: true, item: items.get(args.id) };
  }
  const definitions = [
    ['list_find', 'Search this list of open-source macOS apps. Every word must appear in an app’s name or description. Returns 12 results from offset, strongest matching field first, with matched_fields and total. total 0 means no app in this list matches.',
      { query: { type: 'string', maxLength: 160 }, offset: { type: 'integer', minimum: 0 } }, ['query'], find],
    ['list_get', 'Return one app’s recorded fields: name, description, sections, repository URL, official site and languages. Missing values are null.',
      { id: { type: 'string', maxLength: 200 } }, ['id'], get]
  ];
  for (const [name, description, properties, required, run] of definitions) {
    await document.modelContext.registerTool({ name, description,
      inputSchema: { type: 'object', properties, required, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      execute: args => { try { return run(parse(args)); } catch (_) { return failure('invalid_arguments', 'Arguments must be a JSON object.'); } }
    });
  }
  status.textContent = all.length + ' apps; two tools registered.';
})();
