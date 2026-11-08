'use strict';
(()=>{
 const seed=document.getElementById('marketplace-data');
 if(seed){const data=JSON.parse(seed.textContent),input=document.getElementById('market-search'),select=document.getElementById('market-category'),cards=[...document.querySelectorAll('#market-products .market-card')],lookup=new Map(data.items.map(x=>[x.id,x]));
 const update=()=>{const q=(input.value||'').normalize('NFC').trim().toLowerCase(),cat=select.value;let count=0;for(const card of cards){const p=lookup.get(card.dataset.marketId);const show=!!p&&(cat==='all'||p.category===cat)&&[p.name,p.description,p.category].join(' ').normalize('NFC').toLowerCase().includes(q);card.hidden=!show;if(show)count++;}document.getElementById('market-count').textContent=count+' รายการ';document.getElementById('market-empty').hidden=count>0;};
 if(input&&select){input.addEventListener('input',update);select.addEventListener('change',()=>{if(cards.length<data.items.length){location.href=select.value==='all'?'/shop/':'/shop/'+select.value+'/';return;}update();});update();}}
 const result=document.getElementById('finder-result');
 if(result){const observer=new MutationObserver(()=>{if(result.hidden||result.querySelector('.market-suggestion'))return;const selected=document.querySelector('input[name="q0"]:checked')?.value;if(!['capsules','drip'].includes(selected))return;const box=document.createElement('p');box.className='market-suggestion';const a=document.createElement('a');a.className='text-link';a.href='/shop/'+selected+'/';a.textContent=selected==='capsules'?'ดูแคปซูลของร้านก่อนเลือกซื้อ →':'ดู Drip Bag ของร้าน →';box.append(a);result.append(box);});observer.observe(result,{childList:true,attributes:true,attributeFilter:['hidden']});}
})();
