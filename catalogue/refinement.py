"""Polish generated customer pages without changing stored product facts or URLs."""
from pathlib import Path
from html import escape
import re,shutil,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'catalogue/dist';E=lambda x:escape(str(x),quote=True)
def refine(base):
 for name in ['refinement.css','refinement.js']:shutil.copy2(ROOT/'catalogue'/name,OUT/'assets'/name)
 data=json.loads((ROOT/'_data/brewtanist/products.json').read_text());pack=[]
 for p in data['items']:
  if p.get('visible'):
   image='/assets/'+Path(p['image']).name
   if not (OUT/image.lstrip('/')).is_file():raise ValueError('Missing existing package image')
   pack.append('<img src="'+E(image)+'" alt="" width="450" height="450" decoding="async">')
 art='<div class="market-hero-art" aria-hidden="true">'+''.join(pack[:3])+'<span class="pack-caption">BREWTANIST / HOUSE BLENDS</span><span class="pack-mark">✳</span></div>'
 for f in OUT.rglob('*.html'):
  s=f.read_text(encoding='utf-8')
  s=s.replace('<body data-page=','<body class="catalogue-refined" data-page=',1)
  s=s.replace('</head>','<link rel="stylesheet" href="/assets/refinement.css"><script src="/assets/refinement.js" defer></script></head>',1)
  s=re.sub(r'<div class="market-hero-art" aria-hidden="true">.*?</div>',lambda m:art,s,count=1,flags=re.S)
  f.write_text(s,encoding='utf-8')
 print('Refined catalogue pages; existing package renders only; no prices, stock or hosting changes.')
