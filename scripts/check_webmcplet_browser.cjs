/* WebMCPlet on Awesome Open* and on the live open-source-mac-os-apps page: the same
 * webmcplet/webmcplet.js, its tools, and its panel's keyboard, touch, focus and
 * silencing behavior. The Mac list page gets the script injected in this browser only.
 *
 * SITE_URL=<served Awesome Open build> node scripts/check_webmcplet_browser.cjs <mac list.json>
 * SITE_URL=<served Awesome Open build> node scripts/check_webmcplet_browser.cjs --awesome-open-only
 *
 * Build the Mac list with `node webmcplet/build.cjs markdown` from its README.
 * MAC_URL overrides the Mac list page, https://serhii-londar.github.io/open-source-mac-os-apps/.
 * The assistant runs against a scripted LanguageModel stand-in; experiments/prompt-api-m5
 * and scripts/check_webmcplet_assistant.cjs cover the real model.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const args = process.argv.slice(2);
const AO_ONLY = args.includes('--awesome-open-only');
const macList = args.find(a => !a.startsWith('--'));
if (!AO_ONLY && !macList) { console.error('Usage: check_webmcplet_browser.cjs <mac list.json> | --awesome-open-only'); process.exit(1); }
const SCRIPT = path.join(__dirname, '..', 'webmcplet', 'webmcplet.js');
const AO = new URL(process.env.SITE_URL || 'http://127.0.0.1:8000/').href.replace(/\/?$/, '/');
const MAC = process.env.MAC_URL || 'https://serhii-londar.github.io/open-source-mac-os-apps/';
const PANEL = '[data-webmcplet-host]';

// Serves the script and list at <page>/webmcplet/ for this browser context only, then adds the tag.
async function inject(context, page, base, listPath, attributes = {}) {
  const prefix = new URL('webmcplet/', base).href;
  await context.route(prefix + '**', route => {
    const file = route.request().url().endsWith('/webmcplet.js') ? SCRIPT : listPath;
    route.fulfill({ path: file, contentType: file.endsWith('.js') ? 'text/javascript' : 'application/json' });
  });
  await page.goto(base, { waitUntil: 'domcontentloaded' });
  return page.evaluate(({ src, attributes }) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src + 'webmcplet.js'; script.dataset.webmcpletSrc = src + 'list.json';
    Object.assign(script.dataset, attributes);
    script.onload = () => window.WebMCPlet.ready.then(resolve); script.onerror = reject; document.head.append(script);
  }), { src: prefix, attributes });
}

async function openAwesome(context, page) {
  await page.goto(AO);
  return page.evaluate(() => window.WebMCPlet.ready);
}

// Awesome Open with its published tag plus extra data attributes, in this context only.
async function withAttributes(context, attributes) {
  await context.route(AO, async route => {
    const response = await route.fetch();
    route.fulfill({ response, body: (await response.text()).replace('data-webmcplet-title=', attributes + ' data-webmcplet-title=') });
  });
}

function call(page, name, args) {
  return page.evaluate(async ({ name, args }) => {
    const tool = (await document.modelContext.getTools()).find(t => t.name === name);
    const result = await document.modelContext.executeTool(tool, args);
    return typeof result === 'string' ? JSON.parse(result) : result;
  }, { name, args });
}

async function every(page, name, args, key) {
  const rows = [];
  for (;;) {
    const result = await call(page, name, { ...args, offset: rows.length });
    assert.equal(result.ok, true, JSON.stringify(result));
    rows.push(...result[key]);
    if (rows.length >= result.total || !result[key].length) return rows;
  }
}

// The focused element, through the panel's shadow root.
function focused(page) {
  return page.evaluate(() => {
    let el = document.activeElement;
    while (el && el.shadowRoot && el.shadowRoot.activeElement) el = el.shadowRoot.activeElement;
    return el ? { tag: el.tagName.toLowerCase(), id: el.id, text: (el.textContent || '').trim().slice(0, 40),
      inDialog: Boolean(el.closest && el.closest('dialog')), outline: getComputedStyle(el).outlineStyle + ' ' + getComputedStyle(el).outlineWidth } : null;
  });
}

const dialogOpen = page => page.evaluate(sel => document.querySelector(sel).shadowRoot.querySelector('dialog').open, PANEL);

// A LanguageModel stand-in. `script(input)` returns the next action for a prompt.
function stubModel(state, script) {
  return `(() => {
    const script = ${script};
    window.LanguageModel = {
      availability: async () => window.__modelState || ${JSON.stringify(state)},
      create: async options => {
        window.__created = (window.__created || 0) + 1;
        if (options.monitor) { const target = new EventTarget(); options.monitor(target); target.dispatchEvent(Object.assign(new Event('downloadprogress'), { loaded: 1 })); window.__modelState = 'available'; }
        return { prompt: async input => JSON.stringify(script(input)), destroy() {} };
      }
    };
  })()`;
}

// Keyboard, focus, touch and silencing checks that hold on every list page.
async function panelChecks(browser, label, open, report) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } }), page = await context.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await open(context, page);
  const trigger = page.locator(PANEL).locator('button.trigger');
  assert.equal(await trigger.textContent(), 'Search this list');
  assert.equal(await dialogOpen(page), false, 'the panel never opens by itself');
  // Keyboard: the button is the page's last tab stop and shows a focus ring; Enter
  // opens; Escape closes and returns focus.
  await page.evaluate(() => { document.activeElement && document.activeElement.blur(); });
  await page.keyboard.press('Shift+Tab');
  const ring = await focused(page);
  assert.equal(ring.text, 'Search this list', 'Shift+Tab from the top reaches the panel button');
  assert.match(ring.outline, /^solid 3px$/, 'focus is visible');
  await page.keyboard.press('Enter');
  assert.equal(await dialogOpen(page), true);
  assert.equal((await focused(page)).id, 'wm-query', 'focus moves to the search field');
  await page.keyboard.type('editor'); await page.keyboard.press('Enter');
  const results = page.locator(PANEL).locator('ol[aria-label="Results"] li');
  await results.first().waitFor();
  assert.ok(await results.count() > 0);
  // A modal dialog makes the page inert: Tab moves through the dialog and may pass to
  // the browser's own controls (seen here as body), never to the page behind it.
  let inside = 0;
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press('Tab');
    const at = await focused(page);
    assert.ok(at.inDialog || at.tag === 'body', 'focus left the dialog for ' + JSON.stringify(at));
    if (at.inDialog) inside++;
  }
  assert.ok(inside > 20);
  await page.keyboard.press('Escape');
  assert.equal(await dialogOpen(page), false);
  assert.equal((await focused(page)).text, 'Search this list', 'focus returns to the button');
  // Visitor dismissal: stored in this browser; the tools stay registered.
  const tools = await page.evaluate(async () => (await document.modelContext.getTools()).length);
  await trigger.click(); await page.locator(PANEL).getByRole('button', { name: 'Hide this button' }).click();
  assert.equal(await page.locator(PANEL).count(), 0);
  await open(context, page);
  assert.equal(await page.locator(PANEL).count(), 0, 'dismissal persists');
  assert.equal(await page.evaluate(async () => (await document.modelContext.getTools()).length), tools, 'tools remain after dismissal');
  assert.deepEqual(errors, []);
  await context.close();
  // Touch at phone width: tap to open and close; the dialog fits the viewport.
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const mobile = await phone.newPage();
  await open(phone, mobile);
  await mobile.locator(PANEL).locator('button.trigger').tap();
  assert.equal(await dialogOpen(mobile), true);
  // Measured against the visual viewport: what the visitor sees, even on a page wider than the screen.
  const fits = await mobile.evaluate(sel => {
    const dialog = document.querySelector(sel).shadowRoot.querySelector('dialog'), box = dialog.getBoundingClientRect(), vv = visualViewport;
    return box.left >= vv.offsetLeft && box.right <= vv.offsetLeft + vv.width && box.top >= vv.offsetTop &&
      box.top < vv.offsetTop + vv.height && dialog.scrollWidth <= dialog.clientWidth;
  }, PANEL);
  assert.equal(fits, true, 'the dialog fits the visible 390px viewport');
  await mobile.screenshot({ path: `tmp/site-qa/webmcplet-${label}-mobile.png` });
  await mobile.locator(PANEL).getByRole('button', { name: 'Close' }).tap();
  assert.equal(await dialogOpen(mobile), false);
  await phone.close();
  report.panel = 'keyboard, focus, touch and dismissal passed';
}

(async () => {
  const options = { headless: true, args: ['--enable-blink-features=WebMCP'] };
  if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
  if (process.env.CHROMIUM_NO_SANDBOX === '1') options.args.push('--no-sandbox');
  const browser = await chromium.launch(options);
  const report = { browser: browser.version(), script: 'webmcplet/webmcplet.js', awesomeOpen: {}, macList: AO_ONLY ? 'skipped' : { url: MAC }, status: 'running' };
  const output = 'tmp/site-qa'; fs.mkdirSync(output, { recursive: true });
  try {
    // Awesome Open: the list tools sit beside the Cabinet's and agree with its search.
    const aoContext = await browser.newContext(), ao = await aoContext.newPage();
    // This context has no Prompt API, so the assistant must stay hidden. Checks never
    // press Download against a real model: it starts a multi-gigabyte download.
    await aoContext.addInitScript(() => { delete window.LanguageModel; });
    const errors = []; ao.on('pageerror', e => errors.push(e.message));
    assert.deepEqual((await openAwesome(aoContext, ao)).registered, ['list_sections', 'list_find', 'list_get']);
    await ao.waitForFunction(async () => (await document.modelContext.getTools()).length === 7);
    const catalog = await ao.evaluate(() => fetch('catalog.json').then(r => r.json()));
    const urls = new Map(catalog.projects.map(p => [p.id, p.url]));
    const queries = ['video editor', 'scad', 'obs', 'self-hosted', 'manage family photos on my own server', ''];
    for (const query of queries) {
      const listed = await every(ao, 'list_find', { query }, 'items');
      const cabinet = await every(ao, 'cabinet_find', { query }, 'projects');
      // Names and order agree; projects sharing a name may tie in another order.
      assert.deepEqual(listed.map(i => i.name), cabinet.map(p => p.name), 'order: ' + query);
      assert.deepEqual(new Set(listed.map(i => i.url)), new Set(cabinet.map(p => urls.get(p.id))), 'identities: ' + query);
      const byUrl = new Map(cabinet.map(p => [urls.get(p.id), p.github]));
      for (const item of listed) {
        const github = byUrl.get(item.url);
        assert.deepEqual([item.fields.github_stars, item.fields.license, item.fields.pushed_at],
          [github.stars, github.license, github.pushed_at], 'unknowns: ' + item.name);
      }
    }
    report.awesomeOpen.queriesMatchingCabinet = queries.length;
    const none = await call(ao, 'list_find', { query: 'manage family photos on my own server' });
    assert.equal(none.total, 0); assert.match(none.message, /^No match in Awesome Open\* \(\d+ items\)\.$/);
    const servers = await call(ao, 'list_find', { filters: { run_modes: 'server' } });
    assert.ok(servers.total > 0);
    assert.match(servers.coverage[0].note, /^\d+ of \d+ items have a recorded run mode\.$/);
    report.awesomeOpen.runModeCoverage = servers.coverage[0].note;
    const editor = (await call(ao, 'list_find', { query: 'video editor' })).items[0];
    const detail = await call(ao, 'list_get', { id: editor.id });
    assert.equal(detail.ok, true); assert.equal(typeof detail.fields.function_summary, 'string');
    assert.match(detail.link, /records\/[a-f0-9]{64}\.html$/);
    const overview = await call(ao, 'list_sections', {});
    assert.deepEqual(overview.sections.map(s => s.title), catalog.categories.map(c => c.name));
    assert.deepEqual(overview.searched_fields, ['name', 'aliases', 'description', 'alternatives', 'function_summary', 'feature_notes']);
    assert.deepEqual(await call(ao, 'list_get', { id: 'nope' }), { ok: false, code: 'unknown_id', message: 'id must be an id returned by list_find.' });
    assert.equal((await call(ao, 'list_find', { query: 'x', offset: -1 })).code, 'invalid_offset');
    // Without the Prompt API, the assistant stays hidden.
    await ao.locator(PANEL).locator('button.trigger').click();
    await ao.locator(PANEL).locator('select option').nth(1).waitFor({ state: 'attached' });
    assert.equal(await ao.locator(PANEL).locator('section[aria-labelledby="wm-ask-title"]').isHidden(), true);
    assert.deepEqual(errors, []);
    report.awesomeOpen.items = overview.list.items; report.awesomeOpen.sections = overview.sections.length;
    await aoContext.close();

    // Silencing: panel off keeps the tools and removes the button.
    const quiet = await browser.newContext(), quietPage = await quiet.newPage();
    await withAttributes(quiet, 'data-webmcplet-panel="off"');
    await openAwesome(quiet, quietPage);
    assert.equal(await quietPage.locator(PANEL).count(), 0);
    assert.equal(await quietPage.evaluate(async () => (await document.modelContext.getTools()).length), 7);
    await quiet.close();

    await panelChecks(browser, 'awesome-open', openAwesome, report.awesomeOpen);

    // The assistant is opt-in: a ready model alone does not show it.
    const plain = await browser.newContext(), plainPage = await plain.newPage();
    await plain.addInitScript(stubModel('available', '() => ({ action: "answer", text: "", ids: [] })'));
    await openAwesome(plain, plainPage);
    await plainPage.locator(PANEL).locator('button.trigger').click();
    await plainPage.locator(PANEL).locator('select option').nth(1).waitFor({ state: 'attached' });
    assert.equal(await plainPage.locator(PANEL).locator('section[aria-labelledby="wm-ask-title"]').isHidden(), true);
    await plain.close();

    // Opted in, the assistant operates the shared Cabinet selection; rows come from tool results.
    const assisted = await browser.newContext(), page = await assisted.newPage();
    await withAttributes(assisted, 'data-webmcplet-assistant="on" data-webmcplet-assistant-tools="cabinet_arrange cabinet_compare cabinet_find cabinet_inspect"');
    await assisted.addInitScript(stubModel('available', `input => {
      const revision = (/"revision":(\\d+)/.exec(input) || [])[1];
      if (!input.startsWith('Result of')) return { action: 'call', tool: 'cabinet_find', args: { query: 'video editor' } };
      if (input.startsWith('Result of cabinet_find')) return { action: 'call', tool: 'cabinet_arrange', args: { ids: ['r1', 'r2'], revision: Number(revision) } };
      if (input.startsWith('Result of cabinet_arrange')) return { action: 'call', tool: 'cabinet_compare', args: {} };
      return { action: 'answer', text: 'These two projects edit video.', ids: ['r1', 'r2', 'r40'] };
    }`));
    await openAwesome(assisted, page);
    await page.locator(PANEL).locator('button.trigger').click();
    await page.locator(PANEL).getByLabel('Question').fill('Find a video editor and compare two.');
    await page.locator(PANEL).getByRole('button', { name: 'Ask', exact: true }).click();
    const answered = page.locator(PANEL).locator('ol[aria-label="Items in the answer"] li');
    await answered.nth(1).waitFor();
    assert.equal(await answered.count(), 2);
    assert.match(await page.locator(PANEL).locator('.state').textContent(), /1 item\(s\) the tools did not return/);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#cabinet-selection li').count(), 2, 'the assistant arranged the shared selection');
    assert.match(await page.locator('#cabinet-activity').textContent(), /Assistant · cabinet_compare · completed/);
    await assisted.close();
    report.awesomeOpen.assistant = 'stand-in model: find, arrange, compare; 2 rows shown, 1 unreturned ID omitted';

    if (!AO_ONLY) {
      // Mac list: the live page, with the list imported from its README.
      const macContext = await browser.newContext(), mac = await macContext.newPage();
      assert.deepEqual((await inject(macContext, mac, MAC, macList)).registered, ['list_sections', 'list_find', 'list_get']);
      const macOverview = await call(mac, 'list_sections', {});
      assert.equal(macOverview.list.page_url, MAC);
      const editors = await every(mac, 'list_find', { query: 'markdown editor' }, 'items');
      for (const name of ['MacDown', 'Mark Text', 'MarkEdit']) assert.ok(editors.some(i => i.name === name), name);
      const markdown = macOverview.sections.find(s => s.title === 'Markdown');
      const scoped = await every(mac, 'list_find', { section: markdown.parent }, 'items');
      assert.ok(scoped.length >= markdown.items, 'a section includes its subsections');
      const macdown = await call(mac, 'list_get', { id: editors.find(i => i.name === 'MacDown').id });
      assert.equal(macdown.url.toLowerCase(), 'https://github.com/macdownapp/macdown');
      assert.deepEqual(macdown.fields, {});
      Object.assign(report.macList, { items: macOverview.list.items, sections: macOverview.sections.length, markdownEditors: editors.length });
      await macContext.close();
      const openMac = (context, page) => inject(context, page, MAC, macList);
      const macQuiet = await browser.newContext(), quietMac = await macQuiet.newPage();
      assert.equal((await inject(macQuiet, quietMac, MAC, macList, { webmcpletPanel: 'off' })).registered.length, 3);
      assert.equal(await quietMac.locator(PANEL).count(), 0);
      await macQuiet.close();
      await panelChecks(browser, 'mac-list', openMac, report.macList);
      // Text naming an item the tools did not return is withheld; the rows stay.
      const macAssisted = await browser.newContext(), macPage = await macAssisted.newPage();
      await macAssisted.addInitScript(stubModel('downloadable', `input => input.startsWith('Result of')
        ? { action: 'answer', text: 'MacDown works; so does Firefox.', ids: ['r1'] }
        : { action: 'call', tool: 'list_find', args: { query: 'markdown editor' } }`));
      await inject(macAssisted, macPage, MAC, macList, { webmcpletAssistant: 'on' });
      await macPage.locator(PANEL).locator('button.trigger').click();
      await macPage.locator(PANEL).getByRole('button', { name: 'Download the model' }).click();
      await macPage.locator(PANEL).getByLabel('Question').fill('Find a Markdown editor.');
      await macPage.locator(PANEL).getByRole('button', { name: 'Ask', exact: true }).click();
      await macPage.locator(PANEL).locator('ol[aria-label="Items in the answer"] li').first().waitFor();
      assert.match(await macPage.locator(PANEL).locator('p.generated').textContent(), /withheld/);
      await macAssisted.close();
      report.macList.assistant = 'stand-in model: download on click; text naming an unreturned item withheld';
    }
    report.status = 'passed';
  } finally {
    fs.writeFileSync(output + '/webmcplet.json', JSON.stringify(report, null, 2) + '\n');
    await browser.close();
  }
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
