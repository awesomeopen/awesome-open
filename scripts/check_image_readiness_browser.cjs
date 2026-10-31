/* Regression controls for responsive-image readiness; no production asset edits. */
const assert = require('node:assert/strict');
const { waitForImageReady } = require('./check_specimen_bounds_browser.cjs');

module.exports = async function checkImageReadiness({ browser, context, url }) {
  const root = new URL('__image-readiness__/', url + '/').href;
  const svg = width => '<svg xmlns="http://www.w3.org/2000/svg" width="' + width +
    '" height="' + width + '"><rect width="100%" height="100%" fill="navy"/></svg>';
  const install = target => target.route('**/__image-readiness__/*', route => {
    const name = new URL(route.request().url()).pathname.split('/').at(-1);
    return route.fulfill({ contentType: 'image/svg+xml',
      body: name === 'broken.svg' ? 'not an image' : svg(name === 'small.svg' ? 512 : 768) });
  });
  const markup = '<img style="width:min(100vw,627px)" src="' + root + 'large.svg" srcset="' +
    root + 'small.svg 512w, ' + root + 'large.svg 768w" sizes="(max-width:660px) 100vw, 627px">';
  const page = await context.newPage();
  try {
    await install(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.setContent(markup);
    const small = await waitForImageReady(page, 'img');
    assert.ok(small.currentSrc.endsWith('/small.svg'));
    await page.setViewportSize({ width: 1440, height: 1000 });
    const large = await waitForImageReady(page, 'img');
    assert.ok(large.currentSrc.endsWith('/large.svg'), 'Upsizing selects and decodes the larger candidate');
    // Deterministically reproduce a request replacement during decode. The
    // replacement still uses native decode, rather than a fabricated success.
    await page.locator('img').evaluate((image, next) => {
      const nativeDecode = image.decode.bind(image);
      let first = true;
      image.decode = () => {
        if (first) {
          first = false; image.removeAttribute('srcset'); image.src = next;
          return Promise.reject(new DOMException('fixture request replaced', 'EncodingError'));
        }
        return nativeDecode();
      };
    }, root + 'replacement.svg');
    const replaced = await waitForImageReady(page, 'img');
    assert.ok(replaced.currentSrc.endsWith('/replacement.svg'));
    await page.setContent('<img src="' + root + 'broken.svg">');
    await assert.rejects(waitForImageReady(page, 'img'), /image is broken/);
    await page.setContent('<img src="' + root + 'large.svg">');
    await waitForImageReady(page, 'img');
    await page.locator('img').evaluate(image => { image.decode = () => new Promise(() => {}); });
    await assert.rejects(waitForImageReady(page, 'img', { timeoutMs: 150 }), /timed out/);
  } finally { await page.close(); }
  const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const staticPage = await noJS.newPage();
    await install(staticPage);
    await staticPage.setContent(markup);
    const ready = await waitForImageReady(staticPage, 'img');
    assert.ok(ready.currentSrc.endsWith('/small.svg'), 'Node polling works without page JavaScript');
  } finally { await noJS.close(); }
  return { responsiveUpsize: true, replacedDecode: true, brokenImageFails: true,
    stalledDecodeBounded: true, noJavaScript: true };
};
