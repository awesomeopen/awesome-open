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
    await page.locator('#' + id).fill(value);
    await page.locator('#' + id).dispatchEvent('change');
  };
  const waitForState = () => page.waitForFunction(() => document.querySelector('#filters').dataset.enhanced === 'true');
  try {
    await page.goto(url);
    await waitForState();
    const data = await page.locator('#catalog-data').textContent().then(JSON.parse);
    assert.equal(await visible(), data.projects.length);
    assert.equal(await page.locator('#sort-order').isEnabled(), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(output, 'desktop.png') });

    // Exact reviewed alternative search, combined metadata filters, empty/reset.
    await change('search', 'NotebookLM');
    assert.ok(await visible() > 0);
    assert.ok((await page.locator('.project-card:not([hidden])').allTextContents()).every(text => text.includes('NotebookLM')));
    await page.locator('#clear-filters').click();
    await page.locator('#category-filter').selectOption('developer-tools');
    await page.locator('#license-filter').selectOption('known');
    await change('min-stars', '100');
    await change('pushed-since', '2025-01-01');
    const expected = await page.evaluate(() => {
      const data = JSON.parse(document.querySelector('#catalog-data').textContent);
      const state = OpenCatalog.normalizeState(new URL(location.href).searchParams, data);
      return OpenCatalog.selectProjects(data.projects, state).map(project => project.id);
    });
    assert.deepEqual(await page.locator('.project-card:not([hidden])').evaluateAll(nodes => nodes.map(node => node.dataset.projectId)), expected);
    await change('search', 'no-project-could-match-this-string-98273');
    assert.equal(await visible(), 0);
    assert.equal(await page.locator('#empty-state').isVisible(), true);
    await page.locator('#clear-filters').click();
    await page.locator('#clear-filters').click();
    assert.equal(await visible(), data.projects.length);

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
    await page.locator('#category-filter').selectOption('infrastructure--devops');
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
    const permalink = await page.locator('.project-card:not([hidden]) .permalink').first().getAttribute('href');
    await page.locator('.project-card:not([hidden]) .permalink').first().click();
    assert.equal(new URL(page.url()).hash, permalink);
    await page.locator('#clear-filters').click();
    assert.equal(new URL(page.url()).hash, permalink);

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
    for (const width of [390, 320, 768]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(url);
      await waitForState();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Horizontal overflow at ${width}px`);
      if (width === 390) {
        assert.equal(await page.locator('.category-panel').getAttribute('open'), null);
        await page.locator('.category-panel summary').click();
        assert.equal(await page.locator('.category-panel').evaluate(node => node.open), true);
        await page.locator('.category-panel summary').click();
        await page.screenshot({ path: path.join(output, 'mobile.png') });
      }
    }
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'Text zoom overflow');

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await noJS.newPage();
    await fallback.goto(url);
    assert.equal(await fallback.locator('.project-card').count(), data.projects.length);
    assert.equal(await fallback.locator('#filters').isVisible(), false);
    assert.equal(await fallback.locator('#sort-order').isDisabled(), true);
    assert.equal(await fallback.locator('.no-script').isVisible(), true);
    assert.equal(await fallback.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await noJS.close();
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'passed', projects: data.projects.length, screenshots: output,
      checks: ['search', 'combined filters', 'zero threshold', 'sorts', 'empty/reset', 'URL reload', 'Back/Forward race', 'permalinks', 'keyboard', '320/390/768px', '200% text', 'no-JS', 'no page errors'] }, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
