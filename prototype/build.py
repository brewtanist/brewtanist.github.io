"""Build one-file preview from saved draft copy/products. No production writes."""
from pathlib import Path
import hashlib
import json
import subprocess
from catalog_data import load_products, embedded_image, warnings_for

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'prototype/dist'
SOURCE_COMMIT = 'd5fb938873581dbc21ad1fafcdc9d89a5695313d'

def main():
    source = ROOT / '_data/brewtanist'
    original = json.loads((source / 'products.json').read_text(encoding='utf-8'))
    settings = json.loads((source / 'settings.json').read_text(encoding='utf-8'))
    home = json.loads((source / 'home.json').read_text(encoding='utf-8'))
    copy = json.loads((ROOT / 'prototype/copy.th.json').read_text(encoding='utf-8'))
    from check_cms import validate_copy
    validate_copy(copy)
    rows = load_products(ROOT)
    items = []
    for row in rows:
        item = dict(row)
        item.update(description=copy['descriptions'][row['id']], image=embedded_image(row['image'], ROOT), originalImage=row['image'], format='beans', source='prototype/products.json')
        items.append(item)
    ids = {'Mr. Plantman': 'plantman', 'Mr. Ozmo': 'ozmo', 'Ms. Lazybug': 'lazybug'}
    previous = {
        'title': 'กาแฟที่ชอบ\nในแบบของคุณ',
        'intro': 'เริ่มจากรสชาติที่คุ้นเคย หรือค่อย ๆ ลองอะไรใหม่ เลือกสำรวจ House Blend ทั้งสามคาแรกเตอร์ของ Brewtanist ได้ที่นี่',
        'descriptions': {ids[p['name']]: p['description'] for p in original['items'] if p['name'] in ids}
    }
    image_digests = {row['id']: hashlib.sha256(items[i]['image'].encode()).hexdigest() for i, row in enumerate(rows)}
    revision = hashlib.sha256(json.dumps({'copy': copy, 'rows': rows, 'images': image_digests}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    data = {
        'schemaVersion': 1, 'sourceCommit': SOURCE_COMMIT,
        'brand': settings['brand'], 'descriptor': settings['descriptor'],
        'title': copy['title'], 'intro': copy['intro'], 'sourceDescription': copy['sourceDescription'],
        'shopUrl': settings['shopee'], 'phone': settings['phone'],
        'heroImage': embedded_image(home['hero_image'], ROOT, owned=True), 'heroAlt': home['hero_alt'],
        'products': items, 'previousCopy': previous, 'copyRevision': copy['revision'], 'catalogRevision': revision
    }
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = (ROOT / 'prototype/template.html').read_text(encoding='utf-8')
    if template.count('__CATALOG_JSON__') != 1:
        raise ValueError('Expected exactly one seed placeholder')
    # A saved-source view must not be masked by older browser-only experiments.
    marker = "if (!document.body.dataset.snapshot) {"
    replacement = "if (!document.body.dataset.snapshot && new URLSearchParams(location.search).get('source') !== 'github') {"
    if marker in template:
        template = template.replace(marker, replacement)
    elif replacement not in template:
        raise ValueError('Cannot locate local-draft restore guard')
    template = template.replace('BREWTANIST / PREVIEW 02', 'BREWTANIST / PREVIEW 03')
    # Purely local editor retains its label; online edits use authenticated Pages CMS.
    needle = '<h1>แก้ข้อความและรูป</h1>'
    # Add the same small entry on all views, outside the router-managed DOM.
    entry = '<div class="wrap" style="padding:12px 0;font-size:12px"><a class="text-link" href="https://app.pagescms.org/" target="_blank" rel="noopener noreferrer">แก้ร่างที่เก็บใน GitHub ↗</a> <span class="muted">· เลือก branch preview/brewtanist-lab-20261108 · หน้าแก้ในเว็บตัวอย่างเก็บเฉพาะเครื่องนี้</span></div>'
    template = template.replace('<main class="wrap" id="app"', entry + '<main class="wrap" id="app"', 1)
    html = template.replace('__CATALOG_JSON__', raw)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'index.html').write_text(html, encoding='utf-8')
    (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    report = {
        'input_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'catalog_revision': revision, 'content_source': ['prototype/copy.th.json', 'prototype/products.json', 'prototype/media/'],
        'products': warnings_for(rows), 'embedded_images': len(items) + 1,
        'checkout': False, 'tracking': False, 'production_files_changed': False,
        'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
        'note': 'Draft data only. Optional unknown values stay empty. Owner login in Pages CMS is not tested by this build.'
    }
    (OUT / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
