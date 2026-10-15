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
  // Sorted by count; ties keep catalog order (stable sort). Unknown stays last.
  const categoryRows = data.categories.map(category => [category.name, projects.filter(project => project.categories.includes(category.id)).length])
    .sort((a, b) => b[1] - a[1]);
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
// One matching key per name: lowercase, Unicode White_Space, hyphen and underscore removed.
const nameKey = name => name.toLowerCase().replace(/[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000_-]/g, '');
function sharedGroups(projects) {
  const unique = [...new Map(projects.map(project => [project.id, project])).values()];
  const map = new Map();
  for (const project of unique) {
    const key = nameKey(project.name);
    if (key) map.set(key, [...(map.get(key) || []), project]);
  }
  const groups = [...map.values()].filter(rows => rows.length > 1);
  return { identical: groups.filter(rows => new Set(rows.map(project => project.name)).size === 1),
    variants: groups.filter(rows => new Set(rows.map(project => project.name)).size > 1) };
}

async function assertSharedNames(page, projects, label) {
  const expected = sharedGroups(projects);
  const countedIDs = Object.values(expected).flat(2).map(project => project.id);
  const summary = clean(await page.locator('#name-group-summary').textContent());
  assert.equal(Number(summary.match(/([\d,]+) groups?\b/)?.[1].replaceAll(',', '')),
    expected.identical.length + expected.variants.length, label + ': disclosure group count');
  assert.equal(Number(summary.match(/([\d,]+) tools\b/)?.[1].replaceAll(',', '')),
    countedIDs.length, label + ': disclosure tool count');
  assert.equal(countedIDs.length, new Set(countedIDs).size, label + ': each project in at most one group');
  assert.equal(number(await page.locator('#shared-name-count').textContent()), countedIDs.length, label + ': headline counts every grouped tool');
  assert.equal(await page.locator('#name-tally .obs-mark').count(), countedIDs.length, label + ': one tally mark per tool');
  const labels = new Map(projects.map(project => [project.id,
    project.name + ' (' + project.url.replace(/^https?:\/\/(github\.com\/)?/, '') + ')']));
  const clusters = await page.locator('#name-tally .obs-cluster').evaluateAll(nodes => nodes.map(node => ({
    href: node.getAttribute('href'), title: node.title, label: node.getAttribute('aria-label'),
    marks: [...node.querySelectorAll('.obs-mark')].map(mark => mark.title),
    ids: [...document.querySelector(node.getAttribute('href')).querySelectorAll('.obs-plate-project')].map(column => column.dataset.projectId)
  })));
  for (const cluster of clusters) {
    const names = cluster.ids.map(id => labels.get(id));
    assert.deepEqual(cluster.marks, names, label + ': marker titles identify each project');
    for (const name of names) {
      assert.ok(cluster.title.includes(name), label + ': cluster title includes project');
      assert.ok(cluster.label.includes(name), label + ': accessible link label includes project');
    }
  }
  for (const [kind, prefix] of [['identical', 'identical'], ['variants', 'variant']]) {
    const groups = expected[kind];
    assert.equal(number(await page.locator('#' + prefix + '-name-count').textContent()), groups.flat().length, label + ': ' + kind + ' tool count');
    assert.equal(await page.locator('#name-tally .obs-mark-' + kind).count(), groups.flat().length, label + ': ' + kind + ' marks');
    const actual = await page.locator('#' + prefix + '-name-groups .shared-name-group').evaluateAll(plates => plates.map(plate =>
      [...plate.querySelectorAll('.obs-plate-project')].map(column => ({ id: column.dataset.projectId, url: column.querySelector('.obs-repo').getAttribute('href'),
        record: column.querySelector('.obs-record').getAttribute('href'),
        metrics: [...column.querySelectorAll('dt')].find(node => node.textContent === 'Metrics cache')?.nextElementSibling.textContent }))));
    const normalize = values => values.map(rows => rows.map(row => JSON.stringify(row)).sort().join('|')).sort();
    assert.deepEqual(normalize(actual), normalize(groups.map(rows => rows.map(project => ({ id: project.id, url: project.url, record: '../#project-' + project.id,
      metrics: (project.metrics_status || 'unknown') + (project.metrics_last_success_at ? ' · observed ' + project.metrics_last_success_at + ' UTC' : ' · no successful observation') })))), label + ': ' + kind + ' linked identities');
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
  const checkFooter = async (offline) => {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.locator('.obs-footer').scrollIntoViewIfNeeded();
      const footer = await page.locator('.obs-footer').evaluate(async node => {
        const style = getComputedStyle(node);
        const background = style.backgroundImage.slice(5, -2);
        const image = new Image();
        image.src = background;
        await image.decode();
        return { background, width: image.naturalWidth, repeat: style.backgroundRepeat,
          border: style.borderTopStyle };
      });
      assert.equal(footer.width, 1254);
      assert.equal(footer.repeat, 'repeat');
      assert.equal(footer.border, 'double');
      if (offline) {
        assert.ok(footer.background.startsWith('data:image/png;base64,'));
        assert.deepEqual(Buffer.from(footer.background.split(',')[1], 'base64'),
          fs.readFileSync(path.join(ROOT, 'site/footer-backgrounds/navypattern2.png')));
      } else {
        assert.equal(footer.background, new URL('../footer-backgrounds/navypattern2.png', target).href);
      }
      await capture('footer-' + (offline ? 'standalone' : 'hosted') + '-' + width);
    }
  };
  const checkClosingMark = async (current, label) => {
    assert.equal(await current.locator('img').count(), 1, label + ': one image');
    assert.equal(await current.locator('.obs-closing-mark').count(), 1, label + ': one closing mark');
    assert.equal(await current.locator('.obs-hero img, .obs-closing-mark figcaption').count(), 0, label + ': no opening image or caption');
    const mark = current.locator('.obs-closing-mark');
    const logo = mark.locator(':scope > .obs-logo');
    assert.equal(await logo.count(), 1, label + ': logo belongs to closing mark');
    assert.equal(await logo.getAttribute('alt'), 'Awesome Open* botanical logo');
    await logo.evaluate(image => image.decode());
    const layout = await mark.evaluate(node => {
      const image = node.querySelector('img'), hero = document.querySelector('.obs-hero');
      const rect = node.getBoundingClientRect(), art = image.getBoundingClientRect();
      const opening = hero.getBoundingClientRect(), copy = hero.querySelector('.obs-hero-copy').getBoundingClientRect();
      return { last: node.parentElement.id === 'observatory-main' && node.parentElement.lastElementChild === node,
        prefooter: node.parentElement.nextElementSibling?.classList.contains('obs-footer'),
        text: node.textContent.trim(), children: node.children.length,
        naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight,
        width: art.width, height: art.height, centerOffset: art.x + art.width / 2 - rect.x - rect.width / 2,
        above: art.top - rect.top, below: rect.bottom - art.bottom,
        heroDisplay: getComputedStyle(hero).display, heroGap: opening.width - copy.width };
    });
    assert.equal(layout.last, true, label + ': last child of main');
    assert.equal(layout.prefooter, true, label + ': immediately before footer');
    assert.equal(layout.text, '', label + ': no visible caption');
    assert.equal(layout.children, 1, label + ': only the existing image');
    assert.deepEqual([layout.naturalWidth, layout.naturalHeight], [128, 128], label + ': original intrinsic dimensions');
    assert.ok(layout.width > 0 && layout.width <= 128 && layout.height > 0 && layout.height <= 128, label + ': no upscaling');
    assert.ok(Math.abs(layout.centerOffset) < 1, label + ': horizontally centered');
    const whitespace = current.viewportSize().width <= 760 ? 96 : 128;
    assert.ok(layout.above >= whitespace && layout.below >= whitespace, label + ': generous whitespace above and below');
    assert.equal(layout.heroDisplay, 'block', label + ': opening uses full-width block');
    assert.ok(Math.abs(layout.heroGap) < 1, label + ': no empty opening column');
    await mark.scrollIntoViewIfNeeded();
    await fits(current, label + ' closing mark');
    await capture(label + '-closing-mark', current);
  };
  const checkProjectDisclosure = async (current, label) => {
    const details = current.locator('#project-data');
    const summary = details.locator(':scope > summary');
    assert.equal(await details.evaluate(node => node.open), false, label + ': collapsed initially');
    assert.ok((await summary.textContent()).startsWith('Data table'), label + ': summary names the table');
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
    const clipped = await current.locator('#observatory-filters select, #observatory-filters button, [data-metric], .obs-bars, .obs-table-scroll, .shared-name-group')
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
      const visual = chart.locator('.obs-bars');
      assert.equal(await chart.locator('svg').count(), 0, 'HTML bars, no SVG: ' + name);
      assert.equal(await visual.getAttribute('aria-hidden'), 'true', 'Table is the accessible chart equivalent: ' + name);
      const bars = await visual.locator('.obs-bar').evaluateAll(nodes => nodes.map(node => ({
        label: node.querySelector('.obs-bar-label').textContent, count: Number(node.dataset.count),
        shown: node.querySelector('.obs-bar-count').textContent, width: parseFloat(node.querySelector('.obs-fill').style.width),
        unknown: node.classList.contains('obs-bar-unknown') })));
      assert.deepEqual(bars.map(bar => [bar.label, bar.count]), actual, `One visible bar per table value: ${name}, ${label}`);
      const shared = ['push', 'release'].includes(name);
      const max = shared ? Math.max(0, ...expected.push.concat(expected.release).map(([, value]) => value)) : Math.max(0, ...actual.map(([, value]) => value));
      const scale = clean(await visual.locator('.obs-scale-max').textContent());
      assert.equal(scale, max.toLocaleString('en-US') + (name === 'star' ? ' stars' : ' projects') + (shared ? ' · shared scale' : ''), 'Maximum scale label: ' + name);
      assert.equal(clean(await visual.locator('.obs-scale-ends > span').first().textContent()), '0', 'Scale starts at zero: ' + name);
      for (const bar of bars) {
        assert.ok(Math.abs(bar.width - (max ? 100 * bar.count / max : 0)) <= .001, `Bar width matches table: ${name}/${bar.label}, ${label}`);
        assert.equal(bar.shown, bar.count.toLocaleString('en-US'), 'Visible count matches value');
        assert.equal(bar.unknown, bar.label === 'Unknown', 'Unknown bars are marked by form');
      }
      assert.equal(await visual.locator('.obs-empty').count(), actual.length ? 0 : 1, `Empty note only without rows: ${name}, ${label}`);
      if (!['category', 'star'].includes(name)) assert.equal(actual.reduce((sum, [, value]) => sum + value, 0), selected.length, 'Distribution denominator: ' + name);
    }
  };
  const assertSelection = async (current, data, selected, label) => {
    await assertSharedNames(current, selected, label);
    // This finding always describes the whole collection, including after filters.
    const observed = data.projects.filter(project => project.github && Number.isFinite(project.stars))
      .map(project => project.stars).sort((a, b) => b - a);
    const total = observed.reduce((sum, stars) => sum + stars, 0);
    if (observed.length >= 10 && total > 0) {
      const text = await current.locator('#obs-finding-text').textContent();
      const share = 100 * observed.slice(0, 10).reduce((sum, stars) => sum + stars, 0) / total;
      assert.deepEqual([...text.matchAll(/(\d+(?:\.\d+)?)%/g)].map(match => match[1]),
        [share.toFixed(1)], label + ': displayed whole-collection top-ten percentage');
      for (const meaning of [/\b10\b/, /\bprojects\b/, /\bstars\b/]) assert.match(text, meaning);
    }
    const ranked = data.projects.filter(project => project.github && Number.isFinite(project.stars))
      .sort((a,b) => b.stars-a.stars || (a.name < b.name ? -1 : a.name > b.name ? 1 : a.id < b.id ? -1 : 1));
    const leaders = current.locator('.obs-strip-leader');
    assert.equal(await leaders.count(), total ? Math.min(10, ranked.length) : 0, label + ': actual leader segments');
    if (total) {
      const segments = await current.locator('.obs-strip-segment').evaluateAll(nodes => nodes.map(node => ({
        stars: Number(node.dataset.stars), width: parseFloat(node.style.width), label: node.getAttribute('aria-label'),
        hidden: Boolean(node.closest('[aria-hidden="true"]')), focus: node.getAttribute('tabindex'),
      })));
      assert.equal(segments.reduce((sum,node) => sum+node.stars,0),total,label + ': leaders plus tail');
      for (const node of segments) {
        assert.ok(Math.abs(node.width - 100*node.stars/total) <= .001, label + ': width from raw count');
        assert.equal(node.hidden,false,label + ': accessible segments');
        assert.equal(node.focus,node.stars ? '0' : null);
      }
      for (let i=0;i<Math.min(10,ranked.length);i++) {
        assert.equal(segments[i].label,ranked[i].name + ' · ' + ranked[i].stars.toLocaleString('en-US') + ' stars');
      }
      // Do not disturb the filter-focus lifecycle assertions on later selections.
      if (['initial', 'standalone initial', 'no JavaScript'].includes(label)) {
        const first=leaders.first();
        await first.hover();
        assert.equal(await first.locator('.obs-strip-tooltip').isVisible(),true,label + ': hover label');
        await current.mouse.move(0,0);
        await first.focus();
        assert.equal(await first.locator('.obs-strip-tooltip').isVisible(),true,label + ': keyboard label');
        await first.evaluate(node => node.blur());
      }
    }
    assert.deepEqual(await visibleIDs(current), selected.map(project => project.id), 'Underlying project selection: ' + label);
    const expected = { total: selected.length, mapped: selected.filter(project => project.github).length,
      stars: selected.filter(project => project.github && Number.isFinite(project.stars)).reduce((sum, project) => sum + project.stars, 0),
      'known-license': selected.filter(hasLicense).length };
    if (selected.length && !selected.some(project => project.github && Number.isFinite(project.stars))) expected.stars = null;
    for (const [metric, value] of Object.entries(expected)) {
      const text = await current.locator('[data-metric="' + metric + '"]').textContent();
      assert.equal(value === null ? clean(text) : number(text), value === null ? 'Unknown' : value, `Metric ${metric}: ${label}`);
    }
    assert.ok(clean(await current.locator('#selection-summary').textContent()).includes(selected.length.toLocaleString('en-US')), 'Announced selection count: ' + label);
    await assertCharts(current, data, selected, label);
  };
  const assertCSV = (csv, data, selected, label) => {
    const headers = csv.replace(/^\uFEFF/, '').split(/\r?\n/, 1)[0].split(',').map(value => value.replace(/^"|"$/g, ''));
    assert.deepEqual(headers, ['id', 'name', 'url', 'description', 'categories', 'github', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_as_of', 'source_sha', 'metrics_status', 'metrics_last_success_at', 'metrics_attempt_at', 'metrics_attempt_status', 'metrics_attempt_http_status', 'metrics_attempt_reason'], 'CSV schema, including empty exports: ' + label);
    const rows = parseCSV(csv);
    assert.deepEqual(rows.map(row => row.id), selected.map(project => project.id), 'Export selection: ' + label);
    const safeCell = value => {
      const text = value === null || value === undefined ? '' : String(value);
      return /^[=+\-@\t\r\n]/.test(text.trimStart()) ? "'" + text : text;
    };
    for (let index = 0; index < rows.length; index++) {
      const actual = rows[index], project = selected[index];
      for (const key of ['id', 'name', 'url', 'description', 'stars', 'license', 'created_at', 'pushed_at', 'release_at', 'release_status', 'release_checked_at', 'metrics_status', 'metrics_last_success_at', 'metrics_attempt_at', 'metrics_attempt_status', 'metrics_attempt_http_status', 'metrics_attempt_reason']) {
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
    await checkFooter(false);
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
      assert.equal(project.github, Boolean(canonical.github) && github.status !== 'unavailable');
      assert.equal(project.metrics_status, canonical.github ? (github.status || 'fresh') : 'unknown');
      assert.equal(project.metrics_last_success_at, canonical.github ? (Object.hasOwn(github, 'last_success_at') ? github.last_success_at : catalog.metrics_as_of) : null);
      for (const [field, key] of [['metrics_attempt_at', 'at'], ['metrics_attempt_status', 'status'], ['metrics_attempt_http_status', 'http_status'], ['metrics_attempt_reason', 'reason']]) assert.equal(project[field], github.last_attempt?.[key] ?? null, 'Metrics attempt provenance: ' + field);
      for (const field of ['stars', 'license', 'created_at', 'pushed_at']) assert.equal(project[field], github[field] ?? null, 'Cached source projection: ' + field);
      assert.equal(project.release_at, release.last_good?.value?.published_at ?? null, 'Release uses its cached publication date');
      assert.equal(project.release_checked_at, release.checked_at ?? null, 'Release checked time remains distinct');
    }
    const logo = page.locator('.obs-logo');
    assert.equal(await logo.getAttribute('src'), '../brand/botanical-128.png');
    assert.equal(await logo.getAttribute('alt'), 'Awesome Open* botanical logo');
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
      await capture(name);
      await checkClosingMark(page, name);
      await page.locator('#shared-names').scrollIntoViewIfNeeded();
      await capture(name + '-shared-names');
      for (const id of ['name-groups', 'name-method']) {
        const disclosure = page.locator('#' + id);
        if (id === 'name-method') await page.locator('#name-groups').evaluate(node => { node.open = true; });
        await disclosure.locator(':scope > summary').focus();
        for (const key of ['Enter', 'Space']) {
          const previous = await disclosure.evaluate(node => node.open);
          await page.keyboard.press(key);
          assert.equal(await disclosure.evaluate(node => node.open), !previous, 'Keyboard disclosure: ' + id);
          assert.equal(await disclosure.locator(':scope > summary').evaluate(node => node === document.activeElement), true, 'Disclosure keeps focus: ' + id);
          await fits(page, name + ' ' + id);
          if (!previous) await capture(name + '-' + id + '-open');
        }
      }
      await page.locator('#name-groups').evaluate(node => { node.open = false; });
      if (await page.locator('#name-tally .obs-cluster').count()) {
        await page.locator('#name-tally .obs-cluster').first().click();
        assert.equal(await page.locator('#name-groups').evaluate(node => node.open), true, 'Tally cluster opens name groups');
        assert.equal(new URL(page.url()).hash, '#name-group-1', 'Tally cluster links to its plate');
        await page.locator('#name-groups').evaluate(node => { node.open = false; });
        await page.evaluate(() => history.replaceState(null, '', location.pathname + location.search));
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
      assert.ok(row.cells[5].includes(project.metrics_status), 'Underlying metrics cache status');
      assert.ok(row.cells[5].includes(project.metrics_last_success_at || 'Unknown'), 'Underlying metrics observation time');
      assert.ok(row.cells[5].includes(project.metrics_attempt_at || 'Not recorded'), 'Underlying metrics attempt time');
      if (project.metrics_attempt_http_status) assert.ok(row.cells[5].includes('HTTP ' + project.metrics_attempt_http_status), 'Underlying metrics HTTP status');
      if (project.metrics_attempt_reason) assert.ok(row.cells[5].includes(project.metrics_attempt_reason), 'Underlying metrics attempt reason');
      assert.ok(row.cells[6].includes(project.release_status), 'Underlying release cache status');
      assert.ok(row.cells[6].includes(project.release_checked_at || 'Not checked'), 'Underlying release check time');
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
    await fallback.locator('#name-groups > summary').click();
    assert.equal(await fallback.locator('#name-groups').evaluate(node => node.open), true, 'Name groups expand without JavaScript');
    await fallback.locator('#name-method > summary').click();
    assert.equal(await fallback.locator('#name-method').evaluate(node => node.open), true, 'Method expands without JavaScript');
    await fallback.locator('#category-chart details > summary').click();
    assert.equal(await fallback.locator('#category-chart table').isVisible(), true, 'Native data disclosure without JavaScript');
    await fits(fallback, 'no JavaScript');
    await capture('no-js', fallback);
    await checkClosingMark(fallback, 'no-js-mobile');
    await fallback.setViewportSize({ width: 1440, height: 1000 });
    await checkClosingMark(fallback, 'no-js-desktop');
    await fallback.setViewportSize({ width: 390, height: 844 });
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
    await assertSharedNames(synthetic, syntheticProjects, 'synthetic case, separators and Unicode whitespace');
    // Every name but the zero-width-space one shares the key "opentool".
    assert.equal(number(await synthetic.locator('#shared-name-count').textContent()), 9, 'Synthetic single-key count');
    assert.equal(await synthetic.locator('#variant-name-groups .obs-tag').allTextContents().then(tags => tags.join('|')), 'Case|Spacing|Exact duplicates', 'Synthetic variant tags');
    await synthetic.setViewportSize({ width: 390, height: 844 });
    await synthetic.locator('#name-groups > summary').click();
    assert.ok(await synthetic.locator('#variant-name-groups .name-diff').count() > 0, 'Differences are marked');
    await synthetic.locator('#variant-name-groups .shared-name-group').first().scrollIntoViewIfNeeded();
    await fits(synthetic, 'synthetic variants mobile');
    await capture('synthetic-variants-open', synthetic);
    await synthetic.close();
    report.checks.push('single-key grouping, tags and difference marks with synthetic case/separator/Unicode names');

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
    await checkFooter(true);
    assert.deepEqual(offlineRequests, [], 'Standalone fetches no neighboring assets');
    assert.ok((await page.locator('.obs-logo').getAttribute('src')).startsWith('data:image/png;base64,'));
    await page.setViewportSize({ width: 1440, height: 1000 });
    await checkClosingMark(page, 'standalone-desktop');
    await page.setViewportSize({ width: 390, height: 844 });
    await checkClosingMark(page, 'standalone-mobile');
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
    report.checks.push('centered prefooter logo at intrinsic size, full-width opening, generous whitespace and closing-mark screenshots across desktop/mobile/no-JavaScript/standalone');
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
