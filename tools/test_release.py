"""Browser checks use saved CMS data, allowing future legitimate owner edits."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib,json,os,subprocess,threading,traceback,yaml
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'qa';QA.mkdir(exist_ok=True)
checks=[];servers=[];errors=[]
def record(name):checks.append({'check':name,'result':'PASS'});print('PASS:',name,flush=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
def serve(folder,port):
    server=ThreadingHTTPServer(('127.0.0.1',port),partial(Quiet,directory=str(folder)));threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
def overflow(page):assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Horizontal overflow'
def images(page):
    loc=page.locator('main img[src]');loc.evaluate_all('(xs)=>Promise.all(xs.map(x=>{x.loading="eager";return x.decode().catch(()=>{});} ))');assert loc.evaluate_all('(xs)=>xs.every(x=>x.naturalWidth>0)'),'Missing image'
def read(name):return json.loads((ROOT/'_data/brewtanist'/f'{name}.json').read_text())
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ['href','src'] and v:self.urls.append(v)
def links_exist(folder):
    for f in folder.rglob('*.html'):
        parser=Links();parser.feed(f.read_text())
        for value in parser.urls:
            u=urlsplit(value)
            if u.scheme or u.netloc or not u.path:continue
            target=folder/u.path.lstrip('/') if u.path.startswith('/') else f.parent/u.path
            if u.path.endswith('/'):target=target/'index.html'
            assert target.is_file(),f'Missing link: {f.name}: {value}'
report={'result':'FAIL','checks':checks,'authenticated_pages_cms_save_tested':False,'catalogue_host_deployment_tested':False}
try:
    p=read('products');settings=read('settings');home=read('home');visible=[x for x in p['items'] if x.get('visible')]
    if os.environ.get('GITHUB_REF')=='refs/heads/release/natural-thai-20261108':
        original=json.loads(subprocess.check_output(['git','show','d5fb938873581dbc21ad1fafcdc9d89a5695313d:_data/brewtanist/products.json'],text=True))
        for a,b in zip(p['items'],original['items']):
            for k in ['name','profile','notes','image','alt','theme','visible']:assert a[k]==b[k],k
            for k in ['price','sizes','grinding','origin','productUrl']:assert not a[k],f'Unconfirmed {k} filled'
        old=json.loads(subprocess.check_output(['git','show','d5fb938873581dbc21ad1fafcdc9d89a5695313d:_data/brewtanist/settings.json'],text=True))
        for k in ['brand','descriptor','phone','address','opens','closes','days','maps','shopee','facebook','instagram','payment']:assert settings[k]==old[k],k
        assert settings['catalogue_url']=='';record('Initial release preserves source product/business facts and leaves unconfirmed commercial fields empty')
    if settings.get('catalogue_url'):
        u=urlsplit(settings['catalogue_url']);assert u.scheme=='https' and u.hostname and not u.hostname.endswith('.invalid') and 'githack' not in u.hostname
    cms=yaml.safe_load((ROOT/'.pages.yml').read_text());assert len(cms['content'])==8;assert any(x['name']=='marketplace' for x in cms['content']);assert cms['media']['input']=='brewtanist/assets'
    fields=next(f for f in next(c for c in cms['content'] if c['name']=='products')['fields'] if f['name']=='items')['fields'];assert {'id','image','notes','price','productUrl','tasteTags','drinkTags','verified'}<={f['name'] for f in fields}
    assert cms['settings']['content']['merge'] is True;assert 'catalogue' in yaml.safe_load((ROOT/'_config.yml').read_text())['exclude']
    record('Existing seven CMS forms preserved; shared product data; catalogue excluded from GitHub Pages')
    links_exist(ROOT/'catalogue/dist')
    for f in (ROOT/'catalogue/dist').rglob('*.html'):
        txt=f.read_text();assert 'noindex,nofollow' in txt;assert 'Content Studio' not in txt and '#/studio' not in txt and 'localStorage' not in txt;assert txt.count('<h1')==1
    record('Customer-only static routes and local links; no local editing code; test host noindex')
    before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'_data/brewtanist').glob('*.json')}
    serve(ROOT/'_site',8766);serve(ROOT/'catalogue/dist',8765);serve(ROOT/'_site-connected',8767)
    with sync_playwright() as pw:
        browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8766/',wait_until='networkidle');expect(page.locator('.nav-links')).to_contain_text('เมนูที่ร้าน');expect(page.locator('.nav-links')).to_contain_text('กาแฟกลับบ้าน');expect(page.locator('#hero-heading')).to_have_text(home['hero_title']);images(page);overflow(page)
        assert not page.locator('a[href*="example.invalid"]').count();assert page.locator('link[rel="canonical"]').get_attribute('href')=='https://brewtanist.github.io/'
        page.screenshot(path=str(QA/'01-main-desktop.png'),full_page=True);record('Main website displays saved copy, original brand images and canonical without guessed hosting links')
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':900});overflow(page)
            if width==390:page.screenshot(path=str(QA/'02-main-mobile.png'),full_page=True)
        record('Main website fits 320, 390, 768 and 1440px')
        page.set_viewport_size({'width':1440,'height':1000});page.goto('http://127.0.0.1:8767/',wait_until='networkidle')
        if p['visible']:
            page.locator('.nav-links .coffee-menu summary').click();assert page.locator('.nav-links .coffee-menu a').nth(0).get_attribute('href')=='https://catalogue.example.invalid';assert page.locator('.nav-links .coffee-menu a').nth(1).get_attribute('href')=='https://catalogue.example.invalid/finder/'
            for item in visible:assert page.locator('a[href="https://catalogue.example.invalid/product/'+item['id']+'/"]').count()==2
            assert page.locator('.catalogue-invite a').get_attribute('href')=='https://catalogue.example.invalid/finder/'
        overflow(page);record('Connected-state Jekyll build: navigation, product image/detail links and finder CTA')
        page.goto('http://127.0.0.1:8765/',wait_until='networkidle');expect(page.locator('#product-list .product-card')).to_have_count(len(visible));images(page);overflow(page);page.screenshot(path=str(QA/'03-catalogue-desktop.png'),full_page=True)
        data=json.loads(page.locator('#catalogue-data').text_content())
        for current,saved in zip(data['products'],visible):
            for k in ['id','name','profile','notes','description','price','sizes','grinding','origin','productUrl','tasteTags','drinkTags']:assert current.get(k)==saved.get(k),k
        record('Customer pages read the same current product data as the main website')
        page.locator('#search').fill('zzzz-not-found-zzzz');expect(page.locator('#empty-search')).to_be_visible();page.locator('#reset-search').click();page.locator('[data-filter="fruity"]').click();expect(page.locator('#product-list .product-card:visible')).to_have_count(sum('fruity' in x['tasteTags'] for x in visible));page.locator('[data-filter="all"]').click();record('Search, empty results, reset and flavor filters use saved data')
        if visible:
            selected=visible[:2]
            for item in selected:page.locator('input[data-compare="'+item['id']+'"]').check()
            page.locator('#dock a').click();expect(page.locator('thead [data-col]:visible')).to_have_count(len(selected))
        record('Select and compare available products')
        for item in visible:
            page.goto('http://127.0.0.1:8765/product/'+item['id']+'/',wait_until='networkidle');expect(page.locator('h1')).to_have_text(item['name']);expect(page.locator('.detail-copy .notes')).to_have_text(item['notes']);images(page);assert page.locator('.detail-copy a.btn').get_attribute('href')==(item.get('productUrl') or settings['shopee'])
            expect(page.locator('.price')).to_have_count(1 if item.get('price') and item.get('sizes') and item.get('verified') else 0)
        record('Static product pages match saved notes and links; prices require verified size and price')
        page.goto('http://127.0.0.1:8765/finder/',wait_until='networkidle')
        for i,value in enumerate(['beans','fruity','black']):page.locator(f'input[name="q{i}"][value="{value}"]').check();page.locator('#quiz-next').click()
        expect(page.locator('#finder-result')).to_be_visible();page.screenshot(path=str(QA/'04-finder-result.png'),full_page=True)
        count=page.evaluate('''()=>{let n=0;for(const f of ['beans','capsules','drip'])for(const t of ['chocolate','sweet','fruity','unsure'])for(const d of ['black','milk','unsure']){const r=BrewtanistCatalogue.rank([f,t,d]);if(f!=='beans'&&r.length)throw Error('Wrong format');if(f==='beans'&&t==='unsure'&&d==='unsure'&&r.length)throw Error('Forced ranking');if(r.some(x=>!x.reasons.length))throw Error('Missing explanation');n++;}return n;}''');assert count==36
        page.locator('#restart').click()
        for i,value in enumerate(['capsules','chocolate','milk']):page.locator(f'input[name="q{i}"][value="{value}"]').check();page.locator('#quiz-next').click()
        expect(page.locator('#finder-result')).to_contain_text('ดูสินค้าใน Shopee');assert page.locator('#finder-result .result-head').count()==0;record('Finder flow and 36 combinations; capsules/Drip Bag never inherit bean recommendations')
        paths=['/','/finder/','/compare/']+['/product/'+x['id']+'/' for x in visible[:1]]
        for path in paths:
            page.goto('http://127.0.0.1:8765'+path,wait_until='networkidle')
            for width in [320,390,768,1440]:page.set_viewport_size({'width':width,'height':900});overflow(page)
        page.set_viewport_size({'width':390,'height':844});page.goto('http://127.0.0.1:8765/');page.screenshot(path=str(QA/'05-catalogue-mobile.png'),full_page=True);record('Catalogue, finder, product and compare fit four viewport widths')
        if visible:
            first=visible[0];nojs=browser.new_context(java_script_enabled=False);np=nojs.new_page();np.goto('http://127.0.0.1:8765/product/'+first['id']+'/');expect(np.locator('h1')).to_have_text(first['name']);expect(np.locator('.detail-copy .notes')).to_have_text(first['notes']);nojs.close()
        record('Product content readable without JavaScript')
        assert not errors,repr(errors);record('No uncaught browser errors');browser.close()
    after={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'_data/brewtanist').glob('*.json')};assert before==after;record('Saved data and real connection settings untouched by tests')
    report.update(result='PASS',checks_count=len(checks),finder_combinations=36,viewport_widths=[320,390,768,1440],notes='Automated Chromium/build tests only. No real iOS Safari, authenticated CMS session or hosting deployment is claimed.')
except Exception as e:report.update(error=str(e),traceback=traceback.format_exc());raise
finally:
    (QA/'release-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
    for server in servers:server.shutdown()
