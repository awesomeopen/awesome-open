const test = require('node:test');
const assert = require('node:assert/strict');
const searchPath = require.resolve('./search.js');
const search = require('./search.js');
const id = c => c.repeat(64);
const projects = [
  { id: id('a'), name: 'Open Zebra', description: 'A video editor.', github: { stars: 5, license: 'MIT' } },
  { id: id('b'), name: 'Open Video Editor', description: 'Trims clips.', github: { stars: 1, license: 'NOASSERTION' } },
  { id: id('c'), name: 'Open Apple', description: 'Signage controller.', github: { stars: 900 } },
  { id: id('d'), name: 'Open Broadcaster', description: 'Obsolete recorder.', aliases: [{ name: 'OBS' }], github: null },
  { id: id('e'), name: 'Open Café', description: 'Menus.', alternatives: [{ name: 'Square Editor' }] },
];
const text = {
  [id('c')]: { summary: 'Plays video on screens.', features: ['Layout editor Arrange zones in the browser.'] },
  [id('e')]: { summary: 'Runs on a home server.', features: [] },
};
const names = (query, withText = text) => search.results(projects, query, withText).map(r => r.project.name);
const fields = (query, name) => search.results(projects, query, text).find(r => r.project.name === name).fields;

test('every word must appear, across any searched field', () => {
  assert.deepEqual(names('video editor'), ['Open Video Editor', 'Open Zebra', 'Open Apple']);
  assert.deepEqual(names('home server'), ['Open Café']);
  assert.deepEqual(names('manage family photos on my own server'), []);
});

test('match order ranks by the weakest field a word needed, then by name', () => {
  // Stars never reorder a search: Open Apple has the most and matches only in notes.
  assert.deepEqual(names('video'), ['Open Video Editor', 'Open Zebra', 'Open Apple']);
  assert.deepEqual(names('editor'), ['Open Video Editor', 'Open Zebra', 'Open Café', 'Open Apple']);
  assert.deepEqual(names('open'), ['Open Apple', 'Open Broadcaster', 'Open Café', 'Open Video Editor', 'Open Zebra']);
});

test('no query keeps the ledger star order, unknown stars last', () => {
  assert.deepEqual(names(''), ['Open Apple', 'Open Zebra', 'Open Video Editor', 'Open Broadcaster', 'Open Café']);
  assert.equal(search.find(projects, '  ', text), null);
});

test('results report every field that matched, strongest first', () => {
  assert.deepEqual(fields('video', 'Open Video Editor'), ['name']);
  assert.deepEqual(fields('video editor', 'Open Apple'), ['summary', 'feature']);
  assert.deepEqual(fields('editor', 'Open Café'), ['alternative']);
  assert.deepEqual(fields('obs', 'Open Broadcaster'), ['alias']);
  assert.deepEqual(search.results(projects, '', text)[0].fields, []);
});

test('reviewed short names use word boundaries in summaries and notes too', () => {
  const summary = { [id('c')]: { summary: 'Replaces obsolete players, and works with OBS.', features: [] },
    [id('e')]: { summary: 'Fixes obsolete menus.', features: [] } };
  assert.deepEqual(names('obs', summary), ['Open Broadcaster', 'Open Apple']);
  assert.deepEqual(names('obso', summary), ['Open Broadcaster', 'Open Apple', 'Open Café']);
});

test('accents fold and query syntax stays literal', () => {
  assert.deepEqual(names('cafe'), ['Open Café']);
  assert.deepEqual(names('CAFÉ'), ['Open Café']);
  assert.deepEqual(names('[.*]'), []);
});

test('without loaded text the same search covers the embedded fields', () => {
  assert.deepEqual(names('video editor', null), ['Open Video Editor', 'Open Zebra']);
});

test('unknown licenses and stars stay unknown, and zero stays zero', () => {
  assert.equal(search.licenseOf(projects[1]), '');
  assert.equal(search.licenseOf(projects[3]), '');
  assert.equal(search.starsOf(projects[3]), null);
  assert.equal(search.starsOf({ github: { stars: 0 } }), 0);
});

test('no match names this catalog', () => {
  assert.equal(search.noMatch(555), 'No match in this catalog of 555 Open*-named projects.');
});

function fresh() { delete require.cache[searchPath]; return require('./search.js'); }
function win(responses) {
  const calls = [];
  return { calls, location: { href: 'https://example.org/awesome/', origin: 'https://example.org' },
    fetch: async (url, options) => { calls.push({ url, options }); return responses.shift(); } };
}
const json = body => ({ ok: true, json: async () => body });

test('search text loads once per revision and rejects a mismatch or other origin', async () => {
  const good = win([json({ source_sha: 'abc', projects: text })]);
  const loader = fresh();
  const [first, second] = await Promise.all([loader.loadText(good, 'search-text.json?v=1', 'abc'), loader.loadText(good, 'search-text.json?v=1', 'abc')]);
  assert.equal(first, text); assert.equal(second, text);
  assert.equal(good.calls.length, 1);
  assert.equal(good.calls[0].url, 'https://example.org/awesome/search-text.json?v=1');
  assert.equal(good.calls[0].options.redirect, 'error');
  await assert.rejects(fresh().loadText(win([json({ source_sha: 'old', projects: text })]), 'search-text.json', 'abc'));
  await assert.rejects(fresh().loadText(win([json({ source_sha: 'abc', projects: null })]), 'search-text.json', 'abc'));
  await assert.rejects(fresh().loadText(win([]), 'https://evil.example/search-text.json', 'abc'));
});

test('a failed load clears so the next search retries', async () => {
  const loader = fresh();
  const target = win([{ ok: false }, json({ source_sha: '', projects: text })]);
  await assert.rejects(loader.loadText(target, 'search-text.json', ''));
  assert.equal(await loader.loadText(target, 'search-text.json', ''), text);
});
