"""Install a reversible presentation layer; never modify owner content or hosting settings."""
from pathlib import Path
import hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def guarded(path,old,new):
 p=ROOT/path;s=p.read_text(encoding='utf-8')
 if new in s:return
 if s.count(old)!=1:raise ValueError(f'Unexpected source in {path}: {old[:75]}')
 p.write_text(s.replace(old,new,1),encoding='utf-8')

def main():
 before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'_data/brewtanist').glob('*.json')}
 guarded('index.html','<body>','<body class="site-refined">')
 guarded('index.html','</head>','<link rel="stylesheet" href="/brewtanist/refinement.css?v=20261109-1">\n<script defer src="/brewtanist/refinement.js?v=20261109-1"></script>\n</head>')
 guarded('catalogue/build.py','    extend(args.base_url)','    extend(args.base_url)\n    from refinement import refine\n    refine(args.base_url)')
 # Only add styling / navigation assets. Canonical, data, verified links and CMS schema stay intact.
 assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'_data/brewtanist').glob('*.json')}
 print('Installed design-only changes; all eight CMS data files unchanged.')
if __name__=='__main__':main()
