"""Validate branch-only Pages CMS copy without contacting or logging into Pages CMS."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import yaml

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
    if not isinstance(descriptions, dict) or set(descriptions) != {'plantman', 'ozmo', 'lazybug'}:
        raise ValueError('Keep the three existing product ids')
    for key, value in descriptions.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError('Invalid product copy: ' + key)
    if type(data.get('revision')) is not int or data['revision'] < 1:
        raise ValueError('Invalid copy revision')

def validate_config(config):
    entries = config.get('content', [])
    if len(entries) != 1 or entries[0].get('type') != 'file' or entries[0].get('path') != 'prototype/copy.th.json':
        raise ValueError('Preview CMS may edit prototype/copy.th.json only')
    if config.get('media') or config.get('actions'):
        raise ValueError('No media uploader or deploy action in this copy-only editor')
    if config.get('settings', {}).get('content', {}).get('merge') is not True:
        raise ValueError('Preserve unmanaged JSON metadata with merge=true')
    fields = entries[0].get('fields', [])
    expected = {'title', 'intro', 'sourceDescription', 'descriptions', 'revision', 'editorial_notes'}
    if {f.get('name') for f in fields} != expected:
        raise ValueError('Unexpected CMS fields')
    for field in fields:
        if field['name'] in {'revision', 'editorial_notes'} and not field.get('readonly'):
            raise ValueError('Editorial metadata must remain read-only')
        if field['name'] == 'descriptions' and {f.get('name') for f in field.get('fields', [])} != {'plantman', 'ozmo', 'lazybug'}:
            raise ValueError('Unexpected product-description fields')

def main():
    config = yaml.safe_load((ROOT / '.pages.yml').read_text(encoding='utf-8'))
    copy = json.loads((ROOT / 'prototype/copy.th.json').read_text(encoding='utf-8'))
    validate_config(config)
    validate_copy(copy)
    cases = []
    for mutate in [lambda d: d.update(title=''), lambda d: d.update(intro='x' * 2001), lambda d: d['descriptions'].pop('ozmo')]:
        invalid = deepcopy(copy)
        mutate(invalid)
        try:
            validate_copy(invalid)
        except ValueError:
            cases.append('invalid copy rejected')
        else:
            raise AssertionError('Invalid copy was accepted')
    unsafe = deepcopy(config)
    unsafe['content'][0]['path'] = '_data/brewtanist/products.json'
    try:
        validate_config(unsafe)
    except ValueError:
        cases.append('production content path rejected')
    else:
        raise AssertionError('Production path allowed in draft CMS')
    subprocess.run(['git', 'diff', '--exit-code', 'origin/main', '--', *PROTECTED], cwd=ROOT, check=True)
    report = {
        'result': 'PASS', 'branch': BRANCH,
        'editable_file': 'prototype/copy.th.json',
        'editable_texts': ['title', 'intro', 'sourceDescription', 'descriptions.plantman', 'descriptions.ozmo', 'descriptions.lazybug'],
        'negative_tests': cases, 'production_content_matches_main': True,
        'preview_cms_configuration_differs_from_main_by_design': True,
        'pages_cms_owner_login_tested': False,
        'note': 'Configuration and build integration checks only. Browser login and owner Save through Pages CMS still need an owner-session test. No merge/publish/branch-protection setting has been applied.'
    }
    output = ROOT / 'prototype/qa/cms-config-report.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
