"""Build a customer-only static catalogue from the same data as the main site.
No credentials, local editor, checkout, tracker, third-party scripts or API calls.
"""
from pathlib import Path
from urllib.parse import urlsplit
from html import escape
import argparse, json, os, re, shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'catalogue/dist'
D=ROOT/'_data/brewtanist'
E=lambda x:escape(str(x or ''),quote=True)
def read(name): return json.loads((D/(name+'.json')).read_text())
def url(value,host=None):
    p=urlsplit(value or '')
    if p.scheme!='https' or not p.hostname or p.username or p.password or (host and p.hostname!=host):raise ValueError('Invalid HTTPS link')
    return value

def main(base):
    base=url(base).rstrip('/');preview=urlsplit(base).hostname.endswith('.invalid')
    source=read('products');settings=read('settings');home=read('home')
    shop=url(settings['shopee'],'shopee.co.th');maps=url(settings['maps']);main_url='https://brewtanist.github.io/'
    products=source['items'];seen=set()
    for p in products:
        if not re.fullmatch('[a-z][a-z0-9-]{0,40}',p.get('id','')) or p['id'] in seen:raise ValueError('Invalid or duplicate product id')
        seen.add(p['id'])
        for k in ['name','profile','notes','description','alt']:
            if not isinstance(p.get(k),str) or not p[k].strip() or len(p[k])>5000:raise ValueError('Invalid text '+k)
        for k in ['visible','verified']:
            if type(p.get(k)) is not bool:raise ValueError('Invalid boolean '+k)
        if p.get('price') and (not re.fullmatch(r'[0-9]{1,6}(\.[0-9]{1,2})?',str(p['price'])) or float(p['price'])<=0):raise ValueError('Invalid price')
        if p.get('productUrl'):url(p['productUrl'],'shopee.co.th')
        for k,values in [('tasteTags',{'chocolate','sweet','fruity'}),('drinkTags',{'black','milk'})]:
            if not isinstance(p.get(k),list) or not set(p[k])<=values:raise ValueError('Invalid recommendation tags')
        if p['theme'] not in ['plantman','ozmo','lazybug']:raise ValueError('Invalid theme')
    if OUT.exists():shutil.rmtree(OUT)
    (OUT/'assets').mkdir(parents=True)
    def asset(path):
        f=(ROOT/path.lstrip('/')).resolve();allowed=(ROOT/'brewtanist/assets').resolve()
        if not f.is_relative_to(allowed) or f.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'} or not f.is_file():raise ValueError('Invalid owned image')
        if f.stat().st_size>8_000_000:raise ValueError('Image too large')
        shutil.copy2(f,OUT/'assets'/f.name)
        return '/assets/'+f.name
    visible=[]
    for original in products:
        if original['visible']:
            p=dict(original);p['image']=asset(p['image']);visible.append(p)
    hero=asset(home['hero_image'])
    shutil.copy2(ROOT/'catalogue/site.css',OUT/'assets/site.css');shutil.copy2(ROOT/'catalogue/site.js',OUT/'assets/site.js')
    client=json.dumps({'products':visible,'shop':shop},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    paths=[]
    def page(path,title,description,body,active='catalogue',schema=None):
        absolute=base+path;seo={'@context':'https://schema.org','@type':'WebPage','name':title,'url':absolute,'description':description}
        if schema:seo=schema
        ld=json.dumps(seo,ensure_ascii=False).replace('<','\\u003c')
        h=f'''<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} | Brewtanist</title><meta name="description" content="{E(description)}"><meta name="robots" content="{'noindex,nofollow' if preview or active=='compare' else 'index,follow'}"><link rel="canonical" href="{E(absolute)}"><meta property="og:type" content="website"><meta property="og:locale" content="th_TH"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{E(absolute)}"><meta property="og:image" content="{E(base+hero)}"><meta name="theme-color" content="#f7f4eb"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Bai+Jamjuree:wght@400;500;600;700&family=Lexend:wght@400;500;600&family=MuseoModerno:wght@500;600;700;800&display=swap" rel="stylesheet"><link rel="stylesheet" href="/assets/site.css"><script src="/assets/site.js" defer></script><script type="application/ld+json">{ld}</script></head><body data-page="{active}"><a class="skip" href="#app">ข้ามไปยังเนื้อหา</a><header class="nav"><div class="wrap nav-inner"><a class="wordmark" href="{main_url}">The Brewtanist<small>Cafe & Coffee Roaster</small></a><nav class="links" aria-label="เมนูหลัก"><a href="/">กาแฟกลับบ้าน</a><a href="/finder/">ช่วยเลือกกาแฟ</a><a href="/compare/">เทียบกาแฟ</a><a href="{main_url}#visit">พิกัดร้าน ↗</a></nav></div></header><main class="wrap site-main" id="app" tabindex="-1">{body}</main><footer class="foot"><div class="wrap"><div><strong>The Brewtanist</strong><br>Cafe & Coffee Roaster · ปราจีนบุรี</div><div><a class="text-link" href="{main_url}">กลับเว็บไซต์ร้าน</a> · <a class="text-link" href="{E(maps)}" target="_blank" rel="noopener noreferrer">เปิดแผนที่ ↗</a><br>เลือกสินค้าและชำระเงินใน Shopee</div></div></footer><div id="dock"></div><script id="catalogue-data" type="application/json">{client}</script></body></html>'''
        target=OUT/path.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(h)
        if active!='compare':paths.append(path)
    def card(p):
        return f'''<article class="product-card" data-id="{p['id']}" data-taste="{' '.join(p['tasteTags'])}"><a class="stage {E(p['theme'])}" href="/product/{p['id']}/"><span class="index">HOUSE BLEND</span><img src="{E(p['image'])}" alt="{E(p['alt'])}" width="600" height="600"><span class="arrow" aria-hidden="true">↗</span></a><div class="card-body"><span class="eyebrow">{E(p['profile'])}</span><h3><a href="/product/{p['id']}/">{E(p['name'])}</a></h3><p class="notes">{E(p['notes'])}</p><p>{E(p['description'])}</p><div class="card-bottom"><a class="text-link" href="/product/{p['id']}/">ดูรายละเอียด ↗</a><label class="compare-label"><input type="checkbox" data-compare="{p['id']}" aria-label="เลือกเทียบ {E(p['name'])}">เลือกเทียบ</label></div></div></article>'''
    cards=''.join(card(p) for p in visible)
    art=''.join(f'<img src="{E(p["image"])}" alt="{E(p["alt"])}" width="500" height="500">' for p in visible[:3])
    filters=''.join(f'<button class="chip" type="button" data-filter="{k}" aria-pressed="{str(k=="all").lower()}">{label}</button>' for k,label in [('all','ทั้งหมด'),('chocolate','ช็อกโกแลต / ถั่ว'),('sweet','วานิลลา / รัมเรซิน'),('fruity','ดอกไม้ / ผลไม้')])
    body=f'''<section class="hero"><div class="hero-copy"><span class="eyebrow">THE BREWTANIST / HOUSE BLENDS</span><h1>{E(source['title'])}</h1><p>{E(source['description'])}</p><div class="actions"><a class="btn" href="/finder/">ช่วยเลือกกาแฟ ↗</a><a class="text-link" href="#blends">ดูกาแฟทั้งหมด ↓</a></div><div class="mini-note">ตอบ 3 ข้อ ไม่ต้องสมัครสมาชิก</div></div><div class="hero-art">{art}<span class="art-top">BREWTANIST HOUSE BLENDS</span><span class="seal" aria-hidden="true">✳</span><div class="art-bottom"><span>Mr. Plantman · Mr. Ozmo · Ms. Lazybug</span></div></div></section><section id="blends"><div class="section-top"><div><span class="eyebrow">OUR HOUSE BLENDS</span><h2>เลือกจากรสที่ชอบ</h2></div><p>ดูระดับคั่วและกลิ่นรสของแต่ละตัว หรือเลือกไว้เทียบกันก่อน</p></div><div class="catalog-controls"><div class="filters" aria-label="กรองกลิ่นรส">{filters}</div><input class="search" id="search" aria-label="ค้นหากาแฟ" placeholder="ค้นชื่อกาแฟหรือกลิ่นรส" type="search"></div><p id="result-count" role="status" class="small">{len(visible)} รายการ</p><div class="cards" id="product-list">{cards}</div><div class="empty" id="empty-search" hidden><h3>ไม่พบกาแฟที่ค้นหา</h3><p>ลองใช้ชื่อกาแฟหรือกลิ่นรส เช่น ช็อกโกแลต หรือผลไม้</p><button type="button" class="btn light" id="reset-search">ดูทั้งหมด</button></div></section><section class="finder-banner"><div><span class="eyebrow">COFFEE FINDER</span><h2>ยังเลือกไม่ถูก?</h2><p>{E(source['finder_text'])}</p><a class="btn" href="/finder/">ลองเลือกกาแฟ ↗</a></div><div class="steps-mini"><div><b>01</b><span>เลือกแบบที่อยากซื้อ</span></div><div><b>02</b><span>บอกกลิ่นรสที่ชอบ</span></div><div><b>03</b><span>ดื่มดำหรือใส่นม</span></div></div></section><section class="story-strip"><img src="{hero}" alt="{E(home['hero_alt'])}" width="700" height="470" loading="lazy"><div><span class="eyebrow">BREWTANIST / PRACHINBURI</span><h2>แวะมาดื่มกาแฟที่ร้าน</h2><p>อยู่ในปั๊ม Shell คลองรั้ง บนถนน 304 จะมานั่งดื่มหรือเลือกเมล็ดกลับบ้านก็ได้</p><a class="text-link" href="{main_url}#visit">ดูพิกัดและเวลาเปิด ↗</a></div></section>'''
    page('/','กาแฟกลับบ้าน',source['description'],body)
    for p in visible:
        facts=''.join(f'<div><dt>{label}</dt><dd>{E(p.get(key))}</dd></div>' for key,label in [('sizes','ขนาดถุง'),('grinding','การบด'),('origin','แหล่งปลูก')] if p.get(key) and p['verified'])
        price=f'<p class="price">{float(p["price"]):,.2f} บาท</p>' if p.get('price') and p.get('sizes') and p['verified'] else ''
        link=p.get('productUrl') or shop;cta='ดูสินค้านี้ใน Shopee' if p.get('productUrl') else 'ดูสินค้าในร้าน Shopee'
        body=f'''<nav class="breadcrumb" aria-label="ตำแหน่งหน้า"><a href="/">กาแฟกลับบ้าน</a> / {E(p['name'])}</nav><section class="detail-grid"><div><div class="stage detail-stage {E(p['theme'])}"><img src="{E(p['image'])}" alt="{E(p['alt'])}" width="900" height="900"></div><p class="fineprint">ภาพจำลองบรรจุภัณฑ์</p></div><div class="detail-copy"><span class="eyebrow">{E(p['profile'])}</span><h1>{E(p['name'])}</h1><p class="notes">{E(p['notes'])}</p><p>{E(p['description'])}</p>{price}<dl class="facts">{facts}</dl><div class="actions"><a class="btn" href="{E(link)}" target="_blank" rel="noopener noreferrer">{cta} ↗</a><label class="compare-label"><input type="checkbox" data-compare="{p['id']}" aria-label="เลือกเทียบ {E(p['name'])}">เลือกเทียบ</label></div><p class="simple-note">ดูราคา ขนาดถุง และตัวเลือกการบดใน Shopee ก่อนสั่งซื้อ</p><p class="simple-note">ชื่อกลิ่นรสใช้บรรยายกาแฟ ไม่ใช่รายการส่วนผสม</p></div></section><div class="section-top"><h2>ลองดูตัวอื่นด้วย</h2></div><div class="cards">{''.join(card(q) for q in visible if q['id']!=p['id'])}</div>'''
        page('/product/'+p['id']+'/',p['name'],p['description'],body)
    questions=[('กำลังหากาแฟแบบไหน?','เลือกแบบที่อยากซื้อกลับไปชง',[('beans','เมล็ดกาแฟ','สำหรับอุปกรณ์ชงที่บ้าน'),('capsules','กาแฟแคปซูล','ใช้กับเครื่องชงแคปซูล'),('drip','กาแฟดริปแบบซอง','Drip Bag')]),('ชอบกลิ่นรสแบบไหน?','เลือกข้อที่ใกล้กับกาแฟที่ชอบดื่ม',[('chocolate','ช็อกโกแลต / ถั่ว',''),('sweet','วานิลลา / รัมเรซิน',''),('fruity','ดอกไม้ / ผลไม้ / ชา',''),('unsure','ยังไม่แน่ใจ','ลองดูหลายตัวก่อน')]),('ปกติดื่มดำหรือใส่นม?','นึกถึงแก้วที่ชงหรือสั่งบ่อยที่สุด',[('black','กาแฟดำ','ไม่ใส่นม'),('milk','กาแฟนม','เติมนมในแก้ว'),('unsure','ดื่มได้ทั้งสองแบบ','เลือกจากกลิ่นรสก่อน')])]
    fields=''
    for i,(heading,intro,options) in enumerate(questions):
        choices=''.join(f'<label class="choice"><span><b>{label}</b><small>{small}</small></span><input type="radio" name="q{i}" value="{v}"></label>' for v,label,small in options)
        fields+=f'<section class="question" data-step="{i}" {"hidden" if i else ""}><h2>{heading}</h2><p>{intro}</p><div class="choices">{choices}</div></section>'
    body=f'''<div class="page-head"><span class="eyebrow">COFFEE FINDER</span><h1>ชอบกาแฟแบบไหน?</h1><p>ตอบ 3 ข้อ แล้วลองดูกาแฟที่ใกล้กับรสที่ชอบ ไม่แน่ใจข้อไหนก็ข้ามด้วยคำตอบ “ยังไม่แน่ใจ” ได้</p></div><div class="quiz-layout"><aside class="quiz-rail"><h3>ตอบแค่ 3 ข้อ</h3><p>ไม่ต้องสมัครสมาชิกหรือกรอกเบอร์โทร คำตอบใช้แนะนำกาแฟในหน้านี้เท่านั้น</p><div id="quiz-count" class="quiz-count" aria-live="polite">ข้อ 1 / 3</div></aside><section><form id="finder-form">{fields}<div class="quiz-actions"><button class="text-link" id="quiz-back" type="button" disabled>← ย้อนกลับ</button><button class="btn" id="quiz-next" type="button" disabled>ถัดไป →</button></div></form><div id="finder-result" aria-live="polite" hidden></div><noscript><p>เปิด JavaScript เพื่อใช้ตัวช่วยเลือกกาแฟ หรือกลับไปดูกาแฟทั้งหมดได้</p><a class="btn" href="/">ดูกาแฟทั้งหมด</a></noscript></section></div>'''
    page('/finder/','ช่วยเลือกกาแฟ','เลือกจากแบบกาแฟ กลิ่นรส และวิธีดื่มที่ชอบ',body,'finder')
    rows=''.join('<tr><th scope="row">'+label+'</th>'+''.join('<td data-col="'+p['id']+'">'+E(p[k])+'</td>' for p in visible)+'</tr>' for k,label in [('profile','ระดับคั่ว'),('notes','กลิ่นรส'),('description','เหมาะกับรสแบบไหน')])
    heads=''.join(f'<th scope="col" data-col="{p["id"]}"><div class="mini-stage"><img src="{p["image"]}" alt="{E(p["alt"])}" width="300" height="300"></div><h3><a href="/product/{p["id"]}/">{E(p["name"])}</a></h3></th>' for p in visible)
    body=f'<div class="page-head"><span class="eyebrow">HOUSE BLENDS</span><h1>เทียบกาแฟที่สนใจ</h1><p>ดูระดับคั่วและกลิ่นรสข้างกัน แล้วเลือกตัวที่อยากลอง</p></div><div class="table-wrap" tabindex="0" aria-label="ตารางเทียบกาแฟ เลื่อนซ้ายขวาได้"><table class="compare-table"><caption class="screen-reader">เปรียบเทียบ House Blend</caption><thead><tr><th scope="col">กาแฟ</th>{heads}</tr></thead><tbody>{rows}</tbody></table></div><p class="link-note"><a class="text-link" href="/">← กลับไปเลือกกาแฟ</a></p>'
    page('/compare/','เทียบกาแฟ','เปรียบเทียบ House Blend ของ Brewtanist',body,'compare')
    notfound='<div class="page-head"><h1>ไม่พบหน้านี้</h1><p>ลิงก์อาจเปลี่ยนไปแล้ว ลองกลับไปดูกาแฟทั้งหมด</p><a class="btn" href="/">ดูกาแฟทั้งหมด</a></div>'
    page('/not-found/','ไม่พบหน้า','กลับไปดูกาแฟทั้งหมด',notfound,'compare');shutil.copy2(OUT/'not-found/index.html',OUT/'404.html');shutil.rmtree(OUT/'not-found')
    (OUT/'robots.txt').write_text('User-agent: *\n'+('Disallow: /\n' if preview else 'Allow: /\nSitemap: '+base+'/sitemap.xml\n'))
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+E(base+p)+'</loc></url>' for p in paths)+'</urlset>')
    print(json.dumps({'pages':len(paths)+1,'visible_products':len(visible),'base_url':base,'preview':preview,'checkout':False,'editor_in_customer_bundle':False},ensure_ascii=False))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default=os.environ.get('CATALOGUE_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL'));args=parser.parse_args()
    if not args.base_url:parser.error('Set CATALOGUE_BASE_URL or use the host-provided RENDER_EXTERNAL_URL; do not guess a production URL')
    main(args.base_url)
    from marketplace import extend
    extend(args.base_url)
