/* Throwaway Prompt API test: runs the PRD journeys through page tools in system Chrome and scores each run.
 *
 * node experiments/prompt-api-m5/run.cjs --site <built site> --maclist <dir with applications.json, categories.json>
 *   --profile <Chrome user-data-dir holding the model> [--runs 5] [--max-turns 8] [--turn-ms 0] [--refs on|off] [--messages arrange] [--out results.json]
 */
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const argv = Object.fromEntries(process.argv.slice(2).join(' ').split('--').filter(Boolean)
  .map(part => part.trim().split(/\s+/)).map(([key, value]) => [key, value]));
const ROOT = path.resolve(__dirname, '../..');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const RUNS = Number(argv.runs || 5), MAX_TURNS = Number(argv['max-turns'] || 8), TURN_MS = Number(argv['turn-ms'] || 0);
const REFS = argv.refs === 'on';
// --messages arrange: the empty_selection message names the tool that selects.
const MESSAGES = argv.messages === 'arrange'
  ? { empty_selection: 'Nothing is selected. Call cabinet_arrange with ids from cabinet_find and its revision, then call cabinet_compare.' } : null;
const PORT = 8790, CDP = 9334;

const JOURNEYS = [
  { id: 'video-compare', list: 'Awesome Open*, a catalog of Open*-named projects', path: '/',
    request: 'Find a video editor and compare two.', expected: ['cabinet_find', 'video edit'] },
  { id: 'markdown-editor', list: 'open-source-mac-os-apps, a list of open-source macOS apps', path: '/maclist/',
    request: 'Find a Markdown editor.', expected: ['list_find', 'markdown edit'] },
  { id: 'family-photos', list: 'Awesome Open*, a catalog of Open*-named projects', path: '/',
    request: 'Manage family photos on my own server.' }
];

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2' };
function serve() {
  const mounts = [['/maclist/search.js', path.join(ROOT, 'site/search.js')],
    ['/maclist/applications.json', path.join(argv.maclist, 'applications.json')],
    ['/maclist/categories.json', path.join(argv.maclist, 'categories.json')],
    ['/maclist/', path.join(__dirname, 'maclist') + '/'], ['/', path.resolve(argv.site) + '/']];
  return http.createServer((req, res) => {
    let url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (url.endsWith('/')) url += 'index.html';
    const [prefix, target] = mounts.find(([p]) => p.endsWith('/') ? url.startsWith(p) : url === p);
    const file = prefix.endsWith('/') ? path.join(target, url.slice(prefix.length)) : target;
    fs.readFile(file, (error, body) => {
      if (error) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); res.end(body);
    });
  }).listen(PORT, '127.0.0.1');
}

async function chrome() {
  // Started directly: Playwright's launch flags disable the component updates the model depends on.
  const child = spawn(CHROME, ['--user-data-dir=' + path.resolve(argv.profile), '--remote-debugging-port=' + CDP,
    '--no-first-run', '--no-default-browser-check', '--enable-blink-features=WebMCP', 'about:blank'], { stdio: 'ignore' });
  for (let i = 0; i < 60; i++) {
    try { return { child, browser: await chromium.connectOverCDP('http://127.0.0.1:' + CDP) }; }
    catch (_) { await new Promise(r => setTimeout(r, 500)); }
  }
  throw new Error('Chrome did not open its debugging port');
}

async function open(context, journey) {
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:' + PORT + journey.path);
  await page.waitForFunction(() => document.modelContext && document.modelContext.getTools().then(t => t.length > 0), null, { timeout: 30000 });
  await page.waitForFunction(async () => (await document.modelContext.getTools()).length >= 2);
  await page.addScriptTag({ path: path.join(__dirname, 'controller.js') });
  return page;
}

// The list's items as {id, name}, read from the page itself.
function items(page) {
  return page.evaluate(() => window.__listItems ||
    JSON.parse(document.getElementById('catalog-data').textContent).projects.map(p => ({ id: p.id, name: p.name })));
}

// Every ID a search for `query` returns through the page's own tool, across pages.
function expectedIds(page, [tool, query]) {
  return page.evaluate(async ({ tool, query }) => {
    const t = (await document.modelContext.getTools()).find(x => x.name === tool), ids = [];
    for (let offset = 0; ; offset += 12) {
      let r = await document.modelContext.executeTool(t, { query, offset });
      if (typeof r === 'string') r = JSON.parse(r);
      if (!r.ok) throw new Error(tool + ' failed: ' + JSON.stringify(r));
      const rows = r.projects || r.items; ids.push(...rows.map(x => x.id));
      if (ids.length >= r.total || !rows.length) return ids;
    }
  }, { tool, query });
}

function escape(text) { return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

// Item names written in the answer, matched case-sensitively as whole words
// outside URLs. Hyphens join words, so a project named "open" is not found in
// "open-source" or a slug such as open-video-editor.
function mentions(text, list) {
  text = text.replace(/\b(?:https?:\/\/|github\.com\/)\S+/g, ' ');
  return list.filter(item => item.name.length >= 4 &&
    new RegExp('(^|[^\\p{L}\\p{N}-])' + escape(item.name) + '(?![\\p{L}\\p{N}-])', 'u').test(text));
}

function score(journey, trace, list, expected) {
  const known = new Set(list.map(i => i.id)), returned = new Set();
  const collect = value => {
    if (typeof value === 'string') { if (known.has(value)) returned.add(value); }
    else if (value && typeof value === 'object') Object.values(value).forEach(collect);
  };
  const calls = [];
  for (const turn of trace.turns) {
    if (turn.invalid) { turn.valid = false; continue; }
    if (turn.action.action === 'call') {
      if (turn.result && turn.result.ok) collect(turn.result);
      turn.valid = Boolean(turn.result && turn.result.ok);
      calls.push({ tool: turn.action.tool, args: turn.args, ok: turn.valid, code: turn.result && turn.result.code });
    }
  }
  const answer = trace.answer, checks = {};
  checks.answered = Boolean(answer);
  if (answer) {
    const turn = trace.turns[trace.turns.length - 1];
    checks.idsReturned = answer.ids.every(id => returned.has(id));
    const named = mentions(answer.text, list);
    checks.unreturnedNames = named.filter(i => !returned.has(i.id)).map(i => i.name);
    checks.namedItems = named.map(i => i.name);
    turn.valid = checks.idsReturned && !checks.unreturnedNames.length;
  }
  const ok = calls.filter(c => c.ok);
  if (journey.id === 'video-compare') {
    const editors = new Set(expected);
    const arranged = ok.filter(c => c.tool === 'cabinet_arrange').pop();
    checks.arrangedTwoEditors = Boolean(arranged && arranged.args.ids.length === 2 && arranged.args.ids.every(id => editors.has(id)));
    checks.compared = Boolean(arranged && ok.slice(ok.indexOf(arranged) + 1).some(c => c.tool === 'cabinet_compare'));
    checks.pass = checks.answered && checks.idsReturned && !checks.unreturnedNames.length && checks.arrangedTwoEditors && checks.compared;
  } else if (journey.id === 'markdown-editor') {
    checks.searched = ok.some(c => c.tool === 'list_find');
    checks.answeredEditor = Boolean(answer && answer.ids.some(id => expected.includes(id)));
    checks.pass = checks.answered && checks.searched && checks.idsReturned && !checks.unreturnedNames.length && checks.answeredEditor;
  } else {
    checks.searched = ok.some(c => c.tool === 'cabinet_find');
    checks.noIds = Boolean(answer && answer.ids.length === 0);
    checks.pass = checks.answered && checks.searched && checks.noIds && !checks.namedItems.length;
  }
  const actions = trace.turns.length, valid = trace.turns.filter(t => t.valid).length;
  return { calls, checks, actions, valid, peakUsage: Math.max(trace.systemUsage, ...trace.turns.map(t => t.usageAfter || 0)) };
}

(async () => {
  for (const key of ['site', 'maclist', 'profile']) if (!argv[key]) throw new Error('--' + key + ' is required');
  const server = serve(), { child, browser } = await chrome();
  const context = browser.contexts()[0];
  const report = { started: new Date().toISOString(), chrome: browser.version(), runs: RUNS, maxTurns: MAX_TURNS, turnMs: TURN_MS, refs: REFS, messages: MESSAGES,
    sourceSha: null, maclistSha: (fs.readFileSync(path.join(argv.maclist, 'sha.txt'), 'utf8') || '').trim(),
    model: JSON.parse(fs.readFileSync(path.join(argv.profile, 'OptGuideOnDeviceModel',
      fs.readdirSync(path.join(argv.profile, 'OptGuideOnDeviceModel')).find(d => !d.startsWith('.')), 'manifest.json'), 'utf8')),
    journeys: {} };
  try {
    for (const journey of JOURNEYS) {
      const probe = await open(context, journey);
      if (!report.info) report.info = await probe.evaluate(() => window.__modelInfo());
      if (journey.path === '/') report.sourceSha = await probe.locator('#specimen-cabinet').getAttribute('data-source-sha');
      const list = await items(probe), expected = journey.expected ? await expectedIds(probe, journey.expected) : [];
      await probe.close();
      const runs = [];
      for (let run = 0; run < RUNS; run++) {
        const page = await open(context, journey);
        const trace = await page.evaluate(args => window.__runJourney(args), { list: journey.list, request: journey.request, maxTurns: MAX_TURNS, turnMs: TURN_MS, refs: REFS, messages: MESSAGES, messages: MESSAGES });
        const result = score(journey, trace, list, expected);
        runs.push({ ...result, trace });
        console.log([journey.id, run + 1, result.checks.pass ? 'PASS' : 'FAIL', result.valid + '/' + result.actions + ' valid',
          (trace.totalMs / 1000).toFixed(1) + ' s', 'peak ' + result.peakUsage + '/' + trace.contextWindow,
          result.calls.map(c => c.tool.replace(/^(cabinet|list)_/, '') + (c.args.query !== undefined ? '(' + JSON.stringify(c.args.query) + ')' : '') + (c.ok ? '' : '!' + c.code)).join(' '),
          trace.error || ''].join(' | '));
        await page.close();
      }
      report.journeys[journey.id] = { request: journey.request, expected, runs };
    }
  } finally {
    await browser.close().catch(() => {}); child.kill(); server.close();
  }
  const all = Object.values(report.journeys).flatMap(j => j.runs);
  report.summary = Object.fromEntries(Object.entries(report.journeys).map(([id, j]) => [id, {
    passed: j.runs.filter(r => r.checks.pass).length + '/' + j.runs.length,
    validActions: j.runs.reduce((n, r) => n + r.valid, 0) + '/' + j.runs.reduce((n, r) => n + r.actions, 0),
    medianSeconds: median(j.runs.map(r => r.trace.totalMs / 1000)),
    medianTurnMs: median(j.runs.flatMap(r => r.trace.turns.map(t => t.ms))),
    peakUsage: Math.max(...j.runs.map(r => r.peakUsage)) }]));
  report.summary.all = { validActions: all.reduce((n, r) => n + r.valid, 0) + '/' + all.reduce((n, r) => n + r.actions, 0),
    contextWindow: all[0] && all[0].trace.contextWindow };
  const out = argv.out || path.join(__dirname, 'results', report.started.replace(/[:.]/g, '-') + '.json');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(report, null, 1) + '\n');
  console.log(JSON.stringify(report.summary, null, 1));
  console.log('Wrote ' + path.relative(process.cwd(), out));
})().catch(error => { console.error(error); process.exit(1); });

function median(values) {
  const sorted = values.slice().sort((a, b) => a - b), mid = sorted.length >> 1;
  return sorted.length ? Math.round((sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2) * 10) / 10 : null;
}
