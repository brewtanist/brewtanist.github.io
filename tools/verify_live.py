"""Verify the public main site after the approved copy is published."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from html import unescape
from html.parser import HTMLParser
import concurrent.futures,hashlib,json,time,os
ROOT=Path(__file__).resolve().parents[1];BASE='https://brewtanist.github.io';QA=ROOT/'qa';QA.mkdir(exist_ok=True)
def get(path):
    with urlopen(Request(BASE+path,headers={'User-Agent':'BrewtanistReleaseVerify/1.0','Cache-Control':'no-cache'}),timeout=30) as r:
        assert r.status==200
        return r.read()
home=json.loads((ROOT/'_data/brewtanist/home.json').read_text());settings=json.loads((ROOT/'_data/brewtanist/settings.json').read_text())
marketplace=json.loads((ROOT/'_data/brewtanist/marketplace.json').read_text())
visible=[item for item in marketplace['items'] if item.get('visible') is True]
class Assets(HTMLParser):
    def __init__(self):super().__init__();self.paths=set()
    def handle_starttag(self,tag,attrs):
        d=dict(attrs);s=d.get('src') if tag in ['img','script'] else d.get('href') if tag=='link' and d.get('rel')=='stylesheet' else None
        if tag in ('img','source'):
            for candidate in d.get('srcset','').split(','):
                parts=candidate.split()
                if parts and parts[0].startswith('/brewtanist/'):self.paths.add(urlsplit(parts[0]).path)
        if s and s.startswith('/brewtanist/'):self.paths.add(urlsplit(s).path)
def verify_assets(home_html,shop_html,stamp):
    parser=Assets()
    parser.feed(home_html)
    parser.feed(shop_html)
    def verify(path):
        data=get(path+'?release='+stamp)
        expected=(ROOT/path.lstrip('/')).read_bytes()
        assert hashlib.sha256(data).digest()==hashlib.sha256(expected).digest(),path
        return path
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(verify,sorted(parser.paths)))

for attempt in range(24):
    try:
        stamp=os.environ.get('GITHUB_SHA','')[:12]+'-'+str(time.time_ns())
        raw=get('/?release='+stamp);text=raw.decode('utf-8')
        assert home['hero_text'] in unescape(text),'Published copy is not this release yet'
        assert home['hero_button'] in unescape(text) and home['hero_second_button'] in unescape(text)
        assert 'https://brewtanist.github.io/' in text
        shop_text=get('/shop/?release='+stamp).decode('utf-8')
        assert 'https://brewtanist.github.io/shop/' in shop_text
        assert shop_text.count(' data-shop-card ')==len(visible),'Published product list is not this release yet'
        for item in visible:
            if item.get('image'):assert item['image'] in shop_text, 'Published image is not this release: '+item['id']
            assert 'id="shop-'+item['id']+'"' in shop_text,item['id']
            assert 'https://shopee.co.th/product/'+marketplace['shopId']+'/'+item['shopeeItemId'] in shop_text,item['id']
        for language, tag in [('en','en'),('zh','zh-Hans')]:
            translation=json.loads((ROOT/'_data/translations'/(language+'.json')).read_text())
            for suffix, expected in [('/',translation['home']['hero_text']),('/shop/',translation['marketplace']['intro'])]:
                route='/'+language+suffix
                other=get(route+'?release='+stamp).decode('utf-8')
                assert '<html lang="'+tag+'">' in other and expected in unescape(other), 'Pending localized release: '+route
        assets=verify_assets(text,shop_text,stamp)
        break
    except Exception as exc:
        if attempt==23:raise
        print(f'Waiting for GitHub Pages ({attempt+1}/24): {exc}',flush=True)
        time.sleep(10)
report={'result':'PASS','website':BASE+'/','shop':BASE+'/shop/','new_thai_copy_live':True,'visible_shop_products':len(visible),'assets_verified':assets,'catalogue_url':settings.get('catalogue_url',''),'catalogue_connected':bool(settings.get('catalogue_url')),'sha':os.environ.get('GITHUB_SHA'),'note':'Public HTTPS homepage/shop HTML and asset byte checks. External catalogue hosting and live Shopee inventory are not asserted.'}
(QA/'live-site-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
