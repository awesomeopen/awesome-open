/* Preload for per-process Playwright operation timings; no image bytes in logs. */
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { AsyncLocalStorage } = require('node:async_hooks');
const active = new AsyncLocalStorage();
const started = performance.now();
const rows = [];
const assertions = { count: 0, milliseconds: 0 };
const assert = require('node:assert/strict');
for (const name of ['ok', 'equal', 'notEqual', 'deepEqual', 'notDeepEqual', 'strictEqual', 'deepStrictEqual', 'match', 'throws', 'fail']) {
  const original = assert[name];
  assert[name] = function (...args) {
    const begin = performance.now();
    try { return original.apply(this, args); }
    finally { assertions.count++; assertions.milliseconds += performance.now() - begin; }
  };
}
const seen = new WeakSet();
function wrap(object, method, kind, transform) {
  const original = object[method];
  if (typeof original !== 'function') return;
  object[method] = async function (...args) {
    const parent = active.getStore();
    const begin = performance.now();
    try {
      const value = await active.run(true, () => original.apply(this, args));
      if (transform) transform(value);
      return value;
    } finally {
      if (!parent) rows.push({ kind, operation: method, milliseconds: +(performance.now() - begin).toFixed(3),
        ...(method === 'screenshot' ? { file: path.basename(args[0]?.path || 'buffer') } : {}) });
      save();
    }
  };
}
function instrument(page) {
  if (seen.has(page)) return;
  seen.add(page);
  wrap(page, 'screenshot', 'captureOperation');
  for (const name of ['goto', 'reload', 'goBack', 'goForward']) wrap(page, name, 'navigation');
  for (const name of ['waitForFunction', 'waitForSelector', 'waitForTimeout', 'waitForLoadState']) wrap(page, name, 'readiness');
}
const { chromium } = require('playwright');
wrap(chromium, 'launch', 'browserStartup', browser => {
  wrap(browser, 'newPage', 'pageSetup', instrument);
  wrap(browser, 'newContext', 'contextSetup', context => {
    context.on('page', instrument);
    wrap(context, 'newPage', 'pageSetup', instrument);
  });
});
function save() {
  if (!process.env.BROWSER_TIMING_FILE) return;
  const totals = {};
  for (const row of rows) totals[row.kind] = (totals[row.kind] || 0) + row.milliseconds;
  fs.writeFileSync(process.env.BROWSER_TIMING_FILE, JSON.stringify({
    sourceSha: process.env.SITE_SOURCE_SHA || null, suite: process.env.BROWSER_SUITE,
    elapsedMilliseconds: performance.now() - started, totals, assertions, operations: rows,
    meaning: 'Capture operation includes rendering, encoding, transfer and file writing. Readiness covers explicit page waits. Assertions measures synchronous node:assert calls, excluding awaited inputs. Remaining elapsed time includes locator operations, decode/font evaluation, report writes and teardown; it is not isolated assertion CPU time.'
  }, null, 2) + '\n');
}
process.on('exit', save);
