"""Idempotent design installer for test workspaces. No stored content changes."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def guarded(path,old,new):
 p=ROOT/path;s=p.read_text(encoding='utf-8')
 if new in s:return
 if s.count(old)!=1:raise ValueError(f'Unexpected source in {path}: {old[:75]}')
 p.write_text(s.replace(old,new,1),encoding='utf-8')
class DesignTags(HTMLParser):
 def __init__(self,text):
  super().__init__();self.body=None;self.assets=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='body':self.body=attrs
  if tag=='link' and attrs.get('rel')=='stylesheet':self.assets.append(urlsplit(attrs.get('href','')).path)
  if tag=='script' and attrs.get('src'):self.assets.append(urlsplit(attrs['src']).path)
def protected_snapshot():
 paths=list((ROOT/'_data/brewtanist').glob('*.json'))
 paths += [ROOT/p for p in ['.pages.yml','render.yaml','_config.yml']]
 paths += list((ROOT/'admin').rglob('*'))
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
def main():
 before=protected_snapshot()
 page=ROOT/'_includes/home-page.html';text=page.read_text(encoding='utf-8');original=text;tags=DesignTags(text)
 if tags.body is None:raise ValueError('Homepage has no body element')
 classes=tags.body.get('class','').split()
 if 'site-refined' not in classes:
  body=re.search(r'<body\b[^>]*>',text,re.I)
  if body is None:raise ValueError('Homepage body tag was not found')
  tag=body.group(0);classes.append('site-refined');attribute='class="'+escape(' '.join(classes),quote=True)+'"'
  pattern=r'\bclass\s*=\s*([\"\']).*?\1'
  tag=re.sub(pattern,lambda m:attribute,tag,count=1,flags=re.S|re.I) if re.search(pattern,tag,re.S|re.I) else tag[:-1]+' '+attribute+'>'
  text=text[:body.start()]+tag+text[body.end():]
 additions=[]
 for asset,markup in [('/brewtanist/refinement.css','<link rel="stylesheet" href="/brewtanist/refinement.css">'),('/brewtanist/refinement.js','<script defer src="/brewtanist/refinement.js"></script>')]:
  count=tags.assets.count(asset)
  if count>1:raise ValueError('Duplicate design asset: '+asset)
  if count==0:additions.append(markup)
 if additions:
  if text.count('</head>')!=1:raise ValueError('Unexpected homepage head')
  text=text.replace('</head>','\n'.join(additions)+'\n</head>',1)
 if text!=original:page.write_text(text,encoding='utf-8')
 builder=ROOT/'catalogue/build.py'
 if 'refine(args.base_url)' not in builder.read_text():
  guarded('catalogue/build.py','    extend(args.base_url)','    extend(args.base_url)\n    from refinement import refine\n    refine(args.base_url)')
 assert before==protected_snapshot(),'Installer changed saved content or hosting settings'
 print('Design installed; all saved content and hosting settings preserved.')
if __name__=='__main__':main()
