/* Optional browser smoke test. Requires Playwright and its Chromium browser.
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
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const url = process.env.SITE_URL || 'http://127.0.0.1:8000';
  const visible = () => page.locator('.project-card:not([hidden])').count();
  const change = async (id, value) => {
    if (['category-filter', 'metrics-filter', 'min-stars', 'pushed-since'].includes(id)) {
      if (!await page.locator('.more-filters').evaluate(node => node.open)) {
        await page.locator('.more-filters > summary').click();
      }
    }
    await page.locator('#' + id).fill(value);
    await page.locator('#' + id).dispatchEvent('change');
  };
  const select = async (id, value) => {
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
    await page.goto(url);
    await waitForState();
    const data = await page.locator('#catalog-data').textContent().then(JSON.parse);
    assert.equal(await visible(), data.projects.length);
    assert.equal(await page.locator('#sort-order').isEnabled(), true);
    assert.equal(await page.locator('.specimen-drawer').count(), data.projects.length);
    await assertLedgerFits(page, 'desktop');
    await page.screenshot({ path: path.join(output, 'desktop.png') });

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
    await firstDrawer.locator('summary').click();
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
    await keyboardDrawer.locator('summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await keyboardDrawer.evaluate(node => node.open), true);
    await page.keyboard.press('Enter');
    assert.equal(await keyboardDrawer.evaluate(node => node.open), false);
    for (const width of [390, 320, 601, 640, 700, 720, 721, 768, 900, 901]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(url);
      await waitForState();
      await assertLedgerFits(page, `${width}px`);
      if (width === 390) {
        assert.equal(await page.locator('.category-panel').getAttribute('open'), null);
        await page.locator('.category-panel summary').click();
        assert.equal(await page.locator('.category-panel').evaluate(node => node.open), true);
        await page.locator('.category-panel summary').click();
        await page.screenshot({ path: path.join(output, 'mobile.png') });
      }
    }
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    await assertLedgerFits(page, '200% root text size');

    // Optional GSAP behavior must revert pins when reduced motion is requested.
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(url);
    await waitForState();
    await page.waitForFunction(() => window.ScrollTrigger && ScrollTrigger.getAll().length > 0);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForFunction(() => ScrollTrigger.getAll().length === 0);
    assert.equal(await page.locator('.pin-spacer').count(), 0);
    assert.equal(await page.locator('html').evaluate(node => getComputedStyle(node).scrollBehavior), 'auto');
    assert.equal(await page.locator('.observation-sheet').count(), 3);
    assert.equal(await visible(), data.projects.length);

    // A missing animation dependency cannot disable the catalog enhancement.
    const blockedMotion = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const plain = await blockedMotion.newPage();
    await plain.route('**/vendor/{gsap.min.js,ScrollTrigger.min.js}', route => route.abort());
    await plain.goto(url);
    await plain.waitForFunction(() => document.querySelector('#filters').dataset.enhanced === 'true');
    assert.equal(await plain.locator('.project-card:not([hidden])').count(), data.projects.length);
    await plain.locator('#search').fill('OpenTofu');
    await plain.locator('#search').dispatchEvent('change');
    assert.ok(await plain.locator('.project-card:not([hidden])').count() > 0);
    await blockedMotion.close();

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await noJS.newPage();
    await fallback.goto(url);
    assert.equal(await fallback.locator('.project-card').count(), data.projects.length);
    assert.equal(await fallback.locator('#filters').isVisible(), false);
    assert.equal(await fallback.locator('#sort-order').isDisabled(), true);
    assert.equal(await fallback.locator('.no-script').isVisible(), true);
    await assertLedgerFits(fallback, 'no JavaScript');
    await fallback.locator('.specimen-drawer').first().locator('summary').click();
    assert.equal(await fallback.locator('.specimen-drawer').first().locator('.source-link').isVisible(), true);
    await noJS.close();

    // The downloadable HTML must load without any neighboring runtime assets.
    const standaloneURL = new URL('standalone.html', page.url());
    await page.goto(standaloneURL.href);
    await waitForState();
    assert.equal(await visible(), data.projects.length);
    assert.equal(await page.locator('script[src^="data:text/javascript;base64,"]').count(), 4);
    assert.equal(await page.locator('a[download]').count(), 3);
    await change('search', 'OpenTofu');
    assert.ok(await visible() > 0);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'passed', projects: data.projects.length, screenshots: output,
      checks: ['search', 'combined filters', 'snapshot windows', 'exact alternatives', 'missing metrics', 'zero threshold', 'sorts', 'empty/reset', 'URL reload', 'Back/Forward race', 'permalinks', 'filtered-out deep links', 'keyboard disclosures', 'responsive boundaries 320–1440px', '200% root text size', 'reduced motion', 'missing GSAP', 'no-JS drawers', 'standalone', 'no page errors'] }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
