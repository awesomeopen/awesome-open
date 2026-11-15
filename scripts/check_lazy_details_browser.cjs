/* Fetch-on-open coverage for the Catalog pane. Runs only inside the existing CI browser
 * harness; this module never starts a browser or a preview server. */
const assert = require('node:assert/strict');

module.exports = async ({ page, context, browser, url, data, capture }) => {
  const base = new URL(url);
  const sample = data.projects.find(project => project.name === 'OpenTofu');
  assert.ok(sample?.deployment && sample.artwork, 'Lifecycle fixture has artwork and nested setup evidence');
  const record = project => new URL(`records/${project.id}.html`, base).href;
  const row = project => page.locator(`#rows .row[data-id="${project.id}"]`);
  const plate = page.locator('#pane-scroll .specimen-plate');
  const ready = () => page.waitForFunction(() => document.querySelector('#filters')?.dataset.enhanced === 'true');
  const requests = [];
  const onRequest = request => {
    if (/\/records\/[^/]+\.html(?:[?#]|$)/.test(request.url()) && !request.isNavigationRequest()) requests.push(request.url());
  };
  page.on('request', onRequest);
  const report = { browser: browser.version(), viewport: { width: 1440, height: 1000 }, checks: [] };
  try {
    await page.setViewportSize(report.viewport);
    await page.goto(base.href);
    await ready();
    const cold = await page.evaluate(() => ({ rows: document.querySelectorAll('#rows .row').length,
      plates: document.querySelectorAll('.specimen-plate').length, elements: document.querySelectorAll('*').length }));
    assert.equal(cold.rows, data.projects.length, 'Every project has a row on first load');
    assert.equal(cold.plates, 0, 'The cold page parses no specimen plates');
    assert.deepEqual(requests, [], 'The cold page fetches no record documents');
    assert.ok(cold.elements <= 16 * data.projects.length, 'DOM budget: about 16 elements per row');
    for (const project of data.projects.slice(0, 20))
      assert.equal(await row(project).locator('a').getAttribute('href'), `records/${project.id}.html`);
    report.checks.push('cold DOM and zero record requests');

    // A held response shows the loading status; the loaded plate resolves its assets from the catalog base.
    const body = await (await context.request.get(record(sample))).text();
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    const hold = async route => { await gate; await route.fulfill({ status: 200, contentType: 'text/html', body }); };
    await page.route(record(sample), hold);
    try {
      await row(sample).locator('a').click();
      assert.equal(await page.locator('#plate-status').textContent(), 'Loading…');
      assert.equal(await page.locator('#plate-name').textContent(), sample.name);
      assert.equal(await plate.count(), 0);
      await capture('detail-loading.png');
      release();
      await plate.waitFor({ state: 'visible' });
      assert.equal(await page.locator('#plate-status').textContent(), '');
      assert.equal(await plate.locator('.plate-departure > a').getAttribute('href'), sample.url);
      await plate.locator('.plate-art img').evaluate(image => image.decode());
      assert.equal(await plate.locator('.plate-art img').evaluate(image => image.complete && image.naturalWidth > 0), true,
        'Fetched record assets resolve from the catalog base');
      assert.equal(new URL(page.url()).hash, '#project-' + sample.id, 'The address carries the permalink');
      assert.equal(await row(sample).evaluate(node => node.classList.contains('is-current')), true);
      await capture('detail-loaded.png');
    } finally {
      release();
      await page.unroute(record(sample), hold);
    }
    assert.equal(requests.filter(href => href === record(sample)).length, 1, 'Opening a row fetches its record once');
    report.checks.push('loading status, one fetch, asset resolution, permalink');

    // Stepping keeps exactly one plate mounted; Esc unmounts it and returns to the jars.
    for (const key of ['ArrowRight', 'ArrowRight', 'ArrowLeft']) {
      await page.keyboard.press(key);
      await page.waitForFunction(() => document.getElementById('plate-status').textContent === '' &&
        document.querySelector('#pane-scroll .specimen-plate'));
      assert.equal(await page.locator('.specimen-plate').count(), 1, 'One plate at a time after ' + key);
    }
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.specimen-plate').count(), 0, 'Esc unmounts the plate');
    assert.equal(await page.locator('#pane-rest').isVisible(), true);
    assert.equal(new URL(page.url()).hash, '');
    report.checks.push('stepping keeps one plate; Esc returns to the jars');

    // A failed or mismatched record keeps a full-record link and a retry.
    // A row far from those opened above, so no prefetched copy can answer for it.
    const ids = await page.locator('#rows .row').evaluateAll(rows => rows.map(row => row.dataset.id));
    for (const [offset, failure] of [[0, 'status'], [40, 'mismatch']]) {
      const other = data.projects.find(project => project.id === ids[Math.floor(ids.length / 2) + offset]);
      const handler = route => failure === 'status'
        ? route.fulfill({ status: 503, body: 'unavailable' })
        : route.fulfill({ status: 200, contentType: 'text/html', body: body });
      await page.route(record(other), handler);
      await row(other).locator('a').click();
      const error = page.locator('#pane-scroll .pane-error');
      await error.waitFor({ state: 'visible' });
      assert.equal(await error.locator('a').getAttribute('href'), `records/${other.id}.html`, failure + ': full-record link');
      assert.equal(await page.locator('.specimen-plate').count(), 0, failure + ': no plate is adopted');
      await page.unroute(record(other), handler);
      await error.getByRole('button', { name: 'Try again' }).click();
      await plate.waitFor({ state: 'visible' });
      assert.equal(await page.locator('#plate-name').textContent(), other.name);
      await page.keyboard.press('Escape');
    }
    report.checks.push('failure and mismatch keep a record link; retry loads');

    // A permalink opens its plate on a cold load.
    await page.goto(new URL('#project-' + sample.id, base).href);
    await plate.waitFor({ state: 'visible' });
    assert.equal(await page.locator('#plate-name').textContent(), sample.name);
    report.checks.push('permalink cold load');

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1440, height: 1000 } });
    try {
      const fallback = await noJS.newPage();
      await fallback.goto(base.href);
      assert.equal(await fallback.locator('#rows .row').count(), data.projects.length);
      assert.equal(await fallback.locator('#filters').isVisible(), false, 'Filters need JavaScript and stay hidden');
      await fallback.locator(`#rows .row[data-id="${sample.id}"] > a`).click();
      await fallback.locator('.specimen-plate').waitFor({ state: 'visible' });
      assert.equal(new URL(fallback.url()).pathname.endsWith(`/records/${sample.id}.html`), true);
    } finally { await noJS.close(); }
    report.checks.push('no-JavaScript rows open static records');
    return report;
  } finally {
    page.off('request', onRequest);
  }
};
