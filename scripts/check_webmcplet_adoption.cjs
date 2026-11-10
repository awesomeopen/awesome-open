/* Follows webmcplet/README.md's "Try it on your list" and "Add it to your site" on the
 * hypothetical webmcplet/example/README.md: the commands and script tag are read from
 * the README, so the docs and this check change together.
 *
 *   node scripts/check_webmcplet_adoption.cjs
 *
 * The README downloads a tagged release; this check copies the same files from the
 * working tree, so it covers the revision under review.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { spawn, execSync } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');

const DIR = path.join(__dirname, '..', 'webmcplet');
const EXAMPLE = path.join(DIR, 'example', 'README.md');
const PANEL = '[data-webmcplet-host]';
const readme = fs.readFileSync(path.join(DIR, 'README.md'), 'utf8');

function section(heading) {
  const start = readme.indexOf('\n## ' + heading + '\n');
  assert.notEqual(start, -1, 'README section ' + heading);
  const end = readme.indexOf('\n## ', start + 1);
  return readme.slice(start, end === -1 ? undefined : end);
}

function fenced(text, language) {
  const match = new RegExp('```' + language + '\\n([\\s\\S]*?)\\n\\s*```').exec(text);
  assert.ok(match, 'a ' + language + ' block');
  return match[1].split('\n').map(line => line.trim()).join('\n');
}

const trying = section('Try it on your list'), adding = section('Add it to your site');
const download = fenced(trying, 'sh');
const files = /for f in ([^;]+);/.exec(download)[1].trim().split(/\s+/);
const kept = adding.match(/^1\. Put ([^\n]+(?:\n {3}[^\n]+)*?) from that download/m)[1].match(/`([^`]+)`/g).map(f => f.slice(1, -1));
const build = fenced(adding, 'sh').replace(/\\\n/g, ' ');
const tag = fenced(adding, 'html');

function copy(names, into) {
  fs.mkdirSync(into, { recursive: true });
  for (const name of names) fs.copyFileSync(path.join(DIR, name), path.join(into, name));
}

// The documented `try` command, with the example README in place of a repository URL.
function startTry(cwd) {
  const command = /^node build\.cjs try (\S+)$/m.exec(download);
  assert.ok(command, 'the try command');
  const child = spawn('node', ['build.cjs', 'try', EXAMPLE], { cwd });
  return new Promise((resolve, reject) => {
    let out = '';
    child.stdout.on('data', chunk => {
      out += chunk;
      const url = /Preview: (\S+)/.exec(out);
      if (url) resolve({ child, url: url[1], out });
    });
    child.stderr.on('data', chunk => { out += chunk; });
    child.on('exit', code => reject(new Error('try exited ' + code + ': ' + out)));
  });
}

function serveStatic(root) {
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
  const server = http.createServer((request, response) => {
    const name = new URL(request.url, 'http://127.0.0.1').pathname.replace(/^\/$/, '/index.html');
    const file = path.join(root, path.normalize(name));
    if (!file.startsWith(root) || !fs.existsSync(file)) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(response);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

async function tools(page, url) {
  await page.goto(url);
  const ready = await page.evaluate(() => window.WebMCPlet.ready);
  assert.deepEqual(ready.registered, ['list_sections', 'list_find', 'list_get']);
  const found = await page.evaluate(async () => {
    const tool = (await document.modelContext.getTools()).find(t => t.name === 'list_find');
    const result = await document.modelContext.executeTool(tool, { query: 'markdown editor' });
    return typeof result === 'string' ? JSON.parse(result) : result;
  });
  assert.deepEqual(found.items.map(i => i.name), ['Inkwell', 'Plainpage']);
  await page.locator(PANEL).locator('button.trigger').click();
  await page.locator(PANEL).locator('#wm-query').fill('video'); await page.keyboard.press('Enter');
  const results = page.locator(PANEL).locator('ol[aria-label="Results"] li');
  await results.first().waitFor();
  assert.equal(await results.count(), 1);
  assert.equal(await results.locator('a').first().textContent(), 'Reelcut');
}

(async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'webmcplet-adoption-'));
  const options = { headless: true, args: ['--enable-blink-features=WebMCP'] };
  if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
  if (process.env.CHROMIUM_NO_SANDBOX === '1') options.args.push('--no-sandbox');
  const browser = await chromium.launch(options);
  const report = { browser: browser.version(), files, kept, status: 'running' };
  let preview, server;
  try {
    // Try it: download, then preview.
    const download = path.join(work, 'download');
    copy(files, download);
    preview = await startTry(download);
    assert.match(preview.out, /^5 items in 5 sections from /m);
    await tools(await browser.newPage(), preview.url);
    report.try = 'preview served; tools and panel search work';

    // Add it: keep the listed files, build list.json, add the tag to a page.
    assert.deepEqual(kept, files.filter(f => f !== 'try.js'));
    const site = path.join(work, 'site');
    copy(kept, path.join(site, 'webmcplet'));
    fs.copyFileSync(EXAMPLE, path.join(site, 'README.md'));
    execSync(build.replace(/^node build\.cjs/, 'node webmcplet/build.cjs'), { cwd: site, stdio: 'pipe', shell: '/bin/bash' });
    fs.renameSync(path.join(site, 'list.json'), path.join(site, 'webmcplet', 'list.json'));
    fs.writeFileSync(path.join(site, 'webmcplet', 'index.html'),
      '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Awesome X</title>' + tag + '</head><body><h1>Awesome X</h1></body></html>');
    server = await serveStatic(path.join(site, 'webmcplet'));
    await tools(await browser.newPage(), 'http://127.0.0.1:' + server.address().port + '/');
    report.add = 'documented build and tag; tools and panel search work';
    report.status = 'passed';
  } finally {
    if (preview) preview.child.kill();
    if (server) server.close();
    await browser.close();
    fs.rmSync(work, { recursive: true, force: true });
    fs.mkdirSync('tmp/site-qa', { recursive: true });
    fs.writeFileSync('tmp/site-qa/webmcplet-adoption.json', JSON.stringify(report, null, 2) + '\n');
  }
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; });
