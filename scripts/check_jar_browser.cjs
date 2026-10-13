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
 assert.ok(await page.locator('.search-submit img').evaluate(n=>n.complete&&n.naturalWidth>0));assert.equal(await page.locator('.jar-central .steam-strand').count(),3);
 const first=page.locator('.jar-select').first();const restingWidth=await page.locator('.vessel').first().evaluate(n=>n.getBoundingClientRect().width);await first.hover({position:{x:45,y:55}});await page.waitForFunction(()=>parseFloat(document.querySelector('.jar-exhibit').style.getPropertyValue('--scene-scale'))>1.08);await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.equal(await first.getAttribute('aria-expanded'),'true');assert.equal(await page.locator('.jar-annotation:visible').count(),1);assert.equal(await page.locator('.jar-annotation:visible .jar-leaders path[d]').count(),3);assert.equal(await page.locator('.jar-annotation:visible').evaluate(n=>getComputedStyle(n).backgroundColor),'rgba(0, 0, 0, 0)');
 assert.ok(await page.locator('.jar-exhibit').first().evaluate(n=>Math.abs(parseFloat(n.style.getPropertyValue('--mx')))>1));assert.ok(await page.locator('.vessel').first().evaluate((n,w)=>n.getBoundingClientRect().width>w*1.2,restingWidth));assert.equal(await page.locator('.jar-exhibit').first().evaluate(n=>parseFloat(n.style.getPropertyValue('--tilt-x'))),0);
 // Presence of SVG paths alone does not prove that Chrome paints them.
 const leaders=page.locator('.jar-annotation:visible .jar-leaders');assert.ok(await leaders.isVisible());
 assert.ok(await leaders.locator('path').first().evaluate(n=>getComputedStyle(n).stroke!=='none'&&n.getTotalLength()>20));
 assert.ok(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform.startsWith('matrix3d')));
 await page.screenshot({path:'tmp/site-qa/jars-hover.png'});
 // Vertical pointer movement must leave the camera unchanged.
 const before=await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform);
 await first.hover({position:{x:45,y:150}});await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.equal(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform),before);
 for(const index of [4,5,6]) assert.equal(await page.locator('.jar-exhibit').nth(index).locator('.callout-function').evaluate(n=>getComputedStyle(n).textAlign),'right');
 // Keyboard selection retains foreground approach and illumination.
 await page.mouse.move(1400,950);await page.locator('.jar-central .jar-select').focus();
 await page.waitForFunction(()=>parseFloat(document.querySelector('.jar-central').style.getPropertyValue('--scene-scale'))>1.09);
 await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.ok(await page.locator('.jar-central .jar-uplight').evaluate(n=>Math.abs(Number(getComputedStyle(n).opacity)-.75)<.02));
 assert.notEqual(await page.locator('.jar-central .jar-lid').evaluate(n=>getComputedStyle(n).transform),'none');
 assert.equal(await page.locator('.jar-central .steam-strand').first().evaluate(n=>getComputedStyle(n).animationName),'steam-fade');
 await page.screenshot({path:'tmp/site-qa/jars-inspect.png'});
 assert.equal(await page.locator('.specimen-idle').first().evaluate(n=>getComputedStyle(n).animationName),'specimen-stir');
 await page.locator('.jar-motion-toggle').click();
 assert.equal(await page.locator('.specimen-idle').first().evaluate(n=>getComputedStyle(n).animationName),'none');
 assert.equal(await page.locator('.jar-motion-toggle').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('.jar-motion-toggle').textContent(),'[>]');assert.equal(await page.locator('.jar-motion-toggle').getAttribute('aria-label'),'Play motion');
 await page.locator('.jar-motion-toggle').click();

 await first.hover({position:{x:45,y:55}});

 const link=page.locator('.jar-annotation:visible a');assert.equal(await link.evaluate(n=>getComputedStyle(n).borderTopStyle),'dashed');await link.hover();assert.equal(await link.evaluate(n=>getComputedStyle(n).borderTopStyle),'solid');const id=await link.getAttribute('data-jar-inspect');await link.click();
 assert.ok(await page.locator('#project-'+id+' > details').evaluate(n=>n.open));
 // Three activations reveal two fractures, then open the record; progress survives hover changes.
 await page.goto(url);await ready();
 const jar=page.locator('.jar-exhibit').first(),target=await jar.getAttribute('data-project');
 await first.click();assert.equal(await jar.getAttribute('data-cracks'),'1');assert.equal(new URL(page.url()).hash,'');
 assert.equal(await jar.locator('.crack-first').evaluate(n=>getComputedStyle(n).opacity),'0.38');
 await page.screenshot({path:'tmp/site-qa/jars-crack-first.png'});
 await page.mouse.move(1400,950);await first.focus();await page.keyboard.press('Enter');
 assert.equal(await jar.getAttribute('data-cracks'),'2');assert.equal(await jar.locator('.crack-first').evaluate(n=>getComputedStyle(n).opacity),'1');assert.match(await first.getAttribute('aria-label'),/^Inspect record/);
 await page.screenshot({path:'tmp/site-qa/jars-crack-second.png'});
 await page.keyboard.press('Space');
 await page.waitForFunction(id=>document.querySelector('#project-'+id+' > details').open,target);
 assert.equal(new URL(page.url()).hash,'#project-'+target);
 assert.equal(await jar.getAttribute('data-cracks'),'0');assert.match(await first.getAttribute('aria-label'),/^Crack glass/);
 await page.goto(url);await ready();await page.locator('#search').fill('OpenTofu');await page.locator('.search-submit').click();await page.waitForFunction(()=>document.querySelectorAll('.project-card:not([hidden])').length===1);
 await page.locator('.jar-low-lid .jar-select').focus();await page.locator('.jar-low-lid .jar-annotation a').click();assert.ok(await page.locator('.project-card:visible > details').evaluate(n=>n.open));
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);await ready();await first.focus();assert.equal(await first.getAttribute('aria-expanded'),'true');
 assert.equal(await page.locator('.specimen-idle').first().evaluate(n=>getComputedStyle(n).animationName),'none');assert.equal(await page.locator('.jar-steam').first().isVisible(),false);
 await page.keyboard.press('Escape');assert.equal(await first.getAttribute('aria-expanded'),'false');
 await first.hover({position:{x:45,y:55}});assert.equal(await page.locator('.jar-exhibit').first().evaluate(n=>parseFloat(n.style.getPropertyValue('--mx'))||0),0);assert.equal(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform.startsWith('matrix3d')),false);
 for(const width of [320,390,680,768,1024]){await page.setViewportSize({width,height:900});await page.goto(url);await ready();await fits(width);if(width===768)assert.equal(await page.locator('.jar-exhibit:visible').count(),5);}
 const touch=await browser.newPage({viewport:{width:390,height:900},isMobile:true,hasTouch:true,reducedMotion:'reduce'});await touch.goto(url);await touch.waitForSelector('body[data-jars-ready=true]');
 await touch.locator('.jar-select').first().tap();assert.equal(await touch.locator('.jar-annotation:visible').count(),1);assert.equal(new URL(touch.url()).hash,'');assert.equal(await touch.locator('.jar-exhibit').first().getAttribute('data-cracks'),'1');
 await touch.screenshot({path:'tmp/site-qa/jars-mobile.png'});
 await touch.locator('.jar-scroll').evaluate(n=>n.scrollLeft=n.scrollWidth);await touch.locator('.jar-select').last().tap();assert.equal(await touch.locator('.jar-select').last().getAttribute('aria-expanded'),'true');
 await touch.locator('.jar-select').last().tap();assert.equal(await touch.locator('.jar-exhibit').last().getAttribute('data-cracks'),'2');await touch.locator('.jar-select').last().tap();assert.match(new URL(touch.url()).hash,/^#project-/);await touch.close();
 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});await fallback.goto(url);assert.equal(await fallback.locator('[data-jar-inspect]').count(),7);await fallback.locator('.project-card summary').first().click();assert.ok(await fallback.locator('.project-card details').first().evaluate(n=>n.open));await fallback.close();
 assert.deepEqual(errors,[]);console.log('Seven jars: assets, hover overlap, foreground zoom, vertical stability, underlight, lid lift, vapor, idle movement/pause, outlined inspect action, record links, search, keyboard/Escape, reduced motion, responsive density, touch selection/scroll and no-JS pass.');
 }catch(e){await page.screenshot({path:'tmp/site-qa/jars-failure.png'});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
