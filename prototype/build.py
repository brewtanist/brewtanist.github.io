"""Build a self-contained review prototype. Never writes production content."""
from pathlib import Path
from urllib.parse import urlsplit
import base64
import hashlib
import json
import mimetypes
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'prototype' / 'dist'
SOURCE_COMMIT = 'd5fb938873581dbc21ad1fafcdc9d89a5695313d'

def asset(path: str) -> str:
    # Only read owned local raster assets already present in this repository.
    target = (ROOT / path.lstrip('/')).resolve()
    allowed = (ROOT / 'brewtanist' / 'assets').resolve()
    if not target.is_relative_to(allowed) or target.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise ValueError('Unsupported image: ' + path)
    data = target.read_bytes()
    if len(data) > 8_000_000:
        raise ValueError('Image exceeds the prototype budget: ' + path)
    mime = mimetypes.guess_type(str(target))[0]
    return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')

def main() -> None:
    src = ROOT / '_data' / 'brewtanist'
    products = json.loads((src / 'products.json').read_text(encoding='utf-8'))
    settings = json.loads((src / 'settings.json').read_text(encoding='utf-8'))
    home = json.loads((src / 'home.json').read_text(encoding='utf-8'))
    ids = {'Mr. Plantman': 'plantman', 'Mr. Ozmo': 'ozmo', 'Ms. Lazybug': 'lazybug'}
    items = []
    for p in products['items']:
        if not p.get('visible', True):
            continue
        if p['name'] not in ids:
            raise ValueError('New product needs explicit review: ' + p['name'])
        notes = p['notes'].lower()
        taste = []
        if any(t in notes for t in ('chocolate', 'nutty')):
            taste.append('chocolate')
        if any(t in notes for t in ('vanilla', 'rum-raisin')):
            taste.append('sweet')
        if any(t in notes for t in ('floral', 'fruity', 'tea-like')):
            taste.append('fruity')
        drinks = [k for k, word in [('black', 'กาแฟดำ'), ('milk', 'กาแฟนม')] if word in p['description']]
        items.append({
            'id': ids[p['name']], 'name': p['name'], 'profile': p['profile'],
            'notes': p['notes'], 'description': p['description'],
            'image': asset(p['image']), 'originalImage': p['image'], 'alt': p['alt'],
            'theme': p['theme'], 'format': 'beans', 'visible': True,
            'price': '', 'sizes': '', 'grinding': '', 'origin': '', 'productUrl': '',
            'tasteTags': taste, 'drinkTags': drinks,
            'verified': False,
            'source': '_data/brewtanist/products.json'
        })
    if len(items) != 3:
        raise ValueError('Expected the three reviewed house blends')
    data = {
        'schemaVersion': 1, 'sourceCommit': SOURCE_COMMIT,
        'brand': settings['brand'], 'descriptor': settings['descriptor'],
        'title': 'กาแฟที่ชอบ\nในแบบของคุณ',
        'intro': 'เริ่มจากรสชาติที่คุ้นเคย หรือค่อย ๆ ลองอะไรใหม่ เลือกสำรวจ House Blend ทั้งสามคาแรกเตอร์ของ Brewtanist ได้ที่นี่',
        'sourceDescription': products['description'],
        'shopUrl': settings['shopee'], 'phone': settings['phone'],
        'heroImage': asset(home['hero_image']), 'heroAlt': home['hero_alt'],
        'products': items
    }
    # Approved copy-only overlay; source notes, roast and finder tags stay unchanged.
    copy = json.loads((ROOT / 'prototype' / 'copy.th.json').read_text(encoding='utf-8'))
    if set(copy['descriptions']) != {p['id'] for p in items}:
        raise ValueError('Copy must match exactly the saved product ids')
    data['previousCopy'] = {'title': data['title'], 'intro': data['intro'], 'descriptions': {p['id']: p['description'] for p in items}}
    for key in ['title', 'intro', 'sourceDescription']:
        if not isinstance(copy[key], str) or not copy[key].strip():
            raise ValueError('Empty editorial copy: ' + key)
        data[key] = copy[key]
    for item in items:
        item['description'] = copy['descriptions'][item['id']]
    data['copyRevision'] = copy['revision']
    raw_json = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    template = (ROOT / 'prototype' / 'template.html').read_text(encoding='utf-8')
    if template.count('__CATALOG_JSON__') != 1:
        raise ValueError('Template must contain one data placeholder')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'index.html').write_text(template.replace('__CATALOG_JSON__', raw_json), encoding='utf-8')
    (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    report = {'source_commit': SOURCE_COMMIT, 'content_source_sha256': hashlib.sha256((src / 'products.json').read_bytes()).hexdigest(), 'products': [p['name'] for p in items], 'embedded_images': len(items) + 1, 'checkout': False, 'tracking': False, 'production_files_changed': False, 'unconfirmed_fields': ['price', 'sizes', 'grinding', 'origin', 'productUrl', 'finder rules'], 'note': 'Flavor/drink tags derive from saved notes/description only; owner verification is still required.'}
    (OUT / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
