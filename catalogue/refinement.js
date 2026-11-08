'use strict';
(()=>{
 if(!document.body.classList.contains('catalogue-refined'))return;
 const nav=document.querySelector('header.nav .links');if(!nav)return;
 const path=location.pathname;
 nav.querySelectorAll('a[href]').forEach(a=>{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.pathname===path)a.setAttribute('aria-current','page');});
 document.querySelectorAll('.collection-tile').forEach(a=>{if(new URL(a.href,location.href).pathname===path)a.setAttribute('aria-current','page');});
 nav.id='catalogue-navigation';const toggle=document.createElement('button');toggle.type='button';toggle.className='catalogue-menu-toggle';toggle.textContent='เมนู ☰';toggle.setAttribute('aria-controls',nav.id);toggle.setAttribute('aria-expanded','false');nav.before(toggle);document.body.classList.add('nav-enhanced');
 const mobile=matchMedia('(max-width:800px)');
 const close=()=>{nav.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');toggle.textContent='เมนู ☰';};
 const resize=()=>{toggle.hidden=!mobile.matches;close();};resize();if(mobile.addEventListener)mobile.addEventListener('change',resize);else mobile.addListener(resize);
 toggle.addEventListener('click',()=>{const open=!nav.classList.contains('is-open');nav.classList.toggle('is-open',open);toggle.setAttribute('aria-expanded',String(open));toggle.textContent=open?'ปิดเมนู ×':'เมนู ☰';});
 document.addEventListener('click',e=>{if(!nav.contains(e.target)&&!toggle.contains(e.target))close();});nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',close));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('is-open')){close();toggle.focus();}});
})();
