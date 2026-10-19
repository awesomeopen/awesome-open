/* Runs inside the existing serial field-guide browser check. */
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
module.exports = async ({ browser, url, data, output }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const requests = [], errors = [];
  page.on('request', request => requests.push(request.url()));
  page.on('pageerror', error => errors.push(error.message));
  const families = { poltawski: 'Poltawski Nowy', instrument: 'Instrument Serif', fraunces: 'Fraunces' };
  const serifRequests = () => requests.filter(value => /\/(fraunces|instrument|poltawski)\.woff2(?:\?|$)/.test(value));
  const check = async choice => {
    await page.waitForFunction(value => document.documentElement.dataset.serif === value, choice);
    await page.evaluate(() => document.fonts.ready);
    const css = await page.locator('h1').first().evaluate(node => {
      const s = getComputedStyle(node); return { family: s.fontFamily, weight: s.fontWeight, axes: s.fontVariationSettings };
    });
    assert.ok(css.family.includes(families[choice]));
    assert.equal(css.weight, choice === 'fraunces' ? '300' : '400');
    if (choice !== 'fraunces') assert.equal(css.axes, 'normal');
    else { assert.match(css.axes, /SOFT.*100/); assert.match(css.axes, /WONK.*1/); }
    assert.equal(await page.locator('.brand,.obs-brand').first().evaluate(node => getComputedStyle(node).fontWeight), choice === 'fraunces' ? '600' : '400');
    assert.ok(await page.evaluate(family => Array.from(document.fonts).some(face => face.family.replace(/["']/g, '') === family && face.status === 'loaded'), families[choice]), 'Selected face actually loaded');
    assert.match(await page.locator('body').evaluate(node => getComputedStyle(node).fontFamily), /Commit Mono/);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal overflow');
    assert.equal(await page.locator('#serif-preview-choice').inputValue(), choice);
  };
  // The private reference is intentionally not published by the production builder.
  await page.route(url + '/design/**', route => {
    const pathname = new URL(route.request().url()).pathname;
    const tokens = pathname.endsWith('/tokens.css');
    route.fulfill({ contentType: tokens ? 'text/css' : 'text/html',
      body: fs.readFileSync(path.join(__dirname, '../site/design/', tokens ? 'tokens.css' : 'index.html')) });
  });
  try {
    for (const [suffix, choice] of [['', 'poltawski'], ['?serif=invalid', 'poltawski'], ['?serif=fraunces', 'fraunces'], ['?serif=instrument', 'instrument']]) {
      requests.length = 0; await page.goto(url + '/' + suffix); await check(choice);
      assert.equal(serifRequests().length, 1, 'Only selected serif is requested on a fresh navigation');
      assert.match(serifRequests()[0], new RegExp('/' + choice + '\\.woff2$'));
      assert.equal(await page.locator('.serif-preview').count(), 1);
    }
    await page.goto(url + '/'); await check('poltawski');
    assert.equal(await page.locator('a[href="#catalog"]').count() > 0, true, 'Default anchors remain same-document links');
    await page.screenshot({ path: path.join(output, 'serif-poltawski-default-desktop.png') });
    await page.locator('#serif-preview-choice').focus();
    assert.equal(await page.locator('#serif-preview-choice').evaluate(node => getComputedStyle(node).outlineStyle), 'solid');
    await page.locator('#serif-preview-choice').selectOption('instrument'); await check('instrument');
    await page.screenshot({ path: path.join(output, 'serif-instrument-desktop.png') });
    await page.goBack(); await check('poltawski'); await page.goForward(); await check('instrument');
    await page.locator('#serif-preview-choice').selectOption('fraunces'); await check('fraunces');
    // Real navigation and filter serialization keep the explicit URL choice.
    await page.locator('#serif-preview-choice').selectOption('instrument'); await check('instrument');
    const obs = page.locator('a[href*="observatory/"]').first();
    assert.match(await obs.getAttribute('href'), /serif=instrument/); await obs.click(); await check('instrument');
    await page.locator('#category-filter').selectOption({ index: 1 });
    assert.equal(new URL(page.url()).searchParams.get('serif'), 'instrument');
    await page.reload(); await check('instrument');
    const record = data.projects.find(p => p.artwork) || data.projects[0];
    await page.goto(url + '/records/' + record.id + '.html?serif=instrument'); await check('instrument');
    await page.locator('.permalink').first().click();
    assert.equal(new URL(page.url()).searchParams.get('serif'), 'instrument');
    assert.equal(new URL(page.url()).hash, '#project-' + record.id); await check('instrument');
    for (const choice of ['instrument', 'poltawski', 'fraunces']) {
      for (const route of ['/', '/observatory/', '/draws/', '/records/' + record.id + '.html', '/design/']) {
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(url + route + '?serif=' + choice); await check(choice);
        await page.screenshot({ path: path.join(output, 'serif-' + choice + '-' + (route.split('/')[1] || 'catalog') + '-mobile.png') });
      }
    }
    await page.goto(url + '/?serif=instrument&test=keep#catalog'); await check('instrument');
    await page.getByRole('link', { name: 'Reset to default' }).click();
    assert.equal(new URL(page.url()).searchParams.has('serif'), false);
    assert.equal(new URL(page.url()).searchParams.get('test'), 'keep');
    assert.equal(new URL(page.url()).hash, '#catalog'); await check('poltawski');
    await page.goto(url + '/?serif=instrument'); await check('instrument');
    await page.goto(url + '/'); await check('poltawski');
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
    const failed = await context.newPage();
    await failed.route('**/vendor/serif-preview/poltawski.woff2', route => route.abort());
    await failed.goto(url + '/');
    await failed.getByRole('status').filter({ hasText: 'Could not load' }).waitFor();
    assert.ok(await failed.locator('h1').first().isVisible());
    await failed.locator('#serif-preview-choice').selectOption('fraunces');
    await failed.getByRole('status').filter({ hasText: 'original weights' }).waitFor();
    await failed.close();
    const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const staticPage = await nojs.newPage();
    for (const route of ['/', '/standalone.html', '/observatory/report.html']) {
      await staticPage.goto(url + route);
      await staticPage.evaluate(() => document.fonts.ready);
      assert.match(await staticPage.locator('h1').first().evaluate(node => getComputedStyle(node).fontFamily), /Poltawski Nowy/);
      assert.ok(await staticPage.evaluate(() => Array.from(document.fonts).some(face => face.family.replace(/["']/g, '') === 'Poltawski Nowy' && face.status === 'loaded')));
      assert.ok(await staticPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    }
    await nojs.close();
    assert.deepEqual(errors, []);
    console.log('Serif defaults, selected-font requests, URL navigation, offline/no-JS, weights, accessibility and failure: passed');
  } finally { await context.close(); }
};
