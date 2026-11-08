"""Extend the existing customer catalogue with source-labelled Shopee listings.
No marketplace authentication, live inventory claims, invented prices or taste transfer.
"""
from pathlib import Path
from html import escape
from urllib.parse import urlsplit
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'catalogue/dist'
E=lambda s:escape(str(s or ''),quote=True)
CATEGORIES={'house':('House Blend','เมล็ดกาแฟ House Blend','เลือกจากระดับคั่วและกลิ่นรสที่ชอบ'),'single-origin':('Single Origin','เมล็ดกาแฟ Single Origin','ดูเมล็ดจากแต่ละแหล่งปลูก'),'capsules':('Capsules','กาแฟแคปซูล','ตรวจรุ่นเครื่องก่อนเลือกซื้อ'),'drip':('Drip Bags','กาแฟดริปแบบซอง','เลือกกาแฟบดบรรจุซองพร้อมชง'),'gifts':('Gift Sets','ชุดของขวัญ','เมล็ดกาแฟหรือแคปซูลในชุดเดียว'),'goods':('Coffee & Goods','อุปกรณ์และของใช้','Clever Dripper และกระเป๋าของร้าน')}
COLORS={'house':('#ead5c3','#503d30'),'single-origin':('#e2e8cf','#314c39'),'capsules':('#ddd5ee','#59476d'),'drip':('#f1d9b5','#654a2c'),'gifts':('#f1d5d3','#824d50'),'goods':('#d6e4e4','#31565b')}
def read(name):return json.loads((ROOT/'_data/brewtanist'/f'{name}.json').read_text(encoding='utf-8'))
def validate(data):
    if data.get('schemaVersion')!=1 or data.get('shopId')!='985117757':raise ValueError('Unexpected store/schema')
    ids=set();itemids=set()
    for p in data['items']:
        if not re.fullmatch('[a-z][a-z0-9-]{0,60}',p.get('id','')) or p['id'] in ids:raise ValueError('Duplicate/invalid listing id')
        ids.add(p['id'])
        if not re.fullmatch('[0-9]{8,15}',str(p.get('shopeeItemId',''))) or p['shopeeItemId'] in itemids:raise ValueError('Duplicate/invalid Shopee item')
        itemids.add(p['shopeeItemId'])
        if p.get('category') not in CATEGORIES or type(p.get('visible')) is not bool:raise ValueError('Invalid category/visibility')
        for k in ['name','description']:
            if not isinstance(p.get(k),str) or not p[k].strip() or len(p[k])>2000:raise ValueError('Invalid '+k)
        if not isinstance(p.get('details'),list) or any(not isinstance(x,str) or len(x)>500 for x in p['details']):raise ValueError('Invalid details')
        if any(k in p for k in ['price','stock','rating','sold','discount']):raise ValueError('Snapshot may not manufacture live commercial data')
        if p.get('houseId') and p['houseId'] not in ['plantman','ozmo','lazybug']:raise ValueError('Invalid house reference')
        if p.get('image'):
            f=(ROOT/p['image'].lstrip('/')).resolve();a=(ROOT/'brewtanist/assets').resolve()
            if not f.is_relative_to(a) or not f.is_file() or f.suffix.lower() not in ['.jpg','.jpeg','.png','.webp'] or not p.get('alt'):raise ValueError('Invalid listing image')
    return data

def extend(base):
    data=validate(read('marketplace'));house={p['id']:p for p in read('products')['items']};settings=read('settings')
    rows=[]
    for item in data['items']:
        if not item['visible']:continue
        p=dict(item);h=house.get(p.get('houseId'))
        if h and not h.get('visible'):continue
        if h:p.update(name=h['name'],description=h['description'],image=h['image'],alt=h['alt'])
        p['url']='https://shopee.co.th/product/'+data['shopId']+'/'+p['shopeeItemId']
        p['path']='/product/'+p['houseId']+'/' if h else '/item/'+p['id']+'/'
        if p.get('image'):
            f=(ROOT/p['image'].lstrip('/')).resolve();dest=OUT/'assets'/f.name
            if not dest.exists():shutil.copy2(f,dest)
            p['image']='/assets/'+f.name
        rows.append(p)
    for f in ['marketplace.css','marketplace.js']:shutil.copy2(ROOT/'catalogue'/f,OUT/'assets'/f)
    seed=json.dumps({'items':[{k:p[k] for k in ['id','name','description','category','path']} for p in rows]},ensure_ascii=False).replace('<','\\u003c')
    shell=(OUT/'index.html').read_text(encoding='utf-8');paths=[]
    def make(path,title,desc,body):
        text=re.sub(r'<main\b[^>]*>.*?</main>',lambda m:'<main class="wrap site-main" id="app" tabindex="-1">'+body+'</main>',shell,count=1,flags=re.S)
        text=re.sub(r'<title>.*?</title>',lambda m:'<title>'+E(title)+' | Brewtanist</title>',text,count=1,flags=re.S)
        text=re.sub(r'<meta name="description"[^>]*>',lambda m:'<meta name="description" content="'+E(desc)+'">',text,count=1)
        text=re.sub(r'<link rel="canonical"[^>]*>',lambda m:'<link rel="canonical" href="'+E(base+path)+'">',text,count=1)
        for key,value in [('title',title),('description',desc),('url',base+path)]:text=re.sub(r'<meta property="og:'+key+r'"[^>]*>',lambda m,v=value,k=key:'<meta property="og:'+k+'" content="'+E(v)+'">',text,count=1)
        ld=json.dumps({'@context':'https://schema.org','@type':'WebPage','name':title,'url':base+path,'description':desc},ensure_ascii=False).replace('<','\\u003c')
        text=re.sub(r'<script type="application/ld\+json">.*?</script>',lambda m:'<script type="application/ld+json">'+ld+'</script>',text,count=1,flags=re.S)
        text=text.replace('data-page="catalogue"','data-page="marketplace"')
        text=text.replace('</body>','<script type="application/json" id="marketplace-data">'+seed+'</script></body>')
        target=OUT/path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8');paths.append(path)
    def visual(p,large=False):
        cat=p['category'];tag=CATEGORIES[cat][0]
        if p.get('image'):return '<div class="market-visual image-visual '+E(cat)+'"><img src="'+E(p['image'])+'" alt="'+E(p['alt'])+'" width="720" height="720" loading="lazy"></div>'
        name=p['name'].split(' · ')[0]
        return '<div class="market-visual type-visual '+E(cat)+'"><span class="art-kicker">BREWTANIST / '+E(tag.upper())+'</span><span class="art-orbit" aria-hidden="true"></span><strong>'+E(name)+'</strong><span class="art-foot">'+E(tag)+'<span aria-hidden="true">↗</span></span></div>'
    def card(p):
        return '<article class="market-card" data-market-id="'+p['id']+'" data-category="'+p['category']+'"><a class="market-card-art" href="'+p['path']+'">'+visual(p)+'</a><div class="market-card-body"><span class="eyebrow">'+E(CATEGORIES[p['category']][1])+'</span><h3><a href="'+p['path']+'">'+E(p['name'])+'</a></h3><p>'+E(p['description'])+'</p><div class="market-card-links"><a class="text-link" href="'+p['path']+'">ดูรายละเอียด</a><a class="text-link" href="'+p['url']+'" target="_blank" rel="noopener noreferrer">ดูใน Shopee ↗</a></div></div></article>'
    def rail():
        return '<nav class="collection-rail" aria-label="หมวดสินค้า">'+''.join('<a class="collection-tile '+k+'" href="/shop/'+k+'/"><span class="eyebrow">'+str(i+1).zfill(2)+' / '+v[0]+'</span><strong>'+v[1]+'</strong><span>'+v[2]+' ↗</span></a>' for i,(k,v) in enumerate(CATEGORIES.items()))+'</nav>'
    controls='<div class="market-controls"><label for="market-search">ค้นหาสินค้า<input type="search" id="market-search" placeholder="ชื่อกาแฟ แคปซูล หรือของฝาก"></label><label for="market-category">หมวดสินค้า<select id="market-category"><option value="all">ทั้งหมด</option>'+''.join('<option value="'+k+'">'+v[1]+'</option>' for k,v in CATEGORIES.items())+'</select></label></div>'
    notice='<p class="market-notice">'+E(data['notice'])+'</p>'
    def listing(items,heading,description,category='all'):
        header='<section class="market-hero"><div><span class="eyebrow">THE BREWTANIST / TAKE HOME</span><h1>'+E(heading)+'</h1><p>'+E(description)+'</p><a class="text-link" href="/finder/">ยังเลือกไม่ถูก? ลองช่วยเลือกกาแฟ ↗</a></div><div class="market-hero-art" aria-hidden="true"><span>COFFEE<br>FOR<br>YOUR DAY.</span><i>✳</i></div></section>'
        options=controls.replace('value="'+category+'"','value="'+category+'" selected',1)
        return header+rail()+notice+'<section id="market-listing">'+options+'<p class="small" id="market-count" role="status">'+str(len(items))+' รายการ</p><div class="market-grid" id="market-products">'+''.join(card(p) for p in items)+'</div><div id="market-empty" class="empty" hidden><h2>ยังไม่พบสินค้าที่ค้นหา</h2><p>ลองเปลี่ยนคำค้นหรือเลือกดูทั้งหมด</p><a class="btn" href="/shop/">ดูสินค้าทั้งหมด</a></div></section>'
    make('/shop/',data['title'],data['intro'],listing(rows,data['title'],data['intro']))
    for key,meta in CATEGORIES.items():
        subset=[p for p in rows if p['category']==key]
        make('/shop/'+key+'/',meta[1],meta[2],listing(subset,meta[1],meta[2],key))
    for p in rows:
        if p.get('houseId'):continue
        cat=CATEGORIES[p['category']]
        detail='<nav class="breadcrumb" aria-label="ตำแหน่งหน้า"><a href="/shop/">สินค้าทั้งหมด</a> / <a href="/shop/'+p['category']+'/">'+E(cat[1])+'</a></nav><section class="detail-grid market-detail"><div>'+visual(p,True)+'<p class="fineprint">'+('ภาพสินค้าของร้าน' if p.get('image') else 'ภาพจัดวางตัวอักษร ดูภาพสินค้าจริงใน Shopee')+'</p></div><div class="detail-copy"><span class="eyebrow">'+E(cat[0])+'</span><h1>'+E(p['name'])+'</h1><p>'+E(p['description'])+'</p>'
        if p['details']:detail+='<ul class="source-facts">'+''.join('<li>'+E(x)+'</li>' for x in p['details'])+'</ul>'
        detail+='<div class="actions"><a class="btn" href="'+p['url']+'" target="_blank" rel="noopener noreferrer">ดูสินค้านี้ใน Shopee ↗</a></div>'+notice+'<p class="fineprint">รายละเอียดหน้านี้อ้างอิงชื่อรายการของร้านใน Shopee ยังไม่ได้เชื่อมราคาและสต็อกอัตโนมัติ</p></div></section><div class="section-top"><h2>ดูสินค้าในหมวดเดียวกัน</h2></div><div class="market-grid">'+''.join(card(q) for q in rows if q['category']==p['category'] and q['id']!=p['id'])+'</div>'
        make(p['path'],p['name'],p['description'],detail)
    banner='<section class="market-cross"><div><span class="eyebrow">MORE TO TAKE HOME</span><h2>มีมากกว่าเมล็ดกาแฟ</h2><p>ดูแคปซูล กาแฟดริป ชุดของขวัญ และของใช้จากร้าน</p></div><a class="btn" href="/shop/">ดูสินค้าทั้งหมด ↗</a></section>'+rail()
    home=OUT/'index.html';text=home.read_text(encoding='utf-8');text=text.replace('<section id="blends">',banner+'<section id="blends">',1);home.write_text(text,encoding='utf-8')
    for f in OUT.rglob('*.html'):
        text=f.read_text(encoding='utf-8')
        text=text.replace('<nav class="links" aria-label="เมนูหลัก">','<nav class="links" aria-label="เมนูหลัก"><a href="/shop/">สินค้าทั้งหมด</a>',1)
        text=text.replace('</head>','<link rel="stylesheet" href="/assets/marketplace.css"><script src="/assets/marketplace.js" defer></script></head>',1)
        f.write_text(text,encoding='utf-8')
    sm=OUT/'sitemap.xml';text=sm.read_text();text=text.replace('</urlset>',''.join('<url><loc>'+E(base+p)+'</loc></url>' for p in paths)+'</urlset>');sm.write_text(text)
    report={'result':'BUILT','imported_listings':len(rows),'new_listings':sum(not p.get('houseId') for p in rows),'categories':{k:sum(p['category']==k for p in rows) for k in CATEGORIES},'live_inventory':False,'live_prices':False,'individual_product_photos_pending':sum(not p.get('image') for p in rows),'source':data['sourceUrl'],'source_status':data['sourceStatus'],'detail_pages_access_verified':False,'direct_links':'mapped from shop ID and observed item IDs; not checkout tested'}
    qa=ROOT/'qa';qa.mkdir(exist_ok=True);(qa/'marketplace-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
