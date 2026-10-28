/* Offline checks for browser readiness, independent of layout correctness. */
const assert = require('node:assert/strict');
const { test, beforeEach, afterEach } = require('node:test');
const { stableLayoutSample, assertGeometry } = require('./check_specimen_bounds_browser.cjs');
let image, leader, rect, plate;
beforeEach(() => {
  rect = { left: 0, top: 0, width: 627, height: 627 };
  image = { complete: true, naturalWidth: 1254, currentSrc: 'specimen.webp' };
  leader = { innerHTML: '<circle cy="500"/>' };
  plate = {
    querySelector: selector => selector === '.plate-art img' ? image : leader,
    querySelectorAll: () => [{ getBoundingClientRect: () => rect }],
  };
  global.document = { querySelector: () => plate, fonts: { status: 'loaded' } };
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
