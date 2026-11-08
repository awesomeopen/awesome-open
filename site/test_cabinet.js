const test = require('node:test');
const assert = require('node:assert/strict');
const { create, evidence } = require('./cabinet.js');
const projects = Array.from({length: 8}, (_, i) => ({ id: String(i).repeat(64), name: 'Open ' + i, description: i % 2 ? 'editor' : 'server' }));
test('canonical IDs, limits and revision prevent partial or stale mutations', () => {
 const model = create(projects);
 const state = model.arrange({ids: [projects[2].id, projects[0].id], revision: 0});
 for (const ids of [[projects[1].id, 'unknown'], [projects[1].id, projects[1].id], projects.slice(0,7).map(p=>p.id), null]) {
  assert.throws(()=> model.arrange({ids, revision: 1})); assert.deepEqual(model.state(), state);
 }
 assert.throws(()=> model.arrange({ids: [], revision: 0}));
 assert.throws(()=> model.arrange({ids: [], revision: 1, url: 'https://example.com'}));
 assert.deepEqual(model.state(), state);
 const copy = model.state(); copy.ids.reverse(); assert.deepEqual(model.state(), state);
 assert.deepEqual(model.arrange({ids: [], revision: 1}).ids, []);
});
test('find is bounded and literal; inspect rejects arbitrary targets', () => {
 const model = create([...projects, ...projects.map(p=>({...p,id:'a'+p.id,name:'Second '+p.name}))]);
 assert.equal(model.find({query:''}).projects.length,12);
 assert.equal(model.find({query:'editor'}).total,8);
 assert.equal(model.find({query:'[.*]'}).total,0);
 for (const args of [null, [], {query:0}, {query:'x'.repeat(161)}, {query:'', fetch:'x'}]) assert.throws(()=>model.find(args));
 assert.throws(()=>model.inspect({id:'https://example.com'}));
 assert.throws(()=>model.inspect({id:projects[0].id, extra:1}));
});
test('find pages through every match in match order, with fields and unknowns', () => {
 const many = Array.from({length: 30}, (_, i) => ({ id: String(i).padStart(64, '0'), name: 'Open ' + String(i).padStart(2, '0'), description: 'editor' }));
 const model = create(many), first = model.find({query:'editor'}), second = model.find({query:'editor', offset:12}), last = model.find({query:'editor', offset:24});
 assert.deepEqual([first.total, first.projects.length, second.projects.length, last.projects.length], [30, 12, 12, 6]);
 assert.deepEqual([...first.projects, ...second.projects, ...last.projects].map(p=>p.id), many.map(p=>p.id));
 assert.deepEqual(first.projects[0].matched_fields, ['description']);
 assert.deepEqual(first.projects[0].github, { stars: null, license: null, pushed_at: null });
 for (const offset of [-1, 1.5, '12']) assert.throws(()=>model.find({query:'editor', offset}), { code: 'invalid_offset' });
});
test('find searches supplied function summaries and reports no match', () => {
 const model = create(projects), text = { [projects[0].id]: { summary: 'Family photos at home.', features: [] } };
 assert.equal(model.find({query:'family photos'}).total, 0);
 assert.deepEqual(model.find({query:'family photos'}, text).projects[0].matched_fields, ['summary']);
 const none = model.find({query:'absent'}, text);
 assert.deepEqual(none.projects, []);
 assert.equal(none.message, 'No match in this catalog of 8 Open*-named projects.');
});
test('rejections carry a stable code', () => {
 const model = create(projects);
 assert.throws(()=>model.arrange({ids:[], revision:9}), { code: 'stale_revision' });
 assert.throws(()=>model.arrange({ids:['unknown'], revision:0}), { code: 'invalid_ids' });
 assert.throws(()=>model.find({query:'x'.repeat(161)}), { code: 'invalid_query' });
 assert.throws(()=>model.find({query:'', fetch:'x'}), { code: 'invalid_arguments' });
});
test('evidence treats unasserted licenses as unknown', () => {
 assert.equal(evidence({...projects[0],github:{license:'NOASSERTION'}}).github.license,null);
});
test('unknown evidence remains null, while zero and stale dates survive', () => {
 assert.equal(evidence(projects[0]).github.stars,null);
 const result=evidence({...projects[0],github:{stars:0,status:'stale',last_success_at:'2026-01-02',last_attempt:{at:'2026-02-03',status:'unavailable'}}});
 assert.equal(result.github.stars,0); assert.equal(result.github.status,'stale');
 assert.equal(result.github.last_success_at,'2026-01-02');
 assert.equal(result.github.last_attempt.status,'unavailable');
});
