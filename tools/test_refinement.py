"""Design regression checks. Uses local builds, no authenticated browser session."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from collections import Counter
import json,subprocess,threading,traceback,re,unicodedata
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'qa/design-20261109';QA.mkdir(parents=True,exist_ok=True)
BASE=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();checks=[];errors=[];servers=[]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
def serve(folder,port):
 s=ThreadingHTTPServer(('127.0.0.1',port),partial(Quiet,directory=str(folder)));threading.Thread(target=s.serve_forever,daemon=True).start();servers.append(s)
def record(name):checks.append(name);print('PASS: '+name,flush=True)
def fit(page):
 info=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
 assert info['document']<=info['viewport']+1,repr(info)
def images(page):
 loc=page.locator('main img[src]');loc.evaluate_all('(xs)=>Promise.all(xs.map(x=>{x.loading="eager";return x.decode().catch(()=>{});} ))');assert loc.evaluate_all('(xs)=>xs.every(x=>x.naturalWidth>0)'),'Missing image'
report={'result':'FAIL','checks':checks,'physical_iphone_tested':False,'authenticated_cms_save_tested':False,'catalogue_host_deployed':False}
try:
 for p in (ROOT/'_data/brewtanist').glob('*.json'):
  assert p.read_bytes()==subprocess.check_output(['git','show',BASE+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),p.name
 for name in ['.pages.yml','render.yaml','_config.yml']:
  assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT),name
 record('Saved content, CMS forms and hosting settings match the current checked-out revision')
 serve(ROOT/'_site',8770);serve(ROOT/'catalogue/dist',8771)
 home=json.loads((ROOT/'_data/brewtanist/home.json').read_text())
 marketplace=json.loads((ROOT/'_data/brewtanist/marketplace.json').read_text())
 houses={p['id']:p for p in json.loads((ROOT/'_data/brewtanist/products.json').read_text())['items']}
 visible=[]
 for item in marketplace['items']:
  house=houses.get(item.get('houseId'))
  if not item['visible'] or (house and not house.get('visible')):continue
  current=dict(item)
  if house:current.update(name=house['name'],description=house['description'])
  visible.append(current)
 category_counts=Counter(p['category'] for p in visible)
 ozmo_matches=sum(p['category']=='capsules' and 'ozmo' in unicodedata.normalize('NFC',' '.join([p['name'],p['description'],p['category']])).lower() for p in visible)
 with sync_playwright() as pw:
  for engine in ['chromium','webkit']:
   browser=getattr(pw,engine).launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:8770/',wait_until='networkidle');expect(page.locator('body')).to_have_class(re.compile(r'(^|\s)site-refined(\s|$)'));expect(page.locator('#hero-heading')).to_have_text(home['hero_title']);images(page)
   for w in [320,390,768,1024,1440]:
    page.set_viewport_size({'width':w,'height':1000});fit(page)
    assert page.locator('.hero-copy>p').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>=16
    if w in [390,1440] and engine=='chromium':page.screenshot(path=str(QA/('home-'+str(w)+'.png')),full_page=True);page.locator('#top').screenshot(path=str(QA/('hero-'+str(w)+'.png')))
   record(engine+': homepage/images at five widths')
   page.set_viewport_size({'width':390,'height':844});page.locator('.mobile-nav>summary').click();page.keyboard.press('Escape');assert not page.locator('.mobile-nav').evaluate('(e)=>e.open')
   page.locator('.mobile-nav>summary').click();page.locator('.mobile-nav>nav>a[href="#visit"]').click();assert not page.locator('.mobile-nav').evaluate('(e)=>e.open');record(engine+': mobile navigation and Escape')
   trigger=page.locator('.gallery-open').first;trigger.click();expect(page.locator('.brew-lightbox')).to_be_visible();expect(page.locator('[data-lightbox-count]')).to_contain_text('1 /');page.keyboard.press('ArrowRight');expect(page.locator('[data-lightbox-count]')).to_contain_text('2 /');page.keyboard.press('Escape');expect(page.locator('.brew-lightbox')).not_to_be_visible();expect(trigger).to_be_focused();assert page.evaluate('document.documentElement.style.overflow')!='hidden';record(engine+': gallery opens, advances, closes and restores focus')
   for route in ['/','/shop/','/shop/capsules/','/item/guatemala-agua-tibia-geisha/','/product/ozmo/','/finder/','/compare/']:
    page.goto('http://127.0.0.1:8771'+route,wait_until='networkidle');images(page)
    for w in [320,390,768,1024,1440]:page.set_viewport_size({'width':w,'height':1000});fit(page)
    assert page.locator('h1').count()==1
   record(engine+': seven catalogue page types at five widths')
   page.goto('http://127.0.0.1:8771/shop/');page.set_viewport_size({'width':390,'height':844});page.locator('.catalogue-menu-toggle').click();expect(page.locator('#catalogue-navigation')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('.catalogue-menu-toggle')).to_have_attribute('aria-expanded','false')
   page.locator('#market-category').select_option('capsules');expect(page.locator('.market-card:visible')).to_have_count(category_counts['capsules']);page.locator('#market-search').fill('Ozmo');expect(page.locator('.market-card:visible')).to_have_count(ozmo_matches);page.locator('#market-search').fill('qa-no-match');expect(page.locator('#market-empty')).to_be_visible();record(engine+': catalogue navigation, filtering and search')
   page.goto('http://127.0.0.1:8771/finder/')
   for i,v in enumerate(['beans','chocolate','milk']):page.locator('input[name="q'+str(i)+'"][value="'+v+'"]').check();page.locator('#quiz-next').click()
   expect(page.locator('#finder-result')).to_be_visible();assert page.locator('#finder-result a[href="/product/plantman/"]').count()>0;page.locator('#restart').click();expect(page.locator('#finder-form')).to_be_visible();record(engine+': Coffee Finder completes and restarts')
   if engine=='chromium':
    for w in [390,1440]:
     page.set_viewport_size({'width':w,'height':1000});page.goto('http://127.0.0.1:8771/shop/',wait_until='networkidle');page.screenshot(path=str(QA/('shop-'+str(w)+'.png')),full_page=True)
   nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844});p=nojs.new_page();p.goto('http://127.0.0.1:8770/');expect(p.locator('#hero-heading')).to_be_visible();fit(p);p.goto('http://127.0.0.1:8771/shop/');expect(p.locator('.market-card')).to_have_count(len(visible));fit(p);nojs.close();record(engine+': content usable without JavaScript')
   reduced=browser.new_context(reduced_motion='reduce');p=reduced.new_page();p.goto('http://127.0.0.1:8770/');assert p.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto';reduced.close();browser.close();record(engine+': reduced motion')
 assert not errors,repr(errors);record('No uncaught browser exceptions')
 report.update(result='PASS',checks_count=len(checks),source_revision=BASE,visible_listings=len(visible),category_counts=dict(category_counts),engines=['Chromium','WebKit'],viewport_widths=[320,390,768,1024,1440])
except Exception as e:report.update(error=str(e),traceback=traceback.format_exc());raise
finally:
 (QA/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False));[s.shutdown() for s in servers]
