# -*- coding: utf-8 -*-
"""
Intègre le skill (skill/), le pont desk.py et les wheels openpyxl dans tpm-desk.html (bloc #bundle).
À relancer après toute modification du skill ou de desk.py :  python app/build.py
Les wheels sont lues dans py/ (voir fetch-runtime.sh).
"""
import base64, glob, json, os, re

ICI = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ICI, 'tpm-desk.html')

fichiers = {}
for f in sorted(glob.glob(os.path.join(ICI, 'skill', '**', '*'), recursive=True)):
    if os.path.isfile(f):
        fichiers['/skill/' + os.path.relpath(f, os.path.join(ICI, 'skill')).replace(os.sep, '/')] = f
fichiers['/skill/desk.py'] = os.path.join(ICI, 'desk.py')
roues = glob.glob(os.path.join(ICI, 'py', '*.whl.wasm'))
if len(roues) < 2:
    raise SystemExit("Wheels openpyxl absentes de app/py/ : lancer d'abord app/fetch-runtime.sh")
for w in roues:
    fichiers['/wheels/' + os.path.basename(w)[:-len('.wasm')]] = w

bundle = {k: base64.b64encode(open(v, 'rb').read()).decode('ascii') for k, v in fichiers.items()}
html = open(PAGE, encoding='utf-8').read()
bloc = '<script type="application/json" id="bundle">' + json.dumps(bundle, separators=(',', ':')) + '</script>'
html, n = re.subn(r'<script type="application/json" id="bundle">.*?</script>', lambda m: bloc, html, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Bloc #bundle introuvable dans tpm-desk.html')
open(PAGE, 'w', encoding='utf-8').write(html)
print(f"{len(bundle)} fichiers intégrés, page : {os.path.getsize(PAGE) // 1024} Ko")
