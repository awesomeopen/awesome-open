/* Fixed-size photographic planes; depth comes from translation, not rescaling. */
(()=>{
 'use strict';
 const hall=document.querySelector('.jar-hall');if(!hall)return;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),fine=matchMedia('(hover: hover) and (pointer: fine)');
 const exhibits=[...hall.querySelectorAll('.jar-exhibit')],stage=hall.querySelector('.jar-stage');
 // Three distinct characters per jar, fixed until the page reloads.
 const vaporPool=[...'∰⋈⌘∑∂∇∞⊕⋇AXRkx0279'];
 exhibits.forEach(node=>{
   const available=[...vaporPool];
   node.querySelectorAll('.steam-strand').forEach(glyph=>{
     glyph.textContent=available.splice(Math.floor(Math.random()*available.length),1)[0];
   });
 });
 let active=null,closeTimer=0,frame=0,lastTime=0,inView=true,motionPaused=false;
 const toggle=hall.querySelector('.jar-motion-toggle');
 const staticMotion=()=>reduced.matches||motionPaused;
 function syncAmbient(){hall.classList.toggle('ambient-paused',staticMotion()||document.hidden||!inView);}
 const pointer={inside:false,x:0};
 const keys=['x','y','ix','iy','reflection','light'];
 const resting={x:0,y:0,ix:0,iy:0,reflection:0,light:.14};
 const motion=exhibits.map(node=>({node,value:{...resting},velocity:Object.fromEntries(keys.map(k=>[k,0]))}));
 const clamp=(n,min,max)=>Math.min(max,Math.max(min,n));
 function paint(item,moving=false){
   const v=item.value,style=item.node.style;
   // Fractional positions are used only in flight. Settle on whole CSS pixels,
   // without a transformed ancestor retaining a composited raster of the jar.
   const pixels=value=>(moving?value.toFixed(3):Math.round(value))+'px';
   style.setProperty('--mx',pixels(v.x));style.setProperty('--my',pixels(v.y));
   style.setProperty('--inner-x',pixels(v.ix));style.setProperty('--inner-y',pixels(v.iy));
   style.setProperty('--reflection-x',pixels(v.reflection));
   style.setProperty('--glass-light',v.light.toFixed(3));
 }
 function targets(item,index,scene){
   if(staticMotion())return {...resting};
   const box=item.node.getBoundingClientRect(),center=box.left+box.width/2;
   const cameraX=pointer.inside?clamp((pointer.x-scene.left)/scene.width*2-1,-1,1):0;
   const near=pointer.inside?Math.exp(-Math.pow((center-pointer.x)/220,2)):0;
   const selected=active===item.node,depth=1-Math.abs(index-3)/5;
   const forward=selected?1:near*.42;
   return {x:-cameraX*(4+depth*3),y:-forward*3,
     ix:cameraX*(2+forward),iy:0,reflection:-cameraX*2,
     light:.14+forward*.11+Math.abs(cameraX)*.04};
 }
 function tick(time){
   frame=0;if(document.hidden||!inView)return;
   const dt=Math.min((time-(lastTime||time-16.67))/1000,1/30);lastTime=time;
   const scene=stage.getBoundingClientRect();let moving=false;
   // Read scene geometry before writing positions. Hit regions stay fixed.
   const goals=motion.map((item,i)=>targets(item,i,scene));
   motion.forEach((item,i)=>{
     let itemMoving=false;
     keys.forEach(key=>{
       const goal=goals[i][key];
       if(staticMotion()){item.value[key]=goal;item.velocity[key]=0;return;}
       const delta=goal-item.value[key];
       item.velocity[key]+=(190*delta-25*item.velocity[key])*dt;
       item.value[key]+=item.velocity[key]*dt;
       if(Math.abs(delta)>.0008||Math.abs(item.velocity[key])>.003)itemMoving=true;
       else{item.value[key]=goal;item.velocity[key]=0;}
     });moving=moving||itemMoving;paint(item,itemMoving);
   });
   drawLeaders(active);
   document.body.dataset.jarMotion=moving?'moving':'settled';
   if(moving)frame=requestAnimationFrame(tick);else lastTime=0;
 }
 function wake(){if(!frame&&!document.hidden&&inView){lastTime=0;frame=requestAnimationFrame(tick);}}
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
 function select(next){
   clearTimeout(closeTimer);active=next;
   exhibits.forEach(exhibit=>{
     const selected=exhibit===active;
     exhibit.classList.toggle('is-active',selected);
     exhibit.querySelector('.jar-select').setAttribute('aria-expanded',String(selected));
     exhibit.querySelector('.jar-annotation').hidden=!selected;
   });wake();if(active)requestAnimationFrame(()=>drawLeaders(active));
 }
 hall.addEventListener('pointermove',event=>{
   if(!fine.matches||staticMotion())return;
   pointer.inside=true;pointer.x=event.clientX;wake();
 });
 hall.addEventListener('pointerleave',()=>{pointer.inside=false;wake();});
 exhibits.forEach(exhibit=>{
   const button=exhibit.querySelector('.jar-select');button.hidden=false;
   exhibit.addEventListener('pointerenter',()=>{if(fine.matches)select(exhibit);});
   exhibit.addEventListener('pointerleave',()=>{closeTimer=setTimeout(()=>{if(!exhibit.contains(document.activeElement))select(document.activeElement.closest('.jar-exhibit')||null);},220);});
   exhibit.addEventListener('focusin',()=>select(exhibit));
   exhibit.addEventListener('focusout',()=>requestAnimationFrame(()=>{if(!exhibit.contains(document.activeElement))select(document.activeElement.closest('.jar-exhibit')||null);}));
   let cracks=0;
   const name=button.getAttribute('aria-label').replace('Crack glass — ','');
   exhibit.dataset.cracks='0';
   button.addEventListener('click',()=>{
     if(cracks<2){
       cracks++;exhibit.dataset.cracks=String(cracks);select(exhibit);
       button.setAttribute('aria-label',(cracks===1?'Crack further — ':'Inspect — ')+name);
     }else{
       cracks=0;exhibit.dataset.cracks='0';
       button.setAttribute('aria-label','Crack glass — '+name);
       exhibit.querySelector('[data-jar-inspect]').click();
     }
   });
 });
 hall.addEventListener('keydown',event=>{
   if(event.key==='Escape'){
     if(active)active.querySelector('.jar-select').focus({preventScroll:true});
     pointer.inside=false;select(null);
   }
 });
 document.addEventListener('pointerdown',event=>{if(!hall.contains(event.target)){pointer.inside=false;select(null);}});
 hall.querySelectorAll('[data-jar-inspect]').forEach(link=>link.addEventListener('click',event=>{
   if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
   const card=document.getElementById('project-'+link.dataset.jarInspect);if(!card)return;
   card.querySelector('details').open=true;
   requestAnimationFrame(()=>{if(!card.hidden)card.querySelector('summary').focus({preventScroll:true});});
 }));
 reduced.addEventListener('change',()=>{pointer.inside=false;syncAmbient();wake();});
 fine.addEventListener('change',()=>{pointer.inside=false;wake();});
 window.addEventListener('resize',wake);
 document.addEventListener('visibilitychange',()=>{
   syncAmbient();
   if(document.hidden){cancelAnimationFrame(frame);frame=0;lastTime=0;}else wake();
 });
 if('IntersectionObserver' in window)new IntersectionObserver(entries=>{
   inView=entries[0].isIntersecting;syncAmbient();
   if(!inView){cancelAnimationFrame(frame);frame=0;lastTime=0;pointer.inside=false;}else wake();
 },{rootMargin:'40px'}).observe(hall);
 document.fonts.ready.then(()=>drawLeaders(active));
 toggle.hidden=false;toggle.addEventListener('click',()=>{motionPaused=!motionPaused;pointer.inside=false;toggle.setAttribute('aria-pressed',String(motionPaused));toggle.textContent=motionPaused?'[>]':'[II]';toggle.setAttribute('aria-label',motionPaused?'Play motion':'Pause motion');toggle.title=motionPaused?'Play motion':'Pause motion';hall.classList.toggle('motion-paused',motionPaused);syncAmbient();wake();});
 syncAmbient();motion.forEach(item=>paint(item));select(null);document.body.classList.add('photo-ready');document.body.dataset.jarsReady='true';
})();
