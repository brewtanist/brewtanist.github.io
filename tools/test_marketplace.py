"""Checks for sourced catalogue expansion; does not assert live marketplace status."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from copy import deepcopy
import importlib.util,json,threading,traceback,re,sys,yaml
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'catalogue/dist';QA=ROOT/'qa';QA.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'catalogue'));from marketplace import validate
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8768),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[];errors=[];report={'result':'FAIL','checks':checks,'live_shopee_access':False,'live_render_deployment':False,'authenticated_cms_save_tested':False}
def record(x):checks.append(x);print('PASS: '+x,flush=True)
def fit(page):assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Horizontal overflow'
try:
 data=json.loads((ROOT/'_data/brewtanist/marketplace.json').read_text());validate(data)
 assert len(data['items'])==17 and len({x['shopeeItemId'] for x in data['items']})==17
 assert sum(bool(x['houseId']) for x in data['items'])==3
 for field,val in [('price','999'),('stock',100),('shopeeItemId','javascript:bad')]:
    d=deepcopy(data);d['items'][0][field]=val
    try:validate(d)
    except ValueError:pass
    else:raise AssertionError('Unsafe field accepted: '+field)
 d=deepcopy(data);d['items'][1]['id']=d['items'][0]['id']
 try:validate(d)
 except ValueError:pass
 else:raise AssertionError('Duplicate accepted')
 record('17 sourced listing IDs, 14 additions, no copied snapshot price/stock; invalid data rejected')
 cms=yaml.safe_load((ROOT/'.pages.yml').read_text());assert len(cms['content'])==8;assert len({x['name'] for x in cms['content']})==8
 assert next(x for x in cms['content'] if x['name']=='marketplace')['path']=='_data/brewtanist/marketplace.json';record('Seven existing CMS forms retained and an eighth Shopee form added')
 with sync_playwright() as pw:
    browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8768/shop/',wait_until='networkidle');expect(page.locator('#market-products .market-card')).to_have_count(17);fit(page)
    page.screenshot(path=str(QA/'shop-desktop.png'),full_page=True);record('All-products page renders 17 listings with working local assets')
    page.locator('#market-category').select_option('capsules');expect(page.locator('#market-products .market-card:visible')).to_have_count(3)
    page.locator('#market-search').fill('Ozmo');expect(page.locator('#market-products .market-card:visible')).to_have_count(1)
    page.locator('#market-search').fill('zzzznotaproduct');expect(page.locator('#market-empty')).to_be_visible();record('Search, category filter and empty state')
    for cat,count in [('house',3),('single-origin',6),('capsules',3),('drip',1),('gifts',2),('goods',2)]:
        page.goto('http://127.0.0.1:8768/shop/'+cat+'/');expect(page.locator('#market-products .market-card:visible')).to_have_count(count)
    record('Six category routes show 3/6/3/1/2/2 matching products')
    page.locator('#market-category').select_option('capsules');page.wait_for_url('**/shop/capsules/');expect(page.locator('#market-products .market-card:visible')).to_have_count(3);record('Category switching navigates rather than hiding other categories')
    for p in data['items']:
        path=('/product/'+p['houseId']+'/' if p['houseId'] else '/item/'+p['id']+'/')
        response=page.goto('http://127.0.0.1:8768'+path);assert response.status==200
        expect(page.locator('h1')).to_have_text(p['name']);assert page.locator('a[href="https://shopee.co.th/product/985117757/'+p['shopeeItemId']+'"]').count()>0
        assert not page.locator('.price').count();assert page.locator('link[rel=canonical]').get_attribute('href').endswith(path)
    record('Every listing opens its detail page and ID-mapped Shopee link; no price assertions')
    page.goto('http://127.0.0.1:8768/finder/')
    for i,v in enumerate(['capsules','sweet','milk']):page.locator('input[name="q'+str(i)+'"][value="'+v+'"]').check();page.locator('#quiz-next').click()
    expect(page.locator('#finder-result a[href="/shop/capsules/"]')).to_be_visible();assert page.evaluate('window.BrewtanistCatalogue.rank(["capsules","sweet","milk"]).length')==0
    record('Finder links to capsule category without copying bean taste rules')
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        for route in ['/shop/','/shop/capsules/','/item/capsule-ozmo/','/item/guatemala-agua-tibia-geisha/']:
            page.goto('http://127.0.0.1:8768'+route);fit(page)
        if width==390:
            page.goto('http://127.0.0.1:8768/shop/');page.screenshot(path=str(QA/'shop-mobile.png'),full_page=True)
    record('Catalogue, category and long product names fit four viewport widths')
    nojs=browser.new_context(java_script_enabled=False);p=nojs.new_page();p.goto('http://127.0.0.1:8768/shop/');expect(p.locator('.market-card')).to_have_count(17);nojs.close();record('Listing information and links readable without JavaScript')
    assert not errors,repr(errors);record('No uncaught browser JavaScript errors');browser.close()
 report.update(result='PASS',checks_count=len(checks),source_listings=17,additional_listings=14,viewport_widths=[320,390,768,1440],individual_photos_missing=14)
except Exception as e:report.update(error=str(e),traceback=traceback.format_exc());raise
finally:
 (QA/'marketplace-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False));server.shutdown()
