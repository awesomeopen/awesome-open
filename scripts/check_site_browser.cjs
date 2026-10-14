/* Browser smoke test, run by the PR preview workflow. Requires Playwright and Chromium.
 * Usage: SITE_URL=http://127.0.0.1:8000 node scripts/check_site_browser.cjs
 * CHROMIUM_PATH can point to an installed Chromium; screenshots go to tmp/site-qa.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const output = path.resolve(__dirname, '../tmp/site-qa');
  fs.mkdirSync(output, { recursive: true });
  const options = { headless: true };
  if (process.env.CHROMIUM_NO_SANDBOX === '1') options.args = ['--no-sandbox'];
  if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(options);
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1, colorScheme: 'light', reducedMotion: 'reduce', locale: 'en-US', timezoneId: 'UTC' });
  context.setDefaultTimeout(15000);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const url = process.env.SITE_URL || 'http://127.0.0.1:8000';
  const report = { status: 'running', url, sourceSha: null,
    prHeadSha: process.env.PR_HEAD_SHA || null, screenshots: [] };
  const writeReport = () => fs.writeFileSync(path.join(output, 'screenshots.json'), JSON.stringify(report, null, 2) + '\n');
  const capture = async name => {
    await page.evaluate(() => document.fonts.ready);
    const png = await page.screenshot({ path: path.join(output, name), animations: 'disabled', caret: 'hide', scale: 'css' });
    const dimensions = { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
    assert.deepEqual(dimensions, page.viewportSize(), `Screenshot dimensions: ${name}`);
    report.screenshots.push({ file: name, ...dimensions, bytes: png.length });
    writeReport();
  };
  const visible = () => page.locator('.project-card:not([hidden])').count();
  const change = async (id, value) => {
    if (id !== 'search' && !await page.locator('.filter-options').evaluate(node => node.open)) await page.locator('.filter-options > summary').click();
    if (['category-filter', 'metrics-filter', 'min-stars', 'pushed-since'].includes(id)) {
      if (!await page.locator('.more-filters').evaluate(node => node.open)) {
        await page.locator('.more-filters > summary').click();
      }
    }
    await page.locator('#' + id).fill(value);
    await page.locator('#' + id).dispatchEvent('change');
  };
  const select = async (id, value) => {
    if (id !== 'search' && !await page.locator('.filter-options').evaluate(node => node.open)) await page.locator('.filter-options > summary').click();
    if (['category-filter', 'metrics-filter'].includes(id) &&
        !await page.locator('.more-filters').evaluate(node => node.open)) {
      await page.locator('.more-filters > summary').click();
    }
    await page.locator('#' + id).selectOption(value);
  };
  const waitForState = () => page.waitForFunction(() => document.querySelector('#filters').dataset.enhanced === 'true');
  const assertLedgerFits = async (target, label) => {
    assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Horizontal overflow: ${label}`);
    // overflow-x:clip on a page shell can hide a grid that is wider than its screen.
    const clipped = await target.locator('.project-card:not([hidden])').first().locator('summary > *').evaluateAll(nodes =>
      nodes.filter(node => {
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && (rect.left < -1 || rect.right > innerWidth + 1);
      }).map(node => node.className));
    assert.deepEqual(clipped, [], `Clipped ledger cells: ${label}`);
  };
  try {
    // Capture both viewports before assertions so a later failure retains useful
    // review artifacts. Fixed motion, fonts, pixel scale, locale and theme avoid
    // screenshots depending on a runner's preferences or an animation frame.
    for (const [name, viewport] of [
      ['desktop.png', { width: 1440, height: 1000 }],
      ['mobile.png', { width: 390, height: 844 }],
    ]) {
      await page.setViewportSize(viewport);
      await page.goto(url);
      await capture(name);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(url);
    await waitForState();
    const index = await page.locator('#catalog-data').textContent().then(JSON.parse);
    // The runtime embeds only its filter fields. Inspect the complete downloadable
    // catalog separately so artwork/evidence checks cannot silently lose coverage.
    const catalogResponse = await context.request.get(new URL('catalog.json', page.url()).href);
    assert.ok(catalogResponse.ok(), 'Full catalog download is available');
    const data = await catalogResponse.json();
    assert.deepEqual(index.projects.map(project => project.id), data.projects.map(project => project.id));
    assert.equal(index.metrics_as_of, data.metrics_as_of);
    assert.ok(JSON.stringify(index).length < JSON.stringify(data).length / 2, 'Compact runtime index');
    report.sourceSha = data.source_sha;
    writeReport();
    if (process.env.SITE_SOURCE_SHA) assert.equal(data.source_sha, process.env.SITE_SOURCE_SHA, 'Browser must test the generated checkout');
    // Deterministically exercise the first and last entries of the random background pool.
    const backgrounds = data.footer_backgrounds || [];
    if (backgrounds.length) {
      await page.addInitScript(() => { Math.random = () => Number(sessionStorage.getItem('footer-test-random') || 0); });
      for (const [random, index] of [[0, 0], [.999999, backgrounds.length - 1]]) {
        await page.evaluate(value => sessionStorage.setItem('footer-test-random', String(value)), random);
        await page.goto(url);
        const art = page.locator('[data-footer-background]');
        await art.scrollIntoViewIfNeeded();
        await art.evaluate(image => image.decode());
        assert.ok((await art.getAttribute('src')).endsWith(backgrounds[index]));
        await capture('footer-background-' + index + '.png');
      }
      await page.setViewportSize({width:390,height:1000});
      await page.locator('#about').scrollIntoViewIfNeeded();
      await assertLedgerFits(page, 'footer artwork mobile');
      await capture('footer-mobile.png');
      await page.setViewportSize({width:1440,height:1000});
      await page.goto(url);
      await waitForState();
    }
    assert.equal(await visible(), data.projects.length);
    assert.equal(await page.locator('#sort-order').isEnabled(), true);
    assert.equal(await page.locator('.specimen-drawer').count(), data.projects.length);
    await assertLedgerFits(page, 'desktop');
    assert.equal(await page.locator('#search').getAttribute('placeholder'), null);
    assert.equal(await page.locator('#search').evaluate(n => getComputedStyle(n).borderBottomStyle), 'dashed');
    assert.equal(await page.locator('.ledger-columns, .ledger-heading').count(), 0);
    assert.deepEqual(await page.locator('.header-links a').allTextContents(), ['Ledger', 'About', 'Observatory', 'GitHub']);
    assert.deepEqual(await page.locator('.footer-actions a').allTextContents(), ['Submit a project', 'Download', 'Top']);
    assert.ok(await page.locator('.footer-baseline').textContent().then(t => t.includes(data.projects.length + ' Projects')));
    const absentLicense = data.projects.find(p => !p.github || !p.github.license);
    if (absentLicense) assert.equal(await page.locator('#project-' + absentLicense.id + ' .license-readout').textContent(), '');
    assert.ok(await page.locator('.specimen-drawer > summary').first().evaluate(n => n.getBoundingClientRect().height <= 50), 'Compact one-line row');

    // Exact reviewed alternative search, combined metadata filters, empty/reset.
    await change('search', 'NotebookLM');
    assert.ok(await visible() > 0);
    assert.ok((await page.locator('.project-card:not([hidden])').allTextContents()).every(text => text.includes('NotebookLM')));
    await page.locator('#clear-filters').click();
    await select('category-filter', 'developer-tools');
    await page.locator('#license-filter').selectOption('known');
    await change('min-stars', '100');
    await change('pushed-since', '2025-01-01');
    const expected = await page.evaluate(() => {
      const data = JSON.parse(document.querySelector('#catalog-data').textContent);
      const state = OpenCatalog.normalizeState(new URL(location.href).searchParams, data);
      return OpenCatalog.selectProjects(data.projects, state, data).map(project => project.id);
    });
    assert.deepEqual(await page.locator('.project-card:not([hidden])').evaluateAll(nodes => nodes.map(node => node.dataset.projectId)), expected);
    await change('search', 'no-project-could-match-this-string-98273');
    assert.equal(await visible(), 0);
    assert.equal(await page.locator('#empty-state').isVisible(), true);
    await page.locator('#clear-filters').click();
    await page.locator('#clear-filters').click();
    assert.equal(await visible(), data.projects.length);

    // Snapshot-relative filters, exact alternatives and honest missing metrics.
    for (const value of ['recent', 'older', 'unknown']) {
      await select('push-window', value);
      const expectedCount = await page.evaluate(value => {
        const data = JSON.parse(document.querySelector('#catalog-data').textContent);
        return OpenCatalog.diagnosticCounts(data.projects, data)[value];
      }, value);
      assert.equal(await visible(), expectedCount);
    }
    await page.locator('#clear-filters').click();
    await select('alternative-filter', 'NotebookLM');
    assert.equal(await visible(), data.projects.filter(project => project.alternatives.some(item => item.name === 'NotebookLM')).length);
    await page.locator('#clear-filters').click();
    await select('metrics-filter', 'missing');
    assert.equal(await visible(), data.projects.filter(project => !project.github).length);
    await page.locator('#clear-filters').click();

    // Explicit zero still means known stars; unknowns cannot pass the threshold.
    await change('min-stars', '0');
    assert.equal(await visible(), data.projects.filter(project => project.github).length);
    await page.locator('#clear-filters').click();

    // Sorting, shareable URLs, Back/Forward, and cancellation of a pending search.
    await page.locator('#sort-order').selectOption('stars');
    const highest = data.projects.filter(project => project.github).sort((a, b) => b.github.stars - a.github.stars)[0];
    assert.equal(await page.locator('.project-card:not([hidden])').first().getAttribute('data-project-id'), highest.id);
    await page.locator('#sort-order').selectOption('pushed');
    const newest = data.projects.filter(project => project.github && project.github.pushed_at).sort((a, b) => Date.parse(b.github.pushed_at) - Date.parse(a.github.pushed_at))[0];
    assert.equal(await page.locator('.project-card:not([hidden])').first().getAttribute('data-project-id'), newest.id);
    await page.locator('#clear-filters').click();
    await change('search', 'OpenTofu');
    const savedURL = page.url();
    const savedCount = await visible();
    await select('category-filter', 'infrastructure--devops');
    await page.locator('#search').fill('a pending search that must be cancelled');
    await page.goBack();
    await page.waitForTimeout(400);
    assert.equal(page.url(), savedURL);
    assert.equal(await page.locator('#search').inputValue(), 'OpenTofu');
    assert.equal(await visible(), savedCount);
    await page.goForward();
    assert.equal(await page.locator('#category-filter').inputValue(), 'infrastructure--devops');
    await page.reload();
    await waitForState();
    assert.equal(await page.locator('#search').inputValue(), 'OpenTofu');
    assert.equal(await page.locator('#category-filter').inputValue(), 'infrastructure--devops');
    const firstDrawer = page.locator('.project-card:not([hidden]) .specimen-drawer').first();
    await firstDrawer.locator(':scope > summary').click();
    assert.equal(await firstDrawer.evaluate(node => node.open), true);
    const permalink = await page.locator('.project-card:not([hidden]) .permalink').first().getAttribute('href');
    await page.locator('.project-card:not([hidden]) .permalink').first().click();
    assert.equal(new URL(page.url()).hash, permalink);
    await page.locator('#clear-filters').click();
    assert.equal(new URL(page.url()).hash, permalink);

    // Direct links open the drawer and focus its native summary. A conflicting
    // filter keeps its state and explains the hidden target instead of clearing it.
    const target = data.projects.find(project => project.github);
    const direct = new URL(url);
    direct.hash = '#project-' + target.id;
    await page.goto(direct.href);
    await waitForState();
    const linked = page.locator('#project-' + target.id + ' .specimen-drawer');
    assert.equal(await linked.evaluate(node => node.open), true);
    assert.equal(await page.locator(':focus').evaluate(node => node.parentElement.className), 'specimen-drawer');
    direct.searchParams.set('metrics', 'missing');
    await page.goto(direct.href);
    await waitForState();
    assert.equal(await page.locator('#project-link-notice').isVisible(), true);
    assert.equal(await page.locator('#project-' + target.id).isVisible(), false);
    assert.equal(new URL(page.url()).searchParams.get('metrics'), 'missing');
    await page.locator('#clear-filters').click();
    assert.equal(await page.locator('#project-link-notice').isVisible(), false);
    assert.equal(await linked.evaluate(node => node.open), true);

    // Keyboard entry points and responsive category disclosure.
    await page.goto(url);
    await waitForState();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('class'), 'skip-link');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'catalog');
    await page.locator('#search').focus();
    await page.keyboard.type('OpenTofu');
    await page.waitForTimeout(350);
    assert.equal(await page.locator(':focus').getAttribute('id'), 'search');
    assert.ok(await visible() > 0);
    await page.locator('#clear-filters').click();
    const keyboardDrawer = page.locator('.specimen-drawer').first();
    await keyboardDrawer.locator(':scope > summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await keyboardDrawer.evaluate(node => node.open), true);
    await page.keyboard.press('Enter');
    assert.equal(await keyboardDrawer.evaluate(node => node.open), false);
    for (const width of [390, 320, 601, 640, 700, 720, 721, 768, 900, 901]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(url);
      await waitForState();
      await assertLedgerFits(page, `${width}px`);
      const controls = await page.locator('.category-panel > summary, .filter-options > summary').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().top));
      assert.ok(Math.abs(controls[0] - controls[1]) < 2, 'Category and filter buttons share a row');
      assert.ok(await page.locator('.project-card').first().evaluate(node => { const hero=document.querySelector('.jar-hall'); return node.getBoundingClientRect().top-(hero?hero.getBoundingClientRect().bottom:0)<500; }), 'Ledger starts promptly after the hero');
      assert.equal(await page.locator('.brand-mark').evaluate(node => node.getBoundingClientRect().width), 64);
      assert.equal(await page.locator('.leader-label').allTextContents().then(labels => labels.some(text => text.includes('Top 3 by stars'))), false);
      await page.locator('.filter-options > summary').click();
      assert.equal(await page.locator('#push-window').isVisible(), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Expanded filters fit');
      await page.locator('.category-panel > summary').click();
      assert.equal(await page.locator('.filter-options').evaluate(node => node.open), false);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Expanded categories fit');
      await page.locator('.category-panel > summary').click();
      if (width === 390) {
        assert.equal(await page.locator('.category-panel').getAttribute('open'), null);
        await page.locator('.category-panel summary').click();
        assert.equal(await page.locator('.category-panel').evaluate(node => node.open), true);
        await page.locator('.category-panel summary').click();
      }
    }
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    await assertLedgerFits(page, '200% root text size');

    // Expanded content must remain usable across the former two-column breakpoint.
    // Checking only page overflow misses zero-width diagnostics hidden by clipping.
    const tofu = data.projects.find(project => project.url === 'https://github.com/opentofu/opentofu');
    assert.ok(tofu?.hn && tofu.star_history?.chart_url && tofu.deployment && tofu.function_summary,
      'OpenTofu covers Function, both cached charts, and reviewed setup');
    for (const width of [320, 390, 900, 901, 1024, 1180, 1200, 1201, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      const expandedURL = new URL(url);
      expandedURL.searchParams.set('q', tofu.name);
      expandedURL.hash = '#project-' + tofu.id;
      await page.goto(expandedURL.href);
      await waitForState();
      const card = page.locator('#project-' + tofu.id);
      const drawer = card.locator('.specimen-drawer');
      assert.equal(await drawer.evaluate(node => node.open), true);
      const catalogWidth = await page.locator('#catalog').evaluate(node => node.getBoundingClientRect().width);
      assert.ok(catalogWidth >= width - 100, `Catalog uses available width at ${width}px`);
      const diagnostics = card.locator('.diagnostics');
      assert.ok(await diagnostics.evaluate(node => node.getBoundingClientRect().width) >= 200,
        `Readable diagnostics at ${width}px`);
      assert.equal(await card.locator('.function-detail > p').first().textContent(), tofu.function_summary.text);
      for (const selector of ['.signal:not(.star-history) .hn-chart img', '.star-chart img']) {
        const chart = card.locator(selector);
        await chart.scrollIntoViewIfNeeded();
        await chart.evaluate(image => image.decode());
        assert.equal(await chart.isVisible(), true, `Visible ${selector} at ${width}px`);
        assert.ok(await chart.evaluate(image => image.complete && image.naturalWidth === 120 &&
          image.getBoundingClientRect().width >= 120 && image.getBoundingClientRect().height >= 24),
          `Loaded, non-collapsed ${selector} at ${width}px`);
      }
      const setup = card.locator('.deployment-evidence details');
      await setup.locator(':scope > summary').click();
      assert.equal(await setup.evaluate(node => node.open), true);
      assert.equal(await setup.locator('.deployment-group').first().isVisible(), true);
      await assertLedgerFits(page, `expanded OpenTofu at ${width}px`);
      const clipped = await card.locator('.specimen-interior, .diagnostics, .function-detail, .evidence-note, .deployment-evidence, .deployment-group')
        .evaluateAll(nodes => nodes.filter(node => {
          const rect = node.getBoundingClientRect();
          return rect.width <= 0 || rect.left < -1 || rect.right > innerWidth + 1 || node.scrollWidth > node.clientWidth + 1;
        }).map(node => node.className));
      assert.deepEqual(clipped, [], `Expanded sections fit at ${width}px`);
      await diagnostics.scrollIntoViewIfNeeded();
      await capture(`expanded-opentofu-${width}.png`);
      await setup.locator(':scope > summary').click();
      assert.equal(await setup.evaluate(node => node.open), false);
      await drawer.locator(':scope > summary').click();
      assert.equal(await diagnostics.isVisible(), false);
      await drawer.locator(':scope > summary').click();
      assert.equal(await diagnostics.isVisible(), true);
    }

    // Ledger-first layout and optional art work without animation dependencies.
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(url);
    await waitForState();
    assert.equal(await page.locator('.hero, .reading-room, .collection-band').count(), 0);
    assert.equal(await page.locator('.specimen-caption h3').count(), 0);
    const traced = data.projects.find(p => p.hn);
    const tracedCard = page.locator('#project-' + traced.id);
    assert.ok(await tracedCard.locator('.name-sparkline').isVisible());
    await tracedCard.locator('.name-sparkline').evaluate(image => image.decode());
    await tracedCard.locator('.specimen-drawer').evaluate(node => { node.open = true; });
    assert.equal(await tracedCard.locator('.name-sparkline').isVisible(), false);
    assert.ok(await tracedCard.locator('.signal.evidence-note:not(.star-history)').isVisible());
    await tracedCard.locator('.specimen-drawer').evaluate(node => { node.open = false; });

    assert.equal(await page.locator('script[src*="gsap"], script[src*="ScrollTrigger"]').count(), 0);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.locator('html').evaluate(node => getComputedStyle(node).scrollBehavior), 'auto');
    for (const project of data.projects.filter(p => p.artwork)) {
      await change('search', project.name);
      const card = page.locator('#project-' + project.id);
      await card.locator('summary').first().click();
      assert.equal(await card.locator('details.specimen-drawer').evaluate(node => node.open), true, 'Click after search must open ' + project.name);
      if (project.function_summary) {
        assert.equal(await card.locator('.function-detail > p').first().textContent(), project.function_summary.text);
        assert.ok(await card.locator('.function-provenance a').count() > 0);
        assert.ok((await card.locator('.description').textContent()).includes(project.description));
      } else {
        assert.equal(await card.locator('.function-detail').count(), 0);
      }
      const image = card.locator('.specimen-art img');
      await image.scrollIntoViewIfNeeded();
      await page.waitForFunction(id => { const img = document.querySelector('#project-' + id + ' .specimen-art img'); return img && img.complete && img.naturalWidth > 0; }, project.id, { timeout: 10000 });
      assert.equal(await image.evaluate(img => img.naturalWidth > 0), true);
      await capture('specimen-' + project.name.toLowerCase() + '.png');
    }
    await page.locator('#clear-filters').click();
    const crossListed = data.projects.find(p => p.leader_categories.length && p.categories.some(c => !p.leader_categories.includes(c)));
    assert.ok(crossListed, 'Fixture needs a project leading only some of its categories');
    await select('category-filter', crossListed.leader_categories[0]);
    assert.equal(await page.locator('#project-' + crossListed.id).getAttribute('data-leader'), 'true');
    await select('category-filter', crossListed.categories.find(c => !crossListed.leader_categories.includes(c)));
    assert.equal(await page.locator('#project-' + crossListed.id).getAttribute('data-leader'), 'false');
    await page.locator('#clear-filters').click();
    const noArt = data.projects.find(p => !p.artwork);
    assert.equal(await page.locator('#project-' + noArt.id + ' .specimen-art').count(), 0);

    // Open sheets must retain their hierarchy and fit at narrow widths.
    const sheetCases = [
      ['full', data.projects.find(p => p.artwork && p.signals?.scorecard?.last_good)],
      ['sparse', data.projects.find(p => !p.github)],
      ['no-art', noArt],
    ].filter(([, project]) => project);
    for (const [kind, project] of sheetCases) {
      await change('search', project.name);
      const card = page.locator('#project-' + project.id);
      await card.locator('details.specimen-drawer').evaluate(node => { node.open = true; });
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({width, height:1000});
        await card.scrollIntoViewIfNeeded();
        await assertLedgerFits(page, 'open specimen ' + kind + ' at ' + width);
        assert.equal(await card.locator('.specimen-art figcaption').count(), 0);
        assert.ok(!await card.textContent().then(text => text.includes('Unknown values indicate missing cached data.')));
        if (width !== 320) await capture('sheet-' + kind + '-' + width + '.png');
      }
    }
    await page.setViewportSize({width:1440, height:1000});

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await noJS.newPage();
    await fallback.goto(url);
    assert.equal(await fallback.locator('.project-card').count(), data.projects.length);
    assert.equal(await fallback.locator('#filters').isVisible(), false);
    assert.equal(await fallback.locator('#sort-order').isDisabled(), true);
    assert.equal(await fallback.locator('.no-script').isVisible(), true);
    await assertLedgerFits(fallback, 'no JavaScript');
    await fallback.locator('.specimen-drawer').first().locator(':scope > summary').click();
    assert.equal(await fallback.locator('.specimen-drawer').first().locator('.plate-departure > a').isVisible(), true);
    await noJS.close();

    // The downloadable HTML must load without any neighboring runtime assets.
    const standaloneURL = new URL('standalone.html', page.url());
    await page.goto(standaloneURL.href);
    await waitForState();
    assert.equal(await visible(), data.projects.length);
    assert.equal(await page.locator('script[src^="data:text/javascript;base64,"]').count(), 1);
    const expectedDownloads = ['catalog.json', 'hn_evidence.json', 'alternatives.json'];
    if (fs.existsSync(path.resolve(__dirname, '../data/project_signals.json'))) expectedDownloads.push('project_signals.json');
    if (data.projects.some(p => p.star_history)) expectedDownloads.push('star_history.json');
    const downloads = await page.locator('a[download]').evaluateAll(nodes => nodes.map(node => ({
      name: node.getAttribute('download'), href: node.getAttribute('href'),
    })));
    assert.deepEqual(downloads.map(item => item.name).sort(), expectedDownloads.sort());
    assert.ok(downloads.every(item => item.href.startsWith('data:application/json;base64,')));
    await change('search', 'OpenTofu');
    assert.ok(await visible() > 0);
    await require('./check_deployment_browser.cjs')({ page, browser, url, data, capture });
    assert.deepEqual(errors, []);
    await require('./check_star_history_browser.cjs')({ page, url, data, capture });
    await require('./check_plate_browser.cjs')({ page, url, data, capture });
    await require('./check_observatory_browser.cjs')({ browser, url });
    assert.deepEqual(errors, []);
    report.status = 'passed';
    writeReport();
    console.log(JSON.stringify(report, null, 2));
    if (process.env.GITHUB_STEP_SUMMARY) {
      fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
        '## Field-guide browser check\n\nPassed against generated revision `' + report.sourceSha + '`' +
        ' (PR head `' + report.prHeadSha + '`).\n\n' +
        'Download `field-guide-browser-screenshots` for desktop.png (1440 × 1000), mobile.png (390 × 844), ' +
        'screenshots.json, and browser/server logs.\n');
    }
    console.log(JSON.stringify({ status: 'passed', projects: data.projects.length, screenshots: output,
      checks: ['search', 'combined filters', 'snapshot windows', 'exact alternatives', 'missing metrics', 'zero threshold', 'sorts', 'empty/reset', 'URL reload', 'Back/Forward race', 'permalinks', 'filtered-out deep links', 'keyboard disclosures', 'responsive boundaries 320–1440px', '200% root text size', 'reduced motion', 'category-aware leaders', 'optional specimen artwork', 'no-JS drawers', 'standalone', 'no page errors'] }, null, 2));
  } catch (error) {
    report.status = 'failed';
    report.error = error.message;
    await capture('failure.png').catch(() => {});
    writeReport();
    console.error(JSON.stringify(report, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
