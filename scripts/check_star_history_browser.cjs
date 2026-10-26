/* Additional cached-chart disclosure and static record checks. */
const assert = require('node:assert/strict');
module.exports = async ({ page, url, data, capture }) => {
  const project = data.projects.find(p => p.hn && p.star_history?.chart_url);
  if (!project) return;
  // catalog.json leaves star counts to the star-history evidence file, keyed by repo.
  assert.equal('last_good' in project.star_history, false);
  const evidence = await page.request.get(new URL('data/star_history.json', url).href);
  assert.ok(evidence.ok(), 'Star-history evidence download is available');
  const counts = (await evidence.json()).repositories[project.star_history.repo].last_good.monthly_counts;
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
    const maximum = Math.max(1, ...counts).toLocaleString('en-US');
    const explanation = 'Stars created in each month that remained at the last successful fetch. ' +
      `Independent square-root scale: 0–${maximum} stars/month.`;
    assert.ok((await provenance.locator('.pg-pop > p:not(.fine-print)').innerText()).includes(explanation));
    const popupText = await provenance.innerText();
    for (const removed of ['Not historical totals', 'not guaranteed UTC', 'HN stories and GitHub stars are independent measurements']) {
      assert.ok(!popupText.includes(removed));
    }
    assert.equal(await provenance.getByRole('link', { name: 'Provider source' }).getAttribute('href'), project.star_history.source_url);
    await provenance.locator('summary').click();
    await capture(name);
    await drawer.locator(':scope > summary').click();
    assert.equal(await chart.isVisible(),false);
    await drawer.locator(':scope > summary').click();
    assert.equal(await chart.isVisible(),true);
  }
  await page.goto(new URL('records/'+project.id+'.html',url).href);
  const chart=page.locator('[data-signal="star-history"] .pg-spark');
  await chart.evaluate(img=>img.decode());
  assert.equal(await chart.evaluate(img=>img.complete && img.naturalWidth===120),true);
};
