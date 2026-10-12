/* Preview-only category exhibition; shares catalog matching and sorting rules. */
(function () {
  'use strict';
  const payload = document.getElementById('exhibition-data');
  if (!payload || !window.OpenCatalog) return;
  const data = JSON.parse(payload.textContent);
  const search = document.getElementById('ex-search');
  const license = document.getElementById('ex-license');
  const sort = document.getElementById('ex-sort');
  const hall = document.getElementById('ex-hall');
  const list = document.getElementById('ex-list');
  const cards = new Map(Array.from(list.children).map(n => [n.dataset.projectId,n]));
  let view = 'exhibition';
  let lastSort = 'name';
  function state() { return OpenCatalog.normalizeState(new URLSearchParams({q:search.value,license:license.value,sort:sort.value}),data); }
  function render(write) {
    const current = state();
    const selected = OpenCatalog.selectProjects(data.projects,current,data);
    const ids = new Set(selected.map(p=>p.id));
    cards.forEach((node,id)=>{node.hidden=!ids.has(id);});
    if (lastSort !== current.sort) {
      const ordered = OpenCatalog.selectProjects(data.projects,{...OpenCatalog.DEFAULTS,sort:current.sort},data);
      ordered.forEach(p=>list.appendChild(cards.get(p.id)));
      lastSort=current.sort;
    }
    const filtered=Boolean(current.q || current.license !== 'all');
    hall.hidden=view!=='exhibition' || filtered;
    document.getElementById('hall-caption').hidden=hall.hidden;
    document.getElementById('ex-count').textContent=selected.length+' of '+data.projects.length+' projects';
    document.getElementById('ex-empty').hidden=selected.length>0;
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));
    if(write) {
      const url=new URL(location.href);
      for(const k of ['q','license','sort','view'])url.searchParams.delete(k);
      if(current.q)url.searchParams.set('q',current.q);
      if(current.license!=='all')url.searchParams.set('license',current.license);
      if(current.sort!=='name')url.searchParams.set('sort',current.sort);
      if(view!=='exhibition')url.searchParams.set('view',view);
      try { history.replaceState(null,'',url); } catch (_) {}
    }
    openLinked(false);
  }
  function openLinked(focus) {
    const id=location.hash.replace('#project-','');
    const card=cards.get(id);
    document.getElementById('ex-link-notice').hidden=!card || !card.hidden;
    if(card && !card.hidden) {
      const drawer=card.querySelector('details');drawer.open=true;
      if(focus) { drawer.querySelector('summary').focus({preventScroll:true});card.scrollIntoView({block:'start'}); }
    }
  }
  function restore() {
    const params=new URL(location.href).searchParams;
    const current=OpenCatalog.normalizeState(params,data);
    search.value=current.q;license.value=current.license;sort.value=current.sort;
    view=params.get('view')==='ledger'?'ledger':'exhibition';
    render(false);openLinked(Boolean(location.hash));
  }
  search.addEventListener('input',()=>render(true));
  license.addEventListener('change',()=>render(true));
  sort.addEventListener('change',()=>render(true));
  document.getElementById('ex-search-form').addEventListener('submit',e=>{e.preventDefault();render(true);});
  document.getElementById('ex-filters').addEventListener('submit',e=>e.preventDefault());
  document.getElementById('ex-reset').addEventListener('click',()=>{search.value='';license.value='all';sort.value='name';render(true);});
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;render(true);}));
  document.querySelectorAll('[data-inspect]').forEach(a=>a.addEventListener('click',e=>{
    if(e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)return;
    const card=cards.get(a.dataset.inspect);if(!card)return;
    card.querySelector('details').open=true;
    // Native fragment navigation remains the permalink and no-JS fallback.
    requestAnimationFrame(()=>card.querySelector('summary').focus({preventScroll:true}));
  }));
  window.addEventListener('hashchange',()=>openLinked(true));
  window.addEventListener('popstate',restore);
  document.getElementById('ex-search-form').hidden=false;
  document.getElementById('ex-filters').hidden=false;
  document.querySelector('.view-switch').hidden=false;
  restore();document.body.dataset.exhibitionReady='true';
})();
