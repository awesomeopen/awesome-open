/* Reviewed renames on the repository timeline: readable label, "(i)" evidence with its source. */
const assert = require('node:assert/strict');
module.exports = async ({page, url, data, capture}) => {
  const projects = data.projects.filter(p => ['OpenTofu','OpenHands','OpenTasks'].includes(p.name) && p.history?.length);
  assert.equal(projects.length, 3, 'Reviewed historical seeds and OpenTasks rename');
  async function check(plate, project, label) {
    const event = project.history[0];
    const rename = plate.locator('.timeline-label.is-rename');
    assert.equal(await rename.count(), 1, label + ': one rename label');
    assert.ok((await rename.innerText()).includes(`Renamed: ${event.old_name} → ${event.new_name} (i)`), label + ': rename label text');
    assert.ok((await rename.innerText()).includes(event.occurred.value), label + ': rename date');
    assert.equal(await plate.locator('.history-marker,.history-dates').count(), 0, label + ': no numbered lanes');
    if (project.name === 'OpenTasks') {
      const labelBox = await rename.boundingBox();
      const timelineBox = await plate.locator('.pg-timeline').boundingBox();
      assert.ok(labelBox.y >= timelineBox.y, label + ': rename label stays inside its timeline box');
    }
    const info = rename.locator('details.timeline-info');
    assert.equal(await info.getAttribute('open'), null, label + ': details start folded');
    await info.locator('summary').focus();
    await page.keyboard.press('Enter');
    const panel = info.locator('.timeline-info-panel');
    assert.ok(await panel.isVisible(), label + ': (i) opens details from the keyboard');
    assert.ok(await panel.locator(`a[href="${event.occurred.source_url}"]`).count() >= 1, label + ': source link');
    // Sources only: the label already names the change and its date (B-PR158-01).
    assert.ok((await panel.innerText()).startsWith('Sources: '), label + ': popup shows sources');
    assert.ok(!(await panel.innerText()).includes('Reviewed '), label + ': no reviewer line');
    const box = await panel.boundingBox();
    const width = await page.evaluate(() => innerWidth);
    assert.ok(box.x >= 0 && box.x + box.width <= width, label + ': details fit the viewport');
    if (project.name === 'OpenTasks') {
      const axis = await plate.locator('.timeline').boundingBox();
      assert.ok(box.width >= Math.min(200, axis.width) - 1, label + ': evidence uses available timeline width');
    }
    const labels = await plate.locator('.timeline-label:visible').evaluateAll(ns => ns.map(n => {
      const r = n.getBoundingClientRect(); return {left:r.left,right:r.right};
    }));
    assert.ok(labels.every(r => r.left >= 0 && r.right <= width), label + ': timeline labels fit');
    await plate.locator('.timeline').scrollIntoViewIfNeeded();
    await capture('history-' + project.name.toLowerCase() + '-' + label.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.png');
    await info.locator('summary').click();
  }
  for (const p of projects) {
    for (const width of [1440,320]) {
      await page.setViewportSize({width,height:1000});
      await page.goto(new URL('#project-'+p.id,url).href);
      const row=page.locator('#project-'+p.id);
      await row.locator('>details').evaluate(n=>n.open=true);
      const plate=row.locator('.specimen-plate'); await plate.waitFor({state:'visible'});
      await check(plate,p,'drawer '+width);
    }
    await page.goto(new URL('records/'+p.id+'.html',url).href);
    const row=page.locator('#project-'+p.id);
    await row.locator('>details').evaluate(n=>n.open=true);
    await check(row.locator('.specimen-plate'),p,'record 320');
  }
};
