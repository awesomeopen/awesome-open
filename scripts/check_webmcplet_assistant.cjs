/* The opt-in WebMCPlet assistant with Chrome's real on-device model, through the panel,
 * on the PRD's three journeys, a search the shared matcher misses whole, and two
 * follow-up conversations. Pass: each journey passes at least 17 of 20 runs and no
 * answer shows an item the tools did not return (PRD/2026-11-06_WebMCPlet-research.md).
 *
 * SITE_URL=<served Awesome Open build> node scripts/check_webmcplet_assistant.cjs \
 *   --profile <Chrome profile holding the model> --mac-list <mac list.json> [--runs 20] [--journeys id,id] [--out report.json]
 *
 * Chrome starts directly with the profile: Playwright's launch flags disable the
 * component updates the model depends on. Create the profile's model with one click
 * in the panel's "Download the model" first. Use system Chrome (CHROME_PATH).
 */
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const argv = {};
process.argv.slice(2).forEach((arg, i, all) => { if (arg.startsWith('--')) argv[arg.slice(2)] = all[i + 1]; });
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const AO = new URL(process.env.SITE_URL || 'http://127.0.0.1:8000/').href;
const MAC = process.env.MAC_URL || 'https://serhii-londar.github.io/open-source-mac-os-apps/';
const RUNS = Number(argv.runs || 20), CDP = 9336, PANEL = '[data-webmcplet-host]';
const SCRIPT = path.join(__dirname, '..', 'webmcplet', 'webmcplet.js');

const JOURNEYS = [
  { id: 'video-compare', page: 'ao', request: 'Find a video editor and compare two.', expected: ['cabinet_find', 'video edit', 'projects'] },
  { id: 'markdown-editor', page: 'mac', request: 'Find a Markdown editor.', expected: ['list_find', 'markdown edit', 'items'] },
  { id: 'family-photos', page: 'ao', request: 'Manage family photos on my own server.' },
  // Owner's question, 2026-11-15: the whole phrase matches nothing; "NotebookLM" alone does.
  { id: 'notebooklm', page: 'ao', request: 'Find a NotebookLM alternative.', expected: ['cabinet_find', 'notebooklm', 'projects'] },
  // Follow-ups: the second request refers to the first answer.
  { id: 'video-mit', page: 'ao', request: ['Find a video editor.', 'Which of those has an MIT license?'], expected: ['cabinet_find', 'video edit', 'projects'] },
  { id: 'markdown-first', page: 'mac', request: ['Find a Markdown editor.', 'Tell me more about the first one.'] }
];

async function open(context, journey) {
  const page = await context.newPage();
  // The Catalog enables the assistant with the Cabinet's tools; the same attributes keep
  // older builds comparable (the first of duplicate attributes wins, with equal values).
  if (journey.page === 'ao') {
    await page.route(AO, async route => {
      const response = await route.fetch();
      route.fulfill({ response, body: (await response.text()).replace('data-webmcplet-title=',
        'data-webmcplet-assistant="on" data-webmcplet-assistant-tools="cabinet_arrange cabinet_compare cabinet_find cabinet_inspect" data-webmcplet-title=') });
    });
    await page.goto(AO);
  }
  else {
    await page.route(MAC + 'webmcplet/**', route => route.fulfill({ path: route.request().url().endsWith('.js') ? SCRIPT : argv['mac-list'] }));
    await page.goto(MAC, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => new Promise(resolve => {
      const script = document.createElement('script');
      script.src = 'webmcplet/webmcplet.js'; script.dataset.webmcpletSrc = 'webmcplet/list.json'; script.dataset.webmcpletAssistant = 'on';
      script.onload = () => window.WebMCPlet.ready.then(resolve); document.head.append(script);
    }));
  }
  await page.evaluate(() => window.WebMCPlet.ready);
  return page;
}

// Names of every item a search returns through the page's own tool, across pages.
function expectedNames(page, [tool, query, key]) {
  return page.evaluate(async ({ tool, query, key }) => {
    const t = (window.webmcpletTools || []).concat((await window.WebMCPlet.ready).tools).find(x => x.name === tool), names = [];
    for (let offset = 0; ; offset += 12) {
      const r = await t.execute({ query, offset });
      names.push(...r[key].map(x => x.name));
      if (names.length >= r.total || !r[key].length) return names;
    }
  }, { tool, query, key });
}

async function ask(page, request) {
  const panel = page.locator(PANEL);
  // A follow-up asks in the dialog that is still open.
  if (!await page.evaluate(sel => document.querySelector(sel).shadowRoot.querySelector('dialog').open, PANEL)) await panel.locator('button.trigger').click();
  await panel.getByLabel('Question').waitFor({ timeout: 30000 });
  await panel.getByLabel('Question').fill(request);
  const started = Date.now();
  await panel.getByRole('button', { name: 'Send', exact: true }).click();
  await page.waitForFunction(sel => {
    const root = document.querySelector(sel).shadowRoot;
    return !root.querySelector('button.primary[type=submit]:disabled') && /Answered|omitted|Stopped|stopped|did not finish|longer than/.test(root.querySelector('.state').textContent);
  }, PANEL, { timeout: 300000, polling: 250 });
  return page.evaluate(({ sel, started }) => {
    const root = document.querySelector(sel).shadowRoot, answer = root.querySelector('div:has(> ol[aria-label="Items in the answer"])');
    return { seconds: (Date.now() - started) / 1000, state: root.querySelector('.state').textContent,
      answered: Boolean(answer && !answer.hidden),
      rows: [...root.querySelectorAll('ol[aria-label="Items in the answer"] li a, ol[aria-label="Items in the answer"] li strong')].map(a => a.textContent),
      text: root.querySelector('p.generated').textContent,
      trace: window.WebMCPlet.lastAnswer ? window.WebMCPlet.lastAnswer.trace : null,
      selection: [...document.querySelectorAll('#cabinet-selection li > a')].map(a => a.textContent),
      activity: document.querySelector('#cabinet-activity') ? document.querySelector('#cabinet-activity').textContent : '' };
  }, { sel: PANEL, started });
}

function score(journey, result, expected, earlier, licenses) {
  const withheld = /withheld/.test(result.text);
  if (!result.answered) return { pass: false, reason: result.state };
  if (journey.id === 'notebooklm') {
    const found = result.rows.some(n => expected.includes(n));
    return { pass: found && !withheld, reason: !found ? 'rows: ' + result.rows.join(', ') : withheld ? 'text withheld' : 'ok' };
  }
  if (journey.id === 'video-mit') {
    const mit = result.rows.length > 0 && result.rows.every(n => expected.includes(n) && licenses[n] === 'MIT');
    return { pass: mit && !withheld, reason: !mit ? 'rows: ' + result.rows.map(n => n + ' (' + licenses[n] + ')').join(', ') : withheld ? 'text withheld' : 'ok' };
  }
  if (journey.id === 'markdown-first') {
    const same = earlier.rows.length > 0 && result.rows[0] === earlier.rows[0];
    return { pass: same && !withheld, reason: !same ? 'first: ' + earlier.rows[0] + '; rows: ' + result.rows.join(', ') : withheld ? 'text withheld' : 'ok' };
  }
  if (journey.id === 'video-compare') {
    const two = result.selection.length === 2 && result.selection.every(n => expected.includes(n));
    const compared = /Assistant · cabinet_compare · completed/.test(result.activity);
    return { pass: two && compared && !withheld, reason: !two ? 'selection: ' + result.selection.join(', ') : !compared ? 'no compare' : withheld ? 'text withheld' : 'ok' };
  }
  if (journey.id === 'markdown-editor') {
    const editor = result.rows.some(n => expected.includes(n));
    return { pass: editor && !withheld, reason: !editor ? 'rows: ' + result.rows.join(', ') : withheld ? 'text withheld' : 'ok' };
  }
  return { pass: !result.rows.length && !withheld, reason: result.rows.length ? 'rows: ' + result.rows.join(', ') : withheld ? 'text withheld' : 'ok' };
}

(async () => {
  if (!argv.profile || !argv['mac-list']) throw new Error('--profile and --mac-list are required');
  const child = spawn(CHROME, ['--user-data-dir=' + path.resolve(argv.profile), '--remote-debugging-port=' + CDP,
    '--no-first-run', '--no-default-browser-check', '--enable-blink-features=WebMCP', 'about:blank'], { stdio: 'ignore' });
  let browser;
  for (let i = 0; i < 60 && !browser; i++) {
    try { browser = await chromium.connectOverCDP('http://127.0.0.1:' + CDP); } catch (_) { await new Promise(r => setTimeout(r, 500)); }
  }
  const context = browser.contexts()[0];
  const report = { started: new Date().toISOString(), chrome: browser.version(), runs: RUNS, site: AO, mac: MAC, journeys: {} };
  try {
    for (const journey of JOURNEYS.filter(j => !argv.journeys || argv.journeys.split(',').includes(j.id))) {
      const probe = await open(context, journey);
      const expected = journey.expected ? await expectedNames(probe, journey.expected) : [];
      const licenses = journey.page === 'ao' ? await probe.evaluate(async () =>
        Object.fromEntries((await (await fetch('catalog.json')).json()).projects.map(p => [p.name, (p.github || {}).license || null]))) : {};
      await probe.close();
      const runs = [];
      for (let run = 0; run < RUNS; run++) {
        // Each run: a fresh page, an empty Cabinet and no stored dismissal.
        const page = await open(context, journey);
        const requests = [].concat(journey.request), steps = [];
        for (const request of requests) steps.push(await ask(page, request));
        const result = steps[steps.length - 1];
        const verdict = steps.length > 1 && !steps[0].answered ? { pass: false, reason: 'first: ' + steps[0].state }
          : score(journey, result, expected, steps[0], licenses);
        if (steps.length > 1) result.earlier = steps.slice(0, -1);
        runs.push({ ...result, ...verdict });
        console.log([journey.id, run + 1, verdict.pass ? 'PASS' : 'FAIL', result.seconds.toFixed(1) + ' s', verdict.reason].join(' | '));
        await page.close();
      }
      const passed = runs.filter(r => r.pass).length;
      report.journeys[journey.id] = { request: journey.request, expected, passed, threshold: 17, met: passed >= 17, runs };
    }
  } finally {
    await browser.close().catch(() => {}); child.kill();
  }
  report.met = Object.values(report.journeys).every(j => j.met);
  const out = argv.out || 'tmp/site-qa/webmcplet-assistant.json';
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(report, null, 1) + '\n');
  console.log(JSON.stringify(Object.fromEntries(Object.entries(report.journeys).map(([id, j]) => [id, j.passed + '/' + RUNS]))), 'threshold met:', report.met);
})().catch(error => { console.error(error); process.exitCode = 1; });
