/* Fetch-on-open regression coverage. Runs only inside the existing CI browser
 * harness; this module never starts a browser or a preview server. */
const assert = require('node:assert/strict');

module.exports = async ({ page, context, browser, url, data, capture }) => {
  const base = new URL(url);
  const sample = data.projects.find(project => project.name === 'OpenTofu');
  assert.ok(sample?.deployment && sample.artwork, 'Lifecycle fixture has artwork and nested setup evidence');
  const row = project => page.locator('#project-' + project.id);
  const host = project => row(project).locator('.specimen-detail-host');
  const plate = project => row(project).locator('.specimen-plate');
  const drawer = project => row(project).locator('details.specimen-drawer');
  const state = (project, value) => page.waitForFunction(({ id, value }) =>
    document.querySelector('#project-' + id + ' .specimen-detail-host')?.dataset.detailState === value,
  { id: project.id, value });
  const ready = () => page.waitForFunction(() => document.querySelector('#filters')?.dataset.enhanced === 'true');
  const loaded = async project => {
    await state(project, 'loaded');
    await plate(project).waitFor({ state: 'visible' });
    assert.equal(await plate(project).count(), 1, 'Exactly one mounted plate for ' + project.name);
  };
  // Wait for native toggle delivery as well as the open property, so retention
  // assertions cannot run before the disclosure's event handler.
  const setOpen = (project, open) => drawer(project).evaluate((node, open) => {
    if (node.open === open) return;
    return new Promise(resolve => {
      node.addEventListener('toggle', () => resolve(), { once: true });
      node.open = open;
    });
  }, open);
  const counts = () => page.evaluate(() => ({
    elements: document.querySelectorAll('*').length,
    summaries: document.querySelectorAll('.specimen-drawer > summary').length,
    plates: document.querySelectorAll('.specimen-plate').length,
    closedPlates: document.querySelectorAll('.specimen-drawer:not([open]) .specimen-plate').length,
    openPlates: document.querySelectorAll('.specimen-drawer[open] .specimen-plate').length,
    hosts: document.querySelectorAll('.specimen-detail-host').length,
  }));
  const requests = [];
  const onRequest = request => {
    if (/\/records\/[^/]+\.html(?:[?#]|$)/.test(request.url()) && !request.isNavigationRequest()) {
      requests.push(request.url());
    }
  };
  page.on('request', onRequest);
  const report = { browser: browser.version(), viewport: { width: 1440, height: 1000 }, checks: [] };
  try {
    await page.setViewportSize(report.viewport);
    await page.goto(base.href);
    await ready();
    report.cold = await counts();
    assert.equal(report.cold.summaries, data.projects.length, 'Every summary is available on first load');
    assert.equal(report.cold.hosts, data.projects.length, 'Every row has a static full-record destination');
    assert.equal(report.cold.plates, 0, 'Cold normal page parses no specimen plates');
    assert.equal(await page.locator('.plate-lens, .plate-terrain, .plate-wild-terrain').count(), 0,
      'Closed details have no generated plate decorations');
    assert.deepEqual(requests, [], 'Closed details do not fetch record documents');
    report.checks.push('cold DOM and zero detail requests');

    const detailURL = new URL(await host(sample).getAttribute('data-detail-url'), base).href;
    const response = await context.request.get(detailURL);
    assert.ok(response.ok(), 'Static detail fixture is available');
    const body = await response.text();
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    const holdResponse = async route => {
      await gate;
      await route.fulfill({ status: 200, contentType: 'text/html', body });
    };
    await page.route(detailURL, holdResponse);
    try {
      await drawer(sample).locator(':scope > summary').click();
      await state(sample, 'loading');
      assert.equal(await host(sample).getAttribute('aria-busy'), 'true');
      assert.equal(await host(sample).locator('.detail-status[role="status"]').isVisible(), true);
      assert.equal(await host(sample).locator('.detail-fallback a').isVisible(), true);
      assert.equal(await plate(sample).count(), 0);
      await host(sample).scrollIntoViewIfNeeded();
      await capture('detail-loading.png');
      await page.keyboard.press('Tab');
      assert.equal(await host(sample).locator('.detail-fallback a').evaluate(node => node === document.activeElement), true,
        'Fallback is keyboard-accessible while loading');
      release();
      await loaded(sample);
      assert.notEqual(await host(sample).getAttribute('aria-busy'), 'true');
      assert.equal(await host(sample).locator('.detail-fallback a').isVisible(), false, 'Loaded plate hides its fallback link');
      assert.equal(await drawer(sample).locator(':scope > summary').evaluate(node => node === document.activeElement), true,
        'Focus returns to the native summary before the fallback disappears');
      assert.equal(await plate(sample).getAttribute('aria-labelledby'), 'name-' + sample.id);
      assert.equal(await plate(sample).locator('.plate-departure > a').getAttribute('href'), sample.url);
      await plate(sample).locator('.plate-art img').evaluate(image => image.decode());
      assert.equal(await plate(sample).locator('.plate-art img').evaluate(image => image.complete && image.naturalWidth > 0), true,
        'Fetched record assets resolve from the catalog base');
      await plate(sample).scrollIntoViewIfNeeded();
      await capture('detail-loaded.png');
    } finally {
      release();
      await page.unroute(detailURL, holdResponse);
    }
    const firstRequestCount = requests.length;
    assert.equal(firstRequestCount, 1, 'Opening one row fetches only that record');
    await plate(sample).evaluate(node => { node.dataset.lifecycleMarker = 'retained'; });
    await page.evaluate(() => OpenCatalog.init(document, window));
    for (let attempt = 0; attempt < 3; attempt++) {
      await setOpen(sample, false);
      await setOpen(sample, true);
      await loaded(sample);
    }
    assert.equal(requests.length, firstRequestCount, 'Repeated toggles reuse the retained plate');
    assert.equal(await plate(sample).getAttribute('data-lifecycle-marker'), 'retained');
    assert.equal(await plate(sample).locator('.plate-lens').count(), 1, 'Repeated toggles do not duplicate the loupe');
    assert.equal(await plate(sample).locator('.plate-wild-terrain').count(), 1, 'Repeated toggles do not duplicate enhancement');
    report.checks.push('loading status, focus, one fetch, asset resolution, idempotent repeated toggles');

    // Both transport errors and a syntactically valid wrong record must fail
    // closed while preserving a usable native full-record link and Retry button.
    const wrong = data.projects.find(project => project.id !== sample.id);
    const wrongResponse = await context.request.get(new URL('records/' + wrong.id + '.html', base).href);
    assert.ok(wrongResponse.ok());
    const wrongBody = await wrongResponse.text();
    for (const failure of ['http', 'identity']) {
      await page.goto(base.href);
      await ready();
      let attempts = 0;
      const failOnce = async route => {
        attempts++;
        if (attempts === 1) {
          await route.fulfill({ status: failure === 'http' ? 503 : 200, contentType: 'text/html',
            body: failure === 'http' ? 'Temporarily unavailable' : wrongBody });
        } else {
          await route.continue();
        }
      };
      await page.route(detailURL, failOnce);
      try {
        await setOpen(sample, true);
        await state(sample, 'error');
        assert.equal(await plate(sample).count(), 0, failure + ': no partial or incorrect plate mounted');
        assert.notEqual(await host(sample).getAttribute('aria-busy'), 'true');
        assert.equal(await host(sample).locator('.detail-fallback a').isVisible(), true);
        assert.equal(await host(sample).locator('.detail-status[role="status"]').isVisible(), true);
        const retry = host(sample).locator('button.detail-retry');
        assert.equal(await retry.isVisible(), true);
        if (failure === 'http') {
          await host(sample).scrollIntoViewIfNeeded();
          await capture('detail-error.png');
        }
        await retry.click();
        await loaded(sample);
        assert.equal(attempts, 2, failure + ': one explicit retry succeeds');
        assert.equal(await host(sample).locator('.detail-fallback a').isVisible(), false);
        assert.equal(await host(sample).locator('button.detail-retry').isVisible(), false);
      } finally {
        await page.unroute(detailURL, failOnce);
      }
    }
    report.checks.push('HTTP and wrong-record errors, fallback and explicit retry');

    // A deliberately uncooperative transport settles after AbortController fires.
    // This verifies the stale-generation guard independently of native fetch's
    // abort behavior, including close + reopen before the older request resolves.
    await page.goto(base.href);
    await ready();
    await page.evaluate(({ detailURL, body }) => {
      const fetch = window.fetch.bind(window);
      window.__detailRace = { calls: 0, aborts: 0, pending: [] };
      window.fetch = (input, options) => {
        const requestURL = new URL(typeof input === 'string' ? input : input.url, location.href).href;
        if (requestURL !== detailURL) return fetch(input, options);
        const race = window.__detailRace;
        race.calls++;
        const call = race.calls;
        options?.signal?.addEventListener('abort', () => { race.aborts++; }, { once: true });
        return new Promise(resolve => race.pending.push(() => {
          const result = new Response(body.replace('specimen-interior specimen-plate',
            'specimen-interior specimen-plate race-' + call), { status: 200, headers: { 'Content-Type': 'text/html' } });
          Object.defineProperty(result, 'url', { value: detailURL });
          resolve(result);
        }));
      };
    }, { detailURL, body });
    await setOpen(sample, true);
    await state(sample, 'loading');
    await setOpen(sample, false);
    await state(sample, 'idle');
    assert.equal(await page.evaluate(() => window.__detailRace.aborts), 1, 'Closing aborts the pending fetch');
    await page.evaluate(() => window.__detailRace.pending.shift()());
    // Drain the controlled response and its async DOMParser continuation.
    await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 0)));
    assert.equal(await plate(sample).count(), 0, 'A late response cannot populate a closed drawer');
    await setOpen(sample, true);
    await state(sample, 'loading');
    await setOpen(sample, false);
    await state(sample, 'idle');
    await setOpen(sample, true);
    await state(sample, 'loading');
    await page.evaluate(() => window.__detailRace.pending.pop()());
    await loaded(sample);
    assert.equal(await plate(sample).evaluate(node => node.classList.contains('race-3')), true);
    await page.evaluate(() => window.__detailRace.pending.shift()());
    await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 0)));
    assert.equal(await plate(sample).evaluate(node => node.classList.contains('race-3')), true,
      'Older response cannot replace the newly opened record');
    assert.equal(await plate(sample).count(), 1);
    assert.equal(await page.evaluate(() => window.__detailRace.aborts), 2);
    report.checks.push('rapid close abort, closed stale response, reopen response ordering');

    await page.goto(base.href);
    await ready();
    await setOpen(sample, true);
    await loaded(sample);
    await plate(sample).locator('.deployment-evidence details > summary').click();
    assert.equal(await plate(sample).locator('.deployment-evidence details').evaluate(node => node.open), true);
    await setOpen(sample, false);
    const others = data.projects.filter(project => project.id !== sample.id).slice(0, 6);
    const pinned = others[0];
    await setOpen(pinned, true);
    await loaded(pinned);
    await plate(pinned).evaluate(node => { node.dataset.lifecycleMarker = 'open'; });
    for (const project of others.slice(1)) {
      await setOpen(project, true);
      await loaded(project);
      await setOpen(project, false);
      const current = await counts();
      assert.ok(current.closedPlates <= 3, 'At most three closed plates remain mounted');
      assert.equal(current.openPlates, 1, 'The open plate remains mounted during eviction');
      assert.ok(current.plates <= 4, 'Retained DOM is bounded by open plates plus three closed');
    }
    assert.equal(await plate(sample).count(), 0, 'Least-recently-used closed plate was evicted');
    assert.equal(await plate(pinned).getAttribute('data-lifecycle-marker'), 'open', 'An open plate is never evicted');
    await setOpen(sample, true);
    await loaded(sample);
    assert.equal(await plate(sample).locator('.deployment-evidence details').evaluate(node => node.open), true,
      'Nested disclosure state survives eviction and remount');
    report.afterRetention = await counts();
    report.checks.push('bounded closed-plate LRU, open-plate retention, nested disclosure restoration');

    // Keyboard toggling at a narrow viewport also exercises the real native
    // summary rather than a custom disclosure control.
    await page.setViewportSize({ width: 390, height: 844 });
    const filtered = new URL(base);
    filtered.searchParams.set('q', sample.name);
    await page.goto(filtered.href);
    await ready();
    const summary = drawer(sample).locator(':scope > summary');
    await summary.focus();
    await page.keyboard.press('Enter');
    await loaded(sample);
    assert.equal(await summary.evaluate(node => node === document.activeElement), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await capture('detail-keyboard-mobile.png');
    await page.keyboard.press('Space');
    await page.waitForFunction(id => !document.querySelector('#project-' + id + ' .specimen-drawer').open, sample.id);
    await page.keyboard.press('Space');
    await loaded(sample);
    report.checks.push('mobile native keyboard disclosure');

    // Direct static record routes are the explicit printing/no-JS destination.
    // Check them with scripting disabled, including <base>-resolved assets.
    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    try {
      const staticPage = await noJS.newPage();
      await staticPage.goto(base.href);
      const staticDrawer = staticPage.locator('#project-' + sample.id + ' .specimen-drawer');
      await staticDrawer.locator(':scope > summary').click();
      const staticFallback = staticDrawer.locator('.detail-fallback a');
      assert.equal(await staticFallback.isVisible(), true, 'No-JS drawers retain their full-record link');
      await staticFallback.click();
      await staticPage.waitForURL(detailURL);
      assert.equal(await staticPage.locator('.specimen-plate').count(), 1);
      assert.equal(await staticPage.locator('.specimen-detail-host').count(), 0);
      assert.equal(await staticPage.locator('.specimen-drawer').evaluate(node => node.open), true);
      assert.equal(await staticPage.locator('.function-detail').isVisible(), true);
      await staticPage.locator('.plate-art img').evaluate(image => image.decode());
      assert.equal(await staticPage.locator('.plate-art img').evaluate(image => image.complete && image.naturalWidth > 0), true);
      await staticPage.emulateMedia({ media: 'print' });
      assert.equal(await staticPage.locator('.specimen-plate').isVisible(), true);
      assert.equal(await staticPage.locator('.deployment-group').first().isVisible(), true,
        'Printing includes evidence inside closed nested disclosures');
      assert.equal(await staticPage.locator('.plate-departure > a').isVisible(), true);
      assert.equal(await staticPage.locator('.plate-departure > a').getAttribute('href'), sample.url);
    } finally {
      await noJS.close();
    }
    await page.setViewportSize(report.viewport);
    await page.goto(detailURL);
    await page.locator('.plate-lens').waitFor({ state: 'attached' });
    await page.locator('.plate-lens').evaluate(node => node.classList.add('is-on'));
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.plate-lens').isVisible(), false, 'Print hides an active magnifier');
    await page.locator('.specimen-plate').scrollIntoViewIfNeeded();
    await capture('detail-static-print.png');
    await page.emulateMedia({ media: 'screen' });
    report.checks.push('full static no-JS record, relative assets and print route');
    report.detailRequests = requests.length;
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base.href);
    await ready();
    return report;
  } finally {
    // Leave a failing page intact for the harness's failure screenshot.
    page.off('request', onRequest);
  }
};
