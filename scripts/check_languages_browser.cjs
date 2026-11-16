/* Synthetic language states through the production renderer; called by Cabinet CI. */
const assert = require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
module.exports=async(browser,base,call)=>{
 const fixtures=JSON.parse(execFileSync('python3',[path.join(__dirname,'browser_evidence_fixture.py'),'--languages'],{encoding:'utf8',maxBuffer:8*1024*1024}));
 const url=new URL(base.endsWith('/')?base:base+'/');
 async function mount(context,state){
  const p=await context.newPage(), f=fixtures[state];
  await p.route('**/*',async route=>{
   const u=new URL(route.request().url()),key=u.pathname.slice(url.pathname.length);
   if(u.origin!==url.origin||!Object.hasOwn(f.responses,key))return route.fallback();
   await route.fulfill({body:f.responses[key],contentType:key.endsWith('.json')?'application/json':key.endsWith('.svg')?'image/svg+xml':'text/html'});
  });
  return p;
 }
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const id=fixtures.available.data.projects.find(p=>p.languages?.length).id;
 try{
  const page=await mount(context,'available');await page.goto(url.href);
  await page.waitForFunction(()=>document.querySelector('#filters').dataset.enhanced==='true');
  await page.locator('#f-language').selectOption('C++');
  assert.equal(new URL(page.url()).searchParams.get('language'),'C++');
  assert.equal(await page.locator('#rows .row:not([hidden])').count(),1);
  await page.locator('#f-language').selectOption('C#');
  await page.goBack();assert.equal(await page.locator('#f-language').inputValue(),'C++');
  await page.goForward();assert.equal(await page.locator('#f-language').inputValue(),'C#');
  const found=await call('cabinet_find',{query:'',language:'C#'},page);
  assert.equal(found.total,1);assert.deepEqual(found.projects[0].languages,['C++','C#','JavaScript','Shell']);
  const listed=await call('list_find',{query:'C++',filters:{languages:'C#'}},page);
  assert.equal(listed.total,1);assert.deepEqual(listed.items[0].fields.languages,found.projects[0].languages);
  const inspect=await call('cabinet_inspect',{id},page);assert.equal(inspect.language_evidence.last_good.value['C++'],300);
  await call('cabinet_arrange',{ids:[id],revision:found.revision},page);
  const compare=await call('cabinet_compare',{},page);assert.deepEqual(compare.projects[0].language_evidence,inspect.language_evidence);
  const schema=await page.evaluate(async()=> (await document.modelContext.getTools()).find(t=>t.name==='cabinet_find').inputSchema);
  assert.ok((typeof schema === "string" ? JSON.parse(schema) : schema).properties.language);
  await page.locator('#specimen-cabinet').evaluate(d=>d.open=false);
  await page.locator('#reset').click();
  assert.equal(await page.locator('#f-language').inputValue(),'');
  assert.equal(new URL(page.url()).searchParams.has('language'),false);
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   await page.goto(url.href+'records/'+id+'.html');
   const box=page.locator('.pg-languages');await box.scrollIntoViewIfNeeded();
   await box.screenshot({path:`tmp/site-qa/languages-closed-${width}.png`});
   await box.locator('summary').focus();await box.locator('summary').press('Enter');assert.match(await box.textContent(),/300 bytes/);
   assert.ok(await box.isVisible());
   await box.screenshot({path:`tmp/site-qa/languages-box-${width}.png`});
   await page.screenshot({path:`tmp/site-qa/languages-${width}.png`,fullPage:true});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  for(const state of ['stale','empty','unknown']){
   const p=await mount(context,state);await p.goto(url.href+'records/'+id+'.html');
   assert.match(await p.locator('.pg-languages').textContent(),state==='stale'?/Stale cached result/:state==='empty'?/None detected/:/Unknown/);
   await p.close();
  }
  const staticContext=await browser.newContext({javaScriptEnabled:false});
  const staticPage=await mount(staticContext,'available');await staticPage.goto(url.href+'records/'+id+'.html');
  await staticPage.locator('.pg-languages summary').click();assert.match(await staticPage.locator('.pg-languages').textContent(),/300 bytes/);
  await staticContext.close();
 }finally{await context.close();}
};
