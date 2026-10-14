/* Observatory browser contract. Run against a locally generated checkout only:
 * SITE_URL=http://127.0.0.1:8000 node scripts/check_observatory_browser.cjs
 * Also invoked by check_site_browser.cjs in the existing PR browser check.
 * CHROMIUM_PATH / CHROMIUM_NO_SANDBOX have the same meaning as that check.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.join(ROOT, 'tmp/site-qa');
const CHARTS = ['category', 'license', 'star', 'age', 'push', 'release'];
const RECENCY = [['0–30 days', 30], ['31–90 days', 90], ['91–365 days', 365], ['366–730 days', 730], ['Over 730 days', Infinity]];
const AGES = [['0–365 days', 365], ['366–1,826 days', 1826], ['1,827–3,653 days', 3653], ['Over 3,653 days', Infinity]];
const clean = text => text.replace(/\s+/g, ' ').trim();
const number = text => Number(text.replace(/[,\s]/g, ''));
const hasLicense = project => Boolean(project.license) && !['NOASSERTION', 'OTHER'].includes(project.license);
const sha256 = body => crypto.createHash('sha256').update(body).digest('hex');

function checkoutState() {
  try {
    return {
      checkoutSha: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(),
      checkoutDirty: Boolean(execFileSync('git', ['status', '--porcelain'], { cwd: ROOT, encoding: 'utf8' }).trim()),
    };
  } catch { return { checkoutSha: null, checkoutDirty: null }; }
}

function localURL(value) {
  const url = new URL(value);
  assert.ok(['http:', 'https:'].includes(url.protocol) &&
    ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname),
  'Browser QA must use a local generated checkout, never production or a public preview');
  return new URL('observatory/', url.href.endsWith('/') ? url : new URL(url.pathname.endsWith('.html') ? '.' : url.pathname + '/', url));
}

// Read the actual downloaded CSV, including quoted commas/newlines and escaped
// quotes. Testing the href alone would miss stale or incorrectly scoped exports.
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  text = text.replace(/^\uFEFF/, '');
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { field += '"'; index++; }
      else { assert.ok(quoted || field === '', 'CSV opening quote follows a delimiter'); quoted = !quoted; }
    } else if (char === ',' && !quoted) { row.push(field); field = ''; }
    else if ((char === '\r' || char === '\n') && !quoted) {
      if (char === '\r' && text[index + 1] === '\n') index++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += char;
  }
  assert.equal(quoted, false, 'CSV quotes are balanced');
  if (row.length || field) { row.push(field); rows.push(row); }
  assert.ok(rows.length, 'CSV contains a header');
  const headers = rows.shift();
  assert.equal(new Set(headers).size, headers.length, 'CSV headers are distinct');
  return rows.map(cells => {
    assert.equal(cells.length, headers.length, 'CSV fields match its header');
    return Object.fromEntries(headers.map((key, index) => [key, cells[index]]));
  });
}

function dateBucket(value, asOf, buckets) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(value)) return buckets.length;
  const date = Date.parse(value.slice(0, 10) + 'T00:00:00Z');
  if (!Number.isFinite(date) || new Date(date).toISOString().slice(0, 10) !== value.slice(0, 10)) return buckets.length;
  const timestamp = Date.parse(value);
  const difference = Math.floor(Date.parse(asOf + 'T00:00:00Z') / 86400000) - Math.floor(timestamp / 86400000);
  if (!Number.isFinite(difference) || difference < 0) return buckets.length;
  return buckets.findIndex(([, maximum]) => difference <= maximum);
}

function chartRows(data, projects) {
  const histogram = (field, buckets) => {
    const rows = [...buckets.map(([label]) => [label, 0]), ['Unknown', 0]];
    for (const project of projects) rows[dateBucket(project[field], data.metrics_as_of, buckets)][1]++;
    return rows;
  };
  const lexical = (left, right) => left < right ? -1 : left > right ? 1 : 0;
  const licenses = new Map();
  for (const project of projects.filter(hasLicense)) licenses.set(project.license, (licenses.get(project.license) || 0) + 1);
  const licenseRows = [...licenses].sort((a, b) => b[1] - a[1] || lexical(a[0], b[0]));
  licenseRows.push(['Unknown', projects.filter(project => !hasLicense(project)).length]);
  const categoryRows = data.categories.map(category => [category.name, projects.filter(project => project.categories.includes(category.id)).length]);
  const knownCategories = new Set(data.categories.map(category => category.id));
  const unmapped = projects.filter(project => !project.categories.some(id => knownCategories.has(id))).length;
  if (unmapped) categoryRows.push(['Unknown', unmapped]);
  const ranked = projects.filter(project => project.github && Number.isFinite(project.stars))
    .sort((a, b) => b.stars - a.stars || lexical(a.name, b.name) || lexical(a.id, b.id));
  const stars = ranked.slice(0, 10).map(project => [project.name, project.stars]);
  if (ranked.length > 10) stars.push(['Other mapped projects', ranked.slice(10).reduce((sum, project) => sum + project.stars, 0)]);
  return { category: categoryRows, license: licenseRows, star: stars,
    age: histogram('created_at', AGES), push: histogram('pushed_at', RECENCY), release: histogram('release_at', RECENCY) };
}

// Independent accounting oracle; runtime and server rendering must agree.
function sharedGroups(projects) {
  const unique = [...new Map(projects.map(project => [project.id, project])).values()];
  const group = (rows, key) => {
    const map = new Map();
    rows.forEach(project => map.set(key(project), [...(map.get(key(project)) || []), project]));
    return [...map.values()].filter(rows => rows.length > 1);
  };
  const exact = group(unique, project => project.name);
  const exactIDs = new Set(exact.flat().map(project => project.id));
  const capitalization = group(unique.filter(project => !exactIDs.has(project.id)), project => project.name.toLowerCase());
  const usedIDs = new Set([...exact.flat(), ...capitalization.flat()].map(project => project.id));
  const whitespace = group(unique.filter(project => !usedIDs.has(project.id)),
    project => project.name.replace(/[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/g, ''))
    .filter(rows => new Set(rows.map(project => project.name)).size > 1);
  return { exact, capitalization, whitespace };
}

async function assertSharedNames(page, projects, label) {
  const expected = sharedGroups(projects);
  const countedIDs = Object.values(expected).flat(2).map(project => project.id);
  assert.equal(countedIDs.length, new Set(countedIDs).size, label + ': disjoint name groups');
  assert.equal(number(await page.locator('#shared-name-count').textContent()), countedIDs.length, label + ': headline includes every match kind');
  for (const [kind, countID] of [['exact', 'exact-name-count'], ['capitalization', 'capitalization-name-count'], ['whitespace', 'whitespace-name-count']]) {
    const groups = expected[kind];
    assert.equal(number(await page.locator('#' + countID).textContent()), groups.flat().length, label + ': ' + kind + ' tool count');
    const actual = await page.locator('#' + kind + '-name-groups .shared-name-group').evaluateAll(details => details.map(detail => [...detail.querySelectorAll('li')].map(item => ({ id: item.dataset.projectId, name: item.querySelector('a').textContent, url: item.querySelector('a').getAttribute('href'), source: item.querySelector('.shared-name-source').textContent }))));
    const normalize = values => values.map(rows => rows.map(row => JSON.stringify(row)).sort().join('|')).sort();
    assert.deepEqual(normalize(actual), normalize(groups.map(rows => rows.map(project => ({ id: project.id, name: project.name, url: project.url, source: project.url })))), label + ': ' + kind + ' linked identities');
  }
}

async function checkObservatory({ browser, url }) {
  const target = localURL(url);
  fs.mkdirSync(OUTPUT, { recursive: true });
  const report = { status: 'running', url: target.href, sourceSha: null,
    expectedSourceSha: process.env.SITE_SOURCE_SHA || null,
    prHeadSha: process.env.PR_HEAD_SHA || null, ...checkoutState(),
    screenshots: [], assets: [], checks: [] };
  const writeReport = () => fs.writeFileSync(path.join(OUTPUT, 'observatory-screenshots.json'), JSON.stringify(report, null, 2) + '\n');
  writeReport();
  const contextOptions = { viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1,
    colorScheme: 'light', reducedMotion: 'reduce', locale: 'en-US', timezoneId: 'UTC' };
  const context = await browser.newContext(contextOptions);
  context.setDefaultTimeout(10000);
  const failures = [];
  const expectedDownloads = new Set();
  // Reading source URLs is not part of this offline view's browser contract.
  // Reject remote runtime requests rather than accidentally testing public data.
  const guard = async ctx => ctx.route('**/*', route => {
    const requestURL = new URL(route.request().url());
    if (['data:', 'blob:'].includes(requestURL.protocol) || requestURL.origin === target.origin) return route.continue();
    failures.push('Unexpected external request: ' + requestURL.href);
    return route.abort('blockedbyclient');
  });
  await guard(context);
  const track = page => {
    page.on('pageerror', error => failures.push('Page error: ' + error.message));
    page.on('console', message => { if (message.type() === 'error') failures.push('Console error: ' + message.text()); });
    page.on('requestfailed', request => {
      // Chromium can report the navigation handed to its download manager as
      // aborted. Only ignore the exact export deliberately clicked by this test.
      if (expectedDownloads.has(request.url()) && request.failure()?.errorText === 'net::ERR_ABORTED') return;
      failures.push('Request failed: ' + request.url() + ' (' + request.failure()?.errorText + ')');
    });
    page.on('response', response => { if (response.status() >= 400) failures.push('HTTP ' + response.status() + ': ' + response.url()); });
  };
  const page = await context.newPage();
  track(page);
  let fallbackContext;
  const capture = async (name, current = page) => {
    await current.evaluate(() => document.fonts.ready);
    const filename = 'observatory-' + name + '.png';
    const png = await current.screenshot({ path: path.join(OUTPUT, filename), animations: 'disabled', caret: 'hide', scale: 'css' });
    const dimensions = { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
    assert.deepEqual(dimensions, current.viewportSize(), 'Screenshot dimensions: ' + filename);
    report.screenshots.push({ file: filename, ...dimensions, bytes: png.length, sha256: sha256(png), sourceSha: report.sourceSha });
    writeReport();
  };
  const checkProjectDisclosure = async (current, label) => {
    const details = current.locator('#project-data');
    const summary = details.locator(':scope > summary');
    assert.equal(await details.evaluate(node => node.open), false, label + ': collapsed initially');
    assert.equal(await summary.textContent(), 'Data table');
    assert.equal(await current.locator('#project-table').isVisible(), false, label + ': table hidden');
    assert.equal(await current.locator('#export-csv').isVisible(), true, label + ': export stays visible');
    await summary.focus();
    for (const key of ['Enter', 'Space', 'Space', 'Enter']) {
      const wasOpen = await details.evaluate(node => node.open);
      await current.keyboard.press(key);
      assert.equal(await details.evaluate(node => node.open), !wasOpen, label + ': native keyboard toggle');
      assert.equal(await current.locator('#project-table').isVisible(), !wasOpen, label + ': table visibility');
      assert.equal(await summary.evaluate(node => node === document.activeElement), true, label + ': focus retained');
    }
  };
  const enhanced = () => page.waitForFunction(() => {
    const form = document.querySelector('#observatory-filters');
    return form && !form.hidden && form.dataset.enhanced === 'true';
  });
  const visibleIDs = current => current.locator('#project-table tbody tr[data-id]:not([hidden])')
    .evaluateAll(nodes => nodes.map(node => node.dataset.id));
  const fits = async (current, label) => {
    assert.ok(await current.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Page fits: ' + label);
    const clipped = await current.locator('#observatory-filters select, #observatory-filters button, [data-metric], .chart-visual, .obs-table-scroll')
      .evaluateAll(nodes => nodes.filter(node => {
        const box = node.getBoundingClientRect();
        return box.width > 0 && (box.left < -1 || box.right > innerWidth + 1);
      }).map(node => node.id || node.tagName + ':' + (node.dataset.metric || '')));
    assert.deepEqual(clipped, [], 'Controls, metrics and charts fit: ' + label);
  };
  const select = async (id, value) => {
    await page.locator('#' + id).selectOption(value);
    assert.equal(await page.locator('#' + id).inputValue(), value);
  };
  const records = (data, category = '', license = 'all') => data.projects.filter(project =>
    (!category || project.categories.includes(category)) &&
    (license === 'all' || (license === 'known' ? hasLicense(project) : !hasLicense(project))));

  const assertCharts = async (current, data, selected, label) => {
    const expected = chartRows(data, selected);
    for (const name of CHARTS) {
      const chart = current.locator('#' + name + '-chart');
      assert.equal(await chart.count(), 1, 'Chart exists: ' + name);
      const table = chart.locator('table');
      assert.ok(await table.locator('caption').textContent(), 'Accessible table caption: ' + name);
      assert.equal(await table.locator('thead th').last().textContent(), name === 'star' ? 'Stars' : 'Projects', 'Chart units: ' + name);
      const actual = await table.locator('tbody tr:has(th)').evaluateAll(rows => rows.map(row =>
        [row.querySelector('th').textContent.trim(), Number(row.querySelector('td').textContent.replace(/[,\s]/g, ''))]));
      assert.deepEqual(actual, expected[name], `Exact chart data: ${name}, ${label}`);
      assert.equal(await table.locator('tbody th:not([scope="row"])').count(), 0, 'Row-header semantics: ' + name);
      const svg = chart.locator('svg');
      assert.equal(await svg.getAttribute('aria-hidden'), 'true', 'Table is the accessible chart equivalent: ' + name);
      assert.equal(await svg.getAttribute('focusable'), 'false', 'Decorative chart is not keyboard focusable: ' + name);
      const bars = await svg.locator('rect').evaluateAll(nodes => nodes.map(node => ({
        x: Number(node.getAttribute('x')), width: Number(node.getAttribute('width')),
        count: node.hasAttribute('data-count') ? Number(node.dataset.count) : null,
      })));
      assert.equal(bars.length, actual.length, `One visible mark per table value: ${name}, ${label}`);
      const max = Math.max(0, ...actual.map(([, value]) => value));
      const axis = await svg.locator('text').evaluateAll(nodes => nodes.slice(0, 2).map(node => ({ x: Number(node.getAttribute('x')), label: node.textContent.trim() })));
      assert.equal(axis[0].label, '0', 'Scale starts at zero: ' + name);
      assert.ok(axis[1].x > axis[0].x, 'Non-collapsed linear scale: ' + name);
      assert.equal(axis[1].label, max.toLocaleString('en-US') + (axis[1].label.includes(' ') ? (name === 'star' ? ' stars' : ' projects') : ''), 'Maximum scale label: ' + name);
      for (let index = 0; index < bars.length; index++) {
        const bar = bars[index];
        assert.equal(bar.x, axis[0].x, 'Common zero baseline: ' + name);
        assert.ok(Math.abs(bar.width - (max ? (axis[1].x - axis[0].x) * actual[index][1] / max : 0)) <= .001, `SVG width matches table: ${name}/${actual[index][0]}, ${label}`);
        if (bar.count !== null) assert.equal(bar.count, actual[index][1], 'Mark metadata matches displayed value');
      }
      const labels = (await svg.locator('text').allTextContents()).map(clean);
      const modernSVG = (await svg.getAttribute('viewBox')).split(/\s+/)[2] === '640';
      const expectedLabels = ['0', axis[1].label, ...actual.flatMap(([name, value]) =>
        [modernSVG && name.length > 29 ? name.slice(0, 28) + '…' : name, value.toLocaleString('en-US')])];
      if (!actual.length && labels.length === 3) expectedLabels.push('No observed values in this selection.');
      assert.deepEqual(labels, expectedLabels,
        `Visible SVG labels/counts match table: ${name}, ${label}`);
      if (!['category', 'star'].includes(name)) assert.equal(actual.reduce((sum, [, value]) => sum + value, 0), selected.length, 'Distribution denominator: ' + name);
    }
  };
  const assertSelection = async (current, data, selected, label) => {
    await assertSharedNames(current, selected, label);
    assert.deepEqual(await visibleIDs(current), selected.map(project => project.id), 'Underlying project selection: ' + label);
    const expected = { total: selected.length, mapped: selected.filter(project => project.github).length,
      stars: selected.filter(project => project.github && Number.isFinite(project.stars)).reduce((sum, project) => sum + project.stars, 0),
      'known-license': selected.filter(hasLicense).length };
    for (const [metric, value] of Object.entries(expected)) assert.equal(number(await current.locator('[data-metric="' + metric + '"]').textContent()), value, `Metric ${metric}: ${label}`);
    assert.ok(clean(await current.locator('#selection-summary').textContent()).includes(selected.length.toLocaleString('en-US')), 'Announced selection count: ' + label);
    await assertCharts(current, data, selected, label);
  };
  const assertCSV = (csv, data, selected, label) => {
    const headers = csv.replace(/^\uFEFF/, '').split(/\r?\n/, 1)[0].split(',').map(value => value.replace(/^"|"$/g, ''));
    assert.deepEqual(headers, ['id', 'name', 'url', 'categories', 'github', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_as_of', 'source_sha'], 'CSV schema, including empty exports: ' + label);
    const rows = parseCSV(csv);
    assert.deepEqual(rows.map(row => row.id), selected.map(project => project.id), 'Export selection: ' + label);
    const safeCell = value => {
      const text = value === null || value === undefined ? '' : String(value);
      return /^[=+\-@\t\r\n]/.test(text.trimStart()) ? "'" + text : text;
    };
    for (let index = 0; index < rows.length; index++) {
      const actual = rows[index], project = selected[index];
      for (const key of ['id', 'name', 'url', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at']) {
        assert.equal(actual[key], safeCell(project[key]), `CSV ${key}: ${label}/${project.id}`);
      }
      assert.equal(actual.github.toLowerCase(), String(project.github), 'CSV GitHub coverage');
      assert.equal(actual.categories, safeCell(project.categories.join('; ')), 'CSV category memberships');
      assert.equal(actual.source_sha, data.source_sha, 'CSV source revision');
      assert.equal(actual.metrics_as_of, data.metrics_as_of, 'CSV snapshot date');
    }
    return rows;
  };
  const downloadCSV = async (current, data, selected, label) => {
    const location = current.url();
    expectedDownloads.add(await current.locator('#export-csv').evaluate(node => node.href));
    const [download] = await Promise.all([current.waitForEvent('download'), current.locator('#export-csv').click()]);
    assert.equal(await download.failure(), null, 'CSV download succeeds: ' + label);
    assert.ok(download.suggestedFilename().endsWith('.csv'), 'CSV filename');
    const chunks = [];
    for await (const chunk of await download.createReadStream()) chunks.push(chunk);
    assertCSV(Buffer.concat(chunks).toString('utf8'), data, selected, label);
    assert.equal(current.url(), location, 'Download preserves current view: ' + label);
  };

  try {
    const response = await page.goto(target.href);
    assert.ok(response.ok(), 'Observatory route loads');
    report.htmlSha256 = sha256(await response.body());
    await enhanced();
    const data = JSON.parse(await page.locator('#observatory-data').textContent());
    report.sourceSha = data.source_sha;
    report.metricsAsOf = data.metrics_as_of;
    assert.ok(data.source_sha, 'Embedded data records the source revision');
    if (process.env.SITE_SOURCE_SHA) assert.equal(data.source_sha, process.env.SITE_SOURCE_SHA, 'Exact generated revision');
    const catalogResponse = await context.request.get(new URL('../catalog.json', target).href);
    assert.ok(catalogResponse.ok(), 'Catalog export is available');
    const catalog = await catalogResponse.json();
    assert.equal(data.source_sha, catalog.source_sha, 'Catalog and Observatory share a source');
    assert.equal(data.metrics_as_of, catalog.metrics_as_of, 'Catalog and Observatory share a cached snapshot');
    assert.deepEqual(data.projects.map(project => project.id), catalog.projects.map(project => project.id), 'Exactly the curated projects');
    assert.equal(new Set(data.projects.map(project => project.id)).size, data.projects.length, 'Project identity is unique');
    assert.deepEqual(data.categories, catalog.categories.map(({ id, name }) => ({ id, name })), 'Canonical categories');
    for (let index = 0; index < data.projects.length; index++) {
      const project = data.projects[index], canonical = catalog.projects[index];
      const github = canonical.github || {};
      const release = canonical.signals?.release || {};
      assert.equal(project.name, canonical.name);
      assert.equal(project.url, canonical.url);
      assert.deepEqual(project.categories, [...new Set(canonical.categories)]);
      assert.equal(project.github, Boolean(canonical.github));
      for (const field of ['stars', 'license', 'created_at', 'pushed_at']) assert.equal(project[field], github[field] ?? null, 'Cached source projection: ' + field);
      assert.equal(project.release_at, release.last_good?.value?.published_at ?? null, 'Release uses its cached publication date');
      assert.equal(project.release_checked_at, release.checked_at ?? null, 'Release checked time remains distinct');
    }
    const logo = page.locator('.obs-logo');
    assert.equal(await logo.getAttribute('src'), '../brand/botanical-128.png');
    assert.equal(await logo.getAttribute('alt'), 'Awesome Open* botanical logo');
    assert.equal(await page.locator('.obs-hero figcaption').count(), 0, 'No logo subtitle');
    await logo.evaluate(image => image.decode());
    assert.equal(await logo.evaluate(image => image.naturalWidth), 128);
    writeReport();

    // Save review artifacts before behavioral checks, so failures retain the page.
    for (const [name, viewport] of [
      ['desktop', { width: 1440, height: 1000 }],
      ['mobile', { width: 390, height: 844 }],
      ['medium', { width: 768, height: 1000 }],
    ]) {
      await page.setViewportSize(viewport);
      await page.evaluate(() => scrollTo(0, 0));
      await fits(page, name);
      assert.ok((await logo.boundingBox()).width <= 128, 'Logo stays within source resolution');
      await capture(name);
      await page.locator('#shared-names').scrollIntoViewIfNeeded();
      await capture(name + '-shared-names');
      const firstNameGroup = page.locator('#exact-name-groups details').first();
      if (await firstNameGroup.count()) {
        await firstNameGroup.locator('summary').focus();
        for (const key of ['Enter', 'Space']) {
          const previous = await firstNameGroup.evaluate(node => node.open);
          await page.keyboard.press(key);
          assert.equal(await firstNameGroup.evaluate(node => node.open), !previous, 'Shared-name keyboard disclosure');
          assert.equal(await firstNameGroup.locator('summary').evaluate(node => node === document.activeElement), true, 'Shared-name disclosure keeps focus');
          await fits(page, name + ' shared names');
          if (!previous) await capture(name + '-shared-names-open');
        }
      }
      await page.locator('#capitalization-names > summary').click();
      await page.locator('#capitalization-name-groups details').first().locator('summary').click();
      await capture(name + '-capitalization-open');
      await page.locator('#capitalization-names > summary').click();
      await page.locator('#whitespace-names > summary').focus();
      for (const key of ['Enter', 'Space']) {
        const wasOpen = await page.locator('#whitespace-names').evaluate(node => node.open);
        await page.keyboard.press(key);
        assert.equal(await page.locator('#whitespace-names').evaluate(node => node.open), !wasOpen, 'Whitespace section keyboard disclosure');
        await fits(page, name + ' whitespace disclosure');
        if (!wasOpen) await capture(name + '-whitespace-open');
      }
      await page.locator('#category-chart').scrollIntoViewIfNeeded();
      await capture(name + '-charts');
      await checkProjectDisclosure(page, name);
      await page.locator('#project-records').scrollIntoViewIfNeeded();
      await capture(name + '-data-closed');
      await page.locator('#project-data > summary').click();
      await capture(name + '-data-open');
      await page.locator('#project-data > summary').click();
    }
    await page.setViewportSize(contextOptions.viewport);

    // Every declared stylesheet/script/image is a real same-origin asset, not a
    // missing route answered by an HTML fallback. Font loads are tracked above.
    const assets = await page.locator('link[rel="stylesheet"], script[src], img[src]')
      .evaluateAll(nodes => [...new Set(nodes.map(node => node.href || node.src))]);
    for (const asset of assets) {
      assert.equal(new URL(asset).origin, target.origin, 'Local runtime asset: ' + asset);
      const result = await context.request.get(asset);
      assert.ok(result.ok(), 'Asset fetch: ' + asset);
      assert.ok(!(result.headers()['content-type'] || '').includes('text/html'), 'Asset is not an HTML fallback: ' + asset);
      const body = await result.body();
      assert.ok(body.length > 0, 'Asset is non-empty: ' + asset);
      report.assets.push({ url: asset, bytes: body.length, sha256: sha256(body) });
    }
    assert.ok(assets.some(asset => asset.includes('observatory') && asset.includes('.js')), 'Local Observatory runtime');
    assert.ok(await page.evaluate(() => document.fonts.status === 'loaded'), 'Fonts finish loading');
    report.checks.push('local assets and source revision');

    await assertSelection(page, data, data.projects, 'initial');
    const projectTable = await page.locator('#project-table tbody tr[data-id]').evaluateAll(rows => rows.map(row => ({
      id: row.dataset.id, name: row.querySelector('th a').textContent.trim(),
      link: row.querySelector('th a').getAttribute('href'),
      cells: [...row.querySelectorAll('td')].map(cell => cell.textContent.trim()),
      source: row.querySelector('td:last-child a').getAttribute('href'),
    })));
    for (let index = 0; index < projectTable.length; index++) {
      const row = projectTable[index], project = data.projects[index];
      assert.equal(row.name, project.name, 'Underlying table name');
      assert.equal(row.link, '../#project-' + project.id, 'Underlying record permalink');
      assert.equal(row.source, project.url, 'Underlying official source');
      assert.deepEqual(row.cells.slice(0, 5), [project.license || 'Unknown',
        project.stars === null ? 'Unknown' : String(project.stars),
        ...['created_at', 'pushed_at', 'release_at'].map(key => project[key] ? project[key].slice(0, 10) : 'Unknown')], 'Underlying table values: ' + project.id);
      assert.ok(row.cells[5].includes(project.release_status), 'Underlying release cache status');
      assert.ok(row.cells[5].includes(project.release_checked_at || 'Not checked'), 'Underlying release check time');
    }
    const coverage = await page.locator('#coverage').innerText();
    assert.equal(await page.locator('#selection-summary').getAttribute('role'), 'status');
    assert.equal(await page.locator('#selection-summary').getAttribute('aria-live'), 'polite');
    const sourceLinks = await page.locator('a[href]').evaluateAll(nodes => nodes.map(node => node.href));
    assert.ok(sourceLinks.some(href => href.endsWith('/commit/' + data.source_sha)), 'Exact revision provenance link');
    assert.ok(sourceLinks.some(href => href.includes('/blob/' + data.source_sha + '/data/github_metrics.json')), 'Pinned metrics source');
    const rawSnapshot = await context.request.get(new URL('snapshot.json', target).href);
    assert.ok(rawSnapshot.ok(), 'Snapshot JSON downloads');
    const snapshot = await rawSnapshot.json();
    for (const key of ['projects', 'categories', 'source_sha', 'metrics_as_of']) assert.deepEqual(snapshot[key], data[key], 'Complete JSON: ' + key);
    const rawCSV = await context.request.get(new URL('projects.csv', target).href);
    assert.ok(rawCSV.ok(), 'Complete CSV downloads');
    assertCSV(await rawCSV.text(), data, data.projects, 'static complete export');
    await downloadCSV(page, data, data.projects, 'initial export');
    report.checks.push('snapshot/CSV/provenance and exact initial chart/table/mark parity');

    const categories = data.categories.filter(category => records(data, category.id).length);
    assert.ok(categories.length > 1, 'The fixture covers combined/category history cases');
    const first = categories.find(category => records(data, category.id, 'known').length && records(data, category.id, 'unknown').length) || categories[0];
    const second = categories.find(category => category.id !== first.id);
    await select('category-filter', first.id);
    await assertSelection(page, data, records(data, first.id), 'category');
    await checkProjectDisclosure(page, 'filtered category');
    const categoryURL = page.url();
    assert.equal(new URL(categoryURL).searchParams.get('category'), first.id, 'Category is shareable');
    await select('license-filter', 'unknown');
    await assertSelection(page, data, records(data, first.id, 'unknown'), 'combined unknown license');
    const combinedURL = page.url();
    assert.equal(new URL(combinedURL).searchParams.get('license'), 'unknown');
    await downloadCSV(page, data, records(data, first.id, 'unknown'), 'filtered unknown export');
    assert.equal(await page.locator('#coverage').innerText(), coverage, 'Whole-collection evidence coverage does not change with filters');
    await page.goBack();
    await page.waitForFunction(value => document.querySelector('#license-filter').value === value, 'all');
    assert.equal(page.url(), categoryURL, 'Back restores prior selection URL');
    await assertSelection(page, data, records(data, first.id), 'history back');
    await page.goForward();
    await page.waitForFunction(value => document.querySelector('#license-filter').value === value, 'unknown');
    assert.equal(page.url(), combinedURL, 'Forward restores combined selection URL');
    await assertSelection(page, data, records(data, first.id, 'unknown'), 'history forward');
    await page.reload();
    await enhanced();
    assert.equal(await page.locator('#category-filter').inputValue(), first.id);
    assert.equal(await page.locator('#license-filter').inputValue(), 'unknown');
    await assertSelection(page, data, records(data, first.id, 'unknown'), 'URL reload');
    await select('license-filter', 'known');
    await select('category-filter', second.id);
    await assertSelection(page, data, records(data, second.id, 'known'), 'changed combined selection');
    await downloadCSV(page, data, records(data, second.id, 'known'), 'repeated filtered export');
    const defaultCategory = await page.locator('#category-filter option').first().getAttribute('value');
    for (let repeat = 0; repeat < 3; repeat++) {
      if (await page.locator('#reset-filters').isEnabled()) await page.locator('#reset-filters').click();
      else await page.locator('#reset-filters').evaluate(node => node.click());
      assert.equal(await page.locator('#category-filter').inputValue(), defaultCategory);
      assert.equal(await page.locator('#license-filter').inputValue(), 'all');
      await assertSelection(page, data, data.projects, 'reset ' + repeat);
      assert.equal(new URL(page.url()).search, '', 'Reset removes only Observatory filter state');
    }
    // A valid pair that yields no results must remain usable and export its header.
    const empty = data.categories.flatMap(category => ['known', 'unknown'].map(license => [category.id, license]))
      .find(([category, license]) => records(data, category, license).length === 0);
    if (empty) {
      await select('category-filter', empty[0]);
      await select('license-filter', empty[1]);
      await assertSelection(page, data, [], 'empty selection');
      await downloadCSV(page, data, [], 'empty export');
      await page.locator('#reset-filters').click();
      await assertSelection(page, data, data.projects, 'recover from empty');
    }
    const invalid = new URL(target);
    invalid.search = '?category=not-a-real-category&license=not-a-license';
    await page.goto(invalid.href);
    await enhanced();
    assert.equal(await page.locator('#category-filter').inputValue(), defaultCategory);
    assert.equal(await page.locator('#license-filter').inputValue(), 'all');
    await assertSelection(page, data, data.projects, 'invalid parameters normalize');
    await page.locator('#reset-filters').evaluate(node => { node.click(); node.click(); });
    await assertSelection(page, data, data.projects, 'reset after invalid URL');
    report.checks.push('combined filters, repeated reset/export, empty recovery, Back/Forward, reload and invalid parameters');

    // Native keyboard controls, disclosure lifecycle and responsive boundaries.
    await page.goto(target.href);
    await enhanced();
    await page.keyboard.press('Tab');
    assert.ok((await page.locator(':focus').getAttribute('class')).split(/\s+/).includes('skip-link'), 'Skip link is first keyboard entry');
    await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).hash, '#observatory-main', 'Skip link targets the main content');
    await page.locator('#category-filter').focus();
    assert.ok(await page.locator('#category-filter').evaluate(node => {
      const style = getComputedStyle(node);
      return (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0) || style.boxShadow !== 'none';
    }), 'Keyboard filter has a visible focus indicator');
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Escape');
    await page.waitForFunction(defaultValue => document.querySelector('#category-filter').value !== defaultValue, defaultCategory);
    const keyboardCategory = await page.locator('#category-filter').inputValue();
    await assertSelection(page, data, records(data, keyboardCategory), 'keyboard category');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'category-filter', 'Filtering keeps keyboard focus');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'license-filter');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'reset-filters');
    await page.keyboard.press('Enter');
    await assertSelection(page, data, data.projects, 'keyboard reset');
    for (const width of [320, 390, 601, 768, 900, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await fits(page, width + 'px');
      const detail = page.locator('#category-chart details');
      await detail.locator('summary').focus();
      for (const open of [true, false, true, false]) {
        await page.keyboard.press('Enter');
        assert.equal(await detail.evaluate(node => node.open), open, 'Keyboard data disclosure at ' + width);
        assert.equal(await detail.locator('table').isVisible(), open, 'Data table visibility follows disclosure at ' + width);
        await fits(page, width + 'px, chart table ' + (open ? 'open' : 'closed'));
      }
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => document.documentElement.style.fontSize = '200%');
    await fits(page, '200% root text size');
    await capture('large-text');
    await page.evaluate(() => document.documentElement.style.fontSize = '');
    report.checks.push('keyboard filters/reset/disclosures, 320–1440px, 200% text');

    fallbackContext = await browser.newContext({ ...contextOptions, javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    await guard(fallbackContext);
    const fallback = await fallbackContext.newPage();
    track(fallback);
    await fallback.goto(target.href);
    assert.equal(await fallback.locator('#observatory-filters').isVisible(), false, 'No inactive controls without JavaScript');
    assert.equal(await fallback.locator('noscript').isVisible(), true, 'No-JavaScript explanation');
    await assertSelection(fallback, data, data.projects, 'no JavaScript');
    await checkProjectDisclosure(fallback, 'no JavaScript');
    await fallback.locator('#exact-name-groups details > summary').first().click();
    assert.equal(await fallback.locator('#exact-name-groups details').first().evaluate(node => node.open), true, 'Shared names expand without JavaScript');
    await fallback.locator('#whitespace-names > summary').click();
    assert.equal(await fallback.locator('#whitespace-names').evaluate(node => node.open), true, 'Whitespace section expands without JavaScript');
    await fallback.locator('#category-chart details > summary').click();
    assert.equal(await fallback.locator('#category-chart table').isVisible(), true, 'Native data disclosure without JavaScript');
    await fits(fallback, 'no JavaScript');
    await capture('no-js', fallback);
    await downloadCSV(fallback, data, data.projects, 'no-JavaScript static export');
    for (const href of await fallback.locator('#coverage a[href]').evaluateAll(nodes => nodes.map(node => node.href))) {
      if (new URL(href).origin !== target.origin) continue;
      assert.ok((await fallbackContext.request.get(href)).ok(), 'Local evidence download: ' + href);
    }
    await fallbackContext.close();
    fallbackContext = null;
    report.checks.push('complete server-rendered charts/tables, native disclosures, local evidence and CSV without JavaScript');

    // Production data can have no whitespace groups. Exercise real DOM rendering
    // with synthetic names while retaining canonical project IDs and URLs.
    const synthetic = await context.newPage();
    track(synthetic);
    const syntheticNames = ['OpenTool', 'OpenTool', 'Open Tool', 'OPEN TOOL',
      'Open  Tool', 'Open\tTool', 'Open\u0085Tool', 'openTool ', 'Open-Tool', 'Open\u200bTool'];
    const syntheticProjects = data.projects.slice(0, syntheticNames.length)
      .map((project, i) => ({ ...project, name: syntheticNames[i] }));
    await synthetic.route(target.href, async route => {
      const response = await route.fetch();
      const body = (await response.text()).replace(/(<script[^>]+id="observatory-data"[^>]*>)[\s\S]*?(<\/script>)/,
        (_, opening, closing) => opening + JSON.stringify({ ...data, projects: syntheticProjects }) + closing);
      await route.fulfill({ response, body });
    });
    await synthetic.goto(target.href);
    await synthetic.waitForFunction(() => document.querySelector('#observatory-filters').dataset.enhanced === 'true');
    await assertSharedNames(synthetic, syntheticProjects, 'synthetic overlap and Unicode whitespace');
    assert.equal(number(await synthetic.locator('#shared-name-count').textContent()), 7, 'Synthetic union count');
    await synthetic.setViewportSize({ width: 390, height: 844 });
    await synthetic.locator('#whitespace-names > summary').click();
    const whitespaceGroup = synthetic.locator('#whitespace-name-groups details').first();
    await whitespaceGroup.locator('summary').focus();
    for (const key of ['Enter', 'Space']) {
      const wasOpen = await whitespaceGroup.evaluate(node => node.open);
      await synthetic.keyboard.press(key);
      assert.equal(await whitespaceGroup.evaluate(node => node.open), !wasOpen, 'Whitespace group keyboard toggle');
      assert.equal(await whitespaceGroup.locator('summary').evaluate(node => node === document.activeElement), true, 'Whitespace group retains focus');
      await fits(synthetic, 'synthetic whitespace mobile');
      if (!wasOpen) await capture('synthetic-whitespace-open', synthetic);
    }
    await synthetic.close();
    report.checks.push('whitespace keyboard disclosure, Unicode matching and exact/capitalization/whitespace priority with synthetic names');

    // Block every neighboring runtime file. A standalone report must render and
    // filter from embedded assets even when none of its sibling files exist.
    const standalone = new URL('report.html', target).href;
    const offlineRequests = [];
    await page.route('**/*', route => {
      if (route.request().url() === standalone && route.request().isNavigationRequest()) return route.continue();
      offlineRequests.push(route.request().url());
      return route.abort('blockedbyclient');
    });
    await page.goto(standalone);
    await enhanced();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('link[rel="stylesheet"], script[src]:not([src^="data:"])').count(), 0, 'Embedded standalone styles and runtime');
    assert.ok(await page.locator('img').evaluateAll(nodes => nodes.every(image => image.src.startsWith('data:') && image.complete && image.naturalWidth > 0)), 'Embedded standalone artwork');
    assert.deepEqual(offlineRequests, [], 'Standalone fetches no neighboring assets');
    assert.ok((await page.locator('.obs-logo').getAttribute('src')).startsWith('data:image/png;base64,'));
    assert.equal(await page.locator('.obs-hero figcaption').count(), 0);
    await assertSelection(page, data, data.projects, 'standalone initial');
    await checkProjectDisclosure(page, 'standalone');
    await select('category-filter', first.id);
    await select('license-filter', 'known');
    await assertSelection(page, data, records(data, first.id, 'known'), 'standalone filtered');
    await downloadCSV(page, data, records(data, first.id, 'known'), 'standalone filtered export');
    await page.locator('#reset-filters').click();
    await page.evaluate(() => scrollTo(0, 0));
    await capture('standalone-mobile');
    assert.deepEqual(failures, [], 'No JavaScript, console, network or HTTP errors');
    report.checks.push('standalone embedded assets, filters and CSV; no page/console/network errors');
    report.status = 'passed';
    writeReport();
    console.log(JSON.stringify(report, null, 2));
    return report;
  } catch (error) {
    report.status = 'failed';
    report.error = error.message;
    report.browserErrors = failures;
    await capture('failure').catch(() => {});
    writeReport();
    throw error;
  } finally {
    if (fallbackContext) await fallbackContext.close();
    await context.close();
  }
}

module.exports = checkObservatory;
// Expose pure CSV parsing for a small offline harness without launching a browser.
module.exports.parseCSV = parseCSV;
module.exports.chartRows = chartRows;

if (require.main === module) {
  (async () => {
    const { chromium } = require('playwright');
    const options = { headless: true };
    if (process.env.CHROMIUM_NO_SANDBOX === '1') options.args = ['--no-sandbox'];
    if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
    let browser;
    try {
      browser = await chromium.launch(options);
      await checkObservatory({ browser, url: process.env.SITE_URL || 'http://127.0.0.1:8000' });
    } catch (error) {
      if (!browser) {
        fs.mkdirSync(OUTPUT, { recursive: true });
        fs.writeFileSync(path.join(OUTPUT, 'observatory-screenshots.json'), JSON.stringify({
          status: 'blocked', stage: 'browser launch', error: error.message,
          expectedSourceSha: process.env.SITE_SOURCE_SHA || null, ...checkoutState(), screenshots: [],
        }, null, 2) + '\n');
      }
      throw error;
    } finally { if (browser) await browser.close(); }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
