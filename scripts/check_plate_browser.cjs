/* Specimen plates for every record: geometry, label, QR code, decoration, keyboard and static record assets.
   Full-width geometry is checked on the static record pages; the Catalog pane is checked at the end. */
const assert=require('node:assert/strict');
module.exports=async({page,url,data,capture})=>{
 const names=['OpenTofu','OpenRefine','Open WebUI',data.projects.find(p=>!p.artwork).name];
 for(const width of [1600,1440,768,390,320]){
  await page.setViewportSize({width,height:1000});
  for(const name of names){
   const p=data.projects.find(p=>p.name===name);assert.ok(p,name);
   await page.goto(new URL('records/'+p.id+'.html',url).href);
   const row=page.locator('#project-'+p.id),plate=row.locator('.specimen-plate');
   await row.locator('> details').evaluate(n=>n.open=true);
   await plate.waitFor({state:'visible'});
   await plate.scrollIntoViewIfNeeded();
   await plate.locator('img').evaluateAll(ns=>Promise.all(ns.map(n=>{n.loading='eager';return n.decode().catch(()=>null);})));
   assert.equal(await plate.count(),1);
   assert.equal(await plate.locator('.plate-departure>a').getAttribute('href'),p.url);
   assert.equal(await plate.locator('.plate-art').count(),p.artwork?1:0);
   assert.equal(await plate.locator('.permalink').textContent(),'Specimen: '+name);
   assert.equal(await plate.locator('.permalink').getAttribute('aria-label'),'Permalink to '+name);
   const qr=plate.locator('.label-qr');
   assert.equal(await qr.getAttribute('href'),'https://awesomeopen.github.io/awesome-open/#project-'+p.id);
   assert.ok(await qr.locator('img').evaluate(img=>img.complete&&img.naturalWidth>0),'QR code loads');
   assert.equal(await plate.locator('.specimen-label .tag').count(),p.categories.length,'Label lists every domain');
   // The evidence grid is fixed (B-PR158-01): same boxes for every record, Unknown when absent.
   const evidence=await plate.locator('.pg-evidence').evaluate(n=>({columns:getComputedStyle(n).gridTemplateColumns.split(' ').map(Number.parseFloat)}));
   assert.equal(evidence.columns.length,width>1100?8:width>720?4:1,'Evidence grid wraps at narrow widths');
   assert.ok(evidence.columns.every(w=>Math.abs(w-evidence.columns[0])<1),'Evidence columns have equal width');
   assert.equal(await plate.locator('.pg-row:not(.pg-alts)>.pg-box').count(),12,'Every record keeps all evidence boxes');
   assert.equal(await plate.locator('.pg-alt').count(),p.alternatives.length,'Alternatives are the only variable row');
   assert.equal(await plate.locator('.pg-collection:visible').count(),1,'Collection log remains visible on mobile');
   assert.equal(await plate.locator('.collection-replay').getAttribute('aria-hidden'),'true');
   assert.ok(JSON.parse(await plate.locator('.pg-collection').getAttribute('data-replay')).length<=4,'Bounded replay');
   const sparks=await plate.locator('.pg-evidence .pg-spark-link,.pg-evidence .pg-spark-empty').evaluateAll(ns=>ns.map(n=>n.getBoundingClientRect().bottom));
   if(width>720)assert.ok(Math.abs(sparks[0]-sparks[1])<1,'Sparklines share a baseline');
   assert.equal(await qr.evaluate(n=>getComputedStyle(n).borderTopWidth),'2px');
   if(!p.artwork)assert.ok(await plate.locator('.specimen-label').evaluate(n=>n.getBoundingClientRect().top>=n.closest('.specimen-plate').getBoundingClientRect().top),'Unillustrated label stays inside plate');
   if(p.artwork){
    const geometry=await plate.evaluate(n=>{
     const art=n.querySelector('.plate-art img').getBoundingClientRect();
     const bbox=n.querySelector('.plate-field').dataset.bbox.split(' ').map(Number);
     const prose=n.querySelector('.plate-function').getBoundingClientRect();
     const label=n.querySelector('.specimen-label').getBoundingClientRect();
     return {art:{left:art.left,right:art.right,bottom:art.top+art.height*bbox[3],width:art.width},proseLeft:prose.left,labelTop:label.top,
      cutout:n.querySelector('.plate-field').dataset.cutout,terrain:!!n.querySelector('.plate-terrain'),
      animation:getComputedStyle(n.querySelector('.plate-art')).animationName};
    });
    assert.ok(geometry.art.left>=0&&geometry.art.right<=width,'Complete artwork fits viewport');
    if(width>900)assert.ok(geometry.art.right<=geometry.proseLeft,'Artwork leaves prose clear');
    assert.ok(geometry.art.width<=627,'Artwork keeps its 627px cap');
    assert.ok(await plate.locator('.specimen-label').evaluate(n=>Math.abs(n.getBoundingClientRect().top-n.previousElementSibling.getBoundingClientRect().bottom)<1.1),'Label sits directly below the illustration');
    assert.equal(geometry.terrain,geometry.cutout==='true','Ground is drawn only behind transparent cut-outs');
    assert.equal(geometry.animation,'none','Reduced motion leaves the final composition');
   }
   if(p.function_summary?.features?.length&&p.artwork){
    assert.equal(await plate.locator('.plate-crop.is-ready').count(),Math.min(2,p.function_summary.features.length));
    assert.ok((await plate.locator('.plate-leaders path').getAttribute('d')).startsWith('M'),'Leader lines join the drawing to its details');
   }
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   const clipped=await plate.locator('.plate-function,.specimen-label,.pg-box,.plate-departure').evaluateAll(ns=>ns.filter(n=>{const r=n.getBoundingClientRect();return r.left<-1||r.right>innerWidth+1}).map(n=>n.className));
   assert.deepEqual(clipped,[],name+' at '+width);
   await plate.evaluate(n=>n.scrollIntoView({block:'start'}));
   await capture('plate-'+name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png');
   await plate.locator('.plate-departure>a').focus();
   assert.equal(await plate.locator('.plate-departure>a').evaluate(n=>n===document.activeElement),true);
   // Box details open from the keyboard, fit the viewport, and close with Escape.
   for(const selector of ['[data-signal="scorecard"]','.pg-runs']){
    const summary=plate.locator(selector+' .pg-info>summary');
    await summary.focus();await page.keyboard.press('Enter');
    const pop=plate.locator(selector+' .pg-pop');
    assert.equal(await pop.isVisible(),true,selector+' popup opens');
    const colors=await summary.evaluate(n=>({background:getComputedStyle(n).backgroundColor,foreground:getComputedStyle(n).color}));
    assert.equal(colors.background,'rgb(17, 24, 32)','Open info control uses the current ink shadow colour');
    assert.equal(colors.foreground,'rgb(255, 255, 255)','Open info icon stays white');
    if(name===names[0]&&selector==='[data-signal="scorecard"]'&&[1440,390].includes(width))
     await capture('plate-info-open-'+width+'.png');
    const r=await pop.boundingBox();
    assert.ok(r.x>=-1&&r.x+r.width<=width+1,selector+' popup fits at '+width);
    await page.keyboard.press('Escape');
    assert.equal(await plate.locator('.pg-info[open]').count(),0,'Escape closes the popup');
    assert.equal(await summary.evaluate(n=>n===document.activeElement),true,'Focus returns to the trigger');
   }
  }
 }
 // The loupe follows a mouse over the drawing and leaves no object behind.
 await page.setViewportSize({width:1440,height:1000});
 const tofu=data.projects.find(p=>p.name==='OpenTofu');
 await page.goto(new URL('records/'+tofu.id+'.html',url).href);
 const tofuRow=page.locator('#project-'+tofu.id);
 await tofuRow.locator('> details').evaluate(n=>n.open=true);
 await tofuRow.locator('.specimen-plate').waitFor({state:'visible'});
 const field=tofuRow.locator('.plate-field');
 await field.scrollIntoViewIfNeeded();
 const box=await field.boundingBox();
 await page.mouse.move(box.x+box.width*.6,box.y+box.height*.6);
 assert.equal(await tofuRow.locator('.plate-lens').evaluate(n=>n.classList.contains('is-on')),true);
 await page.mouse.move(2,2);
 assert.equal(await tofuRow.locator('.plate-lens').evaluate(n=>n.classList.contains('is-on')),false);
 // Opening runs once; it never gates text or repeats.
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.goto(new URL('records/'+tofu.id+'.html',url).href);
 const study=page.locator('#project-'+tofu.id);
 await study.locator('> details').evaluate(n=>n.open=true);
 await study.locator('.specimen-plate').waitFor({state:'visible'});
 assert.equal(await study.locator('.function-detail').isVisible(),true);
 assert.equal(await study.locator('.plate-art').evaluate(n=>getComputedStyle(n).animationIterationCount),'1');
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto(new URL('records/'+tofu.id+'.html',url).href);
 const row=page.locator('#project-'+tofu.id);
 for(const image of [row.locator('.plate-art img'),row.locator('.label-qr img')]){
  await image.scrollIntoViewIfNeeded();
  await image.evaluate(n=>n.decode());
  assert.ok(await image.evaluate(n=>n.complete&&n.naturalWidth>0),'Static record image loads');
 }
 // In the Catalog pane: one plate at a time; the label is as tall as its QR code with one line per fact.
 for(const width of [1920,1440]){
  await page.setViewportSize({width,height:1000});
  for(const name of names){
   const p=data.projects.find(p=>p.name===name);
   await page.goto(new URL('#project-'+p.id,url).href);
   const plate=page.locator('#pane-scroll .specimen-plate');
   await plate.waitFor({state:'visible'});
   assert.equal(await page.locator('.specimen-plate').count(),1,'One plate is mounted');
   assert.equal(await page.locator('#plate-name').textContent(),p.name);
   const label=await plate.locator('.specimen-label').evaluate(n=>{
    const lines=n.querySelector('.label-lines');
    return {lines:lines.getBoundingClientRect().height,qr:n.querySelector('.label-qr').getBoundingClientRect().height,
     wrapped:[...lines.children].filter(c=>c.getBoundingClientRect().height>parseFloat(getComputedStyle(c).lineHeight)*1.5).map(c=>c.textContent)};
   });
   assert.ok(label.lines<=label.qr,`${name}: label lines fit the QR height at ${width}`);
   assert.deepEqual(label.wrapped,[],`${name}: label lines do not wrap`);
   const trophies=(p.scoreboard_trophies||[]).length;
   assert.equal(await plate.locator('.plate-trophies').count(),trophies?1:0);
   if(trophies)assert.equal(await plate.locator('.plate-trophies span').textContent(),trophies+(trophies===1?' Trophy':' Trophies'));
   const clipped=await plate.locator('.plate-function,.specimen-label,.pg-box,.plate-departure').evaluateAll(ns=>{
    const pane=document.getElementById('pane-scroll').getBoundingClientRect();
    return ns.filter(n=>{const r=n.getBoundingClientRect();return r.width&&(r.left<pane.left-1||r.right>pane.right+1)}).map(n=>n.className);
   });
   assert.deepEqual(clipped,[],name+' fits the pane at '+width);
   if(name===names[0])await capture('pane-plate-'+width+'.png');
  }
 }
 // Activity replay is silent, bounded, and stopped by interaction/reduced motion.
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.clock.install();
 await page.setViewportSize({width:390,height:900});
 let historyRequests=0;
 page.on('request',r=>{if(r.url().includes('/collection/'+tofu.id+'.json'))historyRequests++});
 await page.goto(new URL('records/'+tofu.id+'.html',url).href);
 assert.equal(historyRequests,0,'No history fetch before disclosure');
 const log=page.locator('.pg-collection'), replay=log.locator('.collection-replay');
 await log.scrollIntoViewIfNeeded(); await page.mouse.move(0,0);
 if(JSON.parse(await log.getAttribute('data-replay')).length>1){
  const before=await replay.textContent();
  await page.clock.fastForward(6100);
  assert.notEqual(await replay.textContent(),before,'Visible replay advances');
  await log.hover(); const hovered=await replay.textContent();
  await page.clock.fastForward(6200); assert.equal(await replay.textContent(),hovered,'Hover pauses replay');
  await page.emulateMedia({reducedMotion:'reduce'}); await page.mouse.move(0,0);
  const reduced=await replay.textContent(); await page.clock.fastForward(6200);
  assert.equal(await replay.textContent(),reduced,'Reduced motion stays static');
  for(let i=0;i<3;i++){
   await log.locator('.collection-trigger').focus(); await page.keyboard.press(i===1?'Space':'Enter');
   assert.ok(await log.locator('.collection-overview').isVisible());
   await log.locator('.collection-history[data-loaded="true"]').waitFor();
   assert.ok(await log.locator('.collection-events li').count()>4,'Overview preserves older evidence');
   assert.equal(historyRequests,1,'One lazy fetch across repeated opens');
   const dates=await log.locator('time').evaluateAll(nodes=>nodes.map(n=>n.dateTime));
   assert.deepEqual(dates,[...dates].sort().reverse(),'Newest first');
   assert.equal(await log.locator('.collection-source,.collection-caption,h4').count(),0);
   await page.keyboard.press('Escape');
   assert.ok(await log.locator('.collection-trigger').evaluate(n=>n===document.activeElement),'Focus returns');
  }
  await page.emulateMedia({reducedMotion:'no-preference'});
 }
 // Full-box hit area includes blank corners on narrow and desktop records.
 for(const width of [390,1280]){
  await page.setViewportSize({width,height:900});
  await log.scrollIntoViewIfNeeded();
  for(const corner of ['start','end']){
   const b=await log.boundingBox();
   await page.mouse.click(b.x+(corner==='start'?2:b.width-2),b.y+(corner==='start'?2:b.height-2));
   await log.locator('dialog[open]').waitFor();
   await log.locator('.collection-close').click();
   assert.ok(await log.locator('.collection-trigger').evaluate(n=>n===document.activeElement));
  }
 }
 // A failed lazy fetch remains retryable; successful reopening preserves all rows.
 let attempts=0;
 await page.route('**/collection/'+tofu.id+'.json',route=>{attempts++;return attempts===1?route.abort():route.continue()});
 await page.goto(new URL('records/'+tofu.id+'.html',url).href);
 await page.locator('.collection-trigger').click();
 await page.waitForFunction(()=>document.querySelector('.collection-history').textContent.includes('could not be loaded'));
 await page.keyboard.press('Escape'); await page.locator('.collection-trigger').click();
 await page.locator('.collection-history[data-loaded="true"]').waitFor();
 assert.equal(attempts,2,'Failed overview fetch retries on reopen');
 assert.ok(await page.locator('.collection-events li').count()>4);
 await page.unroute('**/collection/'+tofu.id+'.json');
 // Sorting preserves equal-date observations and puts undated counts last.
 await page.route('**/collection/'+tofu.id+'.json',route=>route.fulfill({json:{version:1,
  types:[['hn','HN evidence collected','https://github.com/awesomeopen/awesome-open/blob/main/data/chart_observations.json']],
  events:[['2020-01-01',0,'old'],['2026-01-01',0,'first'],['2026-01-01',0,'second']],undated:{hn:2}}}));
 await page.reload(); await page.locator('.collection-trigger').click();
 await page.locator('.collection-history[data-loaded]').waitFor();
 assert.deepEqual(await page.locator('.collection-events li').evaluateAll(ns=>ns.map(n=>n.dataset.observation)),['first','second','old']);
 assert.ok((await page.locator('.collection-history > :last-child').textContent()).includes('without a collection date'));
 await page.keyboard.press('Escape');
 await page.unroute('**/collection/'+tofu.id+'.json');

};
