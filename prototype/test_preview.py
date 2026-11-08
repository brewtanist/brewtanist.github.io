"""Browser regression checks for the isolated Brewtanist prototype."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import hashlib
import json
import threading
import traceback
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'prototype' / 'dist'
QA = ROOT / 'prototype' / 'qa'
QA.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8765/'
checks = []
errors = []

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 8765), partial(QuietHandler, directory=str(DIST)))
threading.Thread(target=server.serve_forever, daemon=True).start()

def record(name):
    checks.append({'check': name, 'result': 'PASS'})
    print('PASS:', name, flush=True)

def assert_images(page):
    images=page.locator('#app img[src]')
    assert images.count()>0
    images.evaluate_all('(images) => Promise.all(images.map(i => {i.loading="eager";return i.decode().catch(() => {});} ))')
    broken=images.evaluate_all('(images) => images.filter(i => !i.naturalWidth).map(i => ({alt:i.alt,src:i.src.slice(0,60)}))')
    assert not broken, 'Broken page images: '+repr(broken)

def no_overflow(page):
    sizes=page.evaluate('({doc:document.documentElement.scrollWidth,window:innerWidth})')
    assert sizes['doc']<=sizes['window']+1, 'Horizontal document overflow: '+repr(sizes)

prod_files = [ROOT/'index.html', ROOT/'.pages.yml', *sorted((ROOT/'_data'/'brewtanist').glob('*.json'))]
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in prod_files}
report = {'result': 'FAIL', 'checks': checks, 'production_files_unchanged': None}
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.goto(BASE, wait_until='networkidle')
        expect(page.locator('#product-list .product-card')).to_have_count(3)
        assert_images(page)
        assert page.locator('meta[name="robots"]').get_attribute('content') == 'noindex,nofollow,noarchive'
        no_overflow(page)
        page.screenshot(path=str(QA/'01-catalog-desktop.png'), full_page=True)
        record('Catalogue: three source products, embedded images, noindex, desktop layout')

        page.locator('#search').fill('Lazybug')
        expect(page.locator('#product-list .product-card')).to_have_count(1)
        page.locator('#search').fill('')
        page.locator('[data-filter="fruity"]').click()
        expect(page.locator('#product-list .product-card')).to_have_count(1)
        page.locator('[data-filter="all"]').click()
        expect(page.locator('#product-list .product-card')).to_have_count(3)
        page.locator('a[data-scroll="blend-list"]').click()
        expect(page.locator('#product-list .product-card')).to_have_count(3)
        record('Search, flavor filters and in-page catalogue anchor')

        page.locator('#product-list [data-product="plantman"] .stage').click()
        expect(page.locator('h1')).to_have_text('Mr. Plantman')
        expect(page.locator('.facts')).to_contain_text('สอบถามร้าน')
        assert_images(page)
        page.locator('[data-zoom="plantman"]').click()
        expect(page.locator('#zoom')).to_be_visible()
        assert page.locator('#zoom-image').evaluate('(i)=>i.naturalWidth>0')
        page.keyboard.press('Escape')
        expect(page.locator('#zoom')).not_to_be_visible()
        page.screenshot(path=str(QA/'02-product-desktop.png'), full_page=True)
        record('Product route, unknown information and accessible image zoom')

        page.locator('input[data-compare="plantman"]').check()
        page.locator('.links [data-nav="catalog"]').click()
        page.locator('input[data-compare="ozmo"]').check()
        page.locator('input[data-compare="lazybug"]').check()
        page.locator('#dock a').click()
        expect(page.locator('.compare-table h3')).to_have_count(3)
        page.locator('[data-remove="ozmo"]').click()
        expect(page.locator('.compare-table h3')).to_have_count(2)
        record('Select, compare and remove products')

        page.locator('.links [data-nav="finder"]').click()
        assert page.locator('[data-action="quiz-next"]').is_disabled()
        for value in ['beans','fruity','black']:
            page.locator('[data-answer="'+value+'"]').click()
            page.locator('[data-action="quiz-next"]').click()
        expect(page.locator('.product-card').first.locator('h3')).to_have_text('Ms. Lazybug')
        page.screenshot(path=str(QA/'03-finder-result.png'), full_page=True)
        record('Coffee Finder: complete three-step route and explainable recommendation')

        combinations = page.evaluate('''() => {
          let count=0;
          for(const f of ['beans','capsules','drip']) for(const t of ['chocolate','sweet','fruity','unsure']) for(const d of ['black','milk','unsure']){
            const r=window.BrewtanistPreview.rank([f,t,d]);
            if(f!=='beans' && r.length) throw Error('Unsupported format recommended');
            if(r.some(x=>!x.reasons.length || x.score<=0)) throw Error('Unexplained score');
            if(f==='beans' && t==='unsure' && d==='unsure' && r.length) throw Error('Ambiguous answers force a result');
            count++;
          }
          return count;
        }''')
        assert combinations == 36
        page.locator('[data-action="quiz-reset"]').click()
        for value in ['capsules','chocolate','milk']:
            page.locator('[data-answer="'+value+'"]').click()
            page.locator('[data-action="quiz-next"]').click()
        expect(page.locator('#app')).to_contain_text('ดูแคปซูลที่ Shopee')
        expect(page.locator('.product-card')).to_have_count(0)
        record('All 36 answer combinations, ambiguity and capsule/Drip Bag fallback')

        page.locator('.links [data-nav="studio"]').click()
        page.locator('input[data-field="name"]').fill('Mr. Plantman — ทดลองแก้ไข')
        expect(page.frame_locator('#preview').locator('h1')).to_have_text('Mr. Plantman — ทดลองแก้ไข')
        page.locator('[data-action="save-draft"]').click()
        page.reload(wait_until='networkidle')
        expect(page.locator('input[data-field="name"]')).to_have_value('Mr. Plantman — ทดลองแก้ไข')
        page.locator('input[data-field="name"]').fill('Mr. Plantman')
        page.screenshot(path=str(QA/'04-content-studio.png'), full_page=True)
        record('Content Studio: live iframe preview, local draft save and reload')

        page.get_by_text('ราคา ขนาด และลิงก์สินค้า', exact=True).click()
        page.locator('input[data-field="productUrl"]').fill('javascript:alert(1)')
        assert page.evaluate('window.BrewtanistPreview.validate().errors.length') > 0
        page.locator('input[data-field="productUrl"]').fill('')
        page.locator('textarea[data-field="description"]').fill('<img src=x onerror="window.BAD=1">')
        expect(page.frame_locator('#preview').locator('body')).to_contain_text('<img src=x onerror="window.BAD=1">')
        assert page.evaluate('window.BAD === undefined')
        assert page.frame_locator('#preview').locator('img').count() == 1
        page.locator('#image-upload').set_input_files(str(ROOT/'brewtanist'/'assets'/'plantman-3d.webp'))
        page.wait_for_function('document.querySelector("#toast").textContent.includes("เปลี่ยนรูป")')
        record('Unsafe URL rejection, escaped copy and real raster image replacement')

        with page.expect_download() as dl:
            page.locator('[data-action="export-json"]').click()
        json_path=QA/'test-export.json'
        dl.value.save_as(str(json_path))
        exported=json.loads(json_path.read_text())
        assert exported['products'][0]['name']=='Mr. Plantman'
        page.locator('input[data-field="name"]').fill('TEMP CHANGE')
        page.locator('#import-json').set_input_files(str(json_path))
        expect(page.locator('input[data-field="name"]')).to_have_value('Mr. Plantman')
        with page.expect_download() as dl:
            page.locator('[data-action="export-html"]').click()
        snapshot=QA/'test-export.html'
        dl.value.save_as(str(snapshot))
        offline=browser.new_context(viewport={'width':390,'height':844},offline=True)
        local=offline.new_page()
        local.goto(snapshot.as_uri(),wait_until='load')
        expect(local.locator('#product-list .product-card')).to_have_count(3)
        assert_images(local)
        no_overflow(local)
        offline.close()
        record('JSON export/import and fully offline single-file HTML export including images')

        page.evaluate('window.BrewtanistPreview.reset()')
        page.locator('input[data-field="visible"]').uncheck()
        page.locator('.links [data-nav="catalog"]').click()
        expect(page.locator('#product-list .product-card')).to_have_count(2)
        page.goto(BASE+'#/product/plantman')
        expect(page.locator('h1')).to_have_text('ไม่พบสินค้านี้')
        page.evaluate('window.BrewtanistPreview.reset()')
        page.goto(BASE+'#/catalog')
        for w in [320,390,768,1440]:
            page.set_viewport_size({'width':w,'height':900})
            no_overflow(page)
            if w==390:
                assert_images(page)
                page.screenshot(path=str(QA/'05-catalog-mobile.png'),full_page=True)
        record('Hidden products, direct-link fallback and 320/390/768/1440px catalogue layout')

        page.set_viewport_size({'width':390,'height':844})
        page.goto(BASE+'#/finder')
        no_overflow(page)
        page.screenshot(path=str(QA/'06-finder-mobile.png'),full_page=True)
        page.goto(BASE+'#/product/plantman')
        no_overflow(page)
        page.goto(BASE+'#/studio')
        no_overflow(page)
        page.locator('[data-device="mobile"]').click()
        expect(page.locator('#preview')).to_have_class('preview-frame mobile')
        record('Mobile product, finder and editing studio layouts')

        # Copy changes must not manufacture product facts or overwrite owner drafts.
        page.evaluate('window.BrewtanistPreview.reset()')
        page.goto(BASE+'#/catalog')
        expect(page.locator('h1')).to_have_text('เลือกกาแฟ\nกลับไปชงที่บ้าน')
        saved=page.evaluate('window.BrewtanistPreview.getData()')
        source=json.loads((ROOT/'_data'/'brewtanist'/'products.json').read_text())
        for current, original in zip(saved['products'], source['items']):
            for key in ['name','profile','notes','alt','theme']:
                assert current[key] == original[key], 'Unapproved product fact changed: '+key
            for key in ['price','sizes','grinding','origin','productUrl']:
                assert current[key] == '', 'Unconfirmed value invented: '+key
        assert saved['copyRevision']==2
        for path in ['catalog','product/plantman','finder','compare']:
            page.goto(BASE+'#/'+path)
            content=page.locator('#app').inner_text()
            for phrase in ['เหตุผลที่ตรวจสอบได้','จากข้อมูลที่มี','ฟันธง','เปอร์เซ็นต์ความแม่นยำ','ยกระดับ','ตอบโจทย์']:
                assert phrase not in content, 'Unwanted wording: '+phrase
        record('Plain Thai copy and unchanged source product facts')

        old=page.evaluate('window.BrewtanistPreview.getData()')
        old['title']=old['previousCopy']['title']
        old['intro']=old['previousCopy']['intro']
        old['products'][0]['description']=old['previousCopy']['descriptions']['plantman']
        old['products'][1]['description']='ข้อความที่เจ้าของร้านแก้เอง'
        old['products'][1]['name']='ชื่อที่เจ้าของร้านตั้งไว้'
        page.evaluate('(d)=>localStorage.setItem("brewtanist-preview-lab-v1",JSON.stringify(d))',old)
        page.reload(wait_until='networkidle')
        migrated=page.evaluate('window.BrewtanistPreview.getData()')
        assert migrated['title']=='เลือกกาแฟ\nกลับไปชงที่บ้าน'
        assert migrated['products'][0]['description']==saved['products'][0]['description']
        assert migrated['products'][1]['description']=='ข้อความที่เจ้าของร้านแก้เอง'
        assert migrated['products'][1]['name']=='ชื่อที่เจ้าของร้านตั้งไว้'
        page.evaluate('window.BrewtanistPreview.reset()')
        record('Saved owner drafts preserved while previous default copy is refreshed')

        assert not errors, 'Browser errors: '+repr(errors)
        record('No uncaught browser JavaScript errors')
        browser.close()
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in prod_files}
    assert before==after
    report['production_files_unchanged']=True
    report['result']='PASS'
    report['checks_count']=len(checks)
    report['finder_combinations']=36
    report['viewport_widths']=[320,390,768,1440]
    report['notes']='Automated Chromium tests only. Not an iOS Safari test, human design review or production checkout test.'
except Exception as exc:
    report['error']=str(exc)
    report['traceback']=traceback.format_exc()
    raise
finally:
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in prod_files}
    report['production_files_unchanged']=before==after
    (QA/'test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    for path in [QA/'test-export.json',QA/'test-export.html']:
        path.unlink(missing_ok=True)
    server.shutdown()
