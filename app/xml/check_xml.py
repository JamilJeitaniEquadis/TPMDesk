# -*- coding: utf-8 -*-
"""
Contrôle avant dépôt d'un dossier de XML DataModelEquadis, sur les règles Gaia déjà rencontrées.

    python check_xml.py dossier/
"""
import xml.etree.ElementTree as ET, glob, datetime, os, sys, collections

U = {'Gramme (g)': 0.001, 'Kilogramme (kg)': 1, 'Milligramme (mg)': 1e-6}
REGLES = {
    'REQ_603': 'VAT rate (604) empty', 'REQ_1025': 'Packaging type (1025) empty', 'RG_626': 'Customs code without target market (2107)',
    'RG_421': 'Order start after ship start', 'RG_909': 'Consumer-support (CXC) contact without address',
    'RG_180': 'Unit order date after the carton\'s', 'RG_183': 'Unit ship date after the carton\'s',
    'REQ_PK71': 'Order availability date (PK71) empty', 'REQ_PK32': 'Pack packaging type (PK32) empty',
    'DAZ_PK50': 'Minimum order quantity (PK50) is 0', 'DAZ_PK53': 'Order multiple (PK53) is 0',
    'RG_627': 'Pack gross weight below net weight', 'RG_138': 'Pack net weight below units x unit net weight (supplier data)',
    'GLN multiples': 'Several GLNs in one file', 'log sans pack': 'Logistics without any level',
}

def _d(s):
    try: return datetime.datetime.strptime(s, '%d/%m/%Y')
    except (TypeError, ValueError): return None

def verifier_fichier(f):
    ps = ET.parse(f).getroot().findall('product')
    bad = collections.defaultdict(list)
    plusieurs = len({x.get('gln') for x in ps}) > 1
    for p in ps:
        v = lambda i: ([x.findtext('value') for x in p.iter('field') if x.get('id') == i] or [None])[0]
        g, errs = v('2'), set()
        if v('1225') and not v('2107'): errs.add('RG_626')
        if _d(v('2234')) and _d(v('2231')) and _d(v('2234')) > _d(v('2231')): errs.add('RG_421')
        if p.find(".//field[@id='604']") is None: errs.add('REQ_603')
        if not v('1025'): errs.add('REQ_1025')
        if 'CXC' in str(v('185_1')) and not v('185_3'): errs.add('RG_909')
        if plusieurs: errs.add('GLN multiples')
        for lg in p.iter('log'):
            if lg.find('.//pack') is None: errs.add('log sans pack')
        for i, pk in enumerate(p.iter('pack')):
            w = lambda k: ([x.findtext('value') for x in pk.findall('field') if x.get('id') == k] or [None])[0]
            if i == 0 and _d(v('2234')) and _d(w('PK71')) and _d(v('2234')) > _d(w('PK71')): errs.add('RG_180')
            if i == 0 and _d(v('2231')) and _d(w('PK72')) and _d(v('2231')) > _d(w('PK72')): errs.add('RG_183')
            if not w('PK71'): errs.add('REQ_PK71')
            if not w('PK32'): errs.add('REQ_PK32')
            for k in ('PK50', 'PK53'):
                try:
                    if w(k) and float(w(k)) == 0: errs.add('DAZ_' + k)
                except ValueError: pass
            try:
                n = w('PK17') or w('PK10'); G, N = w('PK28'), w('PK30')
                un = float(v('158')) * U.get(v('159'), 0) if v('158') else None
                if G and N and float(G) < float(N): errs.add('RG_627')
                if n and N and un and float(N) + 1e-9 < float(n) * un: errs.add('RG_138')
            except ValueError: pass
        for x in errs: bad[x].append(g)
    return {'fichier': os.path.basename(f), 'gln': ps[0].get('gln') if ps else '', 'produits': len(ps),
            'erreurs': {k: v for k, v in sorted(bad.items())}}

def verifier(dossier):
    return [verifier_fichier(f) for f in sorted(glob.glob(os.path.join(dossier, '*.xml')))]

if __name__ == '__main__':
    for r in verifier(sys.argv[1]):
        e = {k: len(v) for k, v in r['erreurs'].items()}
        print(f"{r['fichier'][41:-4]:50} {r['produits']:4}  {e or 'OK'}")
        for k, gs in r['erreurs'].items():
            print('       ', k, ', '.join(gs[:12]))
