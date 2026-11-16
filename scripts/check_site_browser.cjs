/* Browser smoke test, run by the PR preview workflow. Requires Playwright and Chromium.
 * Usage: SITE_URL=http://127.0.0.1:8000 node scripts/check_site_browser.cjs
 * CHROMIUM_PATH can point to an installed Chromium; screenshots go to tmp/site-qa.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const group = process.argv[2] || 'core';
  const groups = ['core', 'aliases', 'bounds', 'details', 'footer', 'deployment', 'star-history', 'plates', 'history'];
  assert.ok(groups.includes(group), 'Unknown core group');
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
  const report = { status: 'running', group, url, sourceSha: null,
    prHeadSha: process.env.PR_HEAD_SHA || null, planId: require('./browser_capture.cjs').plan?.planId || null, screenshots: [], skippedScreenshots: [] };
  const writeReport = () => fs.writeFileSync(path.join(output, group === 'core' ? 'screenshots.json' : group + '-screenshots.json'), JSON.stringify(report, null, 2) + '\n');
  const capture = async (name, target = page) => {
    if (!require('./browser_capture.cjs').review(name)) {
      report.skippedScreenshots.push({ file: name, reason: 'Unchanged component; assertions retained' });
      writeReport();
      return;
    }
    await target.evaluate(() => document.fonts.ready);
    const png = await target.screenshot({ path: path.join(output, name), animations: 'disabled', caret: 'hide', scale: 'css' });
    const dimensions = { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
    assert.deepEqual(dimensions, target.viewportSize(), `Screenshot dimensions: ${name}`);
    report.screenshots.push({ file: name, ...dimensions, bytes: png.length });
    writeReport();
  };
  const visible = () => page.locator('#rows .row:not([hidden])').count();
  const visibleIds = target => target.locator('#rows .row:not([hidden])').evaluateAll(rows => rows.map(row => row.dataset.id));
  const assertVisiblePositions = async (target, label) => {
    const numbers = await target.locator('#rows .row:not([hidden]) .row-n').allTextContents();
    assert.deepEqual(numbers, numbers.map((_, i) => String(i + 1).padStart(3, '0')), label + ': contiguous visible positions');
  };
  // Rows keep their record identity whatever the order or filter.
  const assertRowIdentities = async (target, data, label) => {
    const rows = await target.locator('#rows .row').evaluateAll(nodes => nodes.map(row => ({
      id: row.dataset.id, href: row.querySelector('a').getAttribute('href'), name: row.querySelector('.specimen-name').textContent })));
    assert.equal(rows.length, data.projects.length, label + ': every row retained');
    const byId = new Map(rows.map(row => [row.id, row]));
    for (const project of data.projects) {
      const row = byId.get(project.id);
      assert.ok(row, label + ': row for ' + project.name);
      assert.equal(row.href, 'records/' + project.id + '.html', label + ': static record link');
      assert.equal(row.name, project.name, label + ': name');
    }
  };
  const waitForPlate = () => page.locator('#pane-scroll .specimen-plate').waitFor({ state: 'visible' });
  const openMore = async () => {
    if (!await page.locator('.rail-more').evaluate(node => node.open)) await page.locator('.rail-more > summary').click();
  };
  const change = async (id, value) => {
    if (['f-stars', 'f-pushed'].includes(id)) await openMore();
    await page.locator('#' + id).fill(value);
    if (id === 'search') {
      await page.waitForFunction(value => (new URL(location.href).searchParams.get('q') || '') === value, value);
      if (value) await page.waitForFunction(() => document.querySelector('#filters').dataset.searchText === 'ready');
    } else await page.locator('#' + id).dispatchEvent('change');
  };
  const select = async (id, value) => {
    if (['f-install', 'f-metrics'].includes(id)) await openMore();
    await page.locator('#' + id).selectOption(value);
  };
  const reset = async () => { if (await page.locator('#reset').isEnabled()) await page.locator('#reset').click(); };
  const category = async id => page.locator(`#rail-cats a[data-category="${id}"]`).click();
  const waitForState = () => page.waitForFunction(() => document.querySelector('#filters')?.dataset.enhanced === 'true');
  const checkReviewedAliases = async (label, data) => {
    const obsId = '0e1c34b3f948e9037466f84680e402b96f2c0b61351865137c4359f41e5d3014';
    const record = data.projects.find(p => p.url === 'https://github.com/obsproject/obs-studio');
    assert.ok(record && record.name === 'OBS Studio');
    assert.equal(record.id, obsId);
    for (const query of ['Open Broadcaster Software', 'obs', 'OBS streaming']) {
      await change('search', query);
      // Reviewed names rank first; summary text can add weaker matches below.
      assert.equal((await visibleIds(page))[0], record.id, label + ': ' + query);
      assert.equal(new URL(page.url()).searchParams.get('q'), query);
    }
    await page.locator(`#rows .row[data-id="${record.id}"] > a`).click();
    await waitForPlate();
    assert.equal(await page.locator('#plate-name').textContent(), 'OBS Studio');
    await capture('aliases-' + label + '.png');
    await page.keyboard.press('Escape');
    await change('search', '');
    assert.equal(await visible(), data.projects.length);
  };
  // The page itself never scrolls sideways, and list rows stay inside their column.
  const assertLedgerFits = async (target, label) => {
    assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Horizontal overflow: ${label}`);
    const clipped = await target.locator('#rows .row:not([hidden])').first().locator('a > *').evaluateAll(nodes =>
      nodes.filter(node => {
        const rect = node.getBoundingClientRect();
        return rect.width > 0 && (rect.left < -1 || rect.right > innerWidth + 1);
      }).map(node => node.className));
    assert.deepEqual(clipped, [], `Clipped list cells: ${label}`);
  };
  try {
    // Capture both viewports before assertions so a later failure retains useful
    // review artifacts. Fixed motion, fonts, pixel scale, locale and theme avoid
    // screenshots depending on a runner's preferences or an animation frame.
    if (group === 'core') for (const [name, viewport] of [
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
    if (group === 'core') {
      const evidenceLink = await page.locator('#hn-evidence').getAttribute('href');
      const response = await context.request.get(new URL(evidenceLink, page.url()).href);
      assert.ok(response.ok(), 'HN evidence download is available');
      const published = await response.json();
      const source = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../data/hn_evidence.json'), 'utf8'));
      assert.equal(published.schema_version, 3);
      assert.equal(published.source_schema_version, source.schema_version);
      assert.deepEqual(published.projects, source.projects, 'Browser consumers retain complete HN projects');
      for (const entry of Object.values(published.queue || {})) {
        const good = entry.last_good;
        if (good && Object.hasOwn(good, 'project_ref')) {
          assert.ok(Number.isInteger(good.project_ref) && good.project_ref >= 0 && good.project_ref < published.projects.length);
          assert.ok(!Object.hasOwn(good, 'project'));
          good.project = structuredClone(published.projects[good.project_ref]);
          delete good.project_ref;
        }
      }
      published.schema_version = published.source_schema_version;
      delete published.source_schema_version;
      assert.deepEqual(published, source, 'Downloaded HN recovery evidence reconstructs exactly');
    }
    assert.deepEqual(index.projects.map(project => project.id), data.projects.map(project => project.id));
    assert.equal(index.metrics_as_of, data.metrics_as_of);
    assert.ok(JSON.stringify(index).length < JSON.stringify(data).length / 2, 'Compact runtime index');
    report.sourceSha = data.source_sha;
    writeReport();
    if (process.env.SITE_SOURCE_SHA) assert.equal(data.source_sha, process.env.SITE_SOURCE_SHA, 'Browser must test the generated checkout');
    if (group !== 'core') {
      const modules = { aliases: 'aliases', bounds: 'specimen_bounds', details: 'lazy_details',
        footer: 'footer', deployment: 'deployment', 'star-history': 'star_history', plates: 'plate', history: 'history' };
      report.result = await require('./check_' + modules[group] + '_browser.cjs')({ page, context, browser, url, data, capture });
      assert.deepEqual(errors, []);
      report.status = 'passed';
      writeReport();
      return;
    }
    // Three columns fill one desktop screen; the page itself never scrolls.
    const layout = await page.evaluate(() => {
      const box = selector => document.querySelector(selector).getBoundingClientRect();
      return { rail: box('.rail').width, list: box('.list').left, pane: box('.pane').left,
        scroll: document.documentElement.scrollHeight <= innerHeight, bars: document.querySelectorAll('.app-header, .app-status, .site-header, .site-footer').length };
    });
    assert.equal(layout.rail, 208, 'Rail width');
    assert.ok(layout.list === 208 && layout.pane > layout.list, 'Rail, list and pane sit side by side');
    assert.equal(layout.scroll, true, 'The page fits the viewport; columns scroll inside');
    assert.equal(layout.bars, 0, 'No top or bottom bar');
    assert.equal(await page.locator('#search').getAttribute('placeholder'), null, 'The search field is empty until the reader types');
    assert.equal(await page.locator('#list-brand').textContent(), 'Awesome Open*');
    assert.equal(await page.locator('.rail-mark img').getAttribute('src'), 'brand/botanical-128.png');
    assert.ok(await page.locator('#rows .row .row-desc').first().evaluate(n => n.getBoundingClientRect().height <= parseFloat(getComputedStyle(n).lineHeight) + 1),
      'One-line description');
    await assertLedgerFits(page, 'desktop');

    // Rail: All and the categories by name; counts follow search and filters.
    const rail = await page.locator('#rail-cats a').evaluateAll(links => links.map(a => ({ id: a.dataset.category, name: a.firstElementChild.textContent })));
    assert.deepEqual(rail.map(item => item.id), ['', ...data.categories.slice().sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase())).map(c => c.id)]);
    assert.deepEqual(rail.slice(1).map(item => item.name), rail.slice(1).map(item => data.categories.find(c => c.id === item.id).name));
    await category('developer-tools');
    assert.equal(await visible(), data.projects.filter(project => project.categories.includes('developer-tools')).length);
    assert.equal(await page.locator('#rail-cats a[data-category="developer-tools"]').getAttribute('aria-current'), 'true');
    assert.equal(await page.locator('#rail-cats a[aria-current="true"] span').first().evaluate(n => getComputedStyle(n).textTransform), 'uppercase');
    assert.ok((await page.locator('#end-mark').getAttribute('src')).endsWith('developer-tools-m.webp'));
    assert.equal(await page.locator('#end-mark').getAttribute('width'), '207');
    assert.equal(new URL(page.url()).searchParams.get('category'), 'developer-tools');
    await category('');
    assert.equal(await page.locator('#end-mark').getAttribute('src'), 'brand/fruit-96.png');
    await change('search', 'video editor');
    const counts = await page.locator('#rail-cats a').evaluateAll(links => Object.fromEntries(links.map(a => [a.dataset.category, Number(a.querySelector('.n').textContent)])));
    assert.equal(counts[''], await visible(), 'All counts the search results');
    assert.ok(Object.values(counts).some(n => n === 0), 'Categories without matches show zero');
    await change('search', '');

    // Default order, positions and sorting.
    assert.equal(await page.locator('#f-sort').inputValue(), 'match');
    const defaultIds = await page.evaluate(() => {
      const d = JSON.parse(document.getElementById('catalog-data').textContent);
      return d.projects.slice().sort(OpenCatalog.comparator('stars')).map(p => p.id);
    });
    assert.deepEqual(await visibleIds(page), defaultIds);
    await assertVisiblePositions(page, 'default stars');
    await assertRowIdentities(page, data, 'default stars');
    await select('f-sort', 'name');
    await assertVisiblePositions(page, 'name sort');
    assert.equal(await page.locator('#f-sort option:checked').textContent(), 'Sort: Name A–Z', 'A chosen value keeps its title');
    await select('f-sort', 'match');
    await checkReviewedAliases('production', data);

    // Exact reviewed alternative search, combined metadata filters, empty/reset.
    await change('search', 'NotebookLM');
    const notebookIds = data.projects.filter(project => [project.name, project.description,
      ...project.alternatives.map(item => item.name), ...(project.aliases || []).map(item => item.name)]
      .join(' ').toLowerCase().includes('notebooklm')).map(project => project.id).sort();
    assert.deepEqual((await visibleIds(page)).sort(), notebookIds, 'Search matches reviewed alternatives');
    await change('search', '');
    await category('developer-tools');
    await select('f-license', 'known');
    await change('f-stars', '100');
    await change('f-pushed', '2025-01-01');
    const expected = await page.evaluate(() => {
      const data = JSON.parse(document.querySelector('#catalog-data').textContent);
      const state = OpenCatalog.normalizeState(new URL(location.href).searchParams, data);
      return OpenCatalog.selectProjects(data.projects, state, data).map(project => project.id);
    });
    assert.deepEqual(await visibleIds(page), expected);
    await assertVisiblePositions(page, 'combined filters');
    await change('search', 'no-project-could-match-this-string-98273');
    assert.equal(await visible(), 0);
    assert.equal(await page.locator('#empty').isVisible(), true);
    await change('search', '');
    await reset();
    await category('');
    assert.equal(await visible(), data.projects.length);
    await assertRowIdentities(page, data, 'reset');

    // Snapshot-relative filters, exact alternatives and honest missing metrics.
    for (const value of ['recent', 'older', 'unknown']) {
      await select('f-window', value);
      const expectedCount = await page.evaluate(value => {
        const data = JSON.parse(document.querySelector('#catalog-data').textContent);
        return OpenCatalog.diagnosticCounts(data.projects, data)[value];
      }, value);
      assert.equal(await visible(), expectedCount);
    }
    await reset();
    await select('f-alternative', 'NotebookLM');
    assert.equal(await visible(), data.projects.filter(project => project.alternatives.some(item => item.name === 'NotebookLM')).length);
    assert.equal(await page.locator('#f-alternative option:checked').textContent(), 'Alternative to: NotebookLM');
    await reset();
    await select('f-metrics', 'missing');
    assert.equal(await visible(), data.projects.filter(project => !project.github).length);
    await reset();
    await change('f-stars', '0');
    assert.equal(await visible(), data.projects.filter(project => project.github).length, 'Zero stars still means known stars');
    await reset();
    assert.equal(await page.locator('#reset').isDisabled(), true);

    // Sorting, shareable URLs, Back/Forward, and cancellation of a pending search.
    await select('f-sort', 'stars');
    const highest = data.projects.filter(project => project.github).sort((a, b) => b.github.stars - a.github.stars)[0];
    assert.equal((await visibleIds(page))[0], highest.id);
    await select('f-sort', 'pushed');
    const newest = data.projects.filter(project => project.github && project.github.pushed_at).sort((a, b) => Date.parse(b.github.pushed_at) - Date.parse(a.github.pushed_at))[0];
    assert.equal((await visibleIds(page))[0], newest.id);
    await reset();
    await change('search', 'OpenTofu');
    const savedURL = page.url();
    const savedCount = await visible();
    await select('f-license', 'known');
    await page.locator('#search').fill('a pending search that must be cancelled');
    await page.goBack();
    await page.waitForTimeout(400);
    assert.equal(page.url(), savedURL);
    assert.equal(await page.locator('#search').inputValue(), 'OpenTofu');
    assert.equal(await visible(), savedCount);
    await page.goForward();
    assert.equal(await page.locator('#f-license').inputValue(), 'known');
    await page.reload();
    await waitForState();
    assert.equal(await page.locator('#search').inputValue(), 'OpenTofu');
    assert.equal(await page.locator('#f-license').inputValue(), 'known');
    await assertVisiblePositions(page, 'URL reload');

    // One plate at a time: rows, arrows and Esc; the hash is the permalink.
    await page.goto(url);
    await waitForState();
    await page.locator('#rows .row > a').first().click();
    await waitForPlate();
    const first = defaultIds[0];
    assert.equal(new URL(page.url()).hash, '#project-' + first);
    assert.equal(await page.locator('#plate-position').textContent(), '001 / ' + String(data.projects.length).padStart(3, '0'));
    await page.keyboard.press('ArrowLeft');
    await page.waitForFunction(() => document.getElementById('plate-status').textContent === '' && document.querySelector('#pane-scroll .specimen-plate'));
    assert.equal(await page.locator('#plate-position').textContent(), String(data.projects.length).padStart(3, '0') + ' / ' + String(data.projects.length).padStart(3, '0'), 'Stepping wraps');
    assert.equal(await page.locator('.specimen-plate').count(), 1);
    assert.equal(await page.locator('#rows .row.is-current > a').evaluate(n => getComputedStyle(n).outlineStyle), 'none', 'The open row shows its marks, not a focus outline');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.specimen-plate').count(), 0);
    assert.equal(await page.locator('#pane-rest').isVisible(), true);
    // Compare adds the open project to the cabinet and says so.
    await page.goto(new URL('#project-' + first, url).href);
    await waitForPlate();
    assert.equal(await page.locator('#plate-cabinet').textContent(), 'Compare');
    await page.locator('#plate-cabinet').click();
    assert.equal(await page.locator('#plate-cabinet').textContent(), 'Added to Cabinet');
    assert.equal(await page.locator('#cabinet-count').textContent(), '1 of 6');
    await page.locator('#plate-cabinet').click();
    assert.equal(await page.locator('#cabinet-count').textContent(), '0 of 6');
    await capture('pane-plate-desktop.png');

    // About: the former footer, with tabs that open the field-guide pages in the pane.
    await page.locator('#rail-about').click();
    assert.equal(await page.locator('#pane-about').isVisible(), true);
    assert.equal(new URL(page.url()).hash, '#about');
    assert.deepEqual(await page.locator('.riders a').allTextContents(), ['About', 'Observatory', 'Scoreboard', 'Spotlight']);
    assert.deepEqual(await page.locator('.about-actions a').allTextContents(), ['Submit a project', 'GitHub repository', 'Support the list with a coffee']);
    assert.ok((await page.locator('.about-baseline').textContent()).includes(data.projects.length + ' Projects'));
    await capture('about-desktop.png');
    for (const [sheet, heading] of [['observatory', 'Observatory'], ['scoreboard', 'Scoreboard'], ['spotlight', 'Spotlight']]) {
      await page.locator(`.riders a[data-sheet="${sheet}"]`).click();
      const frame = page.frameLocator('#pane-frame');
      await frame.locator('.obs-hero h1').waitFor({ state: 'visible' });
      assert.equal(await frame.locator('.obs-hero h1').textContent(), heading);
      assert.equal(await frame.locator('html').evaluate(n => n.classList.contains('is-embedded')), true);
      assert.equal(await frame.locator('.obs-header').isVisible(), false, sheet + ': no header in the pane');
      assert.equal(await frame.locator('.obs-footer').isVisible(), false, sheet + ': no footer in the pane');
      assert.equal(new URL(page.url()).hash, '#' + sheet);
      await capture(`sheet-${sheet}-desktop.png`);
    }
    // On desktop the rail's About link closes the sheet; the head's × is for phones.
    assert.equal(await page.locator('#about-close').isVisible(), false);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#pane-rest').isVisible(), true);
    // A plate's Trophies line opens the Scoreboard in the pane.
    const awarded = await page.evaluate(async () => ((await (await fetch('catalog.json')).json()).projects
      .find(p => (p.scoreboard_trophies || []).length) || {}).id);
    if (awarded) {
      await page.goto(new URL('#project-' + awarded, url).href);
      await waitForPlate();
      await page.locator('#pane-scroll .plate-trophies').click();
      await page.frameLocator('#pane-frame').locator('.obs-hero h1').waitFor({ state: 'visible' });
      assert.equal(new URL(page.url()).hash, '#scoreboard');
      assert.equal(await page.locator('#pane-about').isVisible(), true);
      await page.keyboard.press('Escape');
    }
    report.trophiesInPane = Boolean(awarded);

    // Keyboard entry points.
    await page.goto(url);
    await waitForState();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('class'), 'skip-link');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'rows');
    await page.keyboard.press('ArrowDown');
    await waitForPlate();
    assert.equal(await page.locator(':focus').evaluate(n => n.closest('.row').classList.contains('is-current')), true);
    await page.locator('#search').focus();
    await page.keyboard.type('OpenTofu');
    await page.waitForTimeout(350);
    assert.equal(await page.locator(':focus').getAttribute('id'), 'search');
    assert.ok(await visible() > 0);
    for (const width of [1920, 1280, 390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(url);
      await waitForState();
      await assertLedgerFits(page, `${width}px`);
      if (width === 390) {
        // About covers a phone's screen; its × returns to the list.
        await page.locator('#rail-about').click();
        assert.equal(await page.locator('#about-close').isVisible(), true);
        await page.locator('#about-close').click();
        assert.equal(await page.locator('#pane-about').isVisible(), false);
        assert.equal(new URL(page.url()).hash, '');
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    await assertLedgerFits(page, '200% root text size');
    await page.evaluate(() => document.documentElement.style.fontSize = '');

    // Real renderers supply fixed evidence only to this page's intercepted requests.
    const installEvidence = require('./browser_evidence_fixture.cjs');
    report.evidenceFixtures = { synthetic: true, fixedWindowEnd: '2026-10-01',
      states: ['complete', 'empty', 'partial', 'unavailable', 'rollover'] };
    {
      const fixture = await installEvidence(page, url, 'complete');
      const data = fixture.data;
      try {
        const tofu = data.projects.find(project => project.url === 'https://github.com/opentofu/opentofu');
        assert.ok(tofu?.hn && tofu.star_history?.chart_url && tofu.deployment && tofu.function_summary,
          'OpenTofu covers Function, both cached charts, and reviewed setup');
        for (const width of [1920, 1440, 1280, 390, 320]) {
          await page.setViewportSize({ width, height: 1000 });
          const expandedURL = new URL(url);
          expandedURL.searchParams.set('q', tofu.name);
          expandedURL.hash = '#project-' + tofu.id;
          await page.goto(expandedURL.href);
          await waitForState();
          await waitForPlate();
          const card = page.locator('#pane-scroll');
          const diagnostics = card.locator('.plate-grid');
          assert.ok(await diagnostics.evaluate(node => node.getBoundingClientRect().width) >= 200, `Readable diagnostics at ${width}px`);
          assert.equal(await card.locator('.function-detail > p').first().textContent(), tofu.function_summary.text);
          for (const selector of ['[data-signal="hn"] .pg-spark', '[data-signal="star-history"] .pg-spark']) {
            const chart = card.locator(selector);
            await chart.scrollIntoViewIfNeeded();
            await chart.evaluate(image => image.decode());
            assert.ok(await chart.evaluate(image => image.complete && image.naturalWidth === 120 &&
              image.getBoundingClientRect().width >= 120 && image.getBoundingClientRect().height >= 24),
              `Loaded, non-collapsed ${selector} at ${width}px`);
          }
          const setup = card.locator('.pg-runs .pg-info');
          await setup.locator(':scope > summary').click();
          assert.equal(await setup.locator('.deployment-group').first().isVisible(), true);
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `No overflow at ${width}px`);
          // Closed popups keep a layout box; only the open one must fit.
          const clipped = await card.locator('.specimen-interior, .plate-grid, .function-detail, .pg-box, .pg-info[open] .pg-pop, .deployment-group')
            .evaluateAll(nodes => {
              const pane = document.getElementById('pane-scroll').getBoundingClientRect();
              const labels = [...document.querySelectorAll('.pg-box > .sheet-label')];
              labels.forEach(label => { label.style.display = 'none'; });
              const result = nodes.filter(node => {
                const rect = node.getBoundingClientRect();
                return rect.width <= 0 || rect.left < pane.left - 1 || rect.right > pane.right + 1 || node.scrollWidth > node.clientWidth + 1;
              }).map(node => node.className);
              labels.forEach(label => { label.style.display = ''; });
              return result;
            });
          assert.deepEqual(clipped, [], `Plate sections fit the pane at ${width}px`);
          await diagnostics.scrollIntoViewIfNeeded();
          await capture(`expanded-opentofu-${width}.png`);
          await setup.locator(':scope > summary').click();
        }
        // Sparse legacy histories and dual-series histories link their recorded evidence.
        const singleton = data.projects.find(p => p.hn?.total_stories === 1);
        const multiple = data.projects.find(p => p.hn?.total_stories > 1);
        assert.ok(singleton && multiple, 'Fixed sparse and multiple-story evidence');
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.goto(new URL('#project-' + singleton.id, url).href);
        await waitForState();
        await waitForPlate();
        const sparseBox = page.locator('#pane-scroll [data-signal="hn"]');
        await sparseBox.locator('.pg-spark').evaluate(node => node.decode());
        assert.equal(await sparseBox.locator('.pg-spark-link').evaluate(node => node.href), new URL(singleton.hn.matched_evidence_url, url + '/').href);
        assert.match(await sparseBox.textContent(), /1 matched/);
        await capture('hn-single-story-1440.png');
        await page.goto(new URL('records/' + multiple.id + '.html', url + '/').href);
        const multipleBox = page.locator('[data-signal="hn"]');
        assert.equal(await multipleBox.locator('.pg-hn-broad').textContent(), '6 possible');
        assert.equal(await multipleBox.locator('.pg-hn-matched').textContent(), '3 matched');
        await multipleBox.locator('.pg-hn-matched').focus();
        await page.keyboard.press('Enter');
        await page.waitForURL('**/fixture-tofu-evidence.html#matched');
        assert.equal(await page.locator('#matched li').count(), 3);
        assert.equal(await page.locator('#broad li').count(), 6);
        // The list row's HN trace opens the plate, which shows the full chart.
        await page.goto(url);
        await waitForState();
        const traced = data.projects.find(p => p.hn?.broad_total_stories !== undefined);
        const tracedRow = page.locator(`#rows .row[data-id="${traced.id}"]`);
        await tracedRow.locator('.row-spark').scrollIntoViewIfNeeded();
        await tracedRow.locator('.row-spark').click();
        await waitForPlate();
        assert.ok(await page.locator('#pane-scroll [data-signal="hn"] .pg-spark').isVisible());
      } finally {
        await fixture.dispose();
      }
    }
    for (const state of ['empty', 'partial', 'unavailable', 'rollover']) {
      const fixture = await installEvidence(page, url, state);
      try {
        const project = fixture.data.projects.find(p => p.name === 'OpenTofu');
        for (const width of [390, 1440]) {
          await page.setViewportSize({ width, height: 1000 });
          await page.goto(url + '?fixture=' + state + '&q=OpenTofu#project-' + project.id);
          await waitForState();
          await waitForPlate();
          const card = page.locator('#pane-scroll');
          assert.equal(await card.locator('[data-signal="hn"] .pg-spark').count(), state === 'partial' ? 1 : 0);
          assert.equal(await card.locator('[data-signal="star-history"] .pg-spark').count(), 0);
          for (const signal of ['hn', 'star-history']) {
            const box = card.locator(`[data-signal="${signal}"]`);
            await box.locator('.pg-info > summary').click();
            const expected = signal === 'hn' ? (state === 'partial' ? '3 matched' : 'Not recorded') :
              state === 'empty' ? 'Not recorded' : state === 'rollover' ? 'chart withheld until aligned' : 'History unavailable; no zero values inferred';
            assert.ok((await box.innerText()).includes(expected), `${state}: ${signal} disclosure`);
            await box.locator('.pg-info > summary').click();
          }
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
          await card.locator('.plate-grid').scrollIntoViewIfNeeded();
          await capture(`evidence-${state}-${width}.png`);
        }
      } finally {
        await fixture.dispose();
      }
    }
    // Continue the production-preview checks after removing all fixture routes.
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(url);
    await waitForState();
    assert.equal(await visible(), data.projects.length, 'Production catalog restored after fixture routes');
    assert.equal(await page.locator('html').evaluate(node => getComputedStyle(node).scrollBehavior), 'auto');
    const crossListed = data.projects.find(p => p.leader_categories.length && p.categories.some(c => !p.leader_categories.includes(c)));
    assert.ok(crossListed, 'Fixture needs a project leading only some of its categories');
    await category(crossListed.leader_categories[0]);
    assert.equal(await page.locator(`#rows .row[data-id="${crossListed.id}"]`).getAttribute('data-leader'), 'true');
    await category(crossListed.categories.find(c => !crossListed.leader_categories.includes(c)));
    assert.equal(await page.locator(`#rows .row[data-id="${crossListed.id}"]`).getAttribute('data-leader'), 'false');
    await category('');

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1440, height: 1000 } });
    const fallback = await noJS.newPage();
    await fallback.goto(url);
    assert.equal(await fallback.locator('#rows .row').count(), data.projects.length);
    assert.equal(await fallback.locator('#filters').isVisible(), false);
    assert.equal(await fallback.locator('#search-form').isVisible(), false);
    assert.equal(await fallback.locator('.no-script').isVisible(), true);
    assert.deepEqual(await visibleIds(fallback), defaultIds);
    await assertVisiblePositions(fallback, 'no JavaScript');
    await assertRowIdentities(fallback, data, 'no JavaScript');
    await fallback.locator('#rows .row > a').first().click();
    assert.equal(new URL(fallback.url()).pathname, new URL('records/' + defaultIds[0] + '.html', url).pathname);
    assert.equal(await fallback.locator('.specimen-plate').count(), 1);
    assert.equal(await fallback.locator('.plate-departure > a').getAttribute('href'), data.projects.find(project => project.id === defaultIds[0]).url);
    await noJS.close();
    assert.deepEqual(errors, []);

    report.status = 'passed';
    writeReport();
    console.log(JSON.stringify(report, null, 2));
    if (process.env.GITHUB_STEP_SUMMARY) {
      fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
        '## Field-guide browser check\n\nPassed against generated revision `' + report.sourceSha + '`' +
        ' (PR head `' + report.prHeadSha + '`).\n\n' +
        'Download `field-guide-browser-screenshots` for desktop.png (1440 × 1000), mobile.png (390 × 844), pane and About captures, ' +
        'screenshots.json, and browser/server logs.\n');
    }
    console.log(JSON.stringify({ status: 'passed', group, projects: data.projects.length, screenshots: output }));
  } catch (error) {
    report.status = 'failed';
    report.error = error.message;
    await capture(group + '-failure.png').catch(() => {});
    writeReport();
    console.error(JSON.stringify(report, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
