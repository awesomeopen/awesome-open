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
