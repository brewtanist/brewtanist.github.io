"""Check draft CMS paths, actual images and invalid inputs. No owner-session claims."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import yaml
from catalog_data import validate_products, load_products, warnings_for, IDS

ROOT = Path(__file__).resolve().parents[1]
BRANCH = 'preview/brewtanist-lab-20261108'
PROTECTED = ['index.html', '_data', '_config.yml', 'brewtanist', 'admin', '_includes', 'robots.txt', 'sitemap.xml']

def validate_copy(data):
    if not isinstance(data, dict):
        raise ValueError('Draft must be a JSON object')
    for key, limit in [('title', 160), ('intro', 2000), ('sourceDescription', 2000)]:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Invalid draft text: ' + key)
    descriptions = data.get('descriptions')
    if not isinstance(descriptions, dict) or set(descriptions) != IDS:
        raise ValueError('Keep the three existing product ids')
    if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in descriptions.values()):
        raise ValueError('Invalid product copy')
    if type(data.get('revision')) is not int or data['revision'] < 1:
        raise ValueError('Invalid copy revision')

def validate_config(config):
    entries = config.get('content', [])
    if len(entries) != 2 or {e.get('path') for e in entries} != {'prototype/copy.th.json', 'prototype/products.json'} or any(e.get('type') != 'file' for e in entries):
        raise ValueError('CMS may edit the two preview files only')
    media = config.get('media', {})
    if not isinstance(media, dict) or media.get('input') != 'prototype/media' or media.get('output') != '/prototype/media' or set(media.get('extensions', [])) != {'jpg', 'jpeg', 'png', 'webp'}:
        raise ValueError('Media must be confined to prototype/media raster images')
    if config.get('actions') or media.get('actions') or any(e.get('actions') for e in entries):
        raise ValueError('Preview CMS cannot publish or dispatch deployment actions')
    if config.get('settings', {}).get('content', {}).get('merge') is not True:
        raise ValueError('Preserve metadata with merge=true')
    entry = next(e for e in entries if e['path'] == 'prototype/products.json')
    fields = next(f for f in entry['fields'] if f['name'] == 'items')['fields']
    expected = {'id', 'name', 'visible', 'profile', 'notes', 'image', 'alt', 'theme', 'price', 'sizes', 'grinding', 'origin', 'productUrl', 'tasteTags', 'drinkTags', 'verified'}
    if {f['name'] for f in fields} != expected:
        raise ValueError('Unexpected product fields')
    if not next(f for f in fields if f['name'] == 'id').get('readonly'):
        raise ValueError('Product ids must be read-only')

def main():
    config = yaml.safe_load((ROOT / '.pages.yml').read_text(encoding='utf-8'))
    copy = json.loads((ROOT / 'prototype/copy.th.json').read_text(encoding='utf-8'))
    raw = json.loads((ROOT / 'prototype/products.json').read_text(encoding='utf-8'))
    validate_config(config)
    validate_copy(copy)
    rows = validate_products(raw, ROOT)
    cases = []
    def reject(name, validator, sample, mutation):
        changed = deepcopy(sample)
        mutation(changed)
        try:
            validator(changed)
        except (ValueError, TypeError):
            cases.append(name)
        else:
            raise AssertionError('Unsafe input accepted: ' + name)
    for key, value in [('title', ''), ('intro', 'x' * 2001), ('revision', -1)]:
        reject('invalid copy ' + key, validate_copy, copy, lambda d, k=key, v=value: d.update({k: v}))
    bad = [('price', '-5'), ('price', '0'), ('price', '250 บาท'), ('productUrl', 'javascript:alert(1)'), ('productUrl', 'https://shopee.co.th.evil.example/p'), ('productUrl', 'https://user@shopee.co.th/p'), ('image', '/prototype/media/../../.pages.yml'), ('image', 'https://example.com/a.png'), ('image', '/prototype/media/missing.png'), ('theme', 'red'), ('tasteTags', ['unknown']), ('visible', 'true')]
    for key, value in bad:
        reject('invalid product ' + key + ': ' + str(value), lambda d: validate_products(d, ROOT), raw, lambda d, k=key, v=value: d['items'][0].update({k: v}))
    reject('duplicate product id', lambda d: validate_products(d, ROOT), raw, lambda d: d['items'][1].update(id=d['items'][0]['id']))
    reject('missing product', lambda d: validate_products(d, ROOT), raw, lambda d: d['items'].pop())
    reject('production edit path', validate_config, config, lambda d: d['content'][0].update(path='_data/brewtanist/products.json'))
    reject('production media folder', validate_config, config, lambda d: d['media'].update(input='brewtanist/assets'))
    optional = deepcopy(raw)
    for row in optional['items']:
        for key in ('price', 'sizes', 'grinding', 'origin', 'productUrl'):
            row[key] = None
    assert all(p['price'] == '' for p in validate_products(optional, ROOT))
    subprocess.run(['git', 'diff', '--exit-code', 'origin/main', '--', *PROTECTED], cwd=ROOT, check=True)
    report = {'result': 'PASS', 'branch': BRANCH, 'editable_files': ['prototype/copy.th.json', 'prototype/products.json'], 'media_folder': 'prototype/media', 'negative_tests': cases, 'negative_tests_count': len(cases), 'optional_null_fields_supported': True, 'products': warnings_for(rows), 'production_content_matches_main': True, 'pages_cms_owner_login_tested': False, 'note': 'Configuration/build checks only, not an authenticated Pages CMS browser test. No branch-protection or production deployment change.'}
    out = ROOT / 'prototype/qa/cms-config-report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
