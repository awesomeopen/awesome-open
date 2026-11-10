/* Injects webmcplet/webmcplet.js into Awesome Open* and the live open-source-mac-os-apps page,
 * in this browser only, and checks the same tools on both.
 *
 * SITE_URL=<served Awesome Open build> node scripts/check_webmcplet_browser.cjs <awesome-open list.json> <mac list.json>
 *
 * Build the lists with scripts/build_webmcplet_list.py and `node webmcplet/build.cjs markdown`.
 * MAC_URL overrides the Mac list page, https://serhii-londar.github.io/open-source-mac-os-apps/.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const [aoList, macList] = process.argv.slice(2);
if (!macList) { console.error('Usage: check_webmcplet_browser.cjs <awesome-open list.json> <mac list.json>'); process.exit(1); }
const SCRIPT = path.join(__dirname, '..', 'webmcplet', 'webmcplet.js');
const AO = process.env.SITE_URL || 'http://127.0.0.1:8000/';
const MAC = process.env.MAC_URL || 'https://serhii-londar.github.io/open-source-mac-os-apps/';

// Serves the script and list at <page>/webmcplet/ for this browser context only, then adds the tag.
async function inject(context, page, base, listPath) {
  const prefix = new URL('webmcplet/', base).href;
  await context.route(prefix + '**', route => {
    const file = route.request().url().endsWith('/webmcplet.js') ? SCRIPT : listPath;
    route.fulfill({ path: file, contentType: file.endsWith('.js') ? 'text/javascript' : 'application/json' });
  });
  await page.goto(base);
  await page.evaluate(src => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src + 'webmcplet.js'; script.dataset.webmcpletSrc = src + 'list.json';
    script.onload = resolve; script.onerror = reject; document.head.append(script);
  }), prefix);
  return page.evaluate(() => window.WebMCPlet.ready);
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

(async () => {
  const options = { headless: true, args: ['--enable-blink-features=WebMCP'] };
  if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
  if (process.env.CHROMIUM_NO_SANDBOX === '1') options.args.push('--no-sandbox');
  const browser = await chromium.launch(options);
  const report = { browser: browser.version(), script: 'webmcplet/webmcplet.js', awesomeOpen: {}, macList: { url: MAC }, status: 'running' };
  const output = 'tmp/site-qa'; fs.mkdirSync(output, { recursive: true });
  try {
    // Awesome Open: the list tools sit beside the Cabinet's and agree with its search.
    const aoContext = await browser.newContext(), ao = await aoContext.newPage();
    const errors = []; ao.on('pageerror', e => errors.push(e.message));
    assert.deepEqual((await inject(aoContext, ao, AO, aoList)).registered, ['list_sections', 'list_find', 'list_get']);
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
    assert.deepEqual(errors, []);
    report.awesomeOpen.items = overview.list.items; report.awesomeOpen.sections = overview.sections.length;

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
    report.status = 'passed';
  } finally {
    fs.writeFileSync(output + '/webmcplet.json', JSON.stringify(report, null, 2) + '\n');
    await browser.close();
  }
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
