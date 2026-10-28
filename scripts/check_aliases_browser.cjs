/* Reviewed aliases remain adjacent to the identity heading in both plate views. */
const assert = require('node:assert/strict');
const key = value => value.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().trim().replace(/\s+/g, ' ');
module.exports = async ({ context, url, data, capture }) => {
  const aliases = project => (project.aliases || []).filter(alias => key(alias.name) !== key(project.name));
  const multiple = data.projects.find(project => aliases(project).length > 1);
  const single = data.projects.find(project => aliases(project).length === 1);
  const none = data.projects.find(project => aliases(project).length === 0);
  assert.ok(multiple && single && none, 'Real alias fixtures: multiple, one and none');
  const page = await context.newPage();
  const checked = [];
  try {
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const project of [multiple, single, none]) {
        await page.goto(new URL(`records/${project.id}.html`, url).href);
        await page.evaluate(() => document.fonts.ready);
        const plate = page.locator('.specimen-plate');
        const expected = aliases(project);
        const links = plate.locator('.plate-aliases a');
        assert.deepEqual(await links.allTextContents(), expected.map(alias => alias.name));
        assert.deepEqual(await links.evaluateAll(nodes => nodes.map(node => node.getAttribute('href'))), expected.map(alias => alias.source_url));
        if (expected.length) {
          const geometry = await plate.evaluate(node => {
            const heading = node.querySelector('.plate-heading');
            const list = node.querySelector('.plate-aliases');
            const rows = [...list.children].map(li => li.getBoundingClientRect());
            return { next: heading.nextElementSibling === list,
              below: list.getBoundingClientRect().top >= heading.getBoundingClientRect().bottom,
              lines: rows.every((row, i) => i === 0 || row.top >= rows[i - 1].bottom),
              fits: document.documentElement.scrollWidth <= innerWidth,
              first: list.firstElementChild.textContent, last: list.lastElementChild.textContent };
          });
          assert.ok(geometry.next && geometry.below && geometry.lines && geometry.fits, 'Alias layout at ' + width);
          assert.equal(geometry.first, 'Also known as: ' + expected[0].name);
          await plate.locator('.plate-heading').scrollIntoViewIfNeeded();
          await capture(`aliases-record-${expected.length > 1 ? 'multiple' : 'single'}-${width}.png`, page);
        } else assert.equal(await plate.locator('.plate-aliases').count(), 0);
        checked.push({ id: project.id, width, aliases: expected.length });
      }
      await page.goto(url);
      await page.waitForFunction(() => document.querySelector('#filters')?.dataset.enhanced === 'true');
      const row = page.locator('#project-' + multiple.id);
      await row.locator('details.specimen-drawer').evaluate(node => { node.open = true; });
      await row.locator('.plate-aliases').waitFor({ state: 'visible' });
      assert.deepEqual(await row.locator('.plate-aliases a').allTextContents(), aliases(multiple).map(alias => alias.name));
      assert.ok(await row.locator('.specimen-plate').evaluate(plate => {
        const heading = plate.querySelector('.plate-heading');
        const list = plate.querySelector('.plate-aliases');
        return heading.nextElementSibling === list && list.getBoundingClientRect().top >= heading.getBoundingClientRect().bottom
          && document.documentElement.scrollWidth <= innerWidth;
      }), 'Drawer aliases follow the heading and fit at ' + width);
      await row.locator('.plate-heading').scrollIntoViewIfNeeded();
      await capture(`aliases-drawer-multiple-${width}.png`, page);
    }
  } finally { await page.close(); }
  return { status: 'passed', checked };
};
