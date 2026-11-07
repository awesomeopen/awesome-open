/* Native bridge integration; no model/client conversation is simulated. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
 const options={headless:true,args:['--enable-blink-features=WebMCP']};
 if(process.env.CHROMIUM_PATH) options.executablePath=process.env.CHROMIUM_PATH;
 if(process.env.CHROMIUM_NO_SANDBOX==='1') options.args.push('--no-sandbox');
 const browser=await chromium.launch(options);
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.SITE_URL||'http://127.0.0.1:8000';
 const output='tmp/site-qa';fs.mkdirSync(output,{recursive:true});
 const report={browser:browser.version(),scope:'Native WebMCP bridge; full agent/client untested',status:'running'};
 const major=Number(browser.version().split('.')[0]);
 async function call(name,args, target=page){return target.evaluate(async({name,args,stringInput})=>{
  const tool=(await document.modelContext.getTools()).find(t=>t.name===name);
  const result=await document.modelContext.executeTool(tool,stringInput?JSON.stringify(args):args);
  return typeof result==='string'?JSON.parse(result):result;
 },{name,args,stringInput:major<155});}
 try {
  await page.goto(base);report.sourceSha=await page.locator('#specimen-cabinet').getAttribute('data-source-sha');await page.waitForFunction(()=>document.querySelector('#cabinet-support').textContent.includes('four tools'));
  assert.deepEqual(await page.evaluate(async()=> (await document.modelContext.getTools()).map(t=>t.name).sort()),['cabinet_arrange','cabinet_compare','cabinet_find','cabinet_inspect']);
  const found=await call('cabinet_find',{query:'scad'});assert.equal(found.ok,true);assert.ok(found.projects.length>=2);
  const ids=found.projects.slice(0,2).map(p=>p.id);
  await call('cabinet_arrange',{ids,revision:found.revision});
  assert.equal(await page.locator('#cabinet-selection li').count(),2);
  await page.getByRole('button',{name:'Move '+found.projects[1].name+' earlier',exact:true}).focus();await page.keyboard.press('Enter');
  const shared=await call('cabinet_find',{query:'scad'});assert.deepEqual(shared.ids,ids.slice().reverse());
  // Rejections reach the caller as data, carrying the recovery instruction.
  async function rejected(name,args,code,message,target=page){
   const result=await call(name,args,target);
   assert.deepEqual(Object.keys(result).sort(),['code','message','ok']);
   assert.equal(result.ok,false);assert.equal(result.code,code);assert.match(result.message,message);
  }
  await rejected('cabinet_arrange',{ids:[],revision:found.revision},'stale_revision',/current revision and retry/);
  await rejected('cabinet_arrange',{ids:['unknown'],revision:shared.revision},'invalid_ids',/canonical project IDs/);
  await rejected('cabinet_arrange',{ids:[ids[0],ids[0]],revision:shared.revision},'invalid_ids',/canonical project IDs/);
  await rejected('cabinet_find',{query:'scad',offset:-1},'invalid_offset',/whole number/);
  assert.deepEqual((await call('cabinet_find',{query:''})).ids,shared.ids);
  // Manual Catalog search and the tool return the same IDs, order and unknowns.
  const manual=await context.newPage();
  await manual.goto(base);
  async function allTool(query){
   const rows=[];let total;
   do{const r=await call('cabinet_find',{query,offset:rows.length});assert.equal(r.ok,true);total=r.total;rows.push(...r.projects);if(!r.projects.length)break;}while(rows.length<total);
   assert.equal(rows.length,total);return rows;
  }
  async function manualRows(query){
   await manual.locator('#search').fill(query);await manual.locator('#search').press('Enter');
   if(query)await manual.waitForFunction(()=>document.querySelector('#filters').dataset.searchText==='ready');
   return manual.evaluate(()=>{
    const data=JSON.parse(document.getElementById('catalog-data').textContent),byId=new Map(data.projects.map(p=>[p.id,p]));
    return [...document.querySelectorAll('.project-card:not([hidden])')].map(card=>({id:card.dataset.projectId,
     license:card.querySelector('.license-readout').textContent||null,stars:OpenCatalog.starsOf(byId.get(card.dataset.projectId)),
     pushed_at:(byId.get(card.dataset.projectId).github||{}).pushed_at||null}));
   });
  }
  for(const query of ['video editor','scad','obs','server','self-hosted','manage family photos on my own server','']){
   const tool=await allTool(query),visible=await manualRows(query);
   assert.deepEqual(tool.map(p=>p.id),visible.map(p=>p.id),'IDs and order: '+query);
   assert.deepEqual(tool.map(p=>({id:p.id,license:p.github.license,stars:p.github.stars,pushed_at:p.github.pushed_at})),visible,'Unknowns: '+query);
  }
  report.manualAndToolQueries=7;
  // Journeys: an editor search reaches summaries and notes; the family-photo search names nothing.
  const editors=await call('cabinet_find',{query:'video editor'});
  assert.ok(editors.total>6);
  for(const name of ['OpenCut','OpenReel Video','Open Video Editor']) assert.ok(editors.projects.some(p=>p.name===name),name);
  const ranks=editors.projects.map(p=>p.matched_fields);assert.deepEqual(ranks[0].slice(0,1),['name']);
  assert.ok(editors.projects.some(p=>p.matched_fields.every(f=>f==='summary'||f==='feature')));
  const none=await call('cabinet_find',{query:'manage family photos on my own server'});
  assert.equal(none.ok,true);assert.equal(none.total,0);assert.deepEqual(none.projects,[]);
  assert.match(none.message,/^No match in this catalog of [\d,]+ Open\*-named projects\.$/);
  await manual.locator('#search').fill('manage family photos on my own server');await manual.locator('#search').press('Enter');
  assert.equal(await manual.locator('#empty-state').textContent(),none.message);
  await manual.close();
  // Without summaries, the tool reports it can't search them; the Catalog says what it still covers.
  const offline=await context.newPage();
  await offline.route('**/search-text.json*',route=>route.abort());
  await offline.goto(base);
  await offline.waitForFunction(()=>document.querySelector('#cabinet-support').textContent.includes('four tools'));
  await rejected('cabinet_find',{query:'video'},'search_unavailable',/could not load\. Retry/,offline);
  assert.equal((await call('cabinet_find',{query:''},offline)).ok,true);
  await offline.locator('#search').fill('video');await offline.locator('#search').press('Enter');
  await offline.waitForFunction(()=>document.querySelector('#filters').dataset.searchText==='failed');
  assert.ok(await offline.locator('#project-list .project-card:not([hidden])').count()>0);
  assert.match(await offline.locator('#filters .link-notice:not([hidden])').last().textContent(),/Search covers names, aliases, descriptions and alternatives/);
  await offline.close();
  const comparison=await call('cabinet_compare',{});assert.equal(comparison.ok,true);assert.deepEqual(comparison.ids,shared.ids);
  assert.deepEqual(await page.locator('#cabinet-comparison thead th a').allTextContents(),comparison.projects.map(p=>p.name));
  const link=await page.locator('#cabinet-share').inputValue();
  const other=await context.newPage();await other.goto(link);assert.equal(await other.locator('#cabinet-selection li').count(),2);
  assert.deepEqual((await call('cabinet_find',{query:''},other)).ids,shared.ids);
  await page.locator('#specimen-cabinet').screenshot({path:output+'/cabinet-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#specimen-cabinet').screenshot({path:output+'/cabinet-mobile.png'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  const region=page.locator('#cabinet-comparison');assert.ok(await region.evaluate(el=>el.scrollWidth>el.clientWidth));
  await page.getByRole('button',{name:'Remove '+comparison.projects[0].name,exact:true}).click();
  assert.equal(await page.locator('#cabinet-selection li').count(),1);
  await page.goBack();assert.equal(await page.locator('#cabinet-selection li').count(),2);
  // Hold the evidence request: user cancellation must retain the full selection.
  let release, started;const waiting=new Promise(resolve=>started=resolve);
  await other.route('**/catalog.json',async route=>{started();await new Promise(resolve=>release=resolve);await route.abort();});
  await other.locator('#cabinet-compare').click();await waiting;
  assert.match(await other.locator('#cabinet-status').textContent(),/Running: compare/);
  await other.locator('#cabinet-cancel').click();release();
  await other.waitForFunction(()=>document.querySelector('#cabinet-status').textContent.includes('Cancelled'));
  assert.deepEqual((await call('cabinet_find',{query:''},other)).ids,shared.ids);
  await other.unroute('**/catalog.json');
  await call('cabinet_compare',{},other);
  // Client abort is propagated through the native bridge.
  await other.reload();
  let releaseNative, nativeStarted;const nativeWaiting=new Promise(resolve=>nativeStarted=resolve);
  await other.route('**/catalog.json',async route=>{nativeStarted();await new Promise(resolve=>releaseNative=resolve);await route.abort();});
  const cancelled=other.evaluate(async stringInput=>{
    const tool=(await document.modelContext.getTools()).find(t=>t.name==='cabinet_compare');
    window.cabinetAbort=new AbortController();
    try {
     const result=await document.modelContext.executeTool(tool,stringInput?'{}':{}, {signal:window.cabinetAbort.signal});
     return (typeof result==='string'?JSON.parse(result):result).code==='cancelled';
    } catch(_){return true;}
  },major<155);
  await nativeWaiting;await other.evaluate(()=>window.cabinetAbort.abort());releaseNative();assert.equal(await cancelled,true);
  await other.unroute('**/catalog.json');
  for(let i=0;i<24;i++) await call('cabinet_find',{query:'scad'});
  assert.equal(await page.locator('#cabinet-activity li').count(),20);
  await other.goto(base+'?cabinet=unknown#specimen-cabinet');assert.equal(await other.locator('#cabinet-selection li').count(),0);
  assert.match(await other.locator('#cabinet-status').textContent(),/Invalid cabinet URL/);
  assert.deepEqual(errors,[]);report.status='passed';report.selectionURL=link;
 } finally {fs.writeFileSync(output+'/cabinet.json',JSON.stringify(report,null,2)+'\n');await browser.close();}
 console.log(JSON.stringify(report));
})().catch(error=>{console.error(error);process.exitCode=1;});
