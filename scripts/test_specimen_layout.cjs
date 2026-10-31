/* Offline checks for browser readiness, independent of layout correctness. */
const assert = require('node:assert/strict');
const { test, beforeEach, afterEach } = require('node:test');
const { stableLayoutSample, assertGeometry } = require('./check_specimen_bounds_browser.cjs');
let image, leader, rect, plate;
beforeEach(() => {
  rect = { left: 0, top: 0, width: 627, height: 627 };
  image = { complete: true, naturalWidth: 1254, naturalHeight: 1254, currentSrc: 'specimen.webp',
    getAttribute: name => name === 'src' ? image.currentSrc : null, decode: async () => {} };
  leader = { innerHTML: '<circle cy="500"/>' };
  plate = {
    querySelector: selector => selector === '.plate-art img' ? image : leader,
    querySelectorAll: () => [{ getBoundingClientRect: () => rect }],
  };
  global.document = { querySelector: selector => selector.endsWith('img') ? image : plate, fonts: { status: 'loaded' } };
  global.innerWidth = 1440;
  global.innerHeight = 1000;
});
afterEach(() => {
  delete global.document;
  delete global.innerWidth;
  delete global.innerHeight;
});
const sample = () => stableLayoutSample({ selector: '.specimen-plate' });
test('requires three consecutive rendered samples', () => {
  assert.equal(sample(), false); assert.equal(sample(), false); assert.equal(sample(), true);
});
test('image layout and connector updates each restart readiness', () => {
  sample(); sample(); rect.width = 320;
  assert.equal(sample(), false); sample(); leader.innerHTML = '<circle cy="300"/>';
  assert.equal(sample(), false); assert.equal(sample(), false); assert.equal(sample(), true);
});
test('each resize starts a fresh observation, even for a repeated width', () => {
  sample(); sample(); sample();
  stableLayoutSample({ selector: '.specimen-plate', reset: true });
  assert.equal(sample(), false);
  sample(); global.innerWidth = 901;
  assert.equal(sample(), false);
});
test('waits for image and fonts, resetting interrupted samples', () => {
  sample(); sample(); image.complete = false;
  assert.equal(sample(), false); image.complete = true;
  assert.equal(sample(), false); document.fonts.status = 'loading';
  assert.equal(sample(), false); document.fonts.status = 'loaded';
  assert.equal(sample(), false); assert.equal(sample(), false); assert.equal(sample(), true);
});
test('a stable incorrect SVG is ready, never silently repaired', () => {
  leader.innerHTML = '<circle cy="999"/>';
  sample(); sample(); assert.equal(sample(), true);
  assert.equal(leader.innerHTML, '<circle cy="999"/>');
});
test('unchanged geometry assertion rejects a misplaced leader', () => {
  const m = { bbox: [0, .1, 1, .9], image: { width: 100, height: 100, top: -2 },
    field: { width: 100, left: 0, top: 0, bottom: 96 },
    stage: { height: 96, left: 0, width: 100, top: 0 },
    label: { top: 56 }, labelFont: 10, naturalWidth: 100, naturalHeight: 100,
    studyTop: 0, leaderY: [91], pageFits: true, overflow: 'visible', terrain: null };
  assert.doesNotThrow(() => assertGeometry(m, 'valid'));
  assert.throws(() => assertGeometry({ ...m, leaderY: [111] }, 'wrong'), /leader follows subject baseline/);
});
test('no-JS readiness polls from Node without browser timers', async () => {
  const { waitForSpecimenLayout } = require('./check_specimen_bounds_browser.cjs');
  let samples = 0;
  const page = {
    locator: () => ({ evaluate: async () => undefined }),
    evaluate: async (fn, arg) => { if (fn === stableLayoutSample && arg && !arg.reset) samples++; return fn(arg); },
    waitForFunction: () => { throw new Error('No browser timer in no-JS context'); },
  };
  await waitForSpecimenLayout(page, '.specimen-plate', true);
  assert.equal(samples, 3);
  assert.equal(plate.__boundsReadiness, undefined);
});

const { waitForImageReady } = require('./check_specimen_bounds_browser.cjs');
const mockPage = (hook = () => {}) => ({
  evaluate: async (fn, arg) => { hook(fn, arg); return fn(arg); },
});
test('a changed source rejected during decode is decoded afresh', async () => {
  let calls = 0;
  image.decode = async () => {
    calls++;
    if (calls === 1) {
      image.currentSrc = 'replacement.webp';
      throw Object.assign(new Error('request replaced'), { name: 'EncodingError' });
    }
  };
  const ready = await waitForImageReady(mockPage(), '.plate-art img');
  assert.equal(ready.currentSrc, 'replacement.webp');
  assert.equal(calls, 2);
  assert.equal(image.__decodeReadiness, undefined);
});
test('unchanged source rejection is a hard failure, never retried', async () => {
  let calls = 0;
  image.decode = async () => { calls++; throw new Error('corrupt bytes'); };
  await assert.rejects(waitForImageReady(mockPage(), '.plate-art img'),
    error => /unchanged source/.test(error.message) && error.readiness.history.at(-1).status === 'rejected');
  assert.equal(calls, 1);
});
test('complete broken image fails without decode', async () => {
  image.naturalWidth = 0;
  image.decode = () => { throw new Error('must not decode broken image'); };
  await assert.rejects(waitForImageReady(mockPage(), '.plate-art img'), /image is broken/);
});
test('pending load and never-settling decode are bounded', async () => {
  image.complete = false;
  await assert.rejects(waitForImageReady(mockPage(), '.plate-art img', { timeoutMs: 60 }), /timed out/);
  image.complete = true;
  image.decode = () => new Promise(() => {});
  await assert.rejects(waitForImageReady(mockPage(), '.plate-art img', { timeoutMs: 100 }), /timed out/);
  assert.equal(image.__decodeReadiness, undefined);
});
test('changed source after decode during layout needs its own successful decode', async () => {
  let calls = 0, changed = false;
  image.decode = async () => { calls++; };
  const page = mockPage((fn, arg) => {
    if (fn === stableLayoutSample && !arg.reset && !changed) {
      image.currentSrc = 'new-layout.webp'; changed = true;
    }
  });
  await waitForImageReady(page, '.plate-art img', { layoutSelector: '.specimen-plate' });
  assert.equal(calls, 2);
  assert.equal(plate.__boundsReadiness, undefined);
});
test('source attributes invalidate readiness before currentSrc changes', async () => {
  let srcset = 'first.webp 1x', calls = 0;
  image.getAttribute = name => name === 'srcset' ? srcset : null;
  image.decode = async () => {
    calls++;
    if (calls === 1) { srcset = 'second.webp 1x'; throw new Error('candidate changed'); }
  };
  await waitForImageReady(mockPage(), '.plate-art img');
  assert.equal(calls, 2);
});
