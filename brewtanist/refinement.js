'use strict';
/* Progressive enhancement only: no tracking, storage, third-party code or copy replacement. */
(()=>{
 if(!document.body.classList.contains('site-refined'))return;
 const menu=document.querySelector('.mobile-nav');
 document.addEventListener('click',event=>{if(menu?.open&&!menu.contains(event.target))menu.open=false;});
 document.querySelectorAll('.coffee-menu').forEach(drop=>document.addEventListener('click',event=>{if(drop.open&&!drop.contains(event.target))drop.open=false;}));
 const navLinks=[...document.querySelectorAll('.nav-links>a[href^="#"]')];
 if('IntersectionObserver' in window){const sections=navLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);const observer=new IntersectionObserver(entries=>{const active=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(!active)return;for(const a of navLinks){if(a.hash==='#'+active.target.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');}},{rootMargin:'-90px 0px -45% 0px',threshold:[0,.2,.5]});sections.forEach(el=>observer.observe(el));}
 if(typeof HTMLDialogElement==='undefined'||!HTMLDialogElement.prototype.showModal)return;
 const figures=[...document.querySelectorAll('.gallery-item')].filter(f=>f.querySelector('img'));
 if(!figures.length)return;
 const dialog=document.createElement('dialog');dialog.className='brew-lightbox';dialog.setAttribute('aria-label','ภาพบรรยากาศร้าน Brewtanist');
 dialog.innerHTML='<div class="brew-lightbox-head"><span data-lightbox-count></span><button type="button" data-lightbox-close autofocus>ปิดภาพ ×</button></div><img data-lightbox-image alt=""><div class="brew-lightbox-foot"><p class="brew-lightbox-caption" data-lightbox-caption></p><div class="brew-lightbox-controls"><button type="button" data-lightbox-prev aria-label="ภาพก่อนหน้า">←</button><button type="button" data-lightbox-next aria-label="ภาพถัดไป">→</button></div></div>';
 document.body.append(dialog);let current=0,opener=null,previousOverflow='',scrollLocked=false;
 const large=dialog.querySelector('[data-lightbox-image]'),caption=dialog.querySelector('[data-lightbox-caption]'),count=dialog.querySelector('[data-lightbox-count]');
 function draw(i){
  current=(i+figures.length)%figures.length;
  const f=figures[current],img=f.querySelector('img'),preview=img.currentSrc||img.src;
  large.src=preview;large.alt=img.alt;
  caption.textContent=f.querySelector('figcaption')?.textContent.trim()||img.alt;
  count.textContent='บรรยากาศร้าน · '+(current+1)+' / '+figures.length;
  if(preview!==img.src){
   // Show the cached thumbnail immediately. Upgrade only the still-open photo.
   const full=new Image();full.onload=()=>{if(dialog.open&&figures[current]===f)large.src=full.src;};full.src=img.src;
  }
 }
 function unlock(){if(scrollLocked){document.documentElement.style.overflow=previousOverflow;scrollLocked=false;}}
 function close(){unlock();if(dialog.open)dialog.close();if(opener)opener.focus({preventScroll:true});}
 figures.forEach((f,i)=>{const img=f.querySelector('img');const button=document.createElement('button');button.className='gallery-open';button.type='button';button.setAttribute('aria-label','ดูภาพ: '+img.alt);const media=img.closest('picture')||img;media.before(button);button.append(media);button.addEventListener('click',()=>{if(dialog.open)return;opener=button;draw(i);previousOverflow=document.documentElement.style.overflow;dialog.showModal();scrollLocked=true;document.documentElement.style.overflow='hidden';});});
 dialog.querySelector('[data-lightbox-close]').addEventListener('click',close);dialog.querySelector('[data-lightbox-prev]').addEventListener('click',()=>draw(current-1));dialog.querySelector('[data-lightbox-next]').addEventListener('click',()=>draw(current+1));
 dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)close();}});
 dialog.addEventListener('keydown',event=>{if(event.key==='ArrowRight'){event.preventDefault();draw(current+1);}if(event.key==='ArrowLeft'){event.preventDefault();draw(current-1);}if(event.key==='Escape'){event.preventDefault();close();}});
 // Restore scrolling before hiding the modal; native close events can be dispatched later.
 dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
 dialog.addEventListener('close',()=>{if(!dialog.open){unlock();if(opener)opener.focus({preventScroll:true});}});
})();
