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
  const found=await call('cabinet_find',{query:'scad'});assert.ok(found.projects.length>=2);
  const ids=found.projects.slice(0,2).map(p=>p.id);
  await call('cabinet_arrange',{ids,revision:found.revision});
  assert.equal(await page.locator('#cabinet-selection li').count(),2);
  await page.getByRole('button',{name:'Move '+found.projects[1].name+' earlier',exact:true}).focus();await page.keyboard.press('Enter');
  const shared=await call('cabinet_find',{query:'scad'});assert.deepEqual(shared.ids,ids.slice().reverse());
  await assert.rejects(call('cabinet_arrange',{ids:[],revision:found.revision}));
  await assert.rejects(call('cabinet_arrange',{ids:['unknown'],revision:shared.revision}));
  await assert.rejects(call('cabinet_arrange',{ids:[ids[0],ids[0]],revision:shared.revision}));
  await assert.rejects(call('cabinet_find',{query:'x'.repeat(161)}));
  const comparison=await call('cabinet_compare',{});assert.deepEqual(comparison.ids,shared.ids);
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
    try {await document.modelContext.executeTool(tool,stringInput?'{}':{}, {signal:window.cabinetAbort.signal});return false;}
    catch(_){return true;}
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
