"""Check pinned GitHub Actions against OSV without requiring Dependency Graph access.

Only public action repository names, commit hashes and release versions leave this
process. Unknown pins, failed lookups and API errors fail the check, not a silent pass.
This covers direct workflow actions, not their transitive/npm dependencies.
"""
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USES = re.compile(r'^\s*(?:-\s*)?uses:\s*[\"\']?([^\s\"\'#]+)', re.M)
PIN = re.compile(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([a-f0-9]{40})$')
VERSION = re.compile(r'^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$')


def pins(text):
    result = set()
    for value in USES.findall(text):
        if value.startswith('./'):
            continue
        match = PIN.fullmatch(value)
        if not match:
            raise ValueError('Action must use a full commit pin; unsupported reference: ' + value)
        result.add((match[1], match[2]))
    return result


def api(url, payload=None):
    headers = {'User-Agent': 'Website-Action-Security-Check/1.0', 'Accept': 'application/json'}
    if url.startswith('https://api.github.com/') and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    body = None if payload is None else json.dumps(payload).encode()
    if body is not None:
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=30) as response:
        return json.loads(response.read(8 * 1024 * 1024))


def release_versions(repo, sha, get=api):
    versions = set()
    for page in range(1, 4):
        tags = get(f'https://api.github.com/repos/{repo}/tags?per_page=100&page={page}')
        if not isinstance(tags, list):
            raise ValueError('Unexpected tag response for ' + repo)
        for tag in tags:
            if tag['commit']['sha'] == sha and VERSION.fullmatch(tag['name']):
                versions.add(tag['name'].removeprefix('v'))
        if versions or len(tags) < 100:
            break
    if not versions:
        raise ValueError('No verifiable release version for pinned action ' + repo + '@' + sha)
    return sorted(versions)


def vulnerabilities(query, post=api):
    found = set()
    for _ in range(20):
        data = post('https://api.osv.dev/v1/query', query)
        if not isinstance(data, dict):
            raise ValueError('Unexpected OSV response')
        found.update(v['id'] for v in data.get('vulns', []) if not v.get('withdrawn'))
        token = data.get('next_page_token')
        if not token:
            return found
        query = {**query, 'page_token': token}
    raise ValueError('OSV results exceeded pagination bound')


def main():
    actions = set()
    workflows = list((ROOT / '.github/workflows').glob('*.yml')) + list((ROOT / '.github/workflows').glob('*.yaml'))
    for path in workflows:
        actions.update(pins(path.read_text(encoding='utf-8')))
    if not actions:
        raise ValueError('No pinned actions found; refusing to report an empty successful scan')
    findings = []
    for repo, sha in sorted(actions):
        versions = release_versions(repo, sha)
        known = vulnerabilities({'commit': sha})
        for version in versions:
            known.update(vulnerabilities({'package': {'name': repo, 'ecosystem': 'GitHub Actions'}, 'version': version}))
        print(repo, ','.join(versions), sha, 'FINDINGS: ' + ', '.join(sorted(known)) if known else 'no known OSV findings')
        findings.extend(known)
    if findings:
        raise SystemExit('Known action vulnerabilities require review: ' + ', '.join(sorted(set(findings))))
    print(f'PASS: {len(actions)} direct action pins checked against public commit and release advisories.')


def self_test():
    pin = 'a' * 40
    assert pins('  - uses: actions/checkout@' + pin) == {('actions/checkout', pin)}
    assert pins('    uses: ./.github/workflows/security.yml') == set()
    for unsafe in ('actions/checkout@v4', 'docker://unversioned', '${{'):
        try:
            pins('uses: ' + unsafe)
        except ValueError:
            pass
        else:
            raise AssertionError('Unresolved action passed')
    tags = [{'name': 'v4', 'commit': {'sha': pin}}, {'name': 'v4.2.2', 'commit': {'sha': pin}},
            {'name': 'v6.0.0', 'commit': {'sha': 'b' * 40}}]
    assert release_versions('actions/checkout', pin, lambda _: tags) == ['4.2.2']
    try:
        release_versions('actions/checkout', 'c' * 40, lambda _: tags)
    except ValueError:
        pass
    else:
        raise AssertionError('Unresolved commit passed')
    def fake_post(url, query):
        return {'vulns': [{'id': 'TEST-OLD', 'withdrawn': '2020-01-01'}, {'id': 'TEST-1'}], 'next_page_token': 'next'} if 'page_token' not in query else {'vulns': [{'id': 'TEST-2'}]}
    assert vulnerabilities({'commit': pin}, fake_post) == {'TEST-1', 'TEST-2'}
    print('PASS: mutable/unresolved actions fail, release SHA matching and advisory pagination work.')


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    else:
        main()
