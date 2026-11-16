const test = require('node:test');
const assert = require('node:assert/strict');
const Catalog = require('./catalog.js'), Search = require('./search.js'), Cabinet = require('./cabinet.js');
const projects = [
 {id:'a'.repeat(64),name:'Open A', languages:['C++','C#'],language_status:'stale'},
 {id:'b'.repeat(64),name:'Open B', languages:[],language_status:'available'},
 {id:'c'.repeat(64),name:'Open C', languages:null,language_status:'unknown'}
];
const data = {projects,categories:[]};
test('any detected language, empty and unknown have identical Catalog and Cabinet filters',()=>{
 for(const language of ['C++','C#','unknown','empty','']){
  const state=Catalog.normalizeState({language},data);
  const expected=Catalog.selectProjects(projects,state,data).map(p=>p.id);
  assert.deepEqual(Cabinet.create(projects).find({query:'',language}).projects.map(p=>p.id),expected);
  const url=Catalog.stateToURL('https://example.com/?cabinet=keep',state);
  assert.equal(url.searchParams.get('cabinet'),'keep');
  assert.deepEqual(Catalog.normalizeState(url.searchParams,data),state);
  assert.equal(Catalog.stateToURL(url,Catalog.DEFAULTS).searchParams.has('language'),false);
 }
});
test('punctuation searches remain literal and multi-language stale observations searchable',()=>{
 for(const q of ['C++','C#','C++ C#']){
  assert.deepEqual(Search.results(projects,q).map(r=>r.project.id),[projects[0].id]);
  assert.deepEqual(Cabinet.create(projects).find({query:q}).projects[0].matched_fields,['language']);
 }
 assert.equal(Cabinet.create(projects).find({query:'',language:'Rust'}).total,0);
 assert.throws(()=>Cabinet.create(projects).find({query:'',language:42}));
});
test('inspect and comparison evidence retain full source dates bytes and status',()=>{
 const signal={source_url:'https://api.github.com/repos/a/b/languages',checked_at:'2026-11-16T00:00:00Z',last_good:{value:{'C++':100,'C#':10}}};
 const out=Cabinet.evidence({...projects[0],signals:{languages:signal}});
 assert.deepEqual(out.language_evidence,signal);
 assert.equal(out.language_status,'stale');
 assert.deepEqual(out.languages,['C++','C#']);
 assert.equal(Cabinet.evidence(projects[2]).languages,null);
 assert.deepEqual(Cabinet.evidence(projects[1]).languages,[]);
});
