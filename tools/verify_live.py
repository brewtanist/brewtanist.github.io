"""Verify the public main site after the approved copy is published."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from html import unescape
from html.parser import HTMLParser
import concurrent.futures,hashlib,json,time,os
ROOT=Path(__file__).resolve().parents[1];BASE='https://brewtanist.github.io';QA=ROOT/'qa';QA.mkdir(exist_ok=True)
def get(path):
    with urlopen(Request(BASE+path,headers={'User-Agent':'BrewtanistReleaseVerify/1.0','Cache-Control':'no-cache'}),timeout=30) as r:
        assert r.status==200
        return r.read()
home=json.loads((ROOT/'_data/brewtanist/home.json').read_text());settings=json.loads((ROOT/'_data/brewtanist/settings.json').read_text())
for attempt in range(12):
    try:
        raw=get('/?release='+os.environ.get('GITHUB_SHA','')[:12]);text=raw.decode('utf-8')
        assert home['hero_text'] in unescape(text),'Published copy is not this release yet'
        assert 'กาแฟกลับบ้าน' in text and 'ดูเมนูที่ร้าน' in text
        assert 'https://brewtanist.github.io/' in text
        break
    except Exception:
        if attempt==11:raise
        time.sleep(10)
class Assets(HTMLParser):
    def __init__(self):super().__init__();self.paths=set()
    def handle_starttag(self,tag,attrs):
        d=dict(attrs);s=d.get('src') if tag in ['img','script'] else d.get('href') if tag=='link' and d.get('rel')=='stylesheet' else None
        if s and s.startswith('/brewtanist/'):self.paths.add(urlsplit(s).path)
p=Assets();p.feed(text)
def verify(path):
    data=get(path);expected=(ROOT/path.lstrip('/')).read_bytes();assert hashlib.sha256(data).digest()==hashlib.sha256(expected).digest(),path;return path
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:assets=list(ex.map(verify,sorted(p.paths)))
report={'result':'PASS','website':BASE+'/','new_thai_copy_live':True,'assets_verified':assets,'catalogue_url':settings.get('catalogue_url',''),'catalogue_connected':bool(settings.get('catalogue_url')),'sha':os.environ.get('GITHUB_SHA'),'note':'Public HTTPS HTML and asset byte checks. This does not assert a catalogue hosting deployment.'}
(QA/'live-site-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
