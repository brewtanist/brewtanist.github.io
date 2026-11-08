"""Checks for sourced catalogue expansion; does not assert live marketplace status."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from copy import deepcopy
from collections import Counter
import importlib.util,json,threading,traceback,re,sys,yaml,unicodedata
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'catalogue/dist';QA=ROOT/'qa';QA.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'catalogue'));from marketplace import validate,CATEGORIES
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8768),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[];errors=[];report={'result':'FAIL','checks':checks,'live_shopee_access':False,'live_render_deployment':False,'authenticated_cms_save_tested':False}
def record(x):checks.append(x);print('PASS: '+x,flush=True)
def fit(page):assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Horizontal overflow'
try:
 data=json.loads((ROOT/'_data/brewtanist/marketplace.json').read_text());validate(data)
 source_count=len(data['items']);assert source_count>0,'No saved marketplace listings'
 assert len({x['shopeeItemId'] for x in data['items']})==source_count
 houses={x['id']:x for x in json.loads((ROOT/'_data/brewtanist/products.json').read_text())['items']}
 house_refs=[x['houseId'] for x in data['items'] if x.get('houseId')]
 assert len(house_refs)==len(set(house_refs)),'Duplicate House Blend mapping'
 assert set(house_refs)==set(houses),'House Blend mappings differ from shared product data'
 visible=[]
 for item in data['items']:
    house=houses.get(item.get('houseId'))
    if not item['visible'] or (house and not house.get('visible')):continue
    current=dict(item)
    if house:current.update(name=house['name'],description=house['description'],image=house['image'],alt=house['alt'])
    visible.append(current)
 visible_count=len(visible);category_counts=Counter(x['category'] for x in visible)
 additional_count=sum(not x.get('houseId') for x in data['items'])
 photos_available=sum(bool(x.get('image')) for x in visible);photos_missing=visible_count-photos_available
 for field,val in [('price','999'),('stock',100),('shopeeItemId','javascript:bad')]:
    d=deepcopy(data);d['items'][0][field]=val
    try:validate(d)
    except ValueError:pass
    else:raise AssertionError('Unsafe field accepted: '+field)
 d=deepcopy(data)
 if len(d['items'])>1:d['items'][1]['id']=d['items'][0]['id']
 else:d['items'].append(deepcopy(d['items'][0]))
 try:validate(d)
 except ValueError:pass
 else:raise AssertionError('Duplicate accepted')
 record(f'{source_count} sourced listing IDs, {additional_count} additions, no copied snapshot price/stock; invalid data rejected')
 cms=yaml.safe_load((ROOT/'.pages.yml').read_text());assert len(cms['content'])==8;assert len({x['name'] for x in cms['content']})==8
 assert next(x for x in cms['content'] if x['name']=='marketplace')['path']=='_data/brewtanist/marketplace.json';record('Seven existing CMS forms retained and an eighth Shopee form added')
 with sync_playwright() as pw:
    browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8768/shop/',wait_until='networkidle');expect(page.locator('#market-products .market-card')).to_have_count(visible_count);fit(page)
    expect(page.locator('#market-products .market-card img')).to_have_count(photos_available)
    page.screenshot(path=str(QA/'shop-desktop.png'),full_page=True);record(f'All-products page renders {visible_count} visible listings and {photos_available} configured images')
    page.locator('#market-category').select_option('capsules');expect(page.locator('#market-products .market-card:visible')).to_have_count(category_counts['capsules'])
    ozmo_matches=sum(x['category']=='capsules' and 'ozmo' in unicodedata.normalize('NFC',' '.join([x['name'],x['description'],x['category']])).lower() for x in visible)
    page.locator('#market-search').fill('Ozmo');expect(page.locator('#market-products .market-card:visible')).to_have_count(ozmo_matches)
    page.locator('#market-search').fill('zzzznotaproduct');expect(page.locator('#market-empty')).to_be_visible();record('Search, category filter and empty state')
    for cat in CATEGORIES:
        page.goto('http://127.0.0.1:8768/shop/'+cat+'/');expect(page.locator('#market-products .market-card:visible')).to_have_count(category_counts[cat])
    record(f'All {len(CATEGORIES)} category routes match current saved visibility and category counts')
    if visible_count:
        page.locator('#market-category').select_option('capsules');page.wait_for_url('**/shop/capsules/');expect(page.locator('#market-products .market-card:visible')).to_have_count(category_counts['capsules']);record('Category switching navigates rather than hiding other categories')
    for p in visible:
        path=('/product/'+p['houseId']+'/' if p['houseId'] else '/item/'+p['id']+'/')
        response=page.goto('http://127.0.0.1:8768'+path);assert response.status==200
        expect(page.locator('h1')).to_have_text(p['name']);assert page.locator('a[href="https://shopee.co.th/product/'+data['shopId']+'/'+p['shopeeItemId']+'"]').count()>0
        assert not page.locator('.price').count();assert page.locator('link[rel=canonical]').get_attribute('href').endswith(path)
    record('Every listing opens its detail page and ID-mapped Shopee link; no price assertions')
    page.goto('http://127.0.0.1:8768/finder/')
    for i,v in enumerate(['capsules','sweet','milk']):page.locator('input[name="q'+str(i)+'"][value="'+v+'"]').check();page.locator('#quiz-next').click()
    expect(page.locator('#finder-result a[href="/shop/capsules/"]')).to_be_visible();assert page.evaluate('window.BrewtanistCatalogue.rank(["capsules","sweet","milk"]).length')==0
    record('Finder links to capsule category without copying bean taste rules')
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        detail_sample=sorted(visible,key=lambda x:len(x['name']),reverse=True)[:2]
        routes=['/shop/','/shop/capsules/']+[('/product/'+x['houseId']+'/' if x.get('houseId') else '/item/'+x['id']+'/') for x in detail_sample]
        for route in routes:
            page.goto('http://127.0.0.1:8768'+route);fit(page)
        if width==390:
            page.goto('http://127.0.0.1:8768/shop/');page.screenshot(path=str(QA/'shop-mobile.png'),full_page=True)
    record('Catalogue, category and long product names fit four viewport widths')
    nojs=browser.new_context(java_script_enabled=False);p=nojs.new_page();p.goto('http://127.0.0.1:8768/shop/');expect(p.locator('.market-card')).to_have_count(visible_count);nojs.close();record('Listing information and links readable without JavaScript')
    assert not errors,repr(errors);record('No uncaught browser JavaScript errors');browser.close()
 report.update(result='PASS',checks_count=len(checks),source_listings=source_count,additional_listings=additional_count,visible_listings=visible_count,category_counts={k:category_counts[k] for k in CATEGORIES},viewport_widths=[320,390,768,1440],individual_photos_available=photos_available,individual_photos_missing=photos_missing)
except Exception as e:report.update(error=str(e),traceback=traceback.format_exc());raise
finally:
 (QA/'marketplace-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False));server.shutdown()
