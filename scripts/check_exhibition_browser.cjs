/* Preview-only browser coverage. Uses the existing PR-local server and Chromium. */
const { chromium }=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_NO_SANDBOX==='1'?{args:['--no-sandbox']}:{}),...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=new URL('exhibition.html',process.env.SITE_URL||'http://127.0.0.1:8000/').href;
 const ready=()=>page.waitForSelector('body[data-exhibition-ready=true]');
 const fits=async()=>assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
 const capture=async name=>{await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:'tmp/site-qa/'+name,fullPage:false});};
 fs.mkdirSync('tmp/site-qa',{recursive:true});
 try {
 await page.goto(url);await ready();await fits();
 const data=await page.locator('#exhibition-data').evaluate(n=>JSON.parse(n.textContent));
 assert.equal(await page.locator('.exhibit').count(),3);
 assert.equal(await page.locator('#ex-list .project-card').count(),data.projects.length);
 await page.locator('.ex-hall img').evaluateAll(imgs=>Promise.all(imgs.map(img=>img.decode())));
 await capture('exhibition-desktop.png');
 await page.locator('.exhibit-01 .inspect-link').click();
 const target=await page.locator('.exhibit-01 .inspect-link').getAttribute('data-inspect');
 assert.ok(await page.locator('#project-'+target+' > .specimen-drawer').evaluate(n=>n.open));
 await capture('exhibition-record.png');
 await page.goto(url);await ready();await page.locator('#ex-search').fill('OpenTofu');
 assert.equal(await page.locator('#ex-hall').isVisible(),false);
 assert.equal(await page.locator('#ex-list .project-card:visible').count(),1);
 await page.locator('#ex-reset').click();assert.equal(await page.locator('#ex-hall').isVisible(),true);
 await page.locator('[data-view=ledger]').click();assert.equal(await page.locator('#ex-hall').isVisible(),false);
 await page.reload();await ready();assert.equal(await page.locator('[data-view=ledger]').getAttribute('aria-pressed'),'true');
 await page.locator('[data-view=exhibition]').click();
 await page.locator('#ex-license').selectOption('unknown');assert.equal(await page.locator('#ex-hall').isVisible(),false);
 await page.locator('#ex-reset').click();
 await page.locator('#ex-sort').selectOption('stars');
 const ordered=await page.evaluate(()=>{const d=JSON.parse(document.getElementById('exhibition-data').textContent);return OpenCatalog.selectProjects(d.projects,{...OpenCatalog.DEFAULTS,sort:'stars'},d).map(p=>p.id);});
 assert.deepEqual(await page.locator('#ex-list>.project-card').evaluateAll(ns=>ns.map(n=>n.dataset.projectId)),ordered);
 const noArt=data.projects.find(p=>!p.artwork);assert.ok(noArt);assert.equal(await page.locator('#project-'+noArt.id+' .specimen-art').count(),0);
 await page.locator('#project-'+noArt.id+' > .specimen-drawer > summary').click();assert.equal(await page.locator('#project-'+noArt.id+' .source-link').isVisible(),true);
 for(const width of [320,390,600,768,900,1024]) {await page.setViewportSize({width,height:900});await page.goto(url);await ready();await fits();if(width===390)await capture('exhibition-mobile.png');}
 await page.keyboard.press('Tab');assert.equal(await page.locator(':focus').getAttribute('class'),'skip-link');
 await page.keyboard.press('Enter');assert.equal(new URL(page.url()).hash,'#ex-ledger');
 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});await fallback.goto(url);
 assert.equal(await fallback.locator('.exhibit').count(),3);assert.equal(await fallback.locator('#ex-search-form').isVisible(),false);
 await fallback.locator('#ex-list summary').first().click();assert.ok(await fallback.locator('#ex-list details').first().evaluate(n=>n.open));await fallback.close();
 assert.deepEqual(errors,[]);console.log('Exhibition preview: desktop/mobile, artwork, inspect, search, filters, sort, view URL, missing art, keyboard and no-JS checks pass.');
 }catch(e){await capture('exhibition-failure.png');throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
