/* Local pointer motion; tap selects, the separate record link navigates. */
(()=>{
 'use strict';
 const hall=document.querySelector('.jar-hall');if(!hall)return;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),fine=matchMedia('(hover: hover) and (pointer: fine)');
 const exhibits=[...hall.querySelectorAll('.jar-exhibit')];let pinned=null,closeTimer=0;
 function drawLeaders(exhibit){
   if(!exhibit||exhibit.querySelector('.jar-annotation').hidden)return;
   const box=exhibit.getBoundingClientRect(),specimen=exhibit.querySelector('.specimen-window').getBoundingClientRect();
   const svg=exhibit.querySelector('.jar-leaders');
   svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);svg.style.cssText='left:0;top:0;width:100%;height:100%';
   const positions=[[.3,.25],[.75,.55],[.45,.85]];
   exhibit.querySelectorAll('.jar-callout').forEach((label,i)=>{
     const bounds=label.getBoundingClientRect();const [fx,fy]=positions[i];
     const x=specimen.left-box.left+specimen.width*fx,y=specimen.top-box.top+specimen.height*fy;
     const toRight=bounds.left+bounds.width/2>specimen.left+specimen.width/2;
     const endX=(toRight?bounds.left-5:bounds.right+5)-box.left,endY=bounds.top-box.top+Math.min(16,bounds.height/2);
     const elbow=endX+(toRight?-20:20);const group=svg.children[i];
     group.querySelector('path').setAttribute('d',`M${x} ${y} L${elbow} ${endY} H${endX}`);
     const dot=group.querySelector('circle');dot.setAttribute('cx',x);dot.setAttribute('cy',y);
   });
 }
 function select(active){clearTimeout(closeTimer);exhibits.forEach(exhibit=>{
   const selected=exhibit===active;
   exhibit.classList.toggle('is-active',selected);
   exhibit.querySelector('.jar-select').setAttribute('aria-expanded',String(selected));
   exhibit.querySelector('.jar-annotation').hidden=!selected;
 });if(active)requestAnimationFrame(()=>drawLeaders(active));}
 exhibits.forEach(exhibit=>{
   const button=exhibit.querySelector('.jar-select');button.hidden=false;let frame=0;
   const reset=()=>{cancelAnimationFrame(frame);exhibit.style.setProperty('--mx','0px');exhibit.style.setProperty('--my','0px');};
   exhibit.addEventListener('pointerenter',()=>{if(fine.matches)select(exhibit);});
   exhibit.addEventListener('pointermove',e=>{
     if(reduced.matches||!fine.matches)return;
     const box=exhibit.getBoundingClientRect();const x=(e.clientX-box.left)/box.width-.5,y=(e.clientY-box.top)/box.height-.5;
     cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{exhibit.style.setProperty('--mx',`${Math.max(-4,Math.min(4,x*8))}px`);exhibit.style.setProperty('--my',`${Math.max(-2,Math.min(2,y*4))}px`);drawLeaders(exhibit);});
   });
   exhibit.addEventListener('pointerleave',()=>{reset();closeTimer=setTimeout(()=>{if(!exhibit.contains(document.activeElement))select(document.activeElement.closest('.jar-exhibit')||pinned);},220);});
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
 window.addEventListener('resize',()=>drawLeaders(hall.querySelector('.is-active')));
 document.fonts.ready.then(()=>drawLeaders(hall.querySelector('.is-active')));
 select(null);document.body.classList.add('photo-ready');document.body.dataset.jarsReady='true';
})();
