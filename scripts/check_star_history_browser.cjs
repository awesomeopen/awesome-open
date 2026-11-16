/* Additional cached-chart disclosure and static record checks. */
const assert = require('node:assert/strict');
module.exports = async ({ page, url, data, capture }) => {
  const examples = [
    data.projects.find(p => p.url === 'https://github.com/openclaw/openclaw' && p.star_history?.chart_url),
    data.projects.find(p => p.hn && p.star_history?.chart_url && !p.star_history.display_status && p.star_history.status === 'ok'),
  ].filter((p, i, all) => p && all.indexOf(p) === i);
  assert.ok(examples.length, 'At least one validated history renders');
  for (const project of examples) {
  // catalog.json leaves star counts to the star-history evidence file, keyed by repo.
  assert.equal('last_good' in project.star_history, false);
  const evidence = await page.request.get(new URL('data/star_history.json', url).href);
  assert.ok(evidence.ok(), 'Star-history evidence download is available');
  const good = (await evidence.json()).repositories[project.star_history.repo].last_good;
  const counts = good.monthly_counts;
  const stale = !!project.star_history.display_status || project.star_history.status !== 'ok';
  for (const [name, viewport] of [['stars-desktop.png',{width:1440,height:1000}],['stars-mobile.png',{width:390,height:844}]]) {
    await page.setViewportSize(viewport);
    await page.goto(url + '?q=' + encodeURIComponent(project.name) + '#project-' + project.id);
    const card = page.locator('#pane-scroll');
    await card.locator('.specimen-plate').waitFor({ state: 'visible' });
    const chart = card.locator('[data-signal="star-history"] .pg-spark');
    await chart.scrollIntoViewIfNeeded();
    assert.equal(await chart.isVisible(),true);
    const box = card.locator('[data-signal="star-history"]');
    assert.ok((await box.innerText()).includes('GitHub star history'));
    assert.ok((await chart.getAttribute('alt')).includes(good.months[0] + ' to ' + good.months[23]));
    assert.equal(await box.locator(':scope > .pg-line').filter({hasText:'Stale cached result'}).count(), stale ? 1 : 0);
    if (project.github?.stars != null) {
      const totalBox = card.locator('.pg-box').filter({has: page.locator('.pg-title', {hasText: /^GitHub stars$/})});
      assert.ok((await totalBox.innerText()).includes(project.github.stars.toLocaleString('en-US')));
    }
    await chart.evaluate(img => img.decode());
    assert.equal(await chart.evaluate(img=>img.complete && img.naturalWidth===120),true);
    assert.equal(await page.locator('#rows .pg-spark').count(),0,'List rows carry only the HN sparkline');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    const provenance=card.locator('[data-signal="star-history"] .pg-info');
    await provenance.locator('summary').click();
    const maximum = Math.max(1, ...counts).toLocaleString('en-US');
    const explanation = 'Stars created in each month that remained at the last successful fetch. ' +
      `Independent square-root scale: 0–${maximum} stars/month.`;
    assert.ok((await provenance.locator('.pg-pop > p:not(.fine-print)').innerText()).includes(explanation));
    assert.equal(await provenance.getByRole('link', { name: 'Provider source' }).getAttribute('href'), project.star_history.source_url);
    assert.ok((await provenance.innerText()).includes(good.fetched_at));
    await provenance.locator('summary').click();
    await capture(project.id.slice(0,8) + '-' + name);
    // Closing the plate unmounts it; opening the row mounts it again.
    await page.locator('#plate-close').click();
    assert.equal(await chart.count(),0);
    await page.locator(`#rows .row[data-id="${project.id}"] > a`).click();
    await card.locator('[data-signal="star-history"] .pg-spark').waitFor({ state: 'visible' });
  }
  await page.goto(new URL('records/'+project.id+'.html',url).href);
  const chart=page.locator('[data-signal="star-history"] .pg-spark');
  await chart.evaluate(img=>img.decode());
  assert.equal(await chart.evaluate(img=>img.complete && img.naturalWidth===120),true);
  }
};
