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
  return {
    exact: result.exact.map(group => ({ name: group.name, ids: group.projects.map(item => item.id) })),
    capitalization: result.capitalization.map(group => ({ name: group.name, ids: group.projects.map(item => item.id) })),
    whitespace: result.whitespace.map(group => ({ name: group.name, ids: group.projects.map(item => item.id) })),
    exact_tool_count: result.exact_tool_count,
    whitespace_tool_count: result.whitespace_tool_count,
    tool_count: result.tool_count,
    capitalization_tool_count: result.capitalization_tool_count
  };
}

const EMPTY_SHARED = { exact: [], capitalization: [], whitespace: [], tool_count: 0, exact_tool_count: 0, capitalization_tool_count: 0, whitespace_tool_count: 0 };

test('shared names include exact pairs and three-way groups sorted by name and canonical ID', () => {
  const projects = [
    project({ id: 'z2', name: 'Zebra' }), project({ id: 'a3', name: 'Alpha' }),
    project({ id: 'z1', name: 'Zebra' }), project({ id: 'a1', name: 'Alpha' }),
    project({ id: 'a2', name: 'Alpha' }), project({ id: 'solo', name: 'Unique' })
  ];
  const before = JSON.stringify(projects);
  const result = observatory.sharedNames(projects);
  assert.deepEqual(sharedSummary(result), {
    exact: [{ name: 'Alpha', ids: ['a1', 'a2', 'a3'] }, { name: 'Zebra', ids: ['z1', 'z2'] }],
    capitalization: [], whitespace: [], tool_count: 5, exact_tool_count: 5, capitalization_tool_count: 0, whitespace_tool_count: 0
  });
  assert.deepEqual(result.exact[0].projects[0], projects[3]);
  assert.equal(JSON.stringify(projects), before);
  assert.deepEqual(observatory.sharedNames(projects.slice().reverse()), result);
});

test('shared names deduplicate canonical IDs across category occurrences', () => {
  const first = project({ id: 'a', name: 'Shared', categories: ['one', 'two'] });
  const repeated = project({ id: 'a', name: 'Shared', categories: ['two'] });
  assert.deepEqual(sharedSummary(observatory.sharedNames([first, repeated])), EMPTY_SHARED);
  const result = observatory.sharedNames([first, repeated, project({ id: 'b', name: 'Shared' })]);
  assert.deepEqual(sharedSummary(result), {
    exact: [{ name: 'Shared', ids: ['a', 'b'] }], capitalization: [], whitespace: [], tool_count: 2, exact_tool_count: 2, capitalization_tool_count: 0, whitespace_tool_count: 0
  });
});

test('case-only shared names stay separate from exact groups and use deterministic ordering', () => {
  const projects = [project({ id: 'b', name: 'alpha' }), project({ id: 'a', name: 'Alpha' }),
    project({ id: 'd', name: 'zebra' }), project({ id: 'c', name: 'ZEBRA' })];
  assert.deepEqual(sharedSummary(observatory.sharedNames(projects)), {
    exact: [], capitalization: [{ name: 'Alpha / alpha', ids: ['a', 'b'] }, { name: 'ZEBRA / zebra', ids: ['c', 'd'] }],
    whitespace: [], tool_count: 4, exact_tool_count: 0, capitalization_tool_count: 4, whitespace_tool_count: 0
  });
});

test('mixed exact and capitalization groups never count an exact project twice', () => {
  const projects = [project({ id: 'b', name: 'Echo' }), project({ id: 'd', name: 'echo' }),
    project({ id: 'a', name: 'Echo' }), project({ id: 'c', name: 'ECHO' })];
  const result = observatory.sharedNames(projects);
  assert.deepEqual(sharedSummary(result), {
    exact: [{ name: 'Echo', ids: ['a', 'b'] }], capitalization: [{ name: 'ECHO / echo', ids: ['c', 'd'] }],
    whitespace: [], tool_count: 4, exact_tool_count: 2, capitalization_tool_count: 2, whitespace_tool_count: 0
  });
  const ids = [...result.exact, ...result.capitalization].flatMap(group => group.projects.map(item => item.id));
  assert.equal(ids.length, new Set(ids).size);
});

test('shared names do not infer aliases or combine case and whitespace normalization and handle empty or singleton selections', () => {
  for (const projects of [[], [project()], [project({ id: 'a', name: 'Tool' }),
    project({ id: 'b', name: 'tool ' }), project({ id: 'c', name: 'Tool-' }),
    project({ id: 'd', name: 'Tool OSS' })]]) {
    assert.deepEqual(sharedSummary(observatory.sharedNames(projects)), EMPTY_SHARED);
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
    exact: [{ name: 'Shared', ids: ['a', 'b', 'c'] }], capitalization: [], whitespace: [], tool_count: 3, exact_tool_count: 3, capitalization_tool_count: 0, whitespace_tool_count: 0
  });
  const known = observatory.aggregate(data, { category: 'one', license: 'known' });
  assert.deepEqual(sharedSummary(known.sharedNames), {
    exact: [{ name: 'Shared', ids: ['a', 'b'] }], capitalization: [], whitespace: [], tool_count: 2, exact_tool_count: 2, capitalization_tool_count: 0, whitespace_tool_count: 0
  });
  const unknown = observatory.aggregate(data, { category: 'two', license: 'unknown' });
  assert.deepEqual(sharedSummary(unknown.sharedNames), {
    exact: [], capitalization: [{ name: 'Shared / shared', ids: ['c', 'd'] }], whitespace: [], tool_count: 2, exact_tool_count: 0, capitalization_tool_count: 2, whitespace_tool_count: 0
  });
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'one', license: 'unknown' }).sharedNames), EMPTY_SHARED);
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'two', license: 'known' }).sharedNames), EMPTY_SHARED);
});

test('shared names sort Unicode code points consistently with the static renderer', () => {
  const bmp = '\uE000';
  const supplementary = '\u{10000}';
  const projects = [
    project({ id: 'a2', name: supplementary }), project({ id: 'b2', name: bmp }),
    project({ id: 'a1', name: supplementary }), project({ id: 'b1', name: bmp }),
    project({ id: supplementary, name: 'Tie' }), project({ id: bmp, name: 'Tie' }),
    project({ id: 'case-a2', name: supplementary + 'a' }), project({ id: 'case-b2', name: bmp + 'a' }),
    project({ id: 'case-a1', name: supplementary + 'A' }), project({ id: 'case-b1', name: bmp + 'A' })
  ];
  assert.deepEqual(sharedSummary(observatory.sharedNames(projects)), {
    exact: [{ name: 'Tie', ids: [bmp, supplementary] }, { name: bmp, ids: ['b1', 'b2'] }, { name: supplementary, ids: ['a1', 'a2'] }],
    capitalization: [
      { name: bmp + 'A / ' + bmp + 'a', ids: ['case-b1', 'case-b2'] },
      { name: supplementary + 'A / ' + supplementary + 'a', ids: ['case-a1', 'case-a2'] }
    ],
    whitespace: [], tool_count: 10, exact_tool_count: 6, capitalization_tool_count: 4, whitespace_tool_count: 0
  });
});


test('whitespace-only groups retain original names, deterministic order and three-way membership', () => {
  const projects = [['c', 'Open Tool '], ['a', ' OpenTool'], ['b', 'Open Tool']].map(([id, name]) => project({ id, name }));
  const before = JSON.stringify(projects);
  const result = observatory.sharedNames(projects);
  assert.deepEqual(sharedSummary(result), {
    exact: [], capitalization: [], whitespace: [{ name: ' OpenTool / Open Tool / Open Tool ', ids: ['a', 'b', 'c'] }],
    tool_count: 3, exact_tool_count: 0, capitalization_tool_count: 0, whitespace_tool_count: 3
  });
  assert.equal(JSON.stringify(projects), before);
  assert.deepEqual(observatory.sharedNames(projects.slice().reverse()), result);
});

test('whitespace-only names remove exactly Unicode White_Space across Python and JavaScript', () => {
  const whitespace = [9, 10, 11, 12, 13, 32, 0x85, 0xa0, 0x1680,
    ...Array.from({ length: 11 }, (_, i) => 0x2000 + i), 0x2028, 0x2029, 0x202f, 0x205f, 0x3000];
  for (const codepoint of whitespace) {
    const result = observatory.sharedNames([project({ id: 'a', name: 'OpenTool' }),
      project({ id: 'b', name: 'Open' + String.fromCodePoint(codepoint) + 'Tool' })]);
    assert.equal(result.whitespace_tool_count, 2, codepoint.toString(16));
    assert.equal(result.tool_count, 2);
    assert.equal(result.whitespace.length, 1);
  }
  for (const codepoint of [0x1c, 0x1d, 0x1e, 0x1f, 0x180e, 0x200b, 0xfeff]) {
    const result = observatory.sharedNames([project({ id: 'a', name: 'OpenTool' }),
      project({ id: 'b', name: 'Open' + String.fromCodePoint(codepoint) + 'Tool' })]);
    assert.deepEqual(sharedSummary(result), EMPTY_SHARED, codepoint.toString(16));
  }
});

test('exact, capitalization and whitespace priority partitions identities without mixed normalization', () => {
  const pairs = [['a', 'OpenTool'], ['b', 'OpenTool'], ['c', 'Open Tool'], ['d', 'OPEN TOOL'],
    ['e', 'Open  Tool'], ['f', 'Open\tTool'], ['g', 'openTool '], ['h', 'Open-Tool']];
  const projects = pairs.map(([id, name]) => project({ id, name }));
  const result = observatory.sharedNames(projects);
  assert.deepEqual(result.exact[0].projects.map(p => p.id), ['a', 'b']);
  assert.deepEqual(result.capitalization[0].projects.map(p => p.id), ['d', 'c']);
  assert.deepEqual(result.whitespace[0].projects.map(p => p.id), ['f', 'e']);
  assert.deepEqual([result.tool_count, result.exact_tool_count, result.capitalization_tool_count, result.whitespace_tool_count], [6, 2, 2, 2]);
  const ids = [...result.exact, ...result.capitalization, ...result.whitespace].flatMap(group => group.projects.map(p => p.id));
  assert.equal(ids.length, new Set(ids).size);
  assert.deepEqual(observatory.sharedNames(projects.slice().reverse()), result);
  for (const names of [['OpenTool', 'OpenTool', 'Open Tool'], ['OpenTool', 'opentool', 'Open Tool']]) {
    assert.deepEqual(observatory.sharedNames(names.map((name, i) => project({ id: String(i), name }))).whitespace, []);
  }
});

test('whitespace groups use the current category and license intersection and deduplicate IDs', () => {
  const data = index([project({ id: 'a', name: 'OpenTool', categories: ['one', 'two'], license: 'MIT' }),
    project({ id: 'b', name: 'Open Tool', categories: ['one'], license: 'MIT' }),
    project({ id: 'c', name: 'Open  Tool', categories: ['two'], license: null })]);
  assert.equal(observatory.aggregate(data).sharedNames.whitespace_tool_count, 3);
  assert.equal(observatory.aggregate(data, { category: 'one', license: 'known' }).sharedNames.whitespace_tool_count, 2);
  assert.deepEqual(sharedSummary(observatory.aggregate(data, { category: 'two', license: 'unknown' }).sharedNames), EMPTY_SHARED);
  assert.equal(observatory.sharedNames([...data.projects, { ...data.projects[0], categories: ['two'] }]).whitespace_tool_count, 3);
});
