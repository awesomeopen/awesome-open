/* Three-record visual study: geometry, real source links, keyboard and offline assets. */
const assert=require('node:assert/strict');
module.exports=async({page,url,data,capture})=>{
 const names=['OpenTofu','OpenRefine','Open WebUI'];
 for(const width of [1600,1440,768,390,320]){
  await page.setViewportSize({width,height:1000});
  for(const name of names){
   const p=data.projects.find(p=>p.name===name);assert.ok(p,name);
   await page.goto(new URL('#project-'+p.id,url).href);
   const row=page.locator('#project-'+p.id),plate=row.locator('.specimen-plate');
   await row.locator('> details').evaluate(n=>n.open=true);
   await plate.scrollIntoViewIfNeeded();
   await plate.locator('img').evaluateAll(ns=>Promise.all(ns.map(n=>n.decode())));
   assert.equal(await plate.count(),1);
   assert.equal(await plate.locator('.plate-departure>a').getAttribute('href'),p.url);
   assert.equal(await plate.locator('.plate-art').count(),name==='Open WebUI'?0:1);
   assert.equal(await plate.locator('.source-link').count(),0);
   assert.equal(await plate.locator('.plate-departure .sheet-label').textContent(),'In the wild');
   assert.equal(await plate.locator('.plate-departure').evaluate(n=>getComputedStyle(n).textAlign),'center');
   assert.equal(await plate.locator('.permalink').innerText(),'Specimen: '+name+' (permalink)');
   if(name!=='Open WebUI'){
    assert.equal(await plate.locator('.function-detail mark').innerText(),name);
    assert.equal(await plate.locator('.plate-detail .feature-source').count(),1);
    assert.equal(await plate.locator('[data-signal=release] .deployment-evidence').count(),1);
    const geometry=await plate.evaluate(n=>{
     const art=n.querySelector('.plate-art img').getBoundingClientRect();
     const stage=n.querySelector('.plate-art-stage').getBoundingClientRect();
     const prose=n.querySelector('.plate-function').getBoundingClientRect();
     const heading=n.querySelector('.plate-heading').getBoundingClientRect();
     const detail=n.querySelector('.plate-detail').getBoundingClientRect();
     const crop=n.querySelector('.plate-detail-crop').getBoundingClientRect();
     return {art:{left:art.left,right:art.right,top:art.top,bottom:art.bottom},
      stage:{top:stage.top,bottom:stage.bottom},proseLeft:prose.left,headingBottom:heading.bottom,
      detailTop:detail.top,cropRatio:crop.width/crop.height,
      animation:getComputedStyle(n.querySelector('.plate-art')).animationName};
    });
    assert.ok(geometry.art.left>=0&&geometry.art.right<=width,'Complete artwork fits viewport');
    if(width>720)assert.ok(geometry.art.right<geometry.proseLeft,'Artwork leaves prose clear');
    assert.ok(geometry.detailTop>=geometry.art.bottom-1,'Feature note leaves full silhouette clear');
    assert.equal(geometry.animation,'none','Reduced motion leaves the final composition');
    assert.ok(geometry.cropRatio>=.65&&geometry.cropRatio<=1.05,'Compact detail');
    assert.equal(await plate.locator('.plate-leader').isVisible(),true,'Red connector restored');
    assert.ok(await plate.locator('.plate-detail-crop').evaluate(n=>n.getBoundingClientRect().width<=112),'Small detail window');
   }
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   const clipped=await plate.locator('.plate-function,.plate-register,.evidence-note,.plate-departure').evaluateAll(ns=>ns.filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+1}).map(n=>n.className));
   assert.deepEqual(clipped,[],name+' at '+width);
   await plate.evaluate(n=>n.scrollIntoView({block:'start'}));
   await capture('plate-'+name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png');
   if(name!=='Open WebUI'){
    await plate.locator('.plate-detail').scrollIntoViewIfNeeded();
    await capture('plate-detail-'+name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png');
   }
   await plate.locator('.plate-departure>a').focus();
   assert.equal(await plate.locator('.plate-departure>a').evaluate(n=>n===document.activeElement),true);
  }
 }
 // Opening settles the artwork once; it never gates text or repeats indefinitely.
 await page.emulateMedia({reducedMotion:'no-preference'});
 const animated=data.projects.find(p=>p.name==='OpenTofu');
 await page.goto(new URL('#project-'+animated.id,url).href);
 const study=page.locator('#project-'+animated.id);
 await study.locator('> details').evaluate(n=>n.open=true);
 assert.equal(await study.locator('.function-detail').isVisible(),true);
 assert.equal(await study.locator('.plate-art').evaluate(n=>getComputedStyle(n).animationIterationCount),'1');
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto(new URL('standalone.html',url).href);
 const p=data.projects.find(p=>p.name==='OpenTofu');
 const row=page.locator('#project-'+p.id);await row.locator('> details').evaluate(n=>n.open=true);
 assert.ok(await row.locator('.plate-art img').getAttribute('src').then(s=>s.startsWith('data:image/')));
 assert.ok(await row.locator('.plate-detail img').getAttribute('src').then(s=>s.startsWith('data:image/')));
};
