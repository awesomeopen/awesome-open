/* Reviewed name events: true positions, readable labels, and local record anchors. */
const assert = require('node:assert/strict');
module.exports = async ({page, url, data, capture}) => {
  const projects = data.projects.filter(p => ['OpenTofu','OpenHands'].includes(p.name) && p.history?.length);
  assert.equal(projects.length, 2, 'Two reviewed historical seed records');
  async function check(plate, label) {
    const markers = plate.locator('.history-marker');
    assert.ok(await markers.count() >= 3, label + ': repository and rename milestones');
    const geometry = await markers.evaluateAll(nodes => nodes.map(n => {
      const r = n.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};
    }));
    for (let i=0;i<geometry.length;i++) {
      const a=geometry[i]; assert.ok(a.left>=0 && a.right<=await page.evaluate(()=>innerWidth),label+': marker fits');
      for(let j=i+1;j<geometry.length;j++) {
        const b=geometry[j]; assert.ok(a.right<=b.left || b.right<=a.left || a.bottom<=b.top || b.bottom<=a.top,label+': markers do not overlap');
      }
    }
    const list=plate.locator('.history-dates');
    assert.equal(await list.evaluate(n=>getComputedStyle(n).listStyleType),'decimal',label+': entries keep their marker numbers');
    assert.equal(await list.locator('li').count(), await markers.count());
    assert.equal(await list.locator('li').filter({hasText:'Project renamed'}).locator('time').filter({hasText:'2026-10-19'}).count(),0,'Review day is not a milestone');
    assert.equal(await plate.locator('.history-evidence').getAttribute('open'),null,'Secondary evidence starts folded');
    await plate.locator('.history-evidence summary').click();
    assert.ok((await plate.locator('.history-evidence').innerText()).includes('Reviewed 2026-10-19'));
    const clipped=await plate.locator('.history-dates li,.history-evidence').evaluateAll(ns=>ns.filter(n=>{
      const r=n.getBoundingClientRect(); return r.left<0||r.right>innerWidth||n.scrollWidth>n.clientWidth+1;
    }).map(n=>n.className));
    assert.deepEqual(clipped,[],label+': history text wraps');
    await plate.locator('.history-evidence summary').click();
    const marker=plate.locator('.history-marker[data-record-anchor*="-event-"]').first();
    const target=await marker.getAttribute('data-record-anchor');
    await marker.focus(); await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).hash,'#'+target,label+': marker navigates to matching text');
    assert.equal(await plate.locator('[id="'+target+'"]').count(),1);
    assert.ok(await plate.locator('[id="'+target+'"]').isVisible());
  }
  for (const p of projects) {
    for (const width of [1440,320]) {
      await page.setViewportSize({width,height:1000});
      await page.goto(new URL('#project-'+p.id,url).href);
      const row=page.locator('#project-'+p.id);
      await row.locator('>details').evaluate(n=>n.open=true);
      const plate=row.locator('.specimen-plate'); await plate.waitFor({state:'visible'});
      await check(plate,p.name+' drawer '+width);
      assert.equal(await plate.locator('.history-marker').first().getAttribute('href'),
        '#'+await plate.locator('.history-marker').first().getAttribute('data-record-anchor'));
      const historyURL = page.url();
      await page.goBack();
      await page.goForward();
      assert.equal(page.url(), historyURL, 'Back/Forward retains the history anchor');
      await page.reload();
      await plate.waitFor({state:'visible'});
      const restored = await plate.locator('.history-marker[data-record-anchor*="-event-"]').first().getAttribute('data-record-anchor');
      assert.equal(await plate.locator('[id="'+restored+'"]').evaluate(n=>document.activeElement===n),true,'Reload restores history target after lazy loading');
      await plate.locator('.history-timeline').scrollIntoViewIfNeeded();
      await capture('history-'+p.name.toLowerCase()+'-'+width+'.png');
    }
    for (const route of ['records/'+p.id+'.html','standalone.html']) {
      await page.goto(new URL(route,url).href);
      const row=page.locator('#project-'+p.id);
      await row.locator('>details').evaluate(n=>n.open=true);
      const plate=row.locator('.specimen-plate');
      const before=await plate.locator('.history-dates,.history-marker,.history-evidence').evaluateAll(ns=>ns.map(n=>parseFloat(getComputedStyle(n).fontSize)));
      await page.evaluate(()=>document.documentElement.style.fontSize='200%');
      const after=await plate.locator('.history-dates,.history-marker,.history-evidence').evaluateAll(ns=>ns.map(n=>parseFloat(getComputedStyle(n).fontSize)));
      assert.ok(after.every((value,i)=>value>=before[i]*1.99),'History text really doubles at 200%');
      await check(plate,p.name+' '+route+' 320px 200%');
      assert.equal(new URL(page.url()).pathname,new URL(route,url).pathname,'Marker stays on its output route');
      await plate.locator('.history-timeline').scrollIntoViewIfNeeded();
      await capture('history-'+p.name.toLowerCase()+'-'+(route==='standalone.html'?'offline':'record')+'-200.png');
    }
  }
};
