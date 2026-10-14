const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({reducedMotion:'reduce'});
 for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:1100});
  await page.goto((process.env.SITE_URL||'http://127.0.0.1:8000')+'/specimen-comparison.html');
  await page.locator('.plate-art img').evaluate(n=>n.decode());
  const before=await page.locator('.plate-art').boundingBox();
  for(const variant of ['field','rule']){
   await page.locator('#treatment-'+variant).check();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.deepEqual(await page.locator('.plate-art').boundingBox(),before,'Switch preserves artwork geometry');
   const detail=await page.locator('.plate-detail-crop').boundingBox();
   assert.ok(detail.width<=104&&detail.height<=104,'Detail remains small');
   assert.equal(await page.locator('.feature-source').count(),1);
   assert.ok(await page.locator('.plate-art img').evaluate(n=>getComputedStyle(n).clipPath.includes('pod-contour')));
   await page.screenshot({path:`tmp/site-qa/comparison-${variant}-${width}.png`,fullPage:true});
  }
 }
 await page.locator('#treatment-field').focus();
 await page.keyboard.press('ArrowRight');
 assert.equal(await page.locator('#treatment-rule').isChecked(),true);
 await browser.close();
 console.log('Specimen comparison checks passed');
})().catch(e=>{console.error(e);process.exit(1)});
