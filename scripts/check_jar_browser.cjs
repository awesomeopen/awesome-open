const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=new URL(process.env.JAR_PAGE||'jars.html',process.env.SITE_URL||'http://127.0.0.1:8000/').href;
 const ready=()=>page.waitForSelector('body[data-jars-ready=true]');
 const fits=async width=>assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No overflow at '+width);
 try{
 // Hold the deferred jar script to inspect the actual pre-initialization paint,
 // on both navigation and reload. Release it only after checking visibility.
 let releaseStartup;
 await page.route('**/jars.js', async route=>{await new Promise(resolve=>{releaseStartup=resolve;});await route.continue();});
 for(const reload of [false,true]){
   if(reload)await page.reload({waitUntil:'commit'});else await page.goto(url,{waitUntil:'commit'});
   await page.waitForSelector('.jar-annotation',{state:'attached'});
   await page.waitForFunction(()=>getComputedStyle(document.querySelector('.jar-stage')).display==='grid');
   assert.equal(await page.locator('.jar-annotation:visible').count(),0,'No startup description flash');
   assert.equal(await page.locator('.jar-stage').evaluate(n=>getComputedStyle(n).height),'380px');
   while(!releaseStartup)await new Promise(resolve=>setTimeout(resolve,10));
   releaseStartup();releaseStartup=null;await ready();await page.waitForLoadState('domcontentloaded');
 }
 await page.unroute('**/jars.js');
 // A failed enhancement still exposes ordinary descriptions and record links.
 await page.route('**/jars.js',route=>route.abort());
 await page.reload({waitUntil:'domcontentloaded'});
 assert.equal(await page.locator('.jar-annotation:visible').count(),7);
 await page.unroute('**/jars.js');
 await page.goto(url);await ready();
 assert.equal(await page.locator('.jar-exhibit').count(),7);assert.equal(await page.locator('[data-ground]').count(),0);assert.equal(await page.locator('.jar-review').count(),0);assert.equal(await page.locator('.jar-photo[src*=labelled]').count(),2);
 await page.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
 await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:'tmp/site-qa/jars-desktop.png'});
 assert.ok(await page.locator('.search-submit img').evaluate(n=>n.complete&&n.naturalWidth>0));assert.equal(await page.locator('.jar-central .steam-strand').count(),3);
 const first=page.locator('.jar-select').first();const restingWidth=await page.locator('.vessel').first().evaluate(n=>n.getBoundingClientRect().width);await first.hover({position:{x:45,y:55}});await page.waitForFunction(()=>parseFloat(document.querySelector('.jar-exhibit').style.getPropertyValue('--my'))<-2.9);await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.equal(await first.getAttribute('aria-expanded'),'true');assert.equal(await page.locator('.jar-annotation:visible').count(),1);assert.equal(await page.locator('.jar-annotation:visible .jar-leaders path[d]').count(),3);assert.equal(await page.locator('.jar-annotation:visible').evaluate(n=>getComputedStyle(n).backgroundColor),'rgba(0, 0, 0, 0)');
 assert.ok(await page.locator('.jar-exhibit').first().evaluate(n=>Math.abs(parseFloat(n.style.getPropertyValue('--mx')))>1));assert.equal(await page.locator('.vessel').first().evaluate(n=>n.getBoundingClientRect().width),restingWidth);
 assert.ok(await page.locator('.jar-exhibit').first().evaluate(n=>['--mx','--my','--inner-x','--inner-y','--reflection-x'].every(key=>Number.isInteger(parseFloat(n.style.getPropertyValue(key))))),'Settled layer positions snap to whole pixels');
 // Presence of SVG paths alone does not prove that Chrome paints them.
 const leaders=page.locator('.jar-annotation:visible .jar-leaders');assert.ok(await leaders.isVisible());
 assert.ok(await leaders.locator('path').first().evaluate(n=>getComputedStyle(n).stroke!=='none'&&n.getTotalLength()>20));
 assert.equal(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform),'none');
 assert.ok(await page.locator('.specimen-window').first().evaluate(n=>!getComputedStyle(n).filter.includes('url(')),'No specimen displacement filter');
 await page.screenshot({path:'tmp/site-qa/jars-hover.png'});
 // Read committed bounds, never scan image pixels in the browser.
 const cutoutBounds=JSON.parse(fs.readFileSync(path.join(__dirname,'../site/specimens/cutouts.json'))).cutouts;
 const cutoutVariants=Object.entries(JSON.parse(fs.readFileSync(path.join(__dirname,'../site/jars/responsive.json'))).sources).filter(([source])=>source.includes('/cutouts/')).flatMap(([,entry])=>entry.variants.map(v=>v.path));
 const checkSubjectClearance=async(targetPage=page)=>{
   const subjects=await targetPage.locator('.jar-exhibit').evaluateAll((nodes,{bounds,variants})=>nodes.map(n=>{
     const image=n.querySelector('.specimen-print'),window=n.querySelector('.specimen-window').getBoundingClientRect(),rect=image.getBoundingClientRect();
     const box=(image.getAttribute('src').includes('/cutouts/')||variants.includes(image.getAttribute('src')))?bounds[n.dataset.project].subject_bbox:[0,0,1,1];
     return {id:n.dataset.project,left:rect.left+rect.width*box[0]-window.left,
       right:window.right-(rect.left+rect.width*box[2]),top:rect.top+rect.height*box[1]-window.top,
       bottom:window.bottom-(rect.top+rect.height*box[3])};
   }),{bounds:cutoutBounds,variants:cutoutVariants});
   for(const subject of subjects) for(const edge of ['left','right','top','bottom'])
     assert.ok(subject[edge]>=-.1,`Subject ${subject.id} stays inside ${edge}: ${subject[edge]}`);
 };
 await checkSubjectClearance();
 await page.locator('.jar-select').nth(3).hover();
 await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 await checkSubjectClearance();
 await page.screenshot({path:'tmp/site-qa/jars-central-fit.png'});
 // Matched stage captures use the real PR-base generator, not a CSS mock.
 const baseMetadata=path.join(__dirname,'../tmp/site/bounds-before/source.json');
 if(fs.existsSync(baseMetadata)){
   const comparison=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
   await comparison.addInitScript(()=>{Math.random=()=>.5;});
   const compare=await comparison.newPage();
   for(const [label,route] of [['before','jars-before/index.html'],['after',process.env.JAR_PAGE||'jars.html']]){
     await compare.goto(new URL(route,process.env.SITE_URL||'http://127.0.0.1:8000/').href);
     await compare.waitForSelector('body[data-jars-ready=true]');
     await compare.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
     await compare.evaluate(()=>document.fonts.ready);
     await compare.locator('.jar-stage').screenshot({path:`tmp/site-qa/jars-fit-${label}.png`});
   }
   fs.writeFileSync('tmp/site-qa/jars-fit-comparison.json',JSON.stringify({
     ...JSON.parse(fs.readFileSync(baseMetadata)),headSha:process.env.PR_HEAD_SHA||null,
     viewport:{width:1440,height:1000},crop:'.jar-stage',reducedMotion:true,
     limitation:'Central cylinder cannot fill vertically without cropping or distorting the full OpenObserve ribbons.'
   },null,2));
   await comparison.close();
 }
 // Exercise both horizontal motion extremes with idle translation at its peak.
 for(const [x,label] of [[33,'left'],[1406,'right']]){
   await first.focus();
   await page.mouse.move(x,200);
   await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
   await page.locator('.specimen-idle').evaluateAll((nodes,phase)=>nodes.forEach(n=>{
     for(const a of n.getAnimations()){a.pause();a.currentTime=a.effect.getTiming().delay+a.effect.getTiming().duration*phase;}
   }),label==='left'?.16:.08);
   await checkSubjectClearance();
   await page.screenshot({path:`tmp/site-qa/jars-fit-motion-${label}.png`});
 }

 await first.hover({position:{x:45,y:55}});
 await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');

 // Vertical pointer movement must leave the camera unchanged.
 const before=await page.locator('.vessel').first().evaluate(n=>{const r=n.getBoundingClientRect();return [r.x,r.y,r.width,r.height];});
 await first.hover({position:{x:45,y:150}});await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.deepEqual(await page.locator('.vessel').first().evaluate(n=>{const r=n.getBoundingClientRect();return [r.x,r.y,r.width,r.height];}),before);
 for(const index of [4,5,6]) assert.equal(await page.locator('.jar-exhibit').nth(index).locator('.callout-function').evaluate(n=>getComputedStyle(n).textAlign),'right');
 // Regression: focus can remain on jar 3 while the pointer selects jar 2.
 // These must not share a stacking level, or the later vessel paints over
 // jar 2's Inspect record label. Vessels ignore pointer events, so hit-testing
 // the link alone cannot prove it is visually unobscured.
 const secondJar=page.locator('.jar-exhibit').nth(1),thirdJar=page.locator('.jar-exhibit').nth(2);
 await thirdJar.locator('.jar-select').focus();
 await secondJar.locator('.jar-select').hover({position:{x:45,y:55}});
 await page.waitForFunction(()=>document.querySelectorAll('.jar-exhibit')[1].classList.contains('is-active'));
 await page.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 assert.ok(await thirdJar.evaluate(n=>n.matches(':focus-within')),'Jar 3 retains keyboard focus');
 const secondZ=await secondJar.evaluate(n=>Number(getComputedStyle(n).zIndex));
 const thirdZ=await thirdJar.evaluate(n=>Number(getComputedStyle(n).zIndex));
 assert.ok(secondZ>thirdZ,'Active jar 2 and its label paint above focused jar 3');
 await secondJar.locator('[data-jar-inspect]').hover();
 assert.ok(await secondJar.evaluate(n=>n.classList.contains('is-active')),'Inspect label retains its selected jar');
 await page.screenshot({path:'tmp/site-qa/jar-2-inspect-over-focused-jar-3.png'});
 // Keyboard selection retains the small lift and illumination at a fixed size.
 await page.mouse.move(1400,950);await page.locator('.jar-central .jar-select').focus();
 await page.waitForFunction(()=>parseFloat(document.querySelector('.jar-central').style.getPropertyValue('--my'))<-2.9);
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
 await page.goto(url);await ready();
 // Match the searchable content contract independently of the UI filter.
 const searchData=await page.locator('#catalog-data').evaluate(n=>JSON.parse(n.textContent));
 const expectedSearchIds=searchData.projects.filter(project=>[
   project.name,project.description,...(project.alternatives||[]).map(item=>item.name)
 ].join(' ').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes('opentofu'))
   .map(project=>project.id).sort();
 const openTofu=searchData.projects.find(project=>project.name==='OpenTofu');
 assert.ok(openTofu,'The search fixture includes OpenTofu');
 assert.ok(expectedSearchIds.includes(openTofu.id),'OpenTofu must match its own name');
 await page.locator('#search').fill('OpenTofu');await page.locator('.search-submit').click();
 await page.waitForFunction(expected=>JSON.stringify(Array.from(document.querySelectorAll('.project-card:not([hidden])'),card=>card.dataset.projectId).sort())===JSON.stringify(expected),expectedSearchIds);
 assert.deepEqual(await page.locator('.project-card:visible').evaluateAll(cards=>cards.map(card=>card.dataset.projectId).sort()),expectedSearchIds);
 const selectedJar=page.locator('.jar-exhibit').first();
 const selectedId=await selectedJar.getAttribute('data-project');
 await selectedJar.locator('.jar-select').focus();await selectedJar.locator('.jar-annotation a').click();
 assert.ok(await page.locator('#project-'+selectedId+' > details').evaluate(n=>n.open));
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto(url);await ready();await first.focus();assert.equal(await first.getAttribute('aria-expanded'),'true');
 assert.equal(await page.locator('.specimen-idle').first().evaluate(n=>getComputedStyle(n).animationName),'none');assert.equal(await page.locator('.jar-steam').first().isVisible(),false);
 await page.keyboard.press('Escape');assert.equal(await first.getAttribute('aria-expanded'),'false');
 await first.hover({position:{x:45,y:55}});assert.equal(await page.locator('.jar-exhibit').first().evaluate(n=>parseFloat(n.style.getPropertyValue('--mx'))||0),0);assert.equal(await page.locator('.vessel').first().evaluate(n=>getComputedStyle(n).transform.startsWith('matrix3d')),false);
 for(const width of [320,390,680,768,1024]){await page.setViewportSize({width,height:900});await page.goto(url);await ready();await fits(width);if(width===768)assert.equal(await page.locator('.jar-exhibit:visible').count(),5);}
 await checkSubjectClearance();
 await page.screenshot({path:'tmp/site-qa/jars-reduced-motion-fit.png'});
 const touch=await browser.newPage({viewport:{width:390,height:900},isMobile:true,hasTouch:true,reducedMotion:'reduce'});await touch.goto(url);await touch.waitForSelector('body[data-jars-ready=true]');
 await checkSubjectClearance(touch);
 await touch.locator('.jar-select').first().tap();assert.equal(await touch.locator('.jar-annotation:visible').count(),1);assert.equal(new URL(touch.url()).hash,'');assert.equal(await touch.locator('.jar-exhibit').first().getAttribute('data-cracks'),'1');
 await touch.screenshot({path:'tmp/site-qa/jars-mobile.png'});
 await touch.locator('.jar-scroll').evaluate(n=>n.scrollLeft=n.scrollWidth);await touch.locator('.jar-select').last().tap();assert.equal(await touch.locator('.jar-select').last().getAttribute('aria-expanded'),'true');
 await touch.locator('.jar-select').last().tap();assert.equal(await touch.locator('.jar-exhibit').last().getAttribute('data-cracks'),'2');await touch.locator('.jar-select').last().tap();assert.match(new URL(touch.url()).hash,/^#project-/);await touch.close();
 const mobileMotion=await browser.newPage({viewport:{width:390,height:900},isMobile:true,hasTouch:true});
 await mobileMotion.goto(url);await mobileMotion.waitForSelector('body[data-jars-ready=true]');
 await mobileMotion.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
 await mobileMotion.locator('.jar-select').first().tap();
 await mobileMotion.waitForFunction(()=>document.body.dataset.jarMotion==='settled');
 await checkSubjectClearance(mobileMotion);
 await mobileMotion.screenshot({path:'tmp/site-qa/jars-fit-mobile-motion.png'});
 await mobileMotion.close();
 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});await fallback.goto(url);assert.equal(await fallback.locator('.jar-annotation:visible').count(),7);assert.equal(await fallback.locator('[data-jar-inspect]').count(),7);await fallback.locator('.project-card summary').first().click();assert.ok(await fallback.locator('.project-card details').first().evaluate(n=>n.open));await fallback.close();
 // Resource/visual evidence at real device densities. New contexts avoid cached
 // larger candidates influencing selection at a lower DPR. The control serves
 // original bytes for each derivative URL, keeping markup/layout identical.
 const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../site/jars/responsive.json')));
 // Weekly occupants may use full committed artwork before responsive
 // derivatives exist. Include those sources without weakening glass checks.
 const occupantSources=await page.locator('.specimen-print').evaluateAll(nodes=>nodes.map(n=>({
   path:n.closest('picture').querySelector('source[media="print"]').getAttribute('srcset'),
   width:Number(n.getAttribute('width')),height:Number(n.getAttribute('height'))})));
 for(const record of occupantSources)if(!manifest.sources[record.path])manifest.sources[record.path]={
   width:record.width,height:record.height,variants:[{path:record.path,width:record.width,height:record.height}]};
 const sources=Object.keys(manifest.sources);
 const byVariant=Object.fromEntries(sources.flatMap(source=>manifest.sources[source].variants.map(v=>[v.path,source])));
 const heroPaths=[...sources,...Object.keys(byVariant)];
 const heroPath=resourceURL=>{
   const pathname=new URL(resourceURL).pathname;
   return heroPaths.find(relative=>pathname.endsWith('/'+relative));
 };
 const payload=[];
 const noJavaScript=[];
 for(const dpr of [1,2,3]){
   const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:900},deviceScaleFactor:dpr});
   const probe=await context.newPage(),requested=new Set();
   probe.on('request',request=>{if(heroPath(request.url()))requested.add(request.url());});
   await probe.goto(url);
   await probe.locator('.jar-photo,.jar-reflection,.jar-lid,.jar-sticker,.jar-cork,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
   assert.equal(await probe.locator('.jar-annotation:visible').count(),7,'No-JS annotations at '+dpr+'x');
   assert.equal(await probe.locator('[data-jar-inspect]').count(),7,'No-JS record links at '+dpr+'x');
   const heights=await probe.locator('.vessel').evaluateAll(nodes=>nodes.map(n=>parseFloat(getComputedStyle(n).height)));
   assert.ok(heights.every(height=>height===300),'No-JS vessels remain 300 CSS pixels at '+dpr+'x');
   const images=await probe.locator('.jar-photo,.jar-reflection,.jar-lid,.jar-sticker,.jar-cork,.specimen-print').evaluateAll(nodes=>nodes.map(n=>({
     currentSrc:n.currentSrc,cssWidth:n.getBoundingClientRect().width,sizes:parseFloat(n.sizes),complete:n.complete})));
   for(const image of images){
     const relative=heroPath(image.currentSrc),source=byVariant[relative];
     assert.ok(source&&image.complete,'No-JS screen uses complete responsive images at '+dpr+'x');
     const selected=manifest.sources[source].variants.find(variant=>variant.path===relative);
     assert.ok(image.sizes>=image.cssWidth,'No-JS sizes covers rendered width at '+dpr+'x');
     assert.ok(selected.width>=Math.min(image.cssWidth*dpr,manifest.sources[source].width),'No-JS selected candidate covers device pixels at '+dpr+'x');
   }
   // Native lazy loading is disabled with JS off: the full-size specimen
   // images in evidence drawers may load too. Hero currentSrc was checked
   // above; original glass has no separate detail use and must not download.
   const duplicateGlass=[...requested].filter(resource=>{const relative=heroPath(resource);return !byVariant[relative]&&relative.startsWith('jars/');});
   assert.deepEqual(duplicateGlass,[],'No original glass downloads without JavaScript at '+dpr+'x');
   noJavaScript.push({deviceScaleFactor:dpr,vesselHeights:heights,images,requestedHeroURLs:[...requested]});
   await context.close();
 }
 for(const [label,width,dpr] of [['desktop-1x',1440,1],['desktop-1.5x',1440,1.5],['desktop-2x',1440,2],['mobile-3x',390,3]]){
   for(const control of [false,true]){
     const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:dpr,reducedMotion:'reduce'});
     // Jar lighting and steam glyphs are shuffled on startup. Pin only this
     // visual-comparison context so original/variant captures are comparable.
     await context.addInitScript(()=>{Math.random=()=>0.5;});
     if(control)await context.route('**/jars/responsive/*.webp',route=>{
       const relative=new URL(route.request().url()).pathname.split('/jars/')[1];
       const source=byVariant['jars/'+relative];
       assert.ok(source,'Every control route resolves to an original');
       return route.fulfill({contentType:'image/webp',body:fs.readFileSync(path.join(__dirname,'../site',source))});
     });
     const probe=await context.newPage(),requested=new Set();
     probe.on('request',request=>{if(heroPath(request.url()))requested.add(request.url());});
     await probe.goto(url);await probe.waitForSelector('body[data-jars-ready=true]');
     await probe.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
     await probe.evaluate(()=>document.fonts.ready);
     await probe.locator('.jar-select').first().focus();
     await probe.waitForTimeout(700); // Include the now-visible underlight mask.
     await probe.screenshot({path:`tmp/site-qa/hero-${label}-${control?'original':'responsive'}.png`});
     if(!control){
       const images=await probe.locator('.jar-photo,.jar-reflection,.jar-lid,.jar-sticker,.jar-cork,.specimen-print').evaluateAll(nodes=>nodes.map(n=>({
         class:n.className,currentSrc:new URL(n.currentSrc).pathname,cssWidth:n.getBoundingClientRect().width,
         sizes:n.sizes,naturalWidth:n.naturalWidth,complete:n.complete})));
       assert.ok(images.every(i=>i.complete&&(i.currentSrc.includes('/jars/responsive/')||(i.class==='specimen-print'&&occupantSources.some(s=>i.currentSrc.endsWith('/'+s.path))))),'Screen uses responsive images at '+label);
       const resources=await probe.evaluate(()=>performance.getEntriesByType('resource').map(r=>({path:new URL(r.name).pathname,bytes:r.decodedBodySize})));
       const heroResources=resources.filter(r=>r.path.includes('/jars/responsive/')||sources.some(s=>r.path.endsWith('/'+s)));
       const selected=new Set(images.map(i=>i.currentSrc));
       assert.ok(heroResources.every(r=>selected.has(r.path)),'Masks reuse selected image candidates, no original/extra hero download at '+label);
       const requestedHeroURLs=[...requested];
       assert.deepEqual(requestedHeroURLs.filter(resource=>!selected.has(new URL(resource).pathname)),[],
         'All requested masks reuse selected candidates, including unfinished downloads at '+label);
       const selectedResourceBytes=requestedHeroURLs.reduce((sum,resource)=>
         sum+fs.statSync(path.join(__dirname,'../site',heroPath(resource))).size,0);
       payload.push({label,deviceScaleFactor:dpr,images,resources:heroResources,requestedHeroURLs,
         selectedResourceBytes,byteMeaning:'On-disk bytes of unique requested hero URLs; not measured network transfer bytes'});
       // Print must switch all hero layers back to original, unmodified artwork.
       await probe.emulateMedia({media:'print'});
       await probe.waitForFunction(()=>[...document.querySelectorAll('.jar-photo,.jar-reflection,.jar-lid,.jar-sticker,.jar-cork,.specimen-print')].every(n=>n.currentSrc&&!n.currentSrc.includes('/responsive/')));
       await probe.locator('.jar-photo,.specimen-print').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
       assert.ok(await probe.locator('.jar-photo,.jar-reflection,.jar-lid,.jar-sticker,.jar-cork,.specimen-print').evaluateAll(nodes=>nodes.every(n=>!n.currentSrc.includes('/responsive/'))));
     }
     await context.close();
   }
 }
 fs.writeFileSync('tmp/site-qa/hero-payload.json',JSON.stringify({prHeadSha:process.env.PR_HEAD_SHA||null,sourceSha:process.env.SITE_SOURCE_SHA||null,originalHeroBytes:sources.reduce((sum,s)=>sum+fs.statSync(path.join(__dirname,'../site',s)).size,0),cases:payload,noJavaScript},null,2)+'\n');
 assert.deepEqual(errors,[]);console.log('Seven jars: assets, hover overlap, fixed-size translation parallax, pixel-snapped settling, vertical stability, underlight, lid lift, vapor, idle movement/pause, outlined inspect action, record links, search, keyboard/Escape, reduced motion, responsive density, touch selection/scroll and no-JS pass.');
 }catch(e){await page.screenshot({path:'tmp/site-qa/jars-failure.png'});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
