/* Painted-bounds geometry: transparent source canvas must not reserve empty rows. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const near = (actual, expected, label) => assert.ok(Math.abs(actual - expected) <= 1.1,
  `${label}: expected ${expected}, got ${actual}`);

// Readiness is independent of correctness: a stable but wrong connector must
// still reach assertGeometry and fail. Sample on animation frames so resize
// handlers and responsive layout run before we compare the image and SVG.
function stableLayoutSample({ selector, reset = false }) {
  const plate = document.querySelector(selector);
  if (!plate) return false;
  if (reset) { delete plate.__boundsReadiness; return false; }
  const image = plate.querySelector('.plate-art img');
  if (!image || !image.complete || !image.naturalWidth || document.fonts.status !== 'loaded') {
    delete plate.__boundsReadiness;
    return false;
  }
  const nodes = plate.querySelectorAll('.plate-study, .plate-field, .plate-stage, .plate-art img, .plate-crop, .specimen-label');
  const snapshot = JSON.stringify([
    innerWidth, innerHeight, image.currentSrc,
    ...Array.from(nodes, node => {
      const r = node.getBoundingClientRect();
      return [r.left, r.top, r.width, r.height];
    }),
    plate.querySelector('.plate-leaders')?.innerHTML || ''
  ]);
  const prior = plate.__boundsReadiness;
  const frames = prior && prior.snapshot === snapshot ? prior.frames + 1 : 1;
  plate.__boundsReadiness = { snapshot, frames };
  return frames >= 3;
}

async function waitForSpecimenLayout(page, selector = '.specimen-plate', noJavaScript = false) {
  await page.locator(selector + ' .plate-art img').evaluate(image => image.decode());
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(stableLayoutSample, { selector, reset: true });
  try {
    if (noJavaScript) {
      // Browser timers do not reliably run with page JavaScript disabled.
      // Drive bounded condition polling from Node, not a fixed layout delay.
      const deadline = Date.now() + 5000;
      while (!await page.evaluate(stableLayoutSample, { selector })) {
        assert.ok(Date.now() < deadline, 'No-JS specimen layout did not stabilize');
        await new Promise(resolve => setTimeout(resolve, 16));
      }
    } else {
      await page.waitForFunction(stableLayoutSample, { selector }, { polling: 'raf', timeout: 5000 });
    }
  } finally {
    await page.evaluate(stableLayoutSample, { selector, reset: true });
  }
}

async function measure(page, selector = '.specimen-plate') {
  return page.locator(selector).evaluate(plate => {
    const field = plate.querySelector('.plate-field');
    const stage = field.querySelector('.plate-stage');
    const image = field.querySelector('img');
    const rect = node => {
      const r = node.getBoundingClientRect();
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    };
    return { field: rect(field), stage: rect(stage), image: rect(image),
      label: rect(plate.querySelector('.specimen-label')),
      labelFont: parseFloat(getComputedStyle(plate.querySelector('.specimen-label')).fontSize),
      bbox: field.dataset.bbox.split(' ').map(Number), cutout: field.dataset.cutout,
      naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight,
      overflow: getComputedStyle(stage).overflow,
      studyTop: plate.querySelector('.plate-study').getBoundingClientRect().top,
      leaderY: Array.from(plate.querySelectorAll('.plate-leaders circle'), n => Number(n.getAttribute('cy'))),
      pageFits: document.documentElement.scrollWidth <= innerWidth,
      terrain: field.querySelector('.plate-terrain')?.getAttribute('viewBox') || null };
  });
}

function assertGeometry(m, label) {
  const [left, top, right, bottom] = m.bbox;
  const retainedTop = Math.max(0, top - .08);
  const retainedBottom = Math.min(1, bottom + .08);
  near(m.image.width, Math.min(627, m.field.width), label + ' preserves image width');
  near(m.image.height, m.image.width * m.naturalHeight / m.naturalWidth, label + ' preserves image ratio');
  near(m.stage.height, m.image.height * (retainedBottom - retainedTop), label + ' compacts empty vertical canvas');
  near(m.stage.left + m.stage.width / 2, m.field.left + m.field.width / 2, label + ' centers stage');
  near(m.image.top, m.stage.top - retainedTop * m.image.height, label + ' offsets full source canvas');
  const paintedTop = m.image.top + top * m.image.height;
  const paintedBottom = m.image.top + bottom * m.image.height;
  assert.ok(paintedTop >= m.field.top - 1.1, label + ' preserves subject top');
  assert.ok(paintedBottom <= m.field.bottom + 1.1, label + ' preserves subject bottom');
  near(m.label.top - m.field.bottom, -4 * m.labelFont, label + ' label overlaps field and reclaims flow space');
  if (m.terrain) {
    const viewBox = m.terrain.split(' ').map(Number);
    near(viewBox[3], 1000 * m.stage.height / m.stage.width, label + ' terrain uses compact stage proportions');
  }
  m.leaderY.forEach((y, i) => near(m.studyTop + y, paintedBottom + 3 + i * 2, label + ' leader follows subject baseline'));
  assert.ok(m.pageFits, label + ' fits viewport');
  assert.equal(m.overflow, 'visible', label + ' does not hard-clip soft artwork edges');
  assert.ok(left >= 0 && right <= 1, label + ' normalized horizontal bounds');
}

async function captureSpecimen(page, filename) {
  // The field deliberately reaches into the column gutters. Capture its union
  // with the label, not the narrower parent, so evidence never clips the art.
  await page.locator('.plate-field').scrollIntoViewIfNeeded();
  const clip = await page.locator('.specimen-plate').evaluate(plate => {
    const nodes = ['.plate-field', '.specimen-label'].map(selector => plate.querySelector(selector).getBoundingClientRect());
    const x = Math.max(0, Math.min(...nodes.map(r => r.left)) + scrollX);
    const y = Math.max(0, Math.min(...nodes.map(r => r.top)) + scrollY);
    const right = Math.max(...nodes.map(r => r.right)) + scrollX;
    const bottom = Math.max(...nodes.map(r => r.bottom)) + scrollY;
    return { x, y, width: right - x, height: bottom - y };
  });
  await page.screenshot({ path: filename, fullPage: true, clip, animations: 'disabled', caret: 'hide', scale: 'css' });
}

module.exports = async function checkSpecimenBounds({ browser, context, url, data }) {
  const cutouts = JSON.parse(fs.readFileSync(path.join(__dirname, '../site/specimens/cutouts.json'), 'utf8')).cutouts;
  const projects = data.projects.filter(p => p.artwork && cutouts[p.id]);
  projects.sort((a, b) => {
    const height = p => cutouts[p.id].subject_bbox[3] - cutouts[p.id].subject_bbox[1];
    return height(a) - height(b);
  });
  assert.ok(projects.length >= 2, 'Short and tall specimen fixtures available');
  const cases = [...new Map([projects[0], projects[projects.length - 1],
    ...['OpenSpec', 'OpenBB', 'openpilot', 'OpenRocket', 'OpenTodo'].map(name =>
      projects.find(p => p.name.toLowerCase() === name.toLowerCase())).filter(Boolean)
  ].map(project => [project.id, project])).values()];
  const output = path.join(__dirname, '../tmp/site-qa');
  fs.mkdirSync(output, { recursive: true });
  const screenshots = [];
  const page = await context.newPage();
  const results = [];
  let currentCase = null;
  try {
    for (const project of cases) {
      await page.goto(new URL(`records/${project.id}.html`, url).href);
      await page.locator('.plate-art img').evaluate(image => image.decode());
      for (const [step, width] of [1440, 901, 900, 768, 721, 720, 390, 320,
        390, 720, 721, 900, 901, 1440, 320, 901, 900, 1440].entries()) {
        currentCase = { id: project.id, name: project.name, width, step, phase: 'resize' };
        await page.setViewportSize({ width, height: 1000 });
        await waitForSpecimenLayout(page);
        const m = await measure(page);
        assertGeometry(m, `${project.name} at ${width}px`);
        // srcset sizes "(max-width: 660px) 100vw, 627px" must not undercount the drawing.
        if (await page.locator('.plate-art img[srcset]').count()) {
          assert.ok(m.image.width <= (width <= 660 ? width : 627) + 1,
            `${project.name} at ${width}px: ${m.image.width}px exceeds the sizes slot`);
        }
        results.push({ name: project.name, step, viewport: width, imageWidth: m.image.width, fieldHeight: m.field.height });
        if (step < 8 && [1440, 901, 900, 390, 320].includes(width)) {
          await page.evaluate(() => document.fonts.ready);
          await page.locator('.plate-specimen').scrollIntoViewIfNeeded();
          const file = `bounds-${project.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${width}.png`;
          await captureSpecimen(page, path.join(output, file));
          screenshots.push(file);
        }
      }
      currentCase = { id: project.id, name: project.name, width: 900, phase: 'loupe' };
      await page.setViewportSize({ width: 900, height: 1000 });
      await page.locator('.plate-stage').scrollIntoViewIfNeeded();
      await waitForSpecimenLayout(page);
      const m = await measure(page);
      const x = m.image.left + m.image.width * .5;
      const y = m.image.top + m.image.height * (m.bbox[1] + m.bbox[3]) / 2;
      await page.mouse.move(x, y);
      const lens = await page.locator('.plate-lens').evaluate(node => ({
        on: node.classList.contains('is-on'), left: parseFloat(node.style.left), top: parseFloat(node.style.top),
        image: node.style.backgroundImage
      }));
      assert.ok(lens.on, 'Loupe activates over compacted subject');
      assert.ok(!lens.image.includes('/specimens/responsive/'), 'Loupe magnifies the full-size source');
      near(lens.left, x - m.field.left, 'Loupe pointer x');
      near(lens.top, y - m.field.top, 'Loupe pointer y');
    }
    // Negative control: readiness must never repair the SVG or poll the geometry
    // assertion until it passes. A settled 20px error is still a real failure.
    currentCase = { ...currentCase, phase: 'negative control' };
    const hasLeader = await page.locator('.plate-leaders circle').count();
    assert.ok(hasLeader, 'Negative control has a connector');
    const originalY = await page.locator('.plate-leaders circle').first().getAttribute('cy');
    try {
      await page.locator('.plate-leaders circle').first().evaluate(node => {
        node.setAttribute('cy', String(Number(node.getAttribute('cy')) + 20));
      });
      await waitForSpecimenLayout(page);
      const negativeMeasurement = await measure(page);
      assert.throws(() => assertGeometry(negativeMeasurement, 'Deliberately misplaced connector'),
        /leader follows subject baseline/);
    } finally {
      await page.locator('.plate-leaders circle').first().evaluate((node, y) => node.setAttribute('cy', y), originalY);
    }
    await waitForSpecimenLayout(page);
    assertGeometry(await measure(page), 'Restored connector');
    // A phone at 1x loads the 512px variant rather than the full-size source.
    const phone = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    try {
      const sample = cases.find(project => project.artwork);
      await phone.goto(new URL(`records/${sample.id}.html`, url).href);
      const image = phone.locator('.plate-art img');
      if (await image.getAttribute('srcset')) {
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(node => node.decode());
        const current = await image.evaluate(node => new URL(node.currentSrc).pathname);
        assert.match(current, /\/specimens\/responsive\/[a-f0-9]{64}(-cutout)?-512\.webp$/, 'Phone loads the 512px variant');
      }
    } finally { await phone.close(); }
    // A real PR-base renderer/CSS/JS control, using identical catalog and art.
    const baseResponse = await context.request.get(new URL('bounds-before/source.json', url).href);
    let baseline = null;
    if (baseResponse.ok()) {
      baseline = await baseResponse.json();
      for (const project of cases.filter(p => ['openspec', 'openbb', 'openpilot', 'openrocket'].includes(p.name.toLowerCase()))) {
        for (const width of [1440, 390]) {
          currentCase = { id: project.id, name: project.name, width, phase: 'PR-base capture' };
          await page.setViewportSize({ width, height: 1000 });
          await page.goto(new URL(`bounds-before/${project.id}.html`, url).href);
          await page.locator('.plate-art img').evaluate(image => image.decode());
          await page.evaluate(() => document.fonts.ready);
          const file = `bounds-before-${project.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${width}.png`;
          await captureSpecimen(page, path.join(output, file));
          screenshots.push(file);
        }
      }
      fs.writeFileSync(path.join(output, 'bounds-before-source.json'), JSON.stringify(baseline, null, 2));
    }
  } catch (error) {
    // This child page holds the failing record. The core suite's parent-page
    // failure.png cannot show a record opened here.
    const failure = { ...currentCase, url: page.url(), viewport: page.viewportSize(), error: error.message };
    failure.measurement = await measure(page).catch(() => null);
    await page.screenshot({ path: path.join(output, 'bounds-failure.png'), fullPage: true,
      animations: 'disabled', caret: 'hide', scale: 'css' }).catch(captureError => {
      failure.screenshotError = captureError.message;
    });
    fs.writeFileSync(path.join(output, 'bounds-failure.json'), JSON.stringify(failure, null, 2) + '\n');
    throw error;
  } finally { await page.close(); }
  const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const staticPage = await noJS.newPage();
    await staticPage.goto(new URL(`records/${cases[0].id}.html`, url).href);
    await staticPage.locator('.plate-art img').evaluate(image => image.decode());
    // requestAnimationFrame polling is unavailable in a JavaScript-disabled context.
    // Poll the same readiness condition instead; geometry assertions stay identical.
    await waitForSpecimenLayout(staticPage, '.specimen-plate', true);
    assertGeometry(await measure(staticPage), 'No-JS static record');
    await staticPage.emulateMedia({ media: 'print' });
    // requestAnimationFrame polling is unavailable in a JavaScript-disabled context.
    // Poll the same readiness condition instead; geometry assertions stay identical.
    await waitForSpecimenLayout(staticPage, '.specimen-plate', true);
    assertGeometry(await measure(staticPage), 'Printed no-JS static record');
  } finally { await noJS.close(); }
  const touch = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  try {
    const touchPage = await touch.newPage();
    await touchPage.goto(new URL(`records/${cases[0].id}.html`, url).href);
    await touchPage.locator('.plate-art img').evaluate(image => image.decode());
    await touchPage.locator('.plate-stage').tap();
    assert.equal(await touchPage.locator('.plate-lens').evaluate(n => n.classList.contains('is-on')), true, 'Tap opens loupe');
    await touchPage.locator('.plate-stage').tap();
    assert.equal(await touchPage.locator('.plate-lens').evaluate(n => n.classList.contains('is-on')), false, 'Second tap closes loupe');
  } finally { await touch.close(); }
  return { cases: results, screenshots, noJS: true, print: true, touch: true };
};

module.exports.stableLayoutSample = stableLayoutSample;
module.exports.assertGeometry = assertGeometry;

module.exports.waitForSpecimenLayout = waitForSpecimenLayout;
