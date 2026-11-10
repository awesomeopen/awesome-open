/* Scores the WebMCPlet Markdown importer against open-source-mac-os-apps' own JSON.
 *
 * node scripts/score_webmcplet_importer.cjs <list.json from README.md> <applications.json> <categories.json> [--json]
 *
 * Use README.md, applications.json and categories.json from one commit of
 * https://github.com/serhii-londar/open-source-mac-os-apps (CC0-1.0).
 */
'use strict';
const fs = require('node:fs');
const { normalizeUrl } = require('../webmcplet/webmcplet.js');
const { plain } = require('../webmcplet/markdown.js');

const [listPath, appsPath, categoriesPath] = process.argv.slice(2).filter(a => !a.startsWith('--'));
if (!categoriesPath) { console.error('Usage: score_webmcplet_importer.cjs list.json applications.json categories.json [--json]'); process.exit(1); }
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const list = read(listPath), apps = read(appsPath).applications, categories = read(categoriesPath).categories;
const key = text => String(text || '').normalize('NFKC').replace(/\s+/g, ' ').trim();
const fold = text => key(text).toLowerCase();

// The JSON's identities, merged on normalized repository URL like the importer.
const titleOf = new Map(categories.map(c => [c.id, c.title]));
const expected = new Map();
for (const app of apps) {
  const id = normalizeUrl(app.repo_url.trim());
  const sections = new Set((app.categories || []).map(c => fold(titleOf.get(c) || c)));
  if (expected.has(id)) { const entry = expected.get(id); sections.forEach(s => entry.sections.add(s)); entry.titles.add(key(app.title)); continue; }
  expected.set(id, { titles: new Set([key(app.title)]), description: key(plain(app.short_description || '')), sections });
}
const sectionTitle = new Map(list.sections.map(s => [s.id, fold(s.title)]));
const imported = new Map(list.items.map(item => [item.id, item]));

const matched = [...expected.keys()].filter(id => imported.has(id));
const missed = [...expected.keys()].filter(id => !imported.has(id));
const extra = [...imported.keys()].filter(id => !expected.has(id));
const same = test => matched.filter(id => test(expected.get(id), imported.get(id))).length;
const names = same((want, got) => want.titles.has(key(got.name)));
// Descriptions compare as plain text: the JSON keeps inline Markdown such as links.
const descriptions = same((want, got) => want.description === key(got.description));
const sections = same((want, got) => {
  const have = new Set(got.sections.map(s => sectionTitle.get(s)));
  return have.size === want.sections.size && [...want.sections].every(s => have.has(s));
});

const report = {
  source_revision: list.list.source_revision || null,
  json_items: expected.size, imported_items: imported.size,
  matched: matched.length, recall: matched.length / expected.size, precision: matched.length / imported.size,
  names_equal: names, descriptions_equal: descriptions, sections_equal: sections,
  missed, extra
};
if (process.argv.includes('--json')) { console.log(JSON.stringify(report, null, 1)); process.exit(0); }
const pct = n => (100 * n).toFixed(1) + '%';
console.log(`Items: ${matched.length} of ${expected.size} JSON items found (recall ${pct(report.recall)}); ` +
  `${extra.length} of ${imported.size} imported items absent from the JSON (precision ${pct(report.precision)}).`);
console.log(`Of ${matched.length} matched items: names equal ${names}, descriptions equal ${descriptions}, section sets equal ${sections}.`);
if (missed.length) console.log('In the JSON, not imported: ' + missed.join(', '));
if (extra.length) console.log('Imported, not in the JSON: ' + extra.join(', '));
