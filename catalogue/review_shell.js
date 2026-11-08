const B=JSON.parse(document.getElementById('bundle').textContent),frame=document.getElementById('frame');
function show(){
 const target=location.hash.slice(1)||'/shop/',query=target.includes('?')?'?'+target.split('?')[1]:'',path=target.split('?')[0];
 let html=B.pages[path]||B.pages['/shop/'];
 html=html.replace(/<link rel="stylesheet" href="([^"]+)">/g,(m,k)=>B.assets[k]?'<style>'+B.assets[k].value+'</style>':m);
 html=html.replace(/<script src="([^"]+)" defer><\/script>/g,(m,k)=>{
   if(!B.assets[k])return m;
   const code=B.assets[k].value.replaceAll('new URLSearchParams(location.search)','new URLSearchParams(window.__REVIEW_QUERY__ || location.search)');
   return '<script>document.addEventListener("DOMContentLoaded",function(){'+code+'\n});<'+ '/script>';
 });
 html=html.replace(/src="(\/assets\/[^"]+)"/g,(m,k)=>B.assets[k]?.type==='image'?'src="'+B.assets[k].value+'"':m);
 const bridge='<script>window.__REVIEW_QUERY__='+JSON.stringify(query)+';document.addEventListener("click",e=>{const a=e.target.closest("a");if(!a)return;const h=a.getAttribute("href");if(h&&h.startsWith("/")){e.preventDefault();parent.postMessage({type:"review-route",path:h},"*");}});document.addEventListener("change",e=>{if(e.target.id==="market-category"&&document.querySelectorAll("#market-products .market-card").length<17){e.stopImmediatePropagation();const c=e.target.value;parent.postMessage({type:"review-route",path:c==="all"?"/shop/":"/shop/"+c+"/"},"*");}},true);const height=()=>parent.postMessage({type:"review-height",height:document.documentElement.scrollHeight},"*");window.addEventListener("load",height);new ResizeObserver(height).observe(document.documentElement);<'+ '/script>';
 html=html.replace('</head>',bridge+'</head>');frame.style.height='1000px';frame.srcdoc=html;scrollTo(0,0);
}
window.addEventListener('message',e=>{if(e.source!==frame.contentWindow)return;if(e.data?.type==='review-route'&&typeof e.data.path==='string'&&B.pages[e.data.path.split('?')[0]])location.hash=e.data.path;if(e.data?.type==='review-height'&&Number.isFinite(e.data.height))frame.style.height=Math.min(40000,Math.max(850,e.data.height))+'px';});
window.addEventListener('hashchange',show);show();
