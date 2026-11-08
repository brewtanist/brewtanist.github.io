"""One-time, idempotent integration. Never overwrites existing owner copy or URLs."""
from pathlib import Path
import json,yaml
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'catalogue/build.py';s=p.read_text();needle='    main(args.base_url)'
if '    extend(args.base_url)' not in s:
    if s.count(needle)!=1:raise ValueError('Unexpected builder entry point')
    s=s.replace(needle,needle+'\n    from marketplace import extend\n    extend(args.base_url)');p.write_text(s)
mp=ROOT/'_data/brewtanist/marketplace.json';data=json.loads(mp.read_text())
for item in data['items']:
    if item['id']=='thailand-ban-huay-khanum':item['description']='เมล็ดกาแฟไทย Ban Huay Khanum แปรรูปแบบ Red Honey'
mp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'_data/brewtanist/products.json';products=json.loads(p.read_text())
links={x['houseId']:'https://shopee.co.th/product/'+data['shopId']+'/'+x['shopeeItemId'] for x in data['items'] if x.get('houseId')}
for item in products['items']:
    if not item.get('productUrl') and item['id'] in links:item['productUrl']=links[item['id']]
p.write_text(json.dumps(products,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'.pages.yml';cms=yaml.safe_load(p.read_text())
if not any(x['name']=='marketplace' for x in cms['content']):
    fields=[{'name':'title','label':'หัวเรื่องสินค้าทั้งหมด','type':'text','required':True},{'name':'intro','label':'คำแนะนำใต้หัวเรื่อง','type':'text'},{'name':'notice','label':'หมายเหตุก่อนสั่งซื้อ','type':'text'},{'name':'sourceNote','label':'ที่มาและข้อจำกัดของข้อมูล','type':'text','readonly':True},{'name':'items','label':'สินค้าจาก Shopee (รายการเดิมให้ซ่อนแทนลบ)','type':'object','list':True,'fields':[
      {'name':'id','label':'รหัสหน้าเว็บ','type':'string','readonly':True},
      {'name':'houseId','label':'อ้างอิง House Blend เดิม','type':'string','readonly':True},
      {'name':'name','label':'ชื่อสินค้า','type':'string','required':True},
      {'name':'category','label':'หมวดสินค้า','type':'select','options':{'values':['house','single-origin','capsules','drip','gifts','goods']}},
      {'name':'shopeeItemId','label':'รหัสสินค้า Shopee (ร้าน 985117757)','type':'string','readonly':True},
      {'name':'visible','label':'แสดงในเว็บไซต์','type':'boolean'},
      {'name':'description','label':'คำอธิบายสินค้า','type':'text','required':True},
      {'name':'details','label':'รายละเอียดที่ตรวจจากสินค้าแล้ว','type':'string','list':True},
      {'name':'image','label':'ภาพจริงของสินค้านี้ (เว้นว่างได้ ไม่ใช้ภาพของตัวอื่นแทน)','type':'image'},
      {'name':'alt','label':'คำอธิบายภาพ','type':'string'}]}]
    cms['content'].append({'name':'marketplace','label':'08 · สินค้าจาก Shopee','type':'file','path':'_data/brewtanist/marketplace.json','format':'json','fields':fields})
    p.write_text(yaml.safe_dump(cms,allow_unicode=True,sort_keys=False))
p=ROOT/'tools/test_release.py';s=p.read_text();s=s.replace("assert len(cms['content'])==7;", "assert len(cms['content'])==8;assert any(x['name']=='marketplace' for x in cms['content']);")
p.write_text(s)
p=ROOT/'catalogue/marketplace.js';s=p.read_text();s=s.replace("if(select.value==='all'&&cards.length<data.items.length){location.href='/shop/';return;}","if(cards.length<data.items.length){location.href=select.value==='all'?'/shop/':'/shop/'+select.value+'/';return;}");p.write_text(s)
print('Marketplace integrated; original business details and owner copy preserved; no price or stock imported.')
