"""One-time, owner-requested copy edit and catalogue integration preparation.
Never runs on main. Does not publish or activate a guessed hosting URL.
"""
from pathlib import Path
import json, re, subprocess, yaml
ROOT=Path(__file__).resolve().parents[1]
STAMP=ROOT/'tools/THAI-APPLIED.json'
if STAMP.exists():
    print('Authored changes already applied; preserving subsequent owner edits.')
    raise SystemExit(0)
D=ROOT/'_data/brewtanist'
def load(name): return json.loads((D/(name+'.json')).read_text())
def save(name,data): (D/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
before={n:load(n) for n in ['home','coffee','products','roastery','gallery','faq','settings']}
h=load('home')
h.update(hero_text='คาเฟ่และโรงคั่วกาแฟในศรีมหาโพธิ ปราจีนบุรี อยู่ในปั๊ม Shell คลองรั้ง บนถนน 304 แวะดื่มกาแฟ พักระหว่างทาง หรือเลือกเมล็ดกลับไปชงที่บ้าน',hero_button='ดูพิกัดร้าน',hero_second_button='ดูเมนูที่ร้าน',hero_caption='แวะดื่มกาแฟกันได้ บนถนน 304',story_text='Brewtanist มาจาก Brew กับ Botanist สองความชอบของเรา คือกาแฟกับต้นไม้\n\nเราเลือกเมล็ด คั่ว และลองชง เพื่อหากลิ่นรสที่ชอบ ไม่ต้องรู้ศัพท์กาแฟมาก่อนก็แวะมาได้ ลองบอกบาริสต้าว่าปกติดื่มแบบไหน หรือวันนี้อยากลองรสอะไร',story_caption='บาร์กาแฟของเรา',visit_title='แวะมาดื่มกาแฟ\nที่ Brewtanist',visit_text='จะแวะพัก นั่งทำงาน หรือซื้อเมล็ดกลับบ้านก็ได้ ร้านมีที่นั่งชั้นล่างและชั้นบน มี Wi-Fi และที่จอดรถในบริเวณปั๊ม')
save('home',h)
c=load('coffee');c.update(title='วันนี้อยากดื่ม\nกาแฟแบบไหน?',description='มีทั้ง Espresso, Single Origin และกาแฟดริป ชอบรสแบบไหนบอกบาริสต้าได้ ส่วนใครไม่ได้ดื่มกาแฟ ลองดูมัทฉะกับขนมของร้าน')
for card,text in zip(c['cards'],['House Blend ของเรามี Mr. Plantman, Mr. Ozmo และ Ms. Lazybug แต่ละตัวต่างกันที่กลิ่นรสและระดับคั่ว','เมล็ด Single Origin สลับกันมาตามช่วง มีทั้ง Filter และ Pour Over ถามบาริสต้าได้ว่าวันนี้มีเมล็ดอะไรบ้าง','มีมัทฉะกับเบเกอรี่โฮมเมด ทั้งสโคน ครัวซองต์ และเค้ก ขนมแต่ละวันอาจไม่เหมือนกัน']): card['text']=text
save('coffee',c)
p=load('products');p.update(title='เลือกกาแฟ\nกลับไปชงที่บ้าน',description='ชอบโทนช็อกโกแลต หอมวานิลลา หรือกลิ่นผลไม้? ลองดู House Blend ของเรา แล้วเลือกจากรสที่ชอบ',note='มี Single Origin, กาแฟดริปแบบซอง และแคปซูลด้วย ดูรายการล่าสุดที่ Shopee หรือสอบถามร้านได้',button='ดูสินค้าใน Shopee',finder_title='ยังเลือกไม่ถูก?',finder_text='ตอบ 3 ข้อจากกาแฟที่ชอบดื่ม แล้วลองดูว่าเมล็ดตัวไหนน่าลอง')
ids={'Mr. Plantman':'plantman','Mr. Ozmo':'ozmo','Ms. Lazybug':'lazybug'}
desc={'plantman':'เข้มข้น โทนดาร์กช็อกโกแลต คาราเมล และถั่ว ชงเป็นกาแฟดำหรือใส่นมก็ได้','ozmo':'กลิ่นรสโทนวานิลลา รัมเรซิน และมิลก์ช็อกโกแลต หอมหวานและเข้มข้น','lazybug':'กลิ่นรสโทนดอกไม้ ผลไม้ และชา เหมาะกับคนที่ชอบกาแฟดำโทนสดชื่น'}
taste={'plantman':['chocolate'],'ozmo':['chocolate','sweet'],'lazybug':['fruity']};drinks={'plantman':['black','milk'],'ozmo':[],'lazybug':['black']}
for item in p['items']:
    ident=ids[item['name']];item.update(id=ident,description=desc[ident],price='',sizes='',grinding='',origin='',productUrl='',tasteTags=taste[ident],drinkTags=drinks[ident],verified=False)
save('products',p)
r=load('roastery');r.update(title='จากโรงคั่ว\nถึงแก้วกาแฟ',description='เราคั่วกาแฟสำหรับชงที่ร้านและขายเป็นเมล็ดกลับบ้าน มีทั้ง House Blend และ Single Origin ลองชงและปรับสูตรไปพร้อมกับการคั่ว')
for step,title,text in zip(r['steps'],['เลือกเมล็ด','คั่วกาแฟ','ลองชง'],['เลือกเมล็ดจากกลิ่นรสที่สนใจ แล้วลองหาวิธีชงที่เข้ากัน','ปรับการคั่วโดยดูทั้งความหวาน กลิ่นรส ความหนักแน่น และความเปรี้ยวของกาแฟ','ชิมและปรับสูตรชง ก่อนนำมาใช้ที่บาร์']):step.update(title=title,text=text)
save('roastery',r)
g=load('gallery');g.update(title='มุมต่าง ๆ\nของ Brewtanist',description='ดูบรรยากาศร้าน กาแฟ และขนม ก่อนแวะมาเจอกัน')
for img,caption in zip(g['images'],['บาร์กาแฟ','กาแฟกับขนม','เครื่องดื่มแอปเปิ้ล','เครื่องดื่มกับใบไม้','Cold Brew','อีกแก้วจาก Brewtanist','เรื่องราวของร้าน']): img['caption']=caption
save('gallery',g)
f=load('faq');f['title']='ก่อนแวะมาที่ร้าน'
for item,answer in zip(f['items'],['จอดรถได้ในบริเวณปั๊ม Shell','มีเมล็ด House Blend, Single Origin, กาแฟดริปแบบซอง และแคปซูล รายการที่มีขายสอบถามร้านได้','มี Single Origin สลับกันมาให้ลอง ทั้ง Filter และ Pour Over ส่วน Espresso เลือกเมล็ดได้ตามรายการของร้าน','มีมัทฉะและเบเกอรี่โฮมเมด ขนมแต่ละวันอาจไม่เหมือนกัน']):item['answer']=answer
save('faq',f)
s=load('settings');s['catalogue_url']='';s['seo_description']='Brewtanist คาเฟ่และโรงคั่วกาแฟในศรีมหาโพธิ ปราจีนบุรี อยู่ในปั๊ม Shell คลองรั้ง ถนน 304 มี Espresso กาแฟดริป มัทฉะ เบเกอรี่ และเมล็ดกาแฟกลับบ้าน';save('settings',s)
# Rewrite customer-facing labels, without touching layout, brand fonts or business facts.
file=ROOT/'index.html';text=file.read_text()
for old,new in [('>Our story<','>เรื่องราวของเรา<'),('>Coffee<','>เมนูที่ร้าน<'),('>Take home<','>กาแฟกลับบ้าน<'),('>Gallery<','>บรรยากาศร้าน<'),('>Visit us<','>พิกัดร้าน<'),('>Roastery<','>โรงคั่วกาแฟ<'),('>Location<','>ที่ตั้ง<'),('>Find us<','>จุดสังเกต<'),('>Payment<','>ชำระเงิน<'),('More from Brewtanist on Instagram','ดูรูปเพิ่มเติมใน Instagram'),('A few things to know','คำถามที่พบบ่อย')]:text=text.replace(old,new)
marker='{%- assign f = site.data.brewtanist.faq -%}'
text=text.replace(marker,marker+"\n{%- assign catalogue_ready = false -%}\n{%- assign catalogue_prefix = s.catalogue_url | slice: 0, 8 -%}\n{%- if catalogue_prefix == 'https://' -%}{%- assign catalogue_ready = true -%}{%- endif -%}")
old='<a href="#products">กาแฟกลับบ้าน</a>'
new='''{% if catalogue_ready %}<details class="coffee-menu"><summary>กาแฟกลับบ้าน</summary><div><a href="{% include brewtanist-url.html url=s.catalogue_url %}">ดูกาแฟทั้งหมด</a><a href="{% include brewtanist-url.html url=s.catalogue_url %}/finder/">ช่วยเลือกกาแฟ</a></div></details>{% else %}<a href="#products">กาแฟกลับบ้าน</a>{% endif %}'''
assert text.count(old)==2;text=text.replace(old,new)
old='<div class="product-stage {{ item.theme | escape }}">'
text=text.replace(old,'{% if catalogue_ready and item.id %}<a href="{% include brewtanist-url.html url=s.catalogue_url %}/product/{{ item.id | escape }}/" aria-label="ดู {{ item.name | escape }}">{% endif %}'+old)
old='<div class="product-body"><small>{{ item.profile | escape }}</small>'
text=text.replace(old,'{% if catalogue_ready and item.id %}</a>{% endif %}'+old)
old='<p>{{ item.description | escape }}</p></div></article>'
assert old in text;text=text.replace(old,'<p>{{ item.description | escape }}</p>{% if catalogue_ready and item.id %}<a class="text-link" href="{% include brewtanist-url.html url=s.catalogue_url %}/product/{{ item.id | escape }}/">ดูรายละเอียด ↗</a>{% endif %}</div></article>')
old='<div class="products-bottom">'
text=text.replace(old,'''{% if catalogue_ready %}<div class="catalogue-invite"><div><h3>{{ p.finder_title | escape }}</h3><p>{{ p.finder_text | escape }}</p></div><a class="btn" href="{% include brewtanist-url.html url=s.catalogue_url %}/finder/">ช่วยเลือกกาแฟ ↗</a></div>{% endif %}
    '''+old)
text=text.replace('site.css?v=20260912','site.css?v=20261108-th');file.write_text(text)
css=ROOT/'brewtanist/site.css';css.write_text(css.read_text()+'''\n/* Customer catalogue connection, activated only after verified hosting. */
.coffee-menu{position:relative}.coffee-menu summary{cursor:pointer;list-style:none}.coffee-menu summary:after{content:' ▾'}.coffee-menu>div{position:absolute;top:100%;left:0;min-width:190px;padding:12px;background:#fffdf7;border:1px solid #d5d6cc;box-shadow:0 10px 25px #203a3014;z-index:50}.coffee-menu>div a{display:block;padding:9px}.catalogue-invite{display:flex;justify-content:space-between;gap:24px;align-items:center;margin:30px 0;padding:26px;background:#e4e9da;border-radius:8px}.catalogue-invite p{margin-top:8px}.product-body .text-link{display:inline-block;margin-top:12px}
@media(max-width:800px){.coffee-menu>div{position:static;box-shadow:none}.catalogue-invite{align-items:flex-start;flex-direction:column}}
''')
# Keep the existing seven CMS forms; extend the actual product form, not a parallel local editor.
config=yaml.safe_load((ROOT/'.pages.yml').read_text());config.setdefault('settings',{}).setdefault('content',{})['merge']=True
product_form=next(x for x in config['content'] if x['name']=='products')
product_form['fields'] += [{'name':'finder_title','label':'หัวข้อช่วยเลือกกาแฟ','type':'string'},{'name':'finder_text','label':'ข้อความชวนเลือกกาแฟ','type':'text'}]
fields=next(x for x in product_form['fields'] if x['name']=='items')['fields']
fields.insert(0,{'name':'id','label':'รหัสลิงก์สินค้า (ห้ามเปลี่ยน)','type':'string','readonly':True})
for key,label in [('price','ราคา (บาท ไม่ใส่หน่วย)'),('sizes','ขนาดถุงที่ขาย'),('grinding','ตัวเลือกการบด'),('origin','แหล่งปลูก'),('productUrl','ลิงก์สินค้าใน Shopee')]:fields.append({'name':key,'label':label,'type':'string'})
for key,label,values in [('tasteTags','กลิ่นรสสำหรับช่วยเลือกกาแฟ',[('chocolate','ช็อกโกแลต / ถั่ว'),('sweet','วานิลลา / รัมเรซิน'),('fruity','ดอกไม้ / ผลไม้ / ชา')]),('drinkTags','มีข้อมูลว่าเหมาะกับ',[('black','กาแฟดำ'),('milk','กาแฟนม')])]:fields.append({'name':key,'label':label,'type':'select','options':{'multiple':True,'values':[{'name':v,'label':t} for v,t in values]}})
fields.append({'name':'verified','label':'ตรวจราคา ขนาด และข้อมูลสำหรับแนะนำแล้ว','type':'boolean'})
next(x for x in config['content'] if x['name']=='settings')['fields'].append({'name':'catalogue_url','label':'ที่อยู่เว็บกาแฟกลับบ้าน (ผู้ดูแลเปิดหลังตรวจ Hosting)','type':'string','readonly':True})
(ROOT/'.pages.yml').write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False))
jc=yaml.safe_load((ROOT/'_config.yml').read_text());jc['exclude']=list(dict.fromkeys(jc.get('exclude',[])+['catalogue','tools','qa','render.yaml','RELEASE.md']))
(ROOT/'_config.yml').write_text(yaml.safe_dump(jc,allow_unicode=True,sort_keys=False))
# Reuse the approved preview's visual design, not its editor or experimental router.
source=subprocess.check_output(['git','show','30b43dc95ceb947618428499fd106fb46f8a5fb8:prototype/template.html'],text=True)
style=re.search(r'<style>(.*?)</style>',source,re.S).group(1)
(ROOT/'catalogue/site.css').write_text(style+'\n[hidden]{display:none!important}.site-main{min-height:65vh}.links{flex-wrap:wrap}.price{font-size:22px;font-weight:600;margin:18px 0}.simple-note{font-size:13px;margin-top:18px}.choices label{cursor:pointer}.choice input{accent-color:#203a30}.compare-dock{gap:12px}.link-note{margin:18px 0 42px}.facts:empty{display:none}.hero-art .art-bottom{font-size:11px}.product-card h3{font-size:25px}.question[hidden]{display:none}.quiz-count{margin-bottom:15px}@media(max-width:600px){.nav-inner{gap:10px;flex-wrap:wrap;padding:14px 0}.links{gap:13px;font-size:12px}.wordmark{font-size:21px}.foot .wrap{flex-direction:column}.detail-stage{height:380px}.hero-art .art-bottom{font-size:9px}}\n')
# Business identifiers, images, roast and notes remain exact; only authored descriptions changed.
after={n:load(n) for n in before}
for k in ['brand','descriptor','phone','address','opening_days','opens','closes','days','maps','facebook','instagram','tiktok','shopee','payment']:assert before['settings'][k]==after['settings'][k],k
for a,b in zip(before['products']['items'],after['products']['items']):
    for k in ['name','profile','notes','image','alt','theme','visible']:assert a[k]==b[k],k
STAMP.write_text(json.dumps({'source':'d5fb938873581dbc21ad1fafcdc9d89a5695313d','copy_review':'09-thai-voice.md; 02-copywriter.md','catalogue_connection_active':False,'reason':'No authorized catalogue hosting URL yet','business_facts_preserved':True},ensure_ascii=False,indent=2)+'\n')
print('Thai copy and gated integration prepared; no URL was invented.')
