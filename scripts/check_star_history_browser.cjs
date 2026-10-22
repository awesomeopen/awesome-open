/* Additional cached-chart disclosure and offline export checks. */
const assert = require('node:assert/strict');
module.exports = async ({ page, url, data, capture }) => {
  const project = data.projects.find(p => p.hn && p.star_history?.chart_url);
  if (!project) return;
  for (const [name, viewport] of [['stars-desktop.png',{width:1440,height:1000}],['stars-mobile.png',{width:390,height:844}]]) {
    await page.setViewportSize(viewport);
    await page.goto(url + '?q=' + encodeURIComponent(project.name) + '#project-' + project.id);
    const card = page.locator('#project-' + project.id);
    const drawer = card.locator('.specimen-drawer');
    await drawer.evaluate(node => {node.open = true;});
    await card.locator('.specimen-plate').waitFor({ state: 'visible' });
    const chart = card.locator('[data-signal="star-history"] .pg-spark');
    await chart.scrollIntoViewIfNeeded();
    assert.equal(await chart.isVisible(),true);
    await chart.evaluate(img => img.decode());
    assert.equal(await chart.evaluate(img=>img.complete && img.naturalWidth===120),true);
    assert.equal(await card.locator('summary .pg-spark').count(),0);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    assert.ok(!(await card.innerText()).includes('As of '));
    const provenance=card.locator('[data-signal="star-history"] .pg-info');
    await provenance.locator('summary').click();
    assert.ok((await provenance.innerText()).includes('not guaranteed UTC'));
    await provenance.locator('summary').click();
    await capture(name);
    await drawer.locator(':scope > summary').click();
    assert.equal(await chart.isVisible(),false);
    await drawer.locator(':scope > summary').click();
    assert.equal(await chart.isVisible(),true);
  }
  await page.goto(new URL('standalone.html',url).href);
  const images=page.locator('[data-signal="star-history"] .pg-spark');
  assert.equal(await images.count(),data.projects.filter(p=>p.star_history?.chart_url).length);
  assert.ok(await images.evaluateAll(nodes=>nodes.every(img=>img.src.startsWith('data:image/svg+xml;base64,'))));
};
