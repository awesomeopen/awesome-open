/* Offline Scoreboard coverage, including explicit preview and specimen trophies. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.join(ROOT, 'tmp/site-qa');
const PREVIEW = path.join(ROOT, 'tmp/scoreboard-preview');
(async () => {
  fs.mkdirSync(OUTPUT, {recursive: true});
  const sourceSha = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: ROOT, encoding:'utf8'}).trim();
  execFileSync('python3', ['scripts/build_site.py', '--output', PREVIEW, '--source-sha', sourceSha, '--scoreboard-preview'], {cwd: ROOT});
  const snapshot = JSON.parse(fs.readFileSync(path.join(PREVIEW, 'scoreboard/snapshot.json')));
  assert.equal(snapshot.preview, true);
  const server = http.createServer((req, res) => {
    let file = path.resolve(PREVIEW, '.' + decodeURI(new URL(req.url, 'http://localhost').pathname));
    if (!file.startsWith(PREVIEW + path.sep) && file !== PREVIEW) {res.writeHead(403).end(); return;}
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    if (!fs.existsSync(file)) {res.writeHead(404).end(); return;}
    const types = {'.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.json':'application/json', '.svg':'image/svg+xml', '.webp':'image/webp', '.woff2':'font/woff2'};
    res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/`;
  let browser;
  try {
    browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}), args:process.env.CHROMIUM_NO_SANDBOX ? ['--no-sandbox'] : []});
    const page = await browser.newPage({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
    const errors=[]; page.on('pageerror', e => errors.push(String(e)));
    await page.goto(base+'scoreboard/'); await page.evaluate(() => document.fonts.ready);
    assert.match(await page.locator('.score-scope').innerText(), /Provisional preview/);
    assert.equal(await page.locator('.score-board').count(), 6);
    for (const metric of snapshot.metrics) {
      const section=page.locator('#'+metric.id);
      assert.equal(await section.locator('tbody tr[data-project-id]').count(), metric.rows.length);
      assert.deepEqual(await section.locator('tbody tr[data-project-id]').evaluateAll(rows=>rows.map(r=>Number(r.dataset.rank))), metric.rows.map(r=>r.rank));
    }
    const disclosure=page.locator('.score-evidence').first();
    await disclosure.locator('summary').click(); assert.equal(await disclosure.getAttribute('open'), '');
    await disclosure.locator('summary').click(); assert.equal(await disclosure.getAttribute('open'), null);
    await page.screenshot({path:path.join(OUTPUT,'scoreboard-desktop.png'),fullPage:true});
    const award=snapshot.metrics.find(m=>m.rows.length).rows[0];
    await page.goto(base+'records/'+award.id+'.html');
    const badge=page.locator('.scoreboard-trophies a').first();
    assert.match(await badge.getAttribute('aria-label'), /Preview: .+place [123]/);
    await badge.click(); await page.waitForURL(/scoreboard\/#/);
    await page.goBack(); assert.ok(page.url().includes('/records/'));
    await page.screenshot({path:path.join(OUTPUT,'scoreboard-plate.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844}); await page.goto(base+'scoreboard/');
    assert.ok(await page.locator('.score-jump').isVisible(), 'Ranking navigation stays visible on mobile');
    assert.equal(await page.locator('.score-jump a').count(), 6);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'No narrow viewport overflow');
    await page.screenshot({path:path.join(OUTPUT,'scoreboard-mobile.png'),fullPage:true});
    await page.keyboard.press('Tab'); assert.match(await page.locator(':focus').innerText(), /Skip to scoreboard/);
    await page.keyboard.press('Enter'); assert.equal(await page.locator(':focus').getAttribute('id'),'scoreboard');
    const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:844}});
    await nojs.goto(base+'scoreboard/'); assert.equal(await nojs.locator('.score-board').count(),6);
    await nojs.locator('.score-evidence summary').first().click(); assert.equal(await nojs.locator('.score-evidence').first().getAttribute('open'),'');
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(OUTPUT,'scoreboard.json'), JSON.stringify({status:'passed',sourceSha,preview:true,metrics:snapshot.metrics.map(m=>({id:m.id,rows:m.rows.length})),screenshots:['scoreboard-desktop.png','scoreboard-mobile.png','scoreboard-plate.png']},null,2));
    console.log('Scoreboard browser checks passed: six rankings, ties, preview labels, trophies, history, keyboard, narrow, no-JS.');
  } finally {if(browser) await browser.close(); await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
