/* Runs inside the existing serial field-guide browser check. */
const assert = require('node:assert/strict');
const path = require('node:path');
module.exports = async ({ browser, url, data, output }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const requests = [], errors = [];
  page.on('request', request => requests.push(request.url()));
  page.on('pageerror', error => errors.push(error.message));
  const candidateRequests = () => requests.filter(value => /serif-preview\/.*\.woff2/.test(value));
  const heading = () => page.locator('h1').first().evaluate(node => {
    const css = getComputedStyle(node); return { family: css.fontFamily, weight: css.fontWeight, axes: css.fontVariationSettings };
  });
  const waitChoice = async choice => page.waitForFunction(value => document.documentElement.dataset.serif === value, choice);
  const check = async choice => {
    await waitChoice(choice);
    const css = await heading();
    assert.match(css.family, new RegExp('Preview ' + choice)); assert.equal(css.weight, '400'); assert.equal(css.axes, 'normal');
    assert.equal(await page.locator('.brand,.obs-brand').first().evaluate(node => getComputedStyle(node).fontWeight), '400');
    assert.match(await page.locator('body').evaluate(node => getComputedStyle(node).fontFamily), /Commit Mono/);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Preview horizontal overflow');
  };
  try {
    for (const suffix of ['', '?serif=invalid', '?serif=fraunces']) {
      requests.length = 0; await page.goto(url + '/' + suffix); await page.evaluate(() => document.fonts.ready);
      assert.deepEqual(candidateRequests(), []);
      assert.equal((await heading()).weight, '300');
      assert.equal(await page.locator('.serif-preview').count(), suffix.includes('fraunces') ? 1 : 0);
    }
    requests.length = 0;
    await page.goto(url + '/?serif=instrument'); await check('instrument');
    assert.equal(candidateRequests().length, 1); assert.match(candidateRequests()[0], /instrument\.woff2$/);
    await page.screenshot({ path: path.join(output, 'serif-instrument-desktop.png') });
    await page.locator('#serif-preview-choice').focus();
    assert.equal(await page.locator('#serif-preview-choice').evaluate(node => getComputedStyle(node).outlineStyle), 'solid');
    await page.locator('#serif-preview-choice').selectOption('poltawski'); await check('poltawski');
    assert.equal(candidateRequests().length, 2);
    await page.goBack(); await check('instrument'); await page.goForward(); await check('poltawski');
    await page.locator('#serif-preview-choice').selectOption('fraunces');
    assert.match((await heading()).family, /Fraunces/); assert.equal((await heading()).weight, '300');
    assert.equal(await page.locator('.brand').first().evaluate(node => getComputedStyle(node).fontWeight), '600');
    // Real navigation, not just direct URLs; query and fragment are retained.
    await page.locator('#serif-preview-choice').selectOption('instrument'); await check('instrument');
    const spotlight = page.locator('a[href*="spotlight/"]').first();
    assert.match(await spotlight.getAttribute('href'), /serif=instrument/);
    await spotlight.click(); await check('instrument');
    assert.equal(new URL(page.url()).pathname.endsWith('/spotlight/'), true);
    await page.getByRole('link', { name: 'Catalog', exact: true }).click(); await check('instrument');
    const obs = page.locator('a[href*="observatory/"]').first();
    assert.match(await obs.getAttribute('href'), /serif=instrument/); await obs.click(); await check('instrument');
    await page.locator('#category-filter').selectOption({ index: 1 });
    assert.equal(new URL(page.url()).searchParams.get('serif'), 'instrument');
    await page.reload(); await check('instrument');
    const record = data.projects.find(p => p.artwork) || data.projects[0];
    for (const choice of ['instrument', 'poltawski']) {
      for (const route of ['/', '/observatory/', '/spotlight/', '/records/' + record.id + '.html']) {
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(url + route + '?serif=' + choice); await check(choice);
        await page.screenshot({ path: path.join(output, 'serif-' + choice + '-' + (route.split('/')[1] || 'catalog') + '-mobile.png') });
      }
    }
    await page.goto(url + '/?serif=poltawski#catalog'); await check('poltawski');
    await page.getByRole('link', { name: 'Exit preview' }).click();
    assert.equal(new URL(page.url()).searchParams.has('serif'), false);
    assert.equal(await page.locator('.serif-preview').count(), 0);
    assert.match((await heading()).family, /Fraunces/);
    // No stored preference leaks to a normal URL, even in the same browser.
    await page.goto(url + '/?serif=instrument'); await check('instrument');
    await page.goto(url + '/'); assert.equal(await page.locator('.serif-preview').count(), 0);
    const failed = await context.newPage();
    await failed.route('**/vendor/serif-preview/*.woff2', route => route.abort());
    await failed.goto(url + '/?serif=instrument');
    await failed.getByRole('status').filter({ hasText: 'Could not load' }).waitFor();
    assert.match(await failed.locator('h1').first().evaluate(node => getComputedStyle(node).fontFamily), /Fraunces/);
    await failed.locator('#serif-preview-choice').selectOption('fraunces');
    await failed.getByRole('status').filter({ hasText: 'original weights' }).waitFor();
    await failed.close();
    assert.deepEqual(errors, []);
    console.log('Serif preview: URL choices, 400 weights, fonts, default/no-storage, navigation, history, failure and narrow layouts passed');
  } finally { await context.close(); }
};
