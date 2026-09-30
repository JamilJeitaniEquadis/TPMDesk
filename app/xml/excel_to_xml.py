# -*- coding: utf-8 -*-
"""
Extraction Gaia (.xlsx) -> XML au format DataModelEquadis (products / product / field / logs / log / packs / pack).

    python excel_to_xml.py --excel extraction.xlsx --outdir dossier/ [--export export_supplierxm.xlsx] [--gln "CFEB SISLEY=3xxxxxxxxxxxx" ...]

Un fichier par fournisseur : chaque <product gln="..."> d'un fichier porte le même GLN (condition de
dépôt côté centrale). GLN du produit, dans l'ordre : GLN du fournisseur lu dans l'export SupplierXM
(--export, partyGLN au rôle SUPPLIER ; Gaia n'a pas ce champ), GLN du contact (185_4), GLN du propriétaire de la
marque (172), GLN donné en option pour le nom du contact (185_2), GLN du même contact vu sur un autre
produit, puis GLN des autres produits de la même marque (signalé comme déduit). Un GLN doit passer la
clé GS1. Sans GLN, le produit n'est écrit dans aucun fichier et le rapport le liste.

Règles :
- Produit : une ligne de l'onglet Produit (à partir de la ligne 7) = un <product>. Ligne 1 = id du champ,
  ligne 6 = langue (Français -> LANG_FRA, Anglais -> LANG_ANG). Plusieurs colonnes d'un même id = plusieurs <value>.
- Imbrication : chaque champ va dans ses tables parentes (DynamicTable / DynamicPanel) d'après id_parent
  du dictionnaire equafield.json (table equafield), par ex. 8 > 8_1, 3567 > 126, 185 > 2108 > 185_6.
- Champ 11 : le code de la brique GPC (fin du chemin « … | 10000356 - libellé »), comme dans le modèle.
- Logistique : les lignes de l'onglet Logistique rattachées au GTIN produit (champ 2) donnent <logs><log>,
  avec les champs UL puis <packs><pack> pour les champs PK.
- Valeurs : telles que dans l'Excel, sauf les codes que le modèle montre lui-même (PK3, PK32, PK40…PK49, UL2).
  Le rapport liste les champs à liste de valeurs restés en libellé.
"""
import argparse, json, os, re
from collections import OrderedDict, defaultdict
from xml.sax.saxutils import escape
from openpyxl import load_workbook

LANG = {'Français': 'LANG_FRA', 'Anglais': 'LANG_ANG'}
IDENT = {'2', 'PK1', 'PK9', '3', '172', '185_4', '1225', '2320'}      # textes à conserver tels quels (zéros, codes)
TABLES = ('DynamicTable', 'DynamicPanel')
DICO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'equafield.json'), encoding='utf-8'))
                                                                      # id -> [type, id_parent] (table equafield)
def parents(fid):
    """Tables dynamiques qui contiennent le champ, de la plus proche à la plus haute (sections et modules exclus)."""
    out, p = [], (DICO.get(fid) or [None, None])[1]
    while p in DICO and DICO[p][0] in TABLES and p not in out:
        out.append(p); p = DICO[p][1]
    return out

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

def bloc(rec, ind, restes):
    """Champs de rec, chacun emboîté dans ses tables parentes (id_parent du dictionnaire) :
    <field id="table"><value> … enfants … </value></field>, dans l'ordre des colonnes de l'Excel."""
    arbre = OrderedDict()
    for fid, vals in rec.items():
        n = arbre
        for p in reversed(parents(fid)): n = n.setdefault(p, OrderedDict())
        n[fid] = vals
    def ecrire(n, ind):
        out = []
        for fid, v in n.items():
            if isinstance(v, OrderedDict):
                out += [f'{ind}<field id="{fid}">', f'{ind}\t<value>'] + ecrire(v, ind + '\t\t') + [f'{ind}\t</value>', f'{ind}</field>']
            else:
                out += champ(fid, v, ind, restes)
        return out
    return ecrire(arbre, ind)

def cle_gln(g):
    d = str(g)
    if not d.isdigit() or len(d) != 13: return False
    n = [int(x) for x in d]
    return (10 - sum(x * (1 if i % 2 == 0 else 3) for i, x in enumerate(n[:-1])) % 10) % 10 == n[-1]

norm = lambda s: re.sub(r'\s+', ' ', str(s or '')).strip().upper()
premier = lambda rec, fid: (rec.get(fid) or [(None, None)])[0][1]

def gln_export(chemin):
    """GLN du fournisseur par GTIN, lu dans l'export SupplierXM (partyGLN au rôle SUPPLIER, onglet Product)."""
    ws = load_workbook(chemin, read_only=True, data_only=True)['Product']
    lignes = ws.iter_rows(values_only=True)
    entetes = [next(lignes) for _ in range(7)]            # Thème, Nom, Description, Chemin, Type, Unité, Exemple
    chemins = [str(x or '') for x in entetes[3]]
    col = lambda p: [i for i, x in enumerate(chemins) if x == p]
    gt = col('gtin')[0]
    trio = list(zip(col('partyInformationList.partyRoleCode'), col('partyInformationList.partyGLN'),
                    col('partyInformationList.partyNameText')))
    out = {}
    for r in lignes:
        if not r[gt]: continue
        for ro, gl, no in trio:
            g = str(r[gl] or '').strip()
            if str(r[ro] or '').endswith('SUPPLIER') and g:
                out[str(r[gt]).strip().zfill(14)] = (g.zfill(13), norm(r[no])); break
    return out

def attribuer_gln(prods, donnes, fournisseurs={}):
    """Renvoie {gtin: (gln, fournisseur, comment)} pour les produits dont le GLN est établi."""
    par_contact, par_marque = {}, defaultdict(set)
    for p in prods:
        g = next((x for x in (premier(p, '185_4'), premier(p, '172')) if x and cle_gln(x)), None)
        if g:
            if premier(p, '185_2'): par_contact.setdefault(norm(premier(p, '185_2')), g)
            if premier(p, '109'): par_marque[norm(premier(p, '109'))].add(g)
    out = {}
    for p in prods:
        gt, nom, marque = premier(p, '2'), norm(premier(p, '185_2')), norm(premier(p, '109'))
        g, f = fournisseurs.get(str(gt).zfill(14), (None, None))
        if g and cle_gln(g):
            out[gt] = (g, f or nom or marque, 'GLN du fournisseur (export, partyGLN SUPPLIER)'); continue
        for comment, g in (('GLN du contact (185_4)', premier(p, '185_4')),
                           ('GLN du propriétaire de la marque (172)', premier(p, '172')),
                           ('GLN donné pour ' + nom, donnes.get(nom)),
                           ('même contact sur un autre produit', par_contact.get(nom))):
            if g and cle_gln(g):
                out[gt] = (g, nom or marque, comment); break
        else:
            gs = par_marque.get(marque, set())
            if not nom and len(gs) == 1:
                out[gt] = (next(iter(gs)), marque, 'DÉDUIT de la marque ' + marque + ' (aucun contact sur le produit)')
    return out

def ecrire_produit(L, p, gln, logs, restes):
    L.append(f'\t<product gln="{gln}">')
    L += bloc(p, '\t\t', restes)
    g = p['2'][0][1]
    if logs.get(g):
        L.append('\t\t<logs>')
        for lg in logs[g]:
            L.append('\t\t\t<log>')
            ul = OrderedDict((k, v) for k, v in lg.items() if k.startswith('UL'))
            if p.get('8_1'):                                   # marché cible logistique = marché cible produit
                ul['UL3_1'] = p['8_1']
            pk = OrderedDict((k, v) for k, v in lg.items() if k.startswith('PK'))
            L += bloc(ul, '\t\t\t\t', restes)
            if pk:
                L += ['\t\t\t\t<packs>', '\t\t\t\t\t<pack>']
                L += bloc(pk, '\t\t\t\t\t\t', restes)
                L += ['\t\t\t\t\t</pack>', '\t\t\t\t</packs>']
            L.append('\t\t\t</log>')
        L.append('\t\t</logs>')
    L.append('\t</product>')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--excel', required=True)
    ap.add_argument('--outdir', required=True, help="dossier des fichiers XML, un par GLN")
    ap.add_argument('--export', help="export SupplierXM d'origine : on y lit le GLN du fournisseur (prioritaire)")
    ap.add_argument('--gtin', action='append', default=[], help="n'écrire que ces produits (test)")
    ap.add_argument('--gln', action='append', default=[], help='"NOM DU CONTACT=GLN" pour un fournisseur sans GLN dans l\'Excel')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    donnes = {}
    for x in a.gln:
        nom, _, g = x.rpartition('=')
        if not cle_gln(g.strip()): raise SystemExit(f"GLN refusé (clé GS1 invalide) : {x}")
        donnes[norm(nom)] = g.strip()
    wb = load_workbook(a.excel, read_only=False, data_only=True)
    prods = lire(wb['Produit'])
    if a.gtin: prods = [p for p in prods if premier(p, '2') in a.gtin]
    logs = defaultdict(list)
    if 'Logistique' in wb.sheetnames:
        for rec in lire(wb['Logistique']):
            logs[rec['2'][0][1]].append(rec)
    gln = attribuer_gln(prods, donnes, gln_export(a.export) if a.export else {})
    groupes = defaultdict(list)
    for p in prods:
        if premier(p, '2') in gln: groupes[gln[premier(p, '2')][0]].append(p)
    base = re.sub(r'^[0-9a-f]{8}-', '', re.sub(r'\.xls[xm]$', '', os.path.basename(a.excel), flags=re.I))
    restes, fichiers = set(), []
    for g, ps in sorted(groupes.items(), key=lambda x: -len(x[1])):
        nom = gln[premier(ps[0], '2')][1]
        f = os.path.join(a.outdir, f"{base}_{g}_{re.sub(r'[^A-Za-z0-9]+', '_', nom).strip('_')}.xml")
        L = ['<?xml version="1.0" encoding="UTF-8"?>', '<products>']
        for p in ps: ecrire_produit(L, p, g, logs, restes)
        L.append('</products>')
        open(f, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
        fichiers.append((f, g, nom, ps))
    sans = [p for p in prods if premier(p, '2') not in gln]
    R = [f"{len(prods)} produits : {sum(len(x[3]) for x in fichiers)} répartis en {len(fichiers)} fichier(s), {len(sans)} sans GLN.", '']
    for f, g, nom, ps in fichiers:
        R.append(f"{os.path.basename(f)}  ({len(ps)} produits, GLN {g}, {nom})")
        for p in ps:
            comment = gln[premier(p, '2')][2]
            if comment.startswith('DÉDUIT'): R.append(f"    {premier(p, '2')}  {comment}")
    if sans:
        R += ['', 'SANS GLN, écrits dans aucun fichier (relancer avec --gln "NOM=GLN") :']
        par = defaultdict(list)
        for p in sans: par[norm(premier(p, '185_2')) or '(aucun contact) ' + norm(premier(p, '109'))].append(premier(p, '2'))
        for nom, gs in sorted(par.items(), key=lambda x: -len(x[1])):
            R.append(f"    {nom}: {len(gs)} produits  ({', '.join(gs[:4])}{' ...' if len(gs) > 4 else ''})")
    R += ['', rapport(wb)]
    open(os.path.join(a.outdir, base + '_rapport.txt'), 'w', encoding='utf-8').write('\n'.join(R) + '\n')
    print('\n'.join(R[:len(R)-1]))

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
