/* The About sheet ends on one footer panorama per load, at native size and centred in the pane. */
const assert = require('node:assert/strict');
module.exports = async ({ page, url, data, capture }) => {
  const measure = () => page.locator('.about-art').evaluate(async art => {
    await art.decode();
    const rect = art.getBoundingClientRect(), sheet = art.closest('.about-scroll').getBoundingClientRect();
    return { width: rect.width, height: rect.height, naturalWidth: art.naturalWidth, naturalHeight: art.naturalHeight,
      widthAttr: Number(art.getAttribute('width')), heightAttr: Number(art.getAttribute('height')),
      center: (rect.left + rect.right) / 2, sheetCenter: (sheet.left + sheet.right) / 2,
      choices: JSON.parse(art.dataset.backgrounds), sizes: JSON.parse(art.dataset.backgroundSizes) };
  });
  const backgrounds = data.footer_backgrounds || [];
  assert.ok(backgrounds.length > 0, 'Footer panoramas are published');
  // Exercise every panorama; filename changes must remain automatic.
  await page.addInitScript(() => { Math.random = () => Number(sessionStorage.getItem('footer-test-random') || 0); });
  for (const [index] of backgrounds.entries()) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(url);
    await page.evaluate(value => sessionStorage.setItem('footer-test-random', String(value)), (index + .5) / backgrounds.length);
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#filters')?.dataset.enhanced === 'true');
    await page.locator('#rail-about').click();
    await page.locator('#pane-about').waitFor({ state: 'visible' });
    const art = page.locator('.about-art');
    await art.scrollIntoViewIfNeeded();
    assert.ok((await art.getAttribute('src')).endsWith(backgrounds[index]));
    for (const width of [2560, 1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      const size = await measure();
      assert.deepEqual([size.width, size.height], [size.naturalWidth, size.naturalHeight], `Panorama ${index} keeps native size at ${width}px`);
      assert.deepEqual([size.naturalWidth, size.naturalHeight], [size.widthAttr, size.heightAttr]);
      assert.ok(Math.abs(size.center - size.sheetCenter) < 1, 'Panorama stays centred on the sheet');
      assert.equal(size.choices.length, size.sizes.length);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `No page overflow at ${width}px`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await art.scrollIntoViewIfNeeded();
    await capture('about-art-' + index + '.png');
  }
  // The rail carries the field-guide footers' pattern.
  const pattern = await page.locator('.rail').evaluate(node => getComputedStyle(node).backgroundImage);
  assert.ok(pattern.includes('/patterns/navypattern2.png'), 'Rail uses the navy pattern');
  await page.setViewportSize({ width: 1440, height: 1000 });
};
