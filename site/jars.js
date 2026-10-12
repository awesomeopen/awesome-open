/* Local pointer parallax, native links, no global scroll interception. */
(()=>{
 'use strict';
 const hall=document.querySelector('.jar-hall');if(!hall)return;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const fine=matchMedia('(hover: hover) and (pointer: fine)');
 hall.querySelectorAll('.jar-exhibit').forEach(exhibit=>{
   let frame=0;
   const reset=()=>{cancelAnimationFrame(frame);exhibit.style.setProperty('--mx','0px');exhibit.style.setProperty('--my','0px');};
   exhibit.addEventListener('pointermove',e=>{
     if(reduced.matches||!fine.matches)return;
     const box=exhibit.getBoundingClientRect();const x=(e.clientX-box.left)/box.width-.5,y=(e.clientY-box.top)/box.height-.5;
     cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{exhibit.style.setProperty('--mx',`${x*8}px`);exhibit.style.setProperty('--my',`${y*4}px`);});
   });
   exhibit.addEventListener('pointerleave',reset);reduced.addEventListener('change',reset);
 });
 hall.querySelectorAll('[data-ground]').forEach(button=>button.addEventListener('click',()=>{
   hall.dataset.ground=button.dataset.ground;
   hall.querySelectorAll('[data-ground]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 }));
 hall.querySelectorAll('[data-jar-inspect]').forEach(link=>link.addEventListener('click',event=>{
   if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
   const card=document.getElementById('project-'+link.dataset.jarInspect);if(!card)return;
   const drawer=card.querySelector('details');drawer.open=true;
   requestAnimationFrame(()=>{if(!card.hidden)drawer.querySelector('summary').focus({preventScroll:true});});
 }));
 document.body.dataset.jarsReady='true';
})();
