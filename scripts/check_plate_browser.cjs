/* Three-record visual study: geometry, real source links, keyboard and offline assets. */
const assert=require('node:assert/strict');
module.exports=async({page,url,data,capture})=>{
 const names=['OpenTofu','OpenRefine','Open WebUI'];
 for(const width of [1440,768,390]){
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
   assert.equal(await plate.locator('.plate-departure .sheet-label').innerText(),'In the wild');
   assert.equal(await plate.locator('.plate-departure').evaluate(n=>getComputedStyle(n).textAlign),'center');
   assert.equal(await plate.locator('.permalink').innerText(),'Specimen: '+name+' (permalink)');
   if(name!=='Open WebUI'){
    assert.equal(await plate.locator('.function-detail mark').innerText(),name);
    assert.equal(await plate.locator('.plate-detail .feature-source').count(),1);
    assert.equal(await plate.locator('[data-signal=release] .deployment-evidence').count(),1);
   }
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   const clipped=await plate.locator('.plate-function,.plate-register,.evidence-note,.plate-departure').evaluateAll(ns=>ns.filter(n=>{const r=n.getBoundingClientRect();return r.left<0||r.right>innerWidth+1}).map(n=>n.className));
   assert.deepEqual(clipped,[],name+' at '+width);
   await plate.evaluate(n=>n.scrollIntoView({block:'start'}));
   await capture('plate-'+name.toLowerCase().replaceAll(' ','-')+'-'+width+'.png');
   await plate.locator('.plate-departure>a').focus();
   assert.equal(await plate.locator('.plate-departure>a').evaluate(n=>n===document.activeElement),true);
  }
 }
 await page.goto(new URL('standalone.html',url).href);
 const p=data.projects.find(p=>p.name==='OpenTofu');
 const row=page.locator('#project-'+p.id);await row.locator('> details').evaluate(n=>n.open=true);
 assert.ok(await row.locator('.plate-art img').getAttribute('src').then(s=>s.startsWith('data:image/')));
 assert.ok(await row.locator('.plate-detail img').getAttribute('src').then(s=>s.startsWith('data:image/')));
};
