/* Exhaustive specimen assertions and planned captures, one bounded ID chunk per process. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const CHUNK_SIZE = 32;
const policy = require('./browser_capture.cjs');
(async () => {
  const chunk = Number(process.argv[2]);
  assert.ok(Number.isInteger(chunk) && chunk >= 0, 'Supply a nonnegative chunk index');
  const output = path.resolve(__dirname, '../tmp/site-qa');
  fs.mkdirSync(output, { recursive: true });
  const report = { status: 'running', chunk, sourceSha: null, prHeadSha: process.env.PR_HEAD_SHA || null, planId: policy.plan?.planId || null, projects: [], screenshots: [] };
  const write = () => fs.writeFileSync(path.join(output, `artwork-${chunk}.json`), JSON.stringify(report, null, 2) + '\n');
  write();
  let browser, page;
  try {
    browser = await chromium.launch({ headless: true,
      ...(process.env.CHROMIUM_NO_SANDBOX === '1' ? { args: ['--no-sandbox'] } : {}),
      ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1,
      colorScheme: 'light', reducedMotion: 'reduce', locale: 'en-US', timezoneId: 'UTC' });
    context.setDefaultTimeout(15000);
    page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const url = process.env.SITE_URL || 'http://127.0.0.1:8000';
    await page.goto(url);
    await page.waitForFunction(() => document.querySelector('#filters').dataset.enhanced === 'true');
    const response = await context.request.get(new URL('catalog.json', page.url()).href);
    assert.ok(response.ok(), 'Full catalog download is available');
    const data = await response.json();
    report.sourceSha = data.source_sha;
    if (process.env.SITE_SOURCE_SHA) assert.equal(data.source_sha, process.env.SITE_SOURCE_SHA);
    const illustrated = data.projects.filter(p => p.artwork).sort((a, b) => a.id.localeCompare(b.id));
    assert.equal(new Set(illustrated.map(p => p.id)).size, illustrated.length, 'Canonical IDs are unique');
    const projects = illustrated.slice(chunk * CHUNK_SIZE, (chunk + 1) * CHUNK_SIZE);
    assert.ok(projects.length, 'Chunk must contain artwork');
    report.expectedIds = projects.map(p => p.id);
    report.expectedCaptureIds = report.expectedIds.filter(policy.artwork); write();
    const change = async (id, value) => {
      await page.locator('#' + id).fill(value);
      await page.locator('#' + id).dispatchEvent('change');
    };
    // The Catalog opens one plate at a time in its pane.
    const waitForPlate = card => card.locator('.specimen-plate').waitFor({ state: 'visible' });
    const capture = async name => {
      await page.evaluate(() => document.fonts.ready);
      const png = await page.screenshot({ path: path.join(output, name), animations: 'disabled', caret: 'hide', scale: 'css' });
      const dimensions = { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
      assert.deepEqual(dimensions, page.viewportSize(), `Screenshot dimensions: ${name}`);
      report.screenshots.push({ file: name, ...dimensions, bytes: png.length, sha256: require('node:crypto').createHash('sha256').update(png).digest('hex') }); write();
    };
    for (const project of projects) {
      report.currentProjectId = project.id; write();
      await change('search', project.name);
      const row = page.locator(`#rows .row[data-id="${project.id}"]`);
      await row.locator('a').click();
      const card = page.locator('#pane-scroll');
      // The previous plate stays until this record has loaded and passed its checks.
      await page.waitForFunction(id => document.querySelector('#pane-scroll .specimen-plate')?.getAttribute('aria-labelledby') === 'name-' + id, project.id);
      await waitForPlate(card);
      assert.equal(await page.locator('#plate-name').textContent(), project.name, 'Click after search must open ' + project.name);
      // In All, the description starts with its category.
      assert.ok((await row.locator('.row-desc').textContent()).endsWith(project.description));
      if (project.function_summary) {
        assert.equal(await card.locator('.function-detail > p').first().textContent(), project.function_summary.text);
        assert.ok(await card.locator('.function-provenance a').count() > 0);
      } else {
        assert.equal(await card.locator('.function-detail').count(), 0);
      }
      const image = card.locator('.specimen-art img');
      await image.scrollIntoViewIfNeeded();
      await page.waitForFunction(() => { const img = document.querySelector('#pane-scroll .specimen-art img'); return img && img.complete && img.naturalWidth > 0; }, null, { timeout: 10000 });
      assert.equal(await image.evaluate(img => img.naturalWidth > 0), true);
      if (policy.artwork(project.id)) await capture('specimen-' + project.id + '.png');
      report.projects.push({ id: project.id, name: project.name }); write();
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(report.projects.map(p => p.id), report.expectedIds);
    report.status = 'passed';
  } catch (error) {
    report.status = 'failed'; report.error = error.message;
    if (page) await page.screenshot({ path: path.join(output, `artwork-${chunk}-failure.png`) }).catch(() => {});
    throw error;
  }
  finally { write(); if (browser) await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
