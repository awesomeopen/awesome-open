/* Typography coverage, run independently by the browser-suite runner. */
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
module.exports = async ({ browser, url, data, output }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const requests = [], errors = [];
  page.on('request', request => requests.push(request.url()));
  page.on('pageerror', error => errors.push(error.message));
  const check = async () => {
    await page.evaluate(() => document.fonts.ready);
    const css = await page.locator('h1').first().evaluate(node => {
      const s = getComputedStyle(node); return { family: s.fontFamily, weight: s.fontWeight, axes: s.fontVariationSettings };
    });
    assert.match(css.family, /Poltawski Nowy/); assert.equal(css.weight, '400'); assert.equal(css.axes, 'normal');
    assert.equal(await page.locator('.brand,.obs-brand').first().evaluate(node => getComputedStyle(node).fontWeight), '400');
    assert.ok(await page.evaluate(() => Array.from(document.fonts).some(face => face.family.replace(/["']/g, '') === 'Poltawski Nowy' && face.status === 'loaded')));
    assert.ok(await page.evaluate(() => Array.from(document.fonts).some(face => face.family.replace(/["']/g, '') === 'Commit Mono' && face.status === 'loaded')));
    assert.match(await page.locator('body').evaluate(node => getComputedStyle(node).fontFamily), /Commit Mono/);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.equal(await page.locator('.serif-preview,#serif-preview-choice').count(), 0);
  };
  await page.route(url + '/design/**', route => {
    const tokens = new URL(route.request().url()).pathname.endsWith('/tokens.css');
    route.fulfill({ contentType: tokens ? 'text/css' : 'text/html', body: fs.readFileSync(path.join(__dirname, '../site/design/', tokens ? 'tokens.css' : 'index.html')) });
  });
  try {
    for (const suffix of ['', '?serif=fraunces', '?serif=instrument', '?serif=poltawski', '?serif=invalid']) {
      requests.length = 0; await page.goto(url + '/' + suffix); await check();
      const fonts = requests.filter(value => /\.woff2(?:\?|$)/.test(value));
      assert.equal(fonts.filter(value => /poltawski\.woff2$/.test(value)).length, 1);
      assert.equal(fonts.filter(value => /commit-mono\.woff2$/.test(value)).length, 1);
      assert.equal(fonts.length, 2);
      assert.ok(fonts.every(value => /(?:poltawski|commit-mono)\.woff2$/.test(value)));
      assert.ok(!requests.some(value => /serif-preview\.(js|css)/.test(value)));
    }
    await page.goto(url + '/'); await check();
    // Genuine variable bold, with browser synthesis disabled, using the same file.
    const boldMetrics = await page.evaluate(async () => {
      const faces = await document.fonts.load('700 40px "Poltawski Nowy"');
      const sample = document.createElement('div'); sample.id = 'bold-font-probe';
      sample.style.cssText = 'background:white;color:black;padding:16px;font-family:"Poltawski Nowy";font-size:40px;font-synthesis:none';
      for (const weight of [400, 700]) {
        const line = document.createElement('div'), span = document.createElement('span');
        span.textContent = 'Hamburgefonts 0123456789'; span.style.fontWeight = weight;
        line.append(span); sample.append(line);
      }
      document.body.append(sample);
      const spans = Array.from(sample.querySelectorAll('span'));
      return { weights: faces.map(face => face.weight), loaded: faces.every(face => face.status === 'loaded'),
        widths: spans.map(node => node.getBoundingClientRect().width),
        synthesis: spans.map(node => getComputedStyle(node).fontSynthesis),
        computed: spans.map(node => getComputedStyle(node).fontWeight) };
    });
    assert.ok(boldMetrics.loaded); assert.ok(boldMetrics.weights.includes('400 700'));
    assert.deepEqual(boldMetrics.computed, ['400', '700']);
    assert.deepEqual(boldMetrics.synthesis, ['none', 'none']);
    assert.notEqual(boldMetrics.widths[0], boldMetrics.widths[1], 'Real bold changes glyph metrics without synthesis');
    await page.locator('#bold-font-probe').screenshot({ path: path.join(output, 'serif-poltawski-real-bold.png') });
    await page.locator('#bold-font-probe').evaluate(node => node.remove());
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, 'fonts-poltawski-desktop.png') });
    await page.keyboard.press('Tab');
    assert.match(await page.locator(':focus').getAttribute('href'), /^#/);
    const record = data.projects.find(p => p.artwork) || data.projects[0];
    for (const route of ['/', '/observatory/', '/spotlight/', '/records/' + record.id + '.html', '/design/']) {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(url + route + '?serif=fraunces'); await check();
      await page.screenshot({ path: path.join(output, 'fonts-' + (route.split('/')[1] || 'catalog') + '-mobile.png') });
    }
    await page.goto(url + '/records/' + record.id + '.html?serif=instrument');
    await page.locator('.permalink').first().click();
    assert.equal(new URL(page.url()).searchParams.has('serif'), false);
    assert.equal(new URL(page.url()).hash, '#project-' + record.id); await check();
    const failedContext = await browser.newContext();
    const failed = await failedContext.newPage();
    await failed.route('**/vendor/serif-preview/poltawski.woff2', route => route.abort());
    await failed.goto(url + '/'); await failed.evaluate(() => document.fonts.ready);
    assert.ok(await failed.locator('h1').first().isVisible());
    assert.ok(await failed.locator('h1').first().evaluate(node => node.getBoundingClientRect().width > 0));
    await failedContext.close();
    const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const staticPage = await nojs.newPage();
    for (const route of ['/?serif=instrument', '/standalone.html', '/observatory/report.html']) {
      await staticPage.goto(url + route); await staticPage.evaluate(() => document.fonts.ready);
      assert.match(await staticPage.locator('h1').first().evaluate(node => getComputedStyle(node).fontFamily), /Poltawski Nowy/);
      assert.ok(await staticPage.evaluate(() => Array.from(document.fonts).some(face => face.family.replace(/["']/g, '') === 'Poltawski Nowy' && face.status === 'loaded')));
      assert.ok(await staticPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await nojs.close(); assert.deepEqual(errors, []);
    console.log('Settled typography: real bold, obsolete URLs, two font requests, no selector/runtime, mobile routes, offline/no-JS and failure fallback passed');
  } finally { await context.close(); }
};

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const output = path.resolve(__dirname, '../tmp/site-qa');
    fs.mkdirSync(output, { recursive: true });
    const report = { status: 'running', prHeadSha: process.env.PR_HEAD_SHA || null };
    const write = () => fs.writeFileSync(path.join(output, 'fonts.json'), JSON.stringify(report, null, 2) + '\n');
    write();
    let browser;
    try {
      browser = await chromium.launch({ headless: true,
        ...(process.env.CHROMIUM_NO_SANDBOX === '1' ? { args: ['--no-sandbox'] } : {}),
        ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
      const url = process.env.SITE_URL || 'http://127.0.0.1:8000';
      const response = await browser.newContext().then(context => context.request.get(new URL('catalog.json', url + '/').href));
      assert.ok(response.ok(), 'Full catalog download is available');
      const data = await response.json(); report.sourceSha = data.source_sha; write();
      if (process.env.SITE_SOURCE_SHA) assert.equal(data.source_sha, process.env.SITE_SOURCE_SHA);
      await module.exports({ browser, url, data, output });
      report.status = 'passed';
    } catch (error) { report.status = 'failed'; report.error = error.message; throw error; }
    finally {
      write();
      if (browser) await browser.close();
    }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
