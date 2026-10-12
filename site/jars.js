/* Local pointer motion; tap selects, the separate record link navigates. */
(()=>{
 'use strict';
 const hall=document.querySelector('.jar-hall');if(!hall)return;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),fine=matchMedia('(hover: hover) and (pointer: fine)');
 const exhibits=[...hall.querySelectorAll('.jar-exhibit')];let pinned=null;
 function select(active){exhibits.forEach(exhibit=>{
   const selected=exhibit===active;
   exhibit.classList.toggle('is-active',selected);
   exhibit.querySelector('.jar-select').setAttribute('aria-expanded',String(selected));
   exhibit.querySelector('.jar-annotation').hidden=!selected;
 });}
 exhibits.forEach(exhibit=>{
   const button=exhibit.querySelector('.jar-select');button.hidden=false;let frame=0;
   const reset=()=>{cancelAnimationFrame(frame);exhibit.style.setProperty('--mx','0px');exhibit.style.setProperty('--my','0px');};
   exhibit.addEventListener('pointerenter',()=>{if(fine.matches)select(exhibit);});
   exhibit.addEventListener('pointermove',e=>{
     if(reduced.matches||!fine.matches)return;
     const box=exhibit.getBoundingClientRect();const x=(e.clientX-box.left)/box.width-.5,y=(e.clientY-box.top)/box.height-.5;
     cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{exhibit.style.setProperty('--mx',`${Math.max(-4,Math.min(4,x*8))}px`);exhibit.style.setProperty('--my',`${Math.max(-2,Math.min(2,y*4))}px`);});
   });
   exhibit.addEventListener('pointerleave',()=>{reset();if(!exhibit.contains(document.activeElement))select(document.activeElement.closest('.jar-exhibit')||pinned);});
   exhibit.addEventListener('focusin',()=>select(exhibit));
   exhibit.addEventListener('focusout',()=>requestAnimationFrame(()=>{if(!exhibit.contains(document.activeElement))select(document.activeElement.closest('.jar-exhibit')||pinned);}));
   button.addEventListener('click',()=>{pinned=pinned===exhibit?null:exhibit;select(pinned);});
   reduced.addEventListener('change',reset);
 });
 hall.addEventListener('keydown',e=>{if(e.key==='Escape'){const active=hall.querySelector('.is-active');if(active)active.querySelector('.jar-select').focus({preventScroll:true});pinned=null;select(null);}});
 document.addEventListener('pointerdown',e=>{if(!hall.contains(e.target)){pinned=null;select(null);}});
 hall.querySelectorAll('[data-jar-inspect]').forEach(link=>link.addEventListener('click',event=>{
   if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
   const card=document.getElementById('project-'+link.dataset.jarInspect);if(!card)return;
   card.querySelector('details').open=true;
   requestAnimationFrame(()=>{if(!card.hidden)card.querySelector('summary').focus({preventScroll:true});});
 }));
 select(null);document.body.classList.add('photo-ready');document.body.dataset.jarsReady='true';
})();
