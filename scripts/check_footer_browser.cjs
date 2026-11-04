const assert = require('node:assert/strict');
module.exports = async ({ page, url, data, capture }) => {
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
  const checkFooter = async () => {
    for (const width of [2560, 1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.locator('.site-footer').scrollIntoViewIfNeeded();
      const footer = await page.locator('.site-footer').evaluate(async node => {
        const style = getComputedStyle(node);
        const background = style.backgroundImage.slice(5, -2);
        const image = new Image();
        image.src = background;
        await image.decode();
        const art = node.querySelector('[data-footer-background]');
        await art.decode();
        const rect = art.getBoundingClientRect(), bounds = node.getBoundingClientRect();
        return { renderedWidth: rect.width, renderedHeight: rect.height, center: (rect.left + rect.right) / 2,
          footerCenter: (bounds.left + bounds.right) / 2, bottom: rect.bottom, footerBottom: bounds.bottom - parseFloat(style.borderBottomWidth),
          clipped: style.overflowX, background, width: image.naturalWidth, artWidth: art.naturalWidth,
          artHeight: art.naturalHeight, widthAttr: Number(art.getAttribute('width')), heightAttr: Number(art.getAttribute('height')),
          sizes: JSON.parse(art.dataset.backgroundSizes),
          choices: JSON.parse(art.dataset.backgrounds), border: style.borderTopStyle };
      });
      assert.equal(footer.width, 1254);
      assert.equal(footer.artWidth, footer.widthAttr);
      assert.equal(footer.artHeight, footer.heightAttr);
      assert.equal(footer.renderedWidth, footer.artWidth, "Footer artwork keeps its native width");
      assert.equal(footer.renderedHeight, footer.artHeight, "Footer artwork keeps its native height");
      assert.ok(Math.abs(footer.center - footer.footerCenter) < 1, "Footer artwork stays horizontally centered");
      assert.ok(Math.abs(footer.bottom - footer.footerBottom) < 1, "Footer artwork stays bottom aligned");
      assert.equal(footer.clipped, "hidden");
      assert.ok(footer.choices.length > 0);
      assert.equal(footer.choices.length, footer.sizes.length);
      assert.equal(footer.border, 'double');
      assert.ok(footer.background.endsWith('/patterns/navypattern2.png'));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await capture(`footer-production-${width}.png`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
  };
  const waitForState = () => page.waitForFunction(() => document.querySelector('#filters').dataset.enhanced === 'true');
    // Exercise every panorama at native size; filename changes must remain automatic.
    const backgrounds = data.footer_backgrounds || [];
    if (backgrounds.length) {
      await page.addInitScript(() => { Math.random = () => Number(sessionStorage.getItem('footer-test-random') || 0); });
      for (const [index] of backgrounds.entries()) {
        const random = (index + .5) / backgrounds.length;
        await page.evaluate(value => sessionStorage.setItem('footer-test-random', String(value)), random);
        await page.goto(url);
        const art = page.locator('[data-footer-background]');
        await art.scrollIntoViewIfNeeded();
        await art.evaluate(image => image.decode());
        assert.ok((await art.getAttribute('src')).endsWith(backgrounds[index]));
        for (const width of [2560, 1440, 390]) {
          await page.setViewportSize({width, height:1000});
          const size = await art.evaluate(image => { const r=image.getBoundingClientRect(); return [r.width,r.height,image.naturalWidth,image.naturalHeight]; });
          assert.deepEqual(size.slice(0,2), size.slice(2), 'Every panorama retains native dimensions at '+width+'px');
        }
        await page.setViewportSize({width:1440,height:1000});
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
  await checkFooter();
};
