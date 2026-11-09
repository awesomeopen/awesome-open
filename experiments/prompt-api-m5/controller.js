/* Throwaway Prompt API controller: one JSON action per turn, dispatched only to registered page tools. */
(function () {
  "use strict";
  const LANG = { expectedInputs: [{ type: 'text', languages: ['en'] }], expectedOutputs: [{ type: 'text', languages: ['en'] }] };

  function schemaOf(tool) {
    return typeof tool.inputSchema === 'string' ? JSON.parse(tool.inputSchema) : tool.inputSchema;
  }

  // Chrome 156 rejects a responseConstraint containing uniqueItems with
  // NotSupportedError; the tool still rejects duplicate IDs itself.
  function constrainable(schema) {
    if (Array.isArray(schema)) return schema.map(constrainable);
    if (!schema || typeof schema !== 'object') return schema;
    return Object.fromEntries(Object.entries(schema).filter(([key]) => key !== 'uniqueItems')
      .map(([key, value]) => [key, constrainable(value)]));
  }

  // Structured output restricts each turn to a call of a registered tool with its
  // own argument schema, or a final answer.
  function actionSchema(tools, refs) {
    return { anyOf: [
      ...tools.map(tool => ({ type: 'object', additionalProperties: false, required: ['action', 'tool', 'args'],
        properties: { action: { type: 'string', enum: ['call'] }, tool: { type: 'string', enum: [tool.name] }, args: constrainable(refs ? refSchema(schemaOf(tool)) : schemaOf(tool)) } })),
      { type: 'object', additionalProperties: false, required: ['action', 'text', 'ids'],
        properties: { action: { type: 'string', enum: ['answer'] }, text: { type: 'string' },
          ids: { type: 'array', items: refs ? REF : { type: 'string' } } } }
    ] };
  }

  // Short refs stand in for item IDs in everything the model reads and writes;
  // the controller maps them back before a tool call. Unknown refs pass through
  // unchanged, so the tool rejects them.
  function Refs() {
    const toRef = new Map(), toId = new Map();
    function ref(id) {
      if (!toRef.has(id)) { const r = 'r' + (toRef.size + 1); toRef.set(id, r); toId.set(r, id); }
      return toRef.get(id);
    }
    const id = r => toId.has(r) ? toId.get(r) : r;
    function hide(value, key) {
      if (key === 'id' && typeof value === 'string') return ref(value);
      if (key === 'ids' && Array.isArray(value)) return value.map(v => typeof v === 'string' ? ref(v) : v);
      if (Array.isArray(value)) return value.map(v => hide(v));
      if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, hide(v, k)]));
      return value;
    }
    function reveal(args) {
      const out = { ...args };
      if (typeof out.id === 'string') out.id = id(out.id);
      if (Array.isArray(out.ids)) out.ids = out.ids.map(id);
      return out;
    }
    return { hide, reveal, id };
  }

  const REF = { type: 'string', pattern: '^r[0-9]{1,3}$' };
  function refSchema(schema) {
    if (!schema.properties) return schema;
    const properties = { ...schema.properties };
    if (properties.id) properties.id = REF;
    if (properties.ids) properties.ids = { ...properties.ids, items: REF };
    return { ...schema, properties };
  }

  function instructions(list, tools, refs) {
    return [
      'You help a visitor find items in ' + list + '. You can only read this page through its tools.',
      'Each turn, reply with one JSON action.',
      ...(refs ? ['Items are identified by short refs such as r1. Use these refs in tool arguments and in ids.'] : []),
      'To call a tool: {"action":"call","tool":"<name>","args":{...}}. The next message gives its result.',
      'To finish: {"action":"answer","text":"<answer for the visitor>","ids":["<id>", ...]}.',
      'Rules:',
      '- Search with short keyword queries. A result must contain every word of the query, so long phrases often find nothing; try fewer or simpler words.',
      '- State only facts from tool results. A null value is Unknown.',
      '- ids lists the items your answer presents as fitting the request, copied exactly from tool results.',
      '- If no item fits, say that this list has no match, leave ids empty and name no item.',
      '- If a tool returns ok:false, follow its message.',
      'Tools:',
      ...tools.map(tool => '- ' + tool.name + ': ' + tool.description + ' Arguments: ' + JSON.stringify(refs ? refSchema(schemaOf(tool)) : schemaOf(tool)))
    ].join('\n');
  }

  function usage(session) {
    return session.contextUsage !== undefined ? session.contextUsage : session.inputUsage;
  }

  async function call(tools, name, args) {
    const tool = tools.find(t => t.name === name);
    const result = await document.modelContext.executeTool(tool, args);
    return typeof result === 'string' ? JSON.parse(result) : result;
  }

  // Runs one request to completion or to the turn limit. Returns the full trace.
  window.__runJourney = async function ({ list, request, maxTurns, turnMs, refs: useRefs, messages }) {
    const tools = await document.modelContext.getTools(), refs = useRefs ? Refs() : null;
    const trace = { request, refs: Boolean(refs), turnMs, turns: [], answer: null, error: null };
    const started = performance.now();
    const created = performance.now();
    const session = await LanguageModel.create({ ...LANG, initialPrompts: [{ role: 'system', content: instructions(list, tools, refs) }] });
    trace.createMs = Math.round(performance.now() - created);
    trace.contextWindow = session.contextWindow !== undefined ? session.contextWindow : session.inputQuota;
    trace.systemUsage = usage(session);
    const constraint = actionSchema(tools, refs);
    let input = request;
    try {
      for (let turn = 0; turn < maxTurns; turn++) {
        const before = usage(session), t0 = performance.now();
        const options = { responseConstraint: constraint };
        if (turnMs) options.signal = AbortSignal.timeout(turnMs);
        const raw = await session.prompt(input, options);
        const record = { input: input.length > 400 ? input.slice(0, 400) + '…' : input, inputChars: input.length,
          raw, ms: Math.round(performance.now() - t0), usageBefore: before, usageAfter: usage(session) };
        trace.turns.push(record);
        let action;
        try { action = JSON.parse(raw); } catch (_) { record.invalid = 'malformed_json'; input = 'That was not valid JSON. Reply with one JSON action.'; continue; }
        record.action = action;
        if (action.action === 'answer') {
          trace.answer = refs ? { ...action, refs: action.ids, ids: action.ids.map(refs.id) } : action; break;
        }
        if (action.action !== 'call' || !tools.some(t => t.name === action.tool)) {
          record.invalid = 'unsupported_action'; input = 'Unsupported action. Call one of the listed tools or answer.'; continue;
        }
        record.args = refs ? refs.reveal(action.args || {}) : action.args || {};
        const result = await call(tools, action.tool, record.args);
        record.result = result;
        // Test-only: an alternative recovery message, shown to the model in place of the tool's.
        const shown = messages && result.ok === false && messages[result.code] ? { ...result, message: messages[result.code] } : result;
        if (shown !== result) record.shownMessage = shown.message;
        input = 'Result of ' + action.tool + ': ' + JSON.stringify(refs ? refs.hide(shown) : shown);
      }
    } catch (error) {
      trace.error = error.name + ': ' + error.message;
    }
    trace.totalMs = Math.round(performance.now() - started);
    trace.finalUsage = usage(session);
    session.destroy();
    return trace;
  };

  window.__modelInfo = async function () {
    const info = { availability: await LanguageModel.availability(LANG) };
    if (typeof LanguageModel.params === 'function') info.params = await LanguageModel.params();
    return info;
  };
})();
