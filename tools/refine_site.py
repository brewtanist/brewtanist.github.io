"""Idempotent design installer for test workspaces. No stored content changes."""
from pathlib import Path
import hashlib
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
 builder=ROOT/'catalogue/build.py'
 if 'refine(args.base_url)' not in builder.read_text():
  guarded('catalogue/build.py','    extend(args.base_url)','    extend(args.base_url)\n    from refinement import refine\n    refine(args.base_url)')
 assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'_data/brewtanist').glob('*.json')}
 print('Design installed; all saved content and hosting settings preserved.')
if __name__=='__main__':main()
