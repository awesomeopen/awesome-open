'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const observatory = require('./observatory.js');

const AS_OF = '2026-10-13';
function dateAgo(days) {
  return new Date(Date.parse(AS_OF + 'T00:00:00Z') - days * 86400000).toISOString();
}
function project(overrides = {}) {
  return { id: 'p1', name: 'Open One', url: 'https://example.org/one', categories: ['one'], github: true, stars: 0, license: null, created_at: null, pushed_at: null, release_at: null, release_status: 'not checked', release_checked_at: null, ...overrides };
}
function index(projects) {
  return { schema_version: 1, metrics_as_of: AS_OF, source_sha: '123456789abcdef', categories: [{ id: 'one', name: 'One' }, { id: 'two', name: 'Two' }], projects };
}

test('strict ISO dates reject impossible days, invalid suffixes, and invalid times', () => {
  for (const value of [null, '', '0000-01-01', '0001-01-01T00:00:00+01:00', '9999-12-31T23:30:00-02:00', '2026-2-01', '2026-02-30', '2025-02-29', '2026-13-01', '2026-00-01', '2026-01-00', '2026-10-13garbage', '2026-10-13T99:00:00Z', '2026-10-13T12:60:00Z', '2026-10-13T12:00:99Z', '2026-10-13T12:00:00']) {
    assert.equal(observatory.isoDay(value), null, String(value));
  }
  assert.notEqual(observatory.isoDay('2024-02-29'), null);
  assert.equal(observatory.isoDay(AS_OF + 'T23:59:59.999Z'), observatory.isoDay(AS_OF));
  assert.equal(observatory.isoDay(AS_OF + 'T00:00:00+00:00'), observatory.isoDay(AS_OF));
});

test('recency histograms use inclusive boundaries and explicit Unknown', () => {
  const ages = [0, 30, 31, 90, 91, 365, 366, 730, 731];
  const projects = ages.map(days => project({ pushed_at: dateAgo(days) }));
  projects.push(project({ pushed_at: dateAgo(-1) }), project(), project({ pushed_at: '2026-02-30' }));
  const rows = observatory.dateHistogram(projects, 'pushed_at', AS_OF, observatory.RECENCY_BOUNDS, observatory.RECENCY_LABELS);
  assert.deepEqual(rows.map(row => row.count), [2, 2, 2, 2, 1, 3]);
  assert.deepEqual(rows.map(row => row.label), observatory.RECENCY_LABELS);
  assert.equal(rows.reduce((sum, row) => sum + row.count, 0), projects.length);
});

test('timestamp offsets convert to UTC before snapshot-day bucketing', () => {
  const boundary = '2026-09-12T23:30:00-02:00';
  const sameDay = '2026-10-14T00:30:00+02:00';
  const futureUTC = '2026-10-13T23:30:00-02:00';
  assert.equal(observatory.isoDay(boundary), observatory.isoDay('2026-09-13'));
  assert.equal(observatory.isoDay(AS_OF) - observatory.isoDay(boundary), 30);
  assert.equal(observatory.isoDay(sameDay), observatory.isoDay(AS_OF));
  assert.equal(observatory.isoDay(futureUTC), observatory.isoDay('2026-10-14'));
  const rows = observatory.dateHistogram([boundary, sameDay, futureUTC].map(value => project({ pushed_at: value })), 'pushed_at', AS_OF, observatory.RECENCY_BOUNDS, observatory.RECENCY_LABELS);
  assert.deepEqual(rows.map(row => row.count), [2, 0, 0, 0, 0, 1]);
  for (const invalid of ['2026-02-30T23:30:00-02:00', '2026-10-13T00:00:00+24:00', '2026-10-13T00:00:00-02:60']) {
    assert.equal(observatory.isoDay(invalid), null, invalid);
  }
});

test('repository ages use 365, 1826 and 3653 day boundaries', () => {
  const projects = [0, 365, 366, 1826, 1827, 3653, 3654].map(days => project({ created_at: dateAgo(days) }));
  projects.push(project({ created_at: AS_OF + 'T23:59:59Z' }), project({ created_at: dateAgo(-1) }));
  const result = observatory.aggregate(index(projects));
  assert.deepEqual(result.age.map(row => row.count), [3, 2, 2, 1, 1]);
});

test('unknown snapshot date makes every date Unknown', () => {
  const rows = observatory.dateHistogram([project({ pushed_at: AS_OF })], 'pushed_at', 'unknown', observatory.RECENCY_BOUNDS, observatory.RECENCY_LABELS);
  assert.deepEqual(rows.map(row => row.count), [0, 0, 0, 0, 0, 1]);
});

test('filters normalize invalid and default values, and serialize only shareable keys', () => {
  const categories = index([]).categories;
  assert.deepEqual(observatory.readFilters('?category=one&license=known', categories), { category: 'one', license: 'known' });
  assert.deepEqual(observatory.readFilters('?category=missing&license=bogus&other=x', categories), { category: 'all', license: 'all' });
  assert.deepEqual(observatory.normalizeFilters({ category: '', license: '' }, categories), { category: 'all', license: 'all' });
  assert.equal(observatory.filterSearch({ category: 'all', license: 'all' }), '');
  assert.equal(observatory.filterSearch({ category: 'one', license: 'unknown' }), '?category=one&license=unknown');
});

test('category and license filters are an intersection, with no duplicated project totals', () => {
  const data = index([project({ categories: ['one', 'one', 'two'] }), project({ id: 'p2', categories: ['two'], license: 'MIT' }), project({ id: 'p3', categories: [], github: false, stars: null })]);
  const result = observatory.aggregate(data, { category: 'two', license: 'unknown' });
  assert.equal(result.metrics.total, 1);
  assert.deepEqual(result.categories.map(row => row.count), [1, 1]);
  assert.equal(observatory.aggregate(data).categories.at(-1).label, 'Unknown');
  assert.deepEqual(observatory.aggregate(data, { category: 'one', license: 'known' }).metrics, { total: 0, mapped: 0, stars: 0, 'known-license': 0 });
});

test('zero stars are observed, missing metrics are not, known licenses stay literal', () => {
  const data = index([project(), project({ id: 'p2', github: false, stars: null }), project({ id: 'p3', stars: 12, license: 'MIT' })]);
  const result = observatory.aggregate(data);
  assert.deepEqual(result.metrics, { total: 3, mapped: 2, stars: 12, 'known-license': 1 });
  assert.equal(result.concentration.topCount, 2);
  assert.deepEqual(result.licenses, [{ label: 'MIT', count: 1 }, { label: 'Unknown', count: 2 }]);
});

test('license counts sort by count then codepoint with Unknown always last', () => {
  const projects = ['MIT', 'GPL-3.0', 'BSD-3-Clause', 'MIT', null].map((license, i) => project({ id: String(i), license }));
  assert.deepEqual(observatory.licenseCounts(projects), [{ label: 'MIT', count: 2 }, { label: 'BSD-3-Clause', count: 1 }, { label: 'GPL-3.0', count: 1 }, { label: 'Unknown', count: 1 }]);
});

test('concentration is top ten in current selection and preserves the remaining total', () => {
  const projects = Array.from({ length: 12 }, (_, i) => project({ id: 'p' + i, name: 'Open ' + String(i).padStart(2, '0'), stars: 12 - i }));
  const result = observatory.starConcentration(projects);
  assert.equal(result.topCount, 10);
  assert.equal(result.total, 78);
  assert.equal(result.topTotal, 75);
  assert.deepEqual(result.rows.at(-1), { label: 'Other mapped projects', count: 3 });
  assert.equal(result.rows.reduce((sum, row) => sum + row.count, 0), 78);
  assert.equal(observatory.starConcentration([project()]).share, null);
  const tied = observatory.starConcentration([project({ id: 'b', name: 'Same' }), project({ id: 'a', name: 'Same' }), project({ id: 'z', name: 'Alpha' })]);
  assert.deepEqual(tied.rows.map(row => row.id), ['z', 'a', 'b']);
});

test('CSV guards formula injection and escapes quote, comma and newline syntax', () => {
  for (const value of ['=1+1', '+formula', '-formula', '@formula', '  =formula', '\tformula', '\rformula', '\nformula']) {
    assert.ok(observatory.csvCell(value).startsWith('"\''), value);
  }
  assert.equal(observatory.csvCell('ordinary,"quoted"'), '"ordinary,""quoted"""');
  assert.equal(observatory.csvCell(null), '""');
  assert.equal(observatory.csvCell(0), '"0"');
});

test('CSV selection retains schema, release cache state and provenance', () => {
  const data = index([project({ name: '=unsafe', release_status: 'stale', release_checked_at: '2026-10-12T12:00:00Z' }), project({ id: 'p2' })]);
  const csv = observatory.exportCSV(data, data.projects.slice(0, 1));
  assert.equal(csv.split('\r\n').length, 3);
  assert.ok(csv.startsWith(observatory.CSV_COLUMNS.map(observatory.csvCell).join(',')));
  assert.ok(csv.includes('"\'=unsafe"'));
  assert.ok(csv.includes('"true","0"'));
  assert.ok(csv.includes('"stale","2026-10-12T12:00:00Z","2026-10-13","123456789abcdef"'));
  assert.equal(observatory.exportCSV(data, []).split('\r\n').length, 2);
});

function sharedSummary(result) {
  const groups = kind => result[kind].map(group => ({ name: group.name, ids: group.projects.map(item => item.id), tags: group.tags }));
  return { identical: groups('identical'), variants: groups('variants'), tool_count: result.tool_count,
    identical_tool_count: result.identical_tool_count, variant_tool_count: result.variant_tool_count };
}

const EMPTY_SHARED = { identical: [], variants: [], tool_count: 0, identical_tool_count: 0, variant_tool_count: 0 };

test('shared names group identical pairs and three-way groups sorted by name and canonical ID', () => {
  const projects = [
    project({ id: 'z2', name: 'Zebra' }), project({ id: 'a3', name: 'Alpha' }),
    project({ id: 'z1', name: 'Zebra' }), project({ id: 'a1', name: 'Alpha' }),
    project({ id: 'a2', name: 'Alpha' }), project({ id: 'solo', name: 'Unique' })
  ];
  const before = JSON.stringify(projects);
  const result = observatory.sharedNames(projects);
  assert.deepEqual(sharedSummary(result), {
    identical: [{ name: 'Alpha', ids: ['a1', 'a2', 'a3'], tags: [] }, { name: 'Zebra', ids: ['z1', 'z2'], tags: [] }],
    variants: [], tool_count: 5, identical_tool_count: 5, variant_tool_count: 0
  });
  assert.deepEqual(result.identical[0].projects[0], projects[3]);
  assert.equal(JSON.stringify(projects), before);
  assert.deepEqual(observatory.sharedNames(projects.slice().reverse()), result);
});

test('shared names deduplicate canonical IDs across category occurrences', () => {
  const first = project({ id: 'a', name: 'Shared', categories: ['one', 'two'] });
  const repeated = project({ id: 'a', name: 'Shared', categories: ['two'] });
  assert.deepEqual(sharedSummary(observatory.sharedNames([first, repeated])), EMPTY_SHARED);
  assert.deepEqual(sharedSummary(observatory.sharedNames([first, repeated, project({ id: 'b', name: 'Shared' })])), {
    identical: [{ name: 'Shared', ids: ['a', 'b'], tags: [] }], variants: [], tool_count: 2, identical_tool_count: 2, variant_tool_count: 0
  });
});

test('one matching key combines case and separator differences with descriptive tags', () => {
  const pairs = [['a', 'OpenPilot'], ['b', 'openpilot'], ['c', 'Open pilot'], ['d', 'open-dashboard'], ['e', 'OpenDashboard'],
    ['f', 'Open_Tool'], ['g', 'Open Tool'], ['h', 'OpenBot'], ['i', 'OpenBot'], ['j', 'openbot']];
  const projects = pairs.map(([id, name]) => project({ id, name }));
  const result = observatory.sharedNames(projects);
  assert.deepEqual(sharedSummary(result), { identical: [], variants: [
    { name: 'Open Tool / Open_Tool', ids: ['g', 'f'], tags: ['Spacing'] },
    { name: 'Open pilot / OpenPilot / openpilot', ids: ['c', 'a', 'b'], tags: ['Case', 'Spacing'] },
    { name: 'OpenBot / openbot', ids: ['h', 'i', 'j'], tags: ['Case', 'Exact duplicates'] },
    { name: 'OpenDashboard / open-dashboard', ids: ['e', 'd'], tags: ['Case', 'Spacing'] }
  ], tool_count: 10, identical_tool_count: 0, variant_tool_count: 10 });
  assert.deepEqual(result.tags, { Case: 3, Spacing: 3, Plural: 0, Spelling: 0, 'Exact duplicates': 1 });
  assert.deepEqual(observatory.sharedNames(projects.slice().reverse()), result);
});

test('shared names do not infer aliases and ignore empty keys', () => {
  for (const names of [[], ['Tool'], ['Tool', 'Tool.', 'Tools', 'Tool OSS', 'T00l'], ['---', '_ _'], ['OpenTool', 'Open\u200bTool', 'Open\ufeffTool']]) {
    assert.deepEqual(sharedSummary(observatory.sharedNames(names.map((name, i) => project({ id: String(i), name })))), EMPTY_SHARED, names.join('|'));
  }
});

test('separators are exactly Unicode White_Space, hyphen and underscore across Python and JavaScript', () => {
  const separators = [9, 10, 11, 12, 13, 32, 0x85, 0xa0, 0x1680,
    ...Array.from({ length: 11 }, (_, i) => 0x2000 + i), 0x2028, 0x2029, 0x202f, 0x205f, 0x3000, 0x2d, 0x5f];
  for (const codepoint of separators) {
    const result = observatory.sharedNames([project({ id: 'a', name: 'OpenTool' }), project({ id: 'b', name: 'Open' + String.fromCodePoint(codepoint) + 'Tool' })]);
    assert.equal(result.variant_tool_count, 2, codepoint.toString(16));
    assert.deepEqual(result.variants[0].tags, ['Spacing']);
  }
  for (const codepoint of [0x1c, 0x1d, 0x1e, 0x1f, 0x180e, 0x200b, 0xfeff, 0x2e, 0x2010, 0x2013]) {
    const result = observatory.sharedNames([project({ id: 'a', name: 'OpenTool' }), project({ id: 'b', name: 'Open' + String.fromCodePoint(codepoint) + 'Tool' })]);
    assert.equal(result.tool_count, 0, codepoint.toString(16));
  }
});

test('shared-name aggregate follows the category and license intersection', () => {
  const data = index([
    project({ id: 'a', name: 'Shared', categories: ['one', 'two'], license: 'MIT' }),
    project({ id: 'b', name: 'Shared', categories: ['one'], license: 'MIT' }),
    project({ id: 'c', name: 'Shared', categories: ['two'], license: null }),
    project({ id: 'd', name: 'shared', categories: ['two'], license: null })
  ]);
  assert.deepEqual(sharedSummary(observatory.aggregate(data).sharedNames), {
    identical: [], variants: [{ name: 'Shared / shared', ids: ['a', 'b', 'c', 'd'], tags: ['Case', 'Exact duplicates'] }],
    tool_count: 4, identical_tool_count: 0, variant_tool_count: 4
  });
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'one', license: 'known' }).sharedNames), {
    identical: [{ name: 'Shared', ids: ['a', 'b'], tags: [] }], variants: [], tool_count: 2, identical_tool_count: 2, variant_tool_count: 0
  });
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'two', license: 'unknown' }).sharedNames), {
    identical: [], variants: [{ name: 'Shared / shared', ids: ['c', 'd'], tags: ['Case'] }], tool_count: 2, identical_tool_count: 0, variant_tool_count: 2
  });
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'one', license: 'unknown' }).sharedNames), EMPTY_SHARED);
});

test('shared names sort Unicode code points consistently with the static renderer', () => {
  const bmp = '\ue000';
  const supplementary = '\u{10000}';
  const projects = [
    project({ id: 'a2', name: supplementary }), project({ id: 'b2', name: bmp }),
    project({ id: 'a1', name: supplementary }), project({ id: 'b1', name: bmp }),
    project({ id: supplementary, name: 'Tie' }), project({ id: bmp, name: 'Tie' }),
    project({ id: 'case-a2', name: supplementary + 'a' }), project({ id: 'case-b2', name: bmp + 'a' }),
    project({ id: 'case-a1', name: supplementary + 'A' }), project({ id: 'case-b1', name: bmp + 'A' })
  ];
  assert.deepEqual(sharedSummary(observatory.sharedNames(projects)), {
    identical: [{ name: 'Tie', ids: [bmp, supplementary], tags: [] }, { name: bmp, ids: ['b1', 'b2'], tags: [] }, { name: supplementary, ids: ['a1', 'a2'], tags: [] }],
    variants: [
      { name: bmp + 'A / ' + bmp + 'a', ids: ['case-b1', 'case-b2'], tags: ['Case'] },
      { name: supplementary + 'A / ' + supplementary + 'a', ids: ['case-a1', 'case-a2'], tags: ['Case'] }
    ],
    tool_count: 10, identical_tool_count: 6, variant_tool_count: 4
  });
});

test('categories sort by count with stable catalog ties; push and release share one maximum', () => {
  const data = index([project({ id: 'a', categories: ['two'], pushed_at: dateAgo(1) }), project({ id: 'b', categories: ['two', 'one'], release_at: dateAgo(1) }), project({ id: 'c', categories: ['two'], release_at: dateAgo(2) })]);
  const result = observatory.aggregate(data);
  assert.deepEqual(result.categories.map(row => row.label), ['Two', 'One']);
  assert.equal(result.recencyMaximum, Math.max(...result.push.concat(result.release).map(row => row.count)));
  assert.equal(result.recencyMaximum, 2);
  assert.ok(observatory.CSV_COLUMNS.indexOf('description') === 3);
});

test('all unknown star counts remain unknown; observed zero stays zero', () => {
  assert.equal(observatory.aggregate(index([project({ github: false, stars: null, metrics_status: 'unavailable' })])).metrics.stars, null);
  assert.equal(observatory.aggregate(index([project({ stars: 0, metrics_status: 'stale', metrics_last_success_at: '2026-10-07' })])).metrics.stars, 0);
  const data = index([project({ metrics_status: 'stale', metrics_last_success_at: '2026-10-07', metrics_attempt_at: '2026-10-14T01:00:00Z', metrics_attempt_status: 'unavailable', metrics_attempt_http_status: 404, metrics_attempt_reason: 'repository_unavailable' })]);
  const csv = observatory.exportCSV(data, data.projects);
  assert.ok(csv.includes('"stale","2026-10-07","2026-10-14T01:00:00Z","unavailable","404","repository_unavailable"'));
});


test('comparison plates retain cache status and successful observation date', () => {
  assert.equal(observatory.metricsCacheLabel({ metrics_status: 'stale', metrics_last_success_at: '2026-10-07' }), 'stale · observed 2026-10-07 UTC');
  assert.equal(observatory.metricsCacheLabel({ metrics_status: 'unavailable', metrics_last_success_at: null }), 'unavailable · no successful observation');
});

test('shared search aliases never create Observatory display-name groups', () => {
  const rows = [project({id:'obs', name:'OBS Studio', aliases:[{name:'OBS'}]}),
    project({id:'build', name:'Open Build Service', aliases:[{name:'OBS'}]})];
  assert.deepEqual(sharedSummary(observatory.sharedNames(rows)), EMPTY_SHARED);
  const without = rows.map(({aliases, ...row}) => row);
  assert.deepEqual(observatory.sharedNames(rows), observatory.sharedNames(without));
});

function rhymingProject(id, name, key, onset, overrides = {}) {
  return project({ id, name, rhyme: { key, onset, pronunciation: '/' + onset + key + '/', language: 'en-US' }, ...overrides });
}

test('reviewed rhymes use distinct identities, names and onsets without changing shared names', () => {
  const chat = rhymingProject('chat', 'OpenChat', 'AE1 T', 'tʃ');
  const rows = [chat, chat, rhymingProject('cat', 'OpenCat', 'AE1 T', 'k'), rhymingProject('vat', 'OpenVat', 'AE1 T', 'v'),
    rhymingProject('shell', 'OpenShell', 'EH1 L', 'ʃ'), rhymingProject('spell', 'OpenSpell', 'EH1 L', 'sp'),
    rhymingProject('bell', 'Openbell', 'EH1 L', 'b'), project({ id: 'unreviewed', name: 'OpenMat' })];
  const result = observatory.rhymingNames(rows);
  assert.equal(result.tool_count, 6);
  assert.equal(result.reviewed_count, 6);
  assert.deepEqual(result.groups.map(group => group.key), ['AE1 T', 'EH1 L']);
  assert.deepEqual(result.groups.map(group => group.projects.map(row => row.id)), [['cat', 'chat', 'vat'], ['shell', 'spell', 'bell']]);
  assert.deepEqual(observatory.rhymingNames(rows.slice().reverse()), result);
  assert.equal(observatory.aggregate(index(rows)).sharedNames.tool_count, 0);
  assert.deepEqual(observatory.aggregate(index(rows)).rhymingNames, result);
});

test('duplicate-only, spelling-only, homophone-only and unreviewed matches are excluded', () => {
  for (const rows of [
    [rhymingProject('a', 'OpenCat', 'AE1 T', 'k'), rhymingProject('b', 'OpenCat', 'AE1 T', 'x')],
    [rhymingProject('a', 'OpenCat', 'AE1 T', 'k'), rhymingProject('b', 'Open-Cat', 'AE1 T', 'x')],
    [rhymingProject('a', 'OpenSee', 'ee', 's'), rhymingProject('b', 'OpenSea', 'ee', 's')],
    [rhymingProject('a', 'OpenCat', 'AE1 T', 'k'), project({ id: 'b', name: 'OpenChat' })],
    [rhymingProject('a', 'OpenCat', 'AE1 T', 'k'), rhymingProject('b', 'OpenChat', 'EH1 L', 'tʃ')],
  ]) assert.equal(observatory.rhymingNames(rows).tool_count, 0);
});

test('rhyme selection recomputes eligibility and coverage at fewer than two survivors', () => {
  const data = index([
    rhymingProject('cat', 'OpenCat', 'AE1 T', 'k', { categories: ['one', 'two'], license: 'MIT' }),
    rhymingProject('chat', 'OpenChat', 'AE1 T', 'tʃ', { categories: ['one'], license: 'MIT' }),
    rhymingProject('vat', 'OpenVat', 'AE1 T', 'v', { categories: ['two'] }),
  ]);
  assert.equal(observatory.aggregate(data).rhymingNames.tool_count, 3);
  assert.equal(observatory.aggregate(data, { category: 'one' }).rhymingNames.tool_count, 2);
  const one = observatory.aggregate(data, { category: 'two', license: 'known' }).rhymingNames;
  assert.deepEqual(one, { groups: [], tool_count: 0, reviewed_count: 1 });
  assert.deepEqual(observatory.aggregate(data, { category: 'one', license: 'unknown' }).rhymingNames,
    { groups: [], tool_count: 0, reviewed_count: 0 });
  assert.equal(observatory.aggregate(data).rhymingNames.tool_count, 3);
});

test('invalid rhyme annotations are not counted as reviewed and empty onsets remain valid', () => {
  const valid = rhymingProject('a', 'OpenAt', 'AE1 T', '');
  const cat = rhymingProject('b', 'OpenCat', 'AE1 T', 'k');
  const invalid = [null, {}, { ...cat.rhyme, language: 'other' }, { ...cat.rhyme, key: '' }, { ...cat.rhyme, onset: null }, { ...cat.rhyme, pronunciation: '' }];
  const rows = [valid, cat, ...invalid.map((rhyme, i) => project({ id: 'invalid-' + i, rhyme }))];
  assert.equal(observatory.rhymingNames(rows).reviewed_count, 2);
  assert.equal(observatory.rhymingNames(rows).tool_count, 2);
});

test('rhyme renderer keeps names as text, linked IDs, selected coverage and empty disclosure', () => {
  class Node {
    constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.textContent = ''; }
    append(...nodes) { this.children.push(...nodes); }
    appendChild(node) { this.children.push(node); return node; }
    replaceChildren(...nodes) { this.children = nodes; }
  }
  const ids = new Map(['rhyme-count', 'rhyme-group-summary', 'rhyme-group-list'].map(id => [id, new Node('div')]));
  const doc = { createElement: tag => new Node(tag), createDocumentFragment: () => new Node('fragment'), getElementById: id => ids.get(id) };
  const rows = [rhymingProject('cat', 'OpenCat', 'AE1 T', 'K'), rhymingProject('chat', '<OpenChat>', 'AE1 T', 'CH')];
  observatory.renderRhymingNames(doc, observatory.rhymingNames(rows));
  assert.equal(ids.get('rhyme-count').textContent, '2');
  assert.equal(ids.get('rhyme-group-summary').textContent, '1 groups · 2 reviewed readings');
  const group = ids.get('rhyme-group-list').children[0].children[0];
  assert.equal(group.dataset.rhymeKey, 'AE1 T');
  const links = group.children[1].children.map(item => item.children[0]);
  assert.deepEqual(links.map(link => [link.textContent, link.href]), [['<OpenChat>', '../#project-chat'], ['OpenCat', '../#project-cat']]);
  ids.get('rhyme-group-list').dataset.ledgerBase = 'https://awesomeopen.github.io/awesome-open/';
  observatory.renderRhymingNames(doc, observatory.rhymingNames(rows));
  const standalone = ids.get('rhyme-group-list').children[0].children[0].children[1].children[0].children[0];
  assert.equal(standalone.href, 'https://awesomeopen.github.io/awesome-open/#project-chat');
  observatory.renderRhymingNames(doc, observatory.rhymingNames(rows.slice(0, 1)));
  assert.equal(ids.get('rhyme-count').textContent, '0');
  assert.equal(ids.get('rhyme-group-summary').textContent, '0 groups · 1 reviewed readings');
  assert.equal(ids.get('rhyme-group-list').children[0].children[0].textContent, 'No reviewed rhyming names in this selection.');
});

test('reviewed plural pair stays in spelling variants and keeps distinct rhyme keys', () => {
  const rows = [project({ id: 'a', name: 'OpenTask' }), project({ id: 'b', name: 'OpenTasks' })];
  rows.forEach(row => { row.name_match = { key: 'reviewed:opentask-plural', reason: 'plural' }; });
  const result = observatory.sharedNames(rows.concat(rows[0]));
  assert.equal(result.tool_count, 2);
  assert.deepEqual(result.variants[0].tags, ['Plural']);
  assert.deepEqual(observatory.sharedNames(rows.slice().reverse()), result);
  assert.equal(observatory.sharedNames(rows.slice(0, 1)).tool_count, 0);
  assert.notEqual(observatory.nameKey('OpenTask'), observatory.nameKey('OpenTasks'));
  assert.deepEqual(observatory.sharedNames([project({id:'a',name:'Openİ'}),project({id:'b',name:'Openi\u0307'})]).variants[0].tags, ['Case']);
  const mixed = [project({ id:'a',name:'Open Task' }),project({ id:'b',name:'openTasks' })];
  mixed.forEach(row => { row.name_match = { key: 'reviewed:opentask-plural', reason: 'plural' }; });
  assert.deepEqual(observatory.sharedNames(mixed).variants[0].tags, ['Case','Spacing','Plural']);
  for (const names of [['OpenTool','OpenTools'],['OpenNew','OpenNews'],['OpenTask','OpenTasks.']]) {
    assert.equal(observatory.sharedNames(names.map((name,i) => project({id:String(i),name}))).tool_count, 0);
  }
});


test('reviewed spelling is explicit and unreviewed aliases never create current twins', () => {
  const rows = [project({id:'a',name:'Open Whisper'}), project({id:'b',name:'OpenWhispr'})];
  assert.equal(observatory.sharedNames(rows).tool_count, 0);
  rows.forEach(row => { row.name_match = { key: 'reviewed:whisper-spelling', reason: 'spelling' }; });
  assert.deepEqual(observatory.sharedNames(rows).variants[0].tags, ['Spacing', 'Spelling']);
  assert.deepEqual(observatory.sharedNames(rows.slice().reverse()), observatory.sharedNames(rows));
  const current = [project({id:'a',name:'Open Quill',aliases:['Open Whisper']}), project({id:'b',name:'OpenWhispr'})];
  assert.equal(observatory.sharedNames(current).tool_count, 0);
});

