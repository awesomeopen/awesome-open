const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=new URL('jars.html',process.env.SITE_URL||'http://127.0.0.1:8000/').href;
 try{
 await page.goto(url);await page.waitForSelector('body[data-jars-ready=true]');
 assert.equal(await page.locator('.jar-exhibit').count(),3);
 await page.locator('.jar-specimen img').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
 const first=page.locator('.jar-link').first();await first.hover({position:{x:40,y:40}});await page.waitForTimeout(350);
 assert.equal(await first.locator('.jar-metrics').evaluate(n=>getComputedStyle(n).opacity),'1');
 assert.notEqual(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform),'matrix(1, 0, 0, 1, 0, 0)');
 await page.screenshot({path:'tmp/site-qa/jars-desktop.png'});
 await page.locator('button[data-ground=baseline]').click();assert.equal(await page.locator('.jar-hall').getAttribute('data-ground'),'baseline');
 await page.screenshot({path:'tmp/site-qa/jars-baseline.png'});
 const id=await first.getAttribute('data-jar-inspect');await first.click();
 assert.ok(await page.locator('#project-'+id+' > details').evaluate(n=>n.open));
 await page.goto(url);await page.locator('#search').fill('OpenTofu');assert.equal(await page.locator('.project-card:visible').count(),1);
 await page.locator('.jar-open .jar-link').click();assert.ok(await page.locator('.project-card:visible > details').evaluate(n=>n.open));
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);
 assert.equal(await page.locator('.jar-specimen img').first().evaluate(n=>getComputedStyle(n).animationName),'none');
 await page.locator('.jar-link').first().focus();assert.equal(await page.locator('.jar-metrics').first().evaluate(n=>getComputedStyle(n).opacity),'1');
 for(const width of [320,390,680,768,1024]){await page.setViewportSize({width,height:900});await page.goto(url);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));if(width===390)await page.screenshot({path:'tmp/site-qa/jars-mobile.png'});}
 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});await fallback.goto(url);assert.equal(await fallback.locator('.jar-link').count(),3);await fallback.locator('.project-card summary').first().click();assert.ok(await fallback.locator('.project-card details').first().evaluate(n=>n.open));await fallback.close();
 assert.deepEqual(errors,[]);console.log('Jar preview: artwork, parallax, inspect, search, treatments, keyboard, reduced motion, narrow layouts and no-JS pass.');
 }catch(e){await page.screenshot({path:'tmp/site-qa/jars-failure.png'});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
