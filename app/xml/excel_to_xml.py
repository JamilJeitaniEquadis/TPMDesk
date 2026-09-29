# -*- coding: utf-8 -*-
"""
Extraction Gaia (.xlsx) -> XML au format DataModelEquadis (products / product / field / logs / log / packs / pack).

    python excel_to_xml.py --excel extraction.xlsx --out produits.xml [--report rapport.txt]

Règles :
- Produit : une ligne de l'onglet Produit (à partir de la ligne 7) = un <product>. Ligne 1 = id du champ,
  ligne 6 = langue (Français -> LANG_FRA, Anglais -> LANG_ANG). Plusieurs colonnes d'un même id = plusieurs <value>.
- Groupes imbriqués repris du modèle : 185 (contacts), 2236 (2238), 400_0 (400), UL3P (UL3_1, UL3_2).
- Champ 11 : le code de la brique GPC (fin du chemin « … | 10000356 - libellé »), comme dans le modèle.
- Logistique : les lignes de l'onglet Logistique rattachées au GTIN produit (champ 2) donnent <logs><log>,
  avec les champs UL puis <packs><pack> pour les champs PK.
- Valeurs : telles que dans l'Excel, sauf les codes que le modèle montre lui-même (PK3, PK32, PK40…PK49, UL2).
  Le rapport liste les champs à liste de valeurs restés en libellé.
"""
import argparse, re
from collections import OrderedDict, defaultdict
from xml.sax.saxutils import escape
from openpyxl import load_workbook

LANG = {'Français': 'LANG_FRA', 'Anglais': 'LANG_ANG'}
IDENT = {'2', 'PK1', 'PK9', '3', '172', '185_4', '1225', '2320'}      # textes à conserver tels quels (zéros, codes)
GROUPES_PRODUIT = {                                                   # parent -> enfants (repris du modèle)
    '185': ['185_1', '185_2', '185_3', '185_4', '2227', '2225', '2223', '2224', '185_5'],
    '2236': ['2238', '2241'],
    '400_0': ['400'],
}
GROUPES_LOG = {'UL3P': ['UL3_1', 'UL3_2', 'UL3_3']}
CODES_MODELE = {                                                      # valeurs dont le modèle donne le code
    'PK3': {'Carton': 'COND_CARTON', 'Palette': 'COND_PALETTE'},
    'PK32': {'Carton': 'PACK_TYPE_CT'},
    'UL2': {'Oui': 'true', 'Non': 'false'},
    **{k: {'Oui': '1', 'Non': '0'} for k in ('PK40', 'PK41', 'PK42', 'PK43', 'PK44', 'PK46', 'PK49')},
}

def texte(fid, v):
    if v is None: return None
    if isinstance(v, float) and v.is_integer() and fid not in IDENT: v = int(v)
    s = str(v).strip()
    return s or None

def lire(ws):
    cols = []
    for c in range(1, ws.max_column + 1):
        fid = ws.cell(row=1, column=c).value
        if fid in (None, ''): continue
        cols.append((c, str(fid), LANG.get(str(ws.cell(row=6, column=c).value or '').strip())))
    lignes = []
    for r in range(7, ws.max_row + 1):
        rec = OrderedDict()
        for c, fid, lang in cols:
            s = texte(fid, ws.cell(row=r, column=c).value)
            if s is None: continue
            rec.setdefault(fid, []).append((lang, s))
        if rec.get('2'): lignes.append(rec)
    return lignes

def code_brique(s):
    m = re.search(r'\|\s*(\d{8})\s*-', s)
    return m.group(1) if m else s

def valeurs(fid, vals, ind, restes):
    out = []
    for lang, s in vals:
        if fid == '11': s = code_brique(s)
        elif fid in CODES_MODELE:
            s = CODES_MODELE[fid].get(s, s)
        a = f' lang="{lang}"' if lang else ''
        out.append(f'{ind}\t<value{a}>{escape(s)}</value>')
    return out

def champ(fid, vals, ind, restes):
    return [f'{ind}<field id="{fid}">'] + valeurs(fid, vals, ind, restes) + [f'{ind}</field>']

def bloc(rec, groupes, ind, restes, exclus=()):
    out, faits = [], set(exclus)
    enfant_de = {e: p for p, es in groupes.items() for e in es}
    for fid, vals in rec.items():
        if fid in faits: continue
        p = enfant_de.get(fid)
        if p:
            if p in faits: continue
            faits.add(p)
            enfants = [e for e in groupes[p] if e in rec]
            out += [f'{ind}<field id="{p}">', f'{ind}\t<value>']
            for e in enfants:
                out += champ(e, rec[e], ind + '\t\t', restes); faits.add(e)
            out += [f'{ind}\t</value>', f'{ind}</field>']
            continue
        out += champ(fid, vals, ind, restes); faits.add(fid)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--excel', required=True); ap.add_argument('--out', required=True); ap.add_argument('--report')
    a = ap.parse_args()
    wb = load_workbook(a.excel, read_only=False, data_only=True)
    prods = lire(wb['Produit'])
    logs = defaultdict(list)
    if 'Logistique' in wb.sheetnames:
        for rec in lire(wb['Logistique']):
            logs[rec['2'][0][1]].append(rec)
    restes = set()
    L = ['<?xml version="1.0" encoding="UTF-8"?>', '<products>']
    for p in prods:
        L.append('\t<product>')
        L += bloc(p, GROUPES_PRODUIT, '\t\t', restes)
        g = p['2'][0][1]
        if logs.get(g):
            L.append('\t\t<logs>')
            for lg in logs[g]:
                L.append('\t\t\t<log>')
                ul = OrderedDict((k, v) for k, v in lg.items() if k.startswith('UL'))
                pk = OrderedDict((k, v) for k, v in lg.items() if k.startswith('PK'))
                L += bloc(ul, GROUPES_LOG, '\t\t\t\t', restes)
                if pk:
                    L += ['\t\t\t\t<packs>', '\t\t\t\t\t<pack>']
                    L += bloc(pk, {}, '\t\t\t\t\t\t', restes)
                    L += ['\t\t\t\t\t</pack>', '\t\t\t\t</packs>']
                L.append('\t\t\t</log>')
            L.append('\t\t</logs>')
        L.append('\t</product>')
    L.append('</products>')
    open(a.out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f"{len(prods)} produits, {sum(len(v) for v in logs.values())} unités logistiques -> {a.out}")
    if a.report:
        open(a.report, 'w', encoding='utf-8').write(rapport(wb))

def rapport(wb):
    """Champs dont toutes les valeurs viennent des listes de l'extraction (Lists_Prd / Lists_Log) :
    ce sont des listes de valeurs, écrites ici en libellé alors que le modèle attend peut-être un code."""
    choix = set()
    for nom in ('Lists_Prd', 'Lists_Log'):
        if nom in wb.sheetnames:
            for row in wb[nom].iter_rows(values_only=True):
                choix.update(str(v).strip() for v in row if v not in (None, ''))
    lignes = ['Champs à liste de valeurs écrits en libellé (le modèle attend peut-être un code) :', '']
    for nom in ('Produit', 'Logistique'):
        ws = wb[nom]
        for c in range(1, ws.max_column + 1):
            fid = str(ws.cell(row=1, column=c).value)
            if fid == '11' or fid in CODES_MODELE: continue
            vals = {str(ws.cell(row=r, column=c).value).strip() for r in range(7, ws.max_row + 1)
                    if ws.cell(row=r, column=c).value not in (None, '')}
            if vals and all(v in choix for v in vals) and not all(re.fullmatch(r'[\d.,]+', v) for v in vals):
                lignes.append(f"{nom:10} {fid:7} {str(ws.cell(row=2, column=c).value)[:45]:45}  {', '.join(sorted(vals))[:120]}")
    return '\n'.join(lignes) + '\n'

if __name__ == '__main__':
    main()
