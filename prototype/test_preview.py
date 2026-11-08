"""Browser and file-save integration checks. Draft edits only; restore every test input."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from copy import deepcopy
import hashlib
import json
import re
import subprocess
import sys
import threading
import traceback
from playwright.sync_api import sync_playwright, expect
from PIL import Image
from catalog_data import load_products

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'prototype/dist'
QA = ROOT / 'prototype/qa'
QA.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8765/'
STORE = 'brewtanist-preview-lab-v1'
checks, errors = [], []
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 8765), partial(Quiet, directory=str(DIST)))
threading.Thread(target=server.serve_forever, daemon=True).start()

def record(text):
    checks.append({'check': text, 'result': 'PASS'})
    print('PASS: ' + text, flush=True)

def seed():
    html = (DIST/'index.html').read_text(encoding='utf-8')
    return json.loads(re.search(r'<script id="seed" type="application/json">(.*?)</script>', html, re.S).group(1))

def images(page):
    pics = page.locator('#app img[src]')
    pics.evaluate_all('(xs)=>Promise.all(xs.map(i=>{i.loading="eager";return i.decode().catch(()=>{});} ))')
    assert pics.evaluate_all('(xs)=>xs.every(i=>i.naturalWidth>0)'), 'Broken page image'

def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Horizontal page overflow'

def fixture(page, data, route='/catalog'):
    page.evaluate('(v)=>localStorage.setItem("'+STORE+'",JSON.stringify(v))', data)
    page.goto(BASE+'#'+route, wait_until='networkidle')
    page.reload(wait_until='networkidle')

prod_files = [ROOT/'index.html', ROOT/'.pages.yml', *sorted((ROOT/'_data/brewtanist').glob('*.json'))]
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in prod_files}
product_file = ROOT/'prototype/products.json'
product_bytes = product_file.read_bytes()
qa_image = ROOT/'prototype/media/qa-only-test-upload.webp'
report = {'result':'FAIL', 'checks':checks, 'pages_cms_owner_login_tested':False}
try:
    expected = seed()
    rows = load_products(ROOT)
    copy = json.loads((ROOT/'prototype/copy.th.json').read_text(encoding='utf-8'))
    assert expected['title'] == copy['title']
    for p, saved in zip(expected['products'], rows):
        for k in ['id','name','profile','notes','alt','theme','price','sizes','grinding','origin','productUrl','tasteTags','drinkTags','visible','verified']:
            assert p[k] == saved[k], 'Saved input not reflected: '+k
        assert p['description'] == copy['descriptions'][p['id']]
    record('Built preview matches saved GitHub copy, product data, order and visibility')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':1000})
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.goto(BASE+'?source=github', wait_until='networkidle')
        current_visible = [p for p in expected['products'] if p['visible']]
        expect(page.locator('#product-list .product-card')).to_have_count(len(current_visible))
        expect(page.locator('h1')).to_have_text(expected['title'])
        assert page.locator('meta[name="robots"]').get_attribute('content') == 'noindex,nofollow,noarchive'
        images(page); fits(page)
        page.screenshot(path=str(QA/'01-catalog-desktop.png'), full_page=True)
        record('Saved-source catalogue, owned images, noindex and desktop layout')

        # Interactive regression fixtures use current data but reveal all three products locally.
        local = deepcopy(expected)
        for p in local['products']:
            p['visible'] = True
        fixture(page, local)
        for key in ['all','chocolate','sweet','fruity']:
            page.locator('[data-filter="'+key+'"]').click()
            count = sum(key=='all' or key in p['tasteTags'] for p in local['products'])
            expect(page.locator('#product-list .product-card')).to_have_count(count)
        page.locator('[data-filter="all"]').click()
        page.locator('#search').fill('zzzz-no-such-product-7192')
        expect(page.locator('#product-list .product-card')).to_have_count(0)
        page.locator('#search').fill('')
        expect(page.locator('#product-list .product-card')).to_have_count(3)
        page.locator('[data-scroll="blend-list"]').click()
        record('Search, empty state, flavor filtering and catalogue navigation')
        for product in local['products']:
            page.goto(BASE+'#/product/'+product['id'])
            expect(page.locator('h1')).to_have_text(product['name'])
            images(page)
            page.locator('[data-zoom]').click()
            expect(page.locator('#zoom')).to_be_visible()
            page.locator('#zoom-image').evaluate('(i)=>i.decode()')
            page.keyboard.press('Escape')
            expect(page.locator('#zoom')).not_to_be_visible()
        page.screenshot(path=str(QA/'02-product-desktop.png'), full_page=True)
        record('All product pages and keyboard-accessible image zoom')
        page.goto(BASE+'#/catalog')
        for product in local['products']:
            page.locator('input[data-compare="'+product['id']+'"]').check()
        page.locator('#dock a').click()
        expect(page.locator('.compare-table h3')).to_have_count(3)
        page.locator('[data-remove]').first.click()
        expect(page.locator('.compare-table h3')).to_have_count(2)
        record('Select, compare and remove products')
        page.goto(BASE+'#/finder')
        assert page.locator('[data-action="quiz-next"]').is_disabled()
        for value in ['beans','fruity','black']:
            page.locator('[data-answer="'+value+'"]').click()
            page.locator('[data-action="quiz-next"]').click()
        page.screenshot(path=str(QA/'03-finder-result.png'), full_page=True)
        combinations = page.evaluate('''() => {
          let count=0;
          const products=window.BrewtanistPreview.getData().products.filter(p=>p.visible);
          for(const f of ['beans','capsules','drip']) for(const t of ['chocolate','sweet','fruity','unsure']) for(const d of ['black','milk','unsure']) {
            const actual=window.BrewtanistPreview.rank([f,t,d]);
            const expected=f==='beans'?products.map(p=>({id:p.id,score:(p.tasteTags.includes(t)?3:0)+(p.drinkTags.includes(d)?2:0)})).filter(p=>p.score>0).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id)):[];
            if(JSON.stringify(actual.map(({id,score})=>({id,score})))!==JSON.stringify(expected)) throw Error('Incorrect saved-tag matching');
            if(actual.some(r=>!r.reasons.length)) throw Error('Missing explanation');
            count++;
          }
          return count;
        }''')
        assert combinations == 36
        page.locator('[data-action="quiz-reset"]').click()
        for value in ['capsules','chocolate','milk']:
            page.locator('[data-answer="'+value+'"]').click()
            page.locator('[data-action="quiz-next"]').click()
        expect(page.locator('.product-card')).to_have_count(0)
        record('Coffee Finder: 36 answer combinations follow saved rules; no bean fallback for capsules')

        first = local['products'][0]
        page.goto(BASE+'#/studio')
        page.locator('#edit-product').select_option(first['id'])
        page.locator('input[data-field="name"]').fill(first['name']+' — QA draft')
        expect(page.frame_locator('#preview').locator('h1')).to_have_text(first['name']+' — QA draft')
        page.locator('[data-action="save-draft"]').click()
        page.reload(wait_until='networkidle')
        expect(page.locator('input[data-field="name"]')).to_have_value(first['name']+' — QA draft')
        page.locator('input[data-field="name"]').fill(first['name'])
        page.screenshot(path=str(QA/'04-content-studio.png'), full_page=True)
        record('Local editor, live preview, draft save and reload')
        page.get_by_text('ราคา ขนาด และลิงก์สินค้า', exact=True).click()
        page.locator('input[data-field="productUrl"]').fill('javascript:alert(1)')
        assert page.evaluate('window.BrewtanistPreview.validate().errors.length') > 0
        page.locator('input[data-field="productUrl"]').fill('')
        attack='<img src=x onerror="window.BAD=1">'
        page.locator('textarea[data-field="description"]').fill(attack)
        expect(page.frame_locator('#preview').locator('body')).to_contain_text(attack)
        assert page.evaluate('window.BAD === undefined')
        assert page.frame_locator('#preview').locator('img').count() == 1
        page.locator('#image-upload').set_input_files(str(ROOT/'prototype/media/plantman-3d.webp'))
        page.wait_for_function('document.querySelector("#toast").textContent.includes("เปลี่ยนรูป")')
        record('Unsafe URLs rejected, copy escaped, raster image replacement works')
        with page.expect_download() as dl:
            page.locator('[data-action="export-json"]').click()
        exported=QA/'test-export.json'; dl.value.save_as(str(exported))
        page.locator('input[data-field="name"]').fill('Temporary test name')
        page.locator('#import-json').set_input_files(str(exported))
        expect(page.locator('input[data-field="name"]')).to_have_value(first['name'])
        with page.expect_download() as dl:
            page.locator('[data-action="export-html"]').click()
        snapshot=QA/'test-export.html'; dl.value.save_as(str(snapshot))
        offline=browser.new_context(viewport={'width':390,'height':844}, offline=True)
        offline_page=offline.new_page(); offline_page.on('pageerror',lambda e:errors.append(str(e)))
        offline_page.goto(snapshot.as_uri(), wait_until='load')
        expect(offline_page.locator('#product-list .product-card')).to_have_count(3)
        images(offline_page); fits(offline_page); offline.close()
        record('JSON round-trip and exported HTML opens offline with images')

        # A saved-source link shows GitHub data without deleting or overwriting local owner drafts.
        owner=deepcopy(local); owner['title']='Owner local draft retained'; owner['products'][0]['name']='Owner custom name'
        fixture(page, owner)
        expect(page.locator('h1')).to_have_text(owner['title'])
        stored=page.evaluate('localStorage.getItem("'+STORE+'")')
        page.goto(BASE+'?source=github', wait_until='networkidle')
        expect(page.locator('h1')).to_have_text(expected['title'])
        assert page.evaluate('localStorage.getItem("'+STORE+'")') == stored
        page.goto(BASE, wait_until='networkidle')
        expect(page.locator('h1')).to_have_text(owner['title'])
        record('GitHub saved-source view bypasses stale local drafts without deleting them')
        hidden=deepcopy(local)
        for p in hidden['products']: p['visible']=False
        fixture(page, hidden)
        expect(page.locator('#product-list .product-card')).to_have_count(0)
        page.goto(BASE+'#/product/'+first['id'])
        expect(page.locator('h1')).to_have_text('ไม่พบสินค้านี้')
        record('All-hidden catalogue and hidden-product direct links handled safely')

        # Simulate the file save/upload pipeline, not an authenticated Pages CMS user session.
        changed=json.loads(product_bytes)
        changed['items'][0].update(name='QA integration only', price='321.50', sizes='QA size', image='/prototype/media/qa-only-test-upload.webp', alt='QA raster')
        Image.new('RGB',(64,64),(210,220,200)).save(qa_image,format='WEBP')
        product_file.write_text(json.dumps(changed,ensure_ascii=False),encoding='utf-8')
        subprocess.run([sys.executable, str(ROOT/'prototype/build.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        page.goto(BASE+'?source=github&qa=1#/product/'+changed['items'][0]['id'],wait_until='networkidle')
        expect(page.locator('h1')).to_have_text('QA integration only')
        expect(page.locator('.facts')).to_contain_text('321.5')
        expect(page.locator('.facts')).to_contain_text('QA size')
        images(page)
        product_file.write_bytes(product_bytes); qa_image.unlink(missing_ok=True)
        subprocess.run([sys.executable,str(ROOT/'prototype/build.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        assert seed()==expected
        record('Saved product and uploaded raster flow through builder and browser; all test inputs restored')

        # Final screenshots are the real saved draft, never the test fixture prices or content.
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':900})
            page.goto(BASE+'?source=github#/catalog',wait_until='networkidle'); fits(page); images(page)
            if width==390: page.screenshot(path=str(QA/'05-catalog-mobile.png'),full_page=True)
        record('Saved catalogue fits 320, 390, 768 and 1440px viewports')
        page.set_viewport_size({'width':390,'height':844})
        for route in ['finder','studio','product/'+first['id']]:
            page.goto(BASE+'?source=github#/'+route,wait_until='networkidle'); fits(page)
            if route=='finder': page.screenshot(path=str(QA/'06-finder-mobile.png'),full_page=True)
        page.goto(BASE+'?source=github#/studio',wait_until='networkidle')
        page.locator('[data-device="mobile"]').click()
        expect(page.locator('#preview')).to_have_class('preview-frame mobile')
        record('Mobile finder, product and editing studio layouts')
        assert not errors, errors
        record('No uncaught browser JavaScript errors')
        browser.close()
    assert product_file.read_bytes()==product_bytes
    assert {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in prod_files}==before
    record('Production files and actual saved draft inputs unchanged by tests')
    report.update(result='PASS', checks_count=len(checks), finder_combinations=36, viewport_widths=[320,390,768,1440], production_files_unchanged=True, actual_cms_save_tested=False, file_save_and_upload_simulation_tested=True, note='Automated Chromium and file-pipeline checks. No owner-session Pages CMS Save, iPhone Safari or checkout test.')
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
    raise
finally:
    product_file.write_bytes(product_bytes)
    qa_image.unlink(missing_ok=True)
    for path in [QA/'test-export.json',QA/'test-export.html']:
        path.unlink(missing_ok=True)
    if report['result']!='PASS':
        subprocess.run([sys.executable,str(ROOT/'prototype/build.py')],cwd=ROOT,check=False,stdout=subprocess.DEVNULL)
    (QA/'test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    server.shutdown()
