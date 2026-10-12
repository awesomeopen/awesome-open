const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=new URL('jars.html',process.env.SITE_URL||'http://127.0.0.1:8000/').href;
 const ready=()=>page.waitForSelector('body[data-jars-ready=true]');
 const fits=async width=>assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No overflow at '+width);
 try{
 await page.goto(url);await ready();
 assert.equal(await page.locator('.jar-exhibit').count(),7);assert.equal(await page.locator('[data-ground]').count(),0);assert.equal(await page.locator('.jar-review').count(),0);assert.equal(await page.locator('.jar-photo[src*=labelled]').count(),2);
 await page.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
 await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:'tmp/site-qa/jars-desktop.png'});
 const first=page.locator('.jar-select').first();await first.hover({position:{x:45,y:55}});await page.waitForTimeout(250);
 assert.equal(await first.getAttribute('aria-expanded'),'true');assert.equal(await page.locator('.jar-annotation:visible').count(),1);assert.equal(await page.locator('.jar-annotation:visible .jar-leaders path[d]').count(),3);assert.equal(await page.locator('.jar-annotation:visible').evaluate(n=>getComputedStyle(n).backgroundColor),'rgba(0, 0, 0, 0)');
 assert.notEqual(await page.locator('.jar-exhibit').first().evaluate(n=>n.style.getPropertyValue('--mx')),'0px');
 await page.screenshot({path:'tmp/site-qa/jars-hover.png'});
 const link=page.locator('.jar-annotation:visible a');const id=await link.getAttribute('data-jar-inspect');await link.click();
 assert.ok(await page.locator('#project-'+id+' > details').evaluate(n=>n.open));
 await page.goto(url);await ready();await page.locator('#search').fill('OpenTofu');await page.waitForFunction(()=>document.querySelectorAll('.project-card:not([hidden])').length===1);
 await page.locator('.jar-low-lid .jar-select').focus();await page.locator('.jar-low-lid .jar-annotation a').click();assert.ok(await page.locator('.project-card:visible > details').evaluate(n=>n.open));
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);await ready();await first.focus();assert.equal(await first.getAttribute('aria-expanded'),'true');
 await page.keyboard.press('Escape');assert.equal(await first.getAttribute('aria-expanded'),'false');
 await first.hover({position:{x:45,y:55}});assert.equal(await page.locator('.jar-exhibit').first().evaluate(n=>n.style.getPropertyValue('--mx')||'0px'),'0px');
 for(const width of [320,390,680,768,1024]){await page.setViewportSize({width,height:900});await page.goto(url);await ready();await fits(width);if(width===768)assert.equal(await page.locator('.jar-exhibit:visible').count(),5);}
 const touch=await browser.newPage({viewport:{width:390,height:900},isMobile:true,hasTouch:true,reducedMotion:'reduce'});await touch.goto(url);await touch.waitForSelector('body[data-jars-ready=true]');
 await touch.locator('.jar-select').first().tap();assert.equal(await touch.locator('.jar-annotation:visible').count(),1);assert.equal(new URL(touch.url()).hash,'');
 await touch.screenshot({path:'tmp/site-qa/jars-mobile.png'});
 await touch.locator('.jar-scroll').evaluate(n=>n.scrollLeft=n.scrollWidth);await touch.locator('.jar-select').last().tap();assert.equal(await touch.locator('.jar-select').last().getAttribute('aria-expanded'),'true');
 await touch.locator('.jar-annotation:visible a').tap();assert.match(new URL(touch.url()).hash,/^#project-/);await touch.close();
 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});await fallback.goto(url);assert.equal(await fallback.locator('[data-jar-inspect]').count(),7);await fallback.locator('.project-card summary').first().click();assert.ok(await fallback.locator('.project-card details').first().evaluate(n=>n.open));await fallback.close();
 assert.deepEqual(errors,[]);console.log('Seven jars: assets, hover overlap, local parallax, record links, search, keyboard/Escape, reduced motion, responsive density, touch selection/scroll and no-JS pass.');
 }catch(e){await page.screenshot({path:'tmp/site-qa/jars-failure.png'});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
