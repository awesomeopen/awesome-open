/* Exhaustive specimen capture, one bounded canonical-ID chunk per process. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const CHUNK_SIZE = 32;
(async () => {
  const chunk = Number(process.argv[2]);
  assert.ok(Number.isInteger(chunk) && chunk >= 0, 'Supply a nonnegative chunk index');
  const output = path.resolve(__dirname, '../tmp/site-qa');
  fs.mkdirSync(output, { recursive: true });
  const report = { status: 'running', chunk, sourceSha: null, prHeadSha: process.env.PR_HEAD_SHA || null, projects: [], screenshots: [] };
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
    report.expectedIds = projects.map(p => p.id); write();
    const change = async (id, value) => {
      await page.locator('#' + id).fill(value);
      await page.locator('#' + id).dispatchEvent('change');
    };
    const waitForPlate = card => card.locator('.specimen-plate').waitFor({ state: 'visible' });
    const capture = async name => {
      await page.evaluate(() => document.fonts.ready);
      const png = await page.screenshot({ path: path.join(output, name), animations: 'disabled', caret: 'hide', scale: 'css' });
      const dimensions = { width: png.readUInt32BE(16), height: png.readUInt32BE(20) };
      assert.deepEqual(dimensions, page.viewportSize(), `Screenshot dimensions: ${name}`);
      report.screenshots.push({ file: name, ...dimensions, bytes: png.length }); write();
    };
    for (const project of projects) {
      report.currentProjectId = project.id; write();
      await change('search', project.name);
      const card = page.locator('#project-' + project.id);
      await card.locator('summary').first().click();
      assert.equal(await card.locator('details.specimen-drawer').evaluate(node => node.open), true, 'Click after search must open ' + project.name);
      await waitForPlate(card);
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
      await capture('specimen-' + project.id + '.png');
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
