/* Specimen plates for every record: geometry, label, QR code, decoration, keyboard and offline assets. */
const assert=require('node:assert/strict');
module.exports=async({page,url,data,capture})=>{
 const names=['OpenTofu','OpenRefine','Open WebUI',data.projects.find(p=>!p.artwork).name];
 for(const width of [1600,1440,768,390,320]){
  await page.setViewportSize({width,height:1000});
  for(const name of names){
   const p=data.projects.find(p=>p.name===name);assert.ok(p,name);
   await page.goto(new URL('#project-'+p.id,url).href);
   const row=page.locator('#project-'+p.id),plate=row.locator('.specimen-plate');
   await row.locator('> details').evaluate(n=>n.open=true);
   await plate.waitFor({state:'visible'});
   await plate.scrollIntoViewIfNeeded();
   await plate.locator('img').evaluateAll(ns=>Promise.all(ns.map(n=>n.decode().catch(()=>null))));
   assert.equal(await plate.count(),1);
   assert.equal(await plate.locator('.plate-departure>a').getAttribute('href'),p.url);
   assert.equal(await plate.locator('.plate-art').count(),p.artwork?1:0);
   assert.equal(await plate.locator('.plate-departure .sheet-label').textContent(),'In the wild');
   assert.equal(await plate.locator('.permalink').innerText(),'Specimen: '+name+' (permalink)');
   const qr=plate.locator('.label-qr');
   assert.equal(await qr.getAttribute('href'),'https://awesomeopen.github.io/awesome-open/#project-'+p.id);
   assert.ok(await qr.locator('img').evaluate(img=>img.complete&&img.naturalWidth>0),'QR code loads');
   assert.equal(await plate.locator('.specimen-label .tag').count(),p.categories.length,'Label lists every domain');
   const evidence=await plate.locator('.evidence-notes').evaluate(n=>({columns:getComputedStyle(n).gridTemplateColumns.split(' ').map(Number.parseFloat)}));
   assert.equal(evidence.columns.length,width>1100?4:width>720?2:1,'Evidence wraps at narrow widths');
   assert.ok(evidence.columns.every(w=>Math.abs(w-evidence.columns[0])<1),'Evidence columns have equal width');
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
    if(width>=1440)assert.equal(geometry.art.width,627,'Half-size artwork stays an exact 2:1 downscale');
    assert.ok(await plate.locator('.specimen-label').evaluate(n=>Math.abs(n.getBoundingClientRect().top-n.previousElementSibling.getBoundingClientRect().bottom+4*parseFloat(getComputedStyle(n).fontSize))<1.1),'Label overlaps illustration by 4em');
    assert.equal(geometry.terrain,geometry.cutout==='true','Ground is drawn only behind transparent cut-outs');
    assert.equal(geometry.animation,'none','Reduced motion leaves the final composition');
   }
   if(p.function_summary?.features?.length&&p.artwork){
    assert.equal(await plate.locator('.plate-crop.is-ready').count(),Math.min(2,p.function_summary.features.length));
    assert.ok((await plate.locator('.plate-leaders path').getAttribute('d')).startsWith('M'),'Leader lines join the drawing to its details');
   }
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   const clipped=await plate.locator('.plate-function,.specimen-label,.plate-register,.evidence-note,.plate-departure').evaluateAll(ns=>ns.filter(n=>{const r=n.getBoundingClientRect();return r.left<-1||r.right>innerWidth+1}).map(n=>n.className));
   assert.deepEqual(clipped,[],name+' at '+width);
   await plate.evaluate(n=>n.scrollIntoView({block:'start'}));
   await capture('plate-'+name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png');
   await plate.locator('.plate-departure>a').focus();
   assert.equal(await plate.locator('.plate-departure>a').evaluate(n=>n===document.activeElement),true);
  }
 }
 // The loupe follows a mouse over the drawing and leaves no object behind.
 await page.setViewportSize({width:1440,height:1000});
 const tofu=data.projects.find(p=>p.name==='OpenTofu');
 await page.goto(new URL('#project-'+tofu.id,url).href);
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
 await page.goto(new URL('#project-'+tofu.id,url).href);
 const study=page.locator('#project-'+tofu.id);
 await study.locator('> details').evaluate(n=>n.open=true);
 await study.locator('.specimen-plate').waitFor({state:'visible'});
 assert.equal(await study.locator('.function-detail').isVisible(),true);
 assert.equal(await study.locator('.plate-art').evaluate(n=>getComputedStyle(n).animationIterationCount),'1');
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto(new URL('standalone.html',url).href);
 const row=page.locator('#project-'+tofu.id);await row.locator('> details').evaluate(n=>n.open=true);
 assert.ok(await row.locator('.plate-art img').getAttribute('src').then(s=>s.startsWith('data:image/')));
 assert.ok(await row.locator('.label-qr img').getAttribute('src').then(s=>s.startsWith('data:image/svg+xml')));
};
