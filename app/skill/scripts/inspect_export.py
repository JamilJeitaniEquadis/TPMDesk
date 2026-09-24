# -*- coding: utf-8 -*-
"""
Reconnaissance d'un export SupplierXM avant traitement.

    python scripts/inspect_export.py --export nouvel_export.xlsx [--ref export_deja_traite.xlsx]

Répond à trois questions, dans cet ordre :
  1. La structure est-elle celle que la chaîne sait traiter ? (volumétrie, chemins techniques)
  2. Y a-t-il des catégories produit sans chemin de classification ? -> à compléter avant de livrer
  3. Y a-t-il des valeurs de liste inconnues ? -> à arbitrer avec le client

À lancer systématiquement sur un nouvel export. Cinq minutes ici évitent un aller-retour
d'intégration.
"""
import argparse, os, sys
from collections import Counter, defaultdict
from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import Feuille, code, lab, GPC, CLASSIF, CLASSIF_KIND, V_PACK, V_COLOR, V_TEXTURE, \
    V_SKIN, V_AREA, V_AGE, V_SPF, V_COUNTRY, V_BARCODE, V_GENDER, V_SUBST, V_DANGER, \
    V_ORDER_UOM, V_PLATFORM_TC, V_UOM_FACT

FEUILLES = ['Product', 'Logistical units', 'Images', 'Documents']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', required=True)
    ap.add_argument('--ref', help="export déjà traité, pour comparer les chemins techniques")
    a = ap.parse_args()

    wb = load_workbook(a.export, read_only=True, data_only=True)
    ref_paths = {}
    if a.ref:
        wr = load_workbook(a.ref, read_only=True, data_only=True)
        for sh in FEUILLES:
            if sh in wr.sheetnames:
                ref_paths[sh] = set(Feuille(wr[sh]).idx)
        wr.close()

    print("=" * 70)
    print("1. STRUCTURE")
    feuilles = {}
    for sh in FEUILLES:
        if sh not in wb.sheetnames:
            print(f"   {sh:18} ABSENTE"); continue
        F = Feuille(wb[sh]); feuilles[sh] = F
        msg = f"   {sh:18} {len(F.rows):5} lignes | {len(F.idx):3} chemins"
        if sh in ref_paths:
            new = sorted(set(F.idx) - ref_paths[sh])
            msg += f" | {len(new)} nouveaux"
            print(msg)
            for p in new:
                print(f"        + {p}")
        else:
            print(msg)

    P = feuilles.get('Product')
    if not P:
        return

    print()
    print("=" * 70)
    print("2. CLASSIFICATION (champ 11) — le point qui bloque le plus souvent")
    manquants = Counter()
    for r in P.rows:
        k = code(P.v(r, 'kind')) or ''
        cls = (lab(P.v(r, 'isClassifiedIn')) or '').upper()
        nom = str(P.v(r, 'namePublicLong') or '')
        web = lab(P.v(r, 'org1337WebsiteProductCategory')) or ''
        if 'COFFRET' in cls or 'Coffret' in web or 'coffret' in nom.lower():
            continue                       # traité par la règle coffret
        if 'BAUME LEVRES' in cls:
            continue
        if k in CLASSIF_KIND:
            continue
        brick = GPC.get(k)
        if brick is None or not any(key[0] == brick for key in CLASSIF):
            manquants[str(P.v(r, 'kind'))] += 1
    if manquants:
        print("   Catégories sans chemin — À COMPLÉTER dans pipeline.py avant de livrer :")
        for k, n in manquants.most_common():
            print(f"      {n:4} produits  {k}")
        print("   Pour chacune : regarder les libellés produits réels, puis choisir un chemin")
        print("   dans la liste de validation du champ 11 de l'extraction (voir references/classification.md).")
    else:
        print("   Aucune catégorie inconnue : toutes les catégories ont un chemin.")

    print()
    print("=" * 70)
    print("3. VALEURS DE LISTE INCONNUES")
    CONTROLES = [
        ('packagingInformationList.packagingTypeCode', V_PACK, "Type d'emballage"),
        ('colorGroup', V_COLOR, 'Couleur'),
        ('productTextureList.productTextureCode', V_TEXTURE, 'Texture'),
        ('skinTypeList.skinTypeCode', V_SKIN, 'Type de peau'),
        ('areaOfUseList.areaOfUseCode', V_AREA, 'Utilisation'),
        ('targetConsumerAgeList.targetConsumerAgeCode', V_AGE, "Groupe d'âge"),
        ('sunburnProtectionFactor', V_SPF, 'Indice solaire'),
        ('originCountry', V_COUNTRY, "Pays d'origine"),
        ('countryOfSettlement', V_COUNTRY, 'Pays de facturation'),
        ('dataCarrierTypeCode', V_BARCODE, 'Code à barres'),
        ('targetConsumerGender', V_GENDER, 'Cible consommateur'),
        ('typeOfDangerousSubstanceOrArticle', V_SUBST, 'Substance dangereuse'),
        ('classOfDangerousGoods', V_DANGER, 'Classe de danger'),
        ('orderingUnitOfMeasure', V_ORDER_UOM, 'Unité de commande'),
    ]
    trouve = False
    for path, table, titre in CONTROLES:
        inconnues = Counter()
        for r in P.rows:
            for i in range(P.n(path)):
                v = P.v(r, path, i)
                if v not in (None, '') and code(v) not in table:
                    inconnues[str(v)] += 1
        if inconnues:
            trouve = True
            print(f"   {titre} :")
            for v, n in inconnues.most_common():
                print(f"      {n:4} × {v}")
    L = feuilles.get('Logistical units')
    if L:
        for path, table, titre in [
                ('packagingInformationList.packagingTypeCode', V_PACK, "Type d'emballage (logistique)"),
                ('packagingInformationList.platformTermsAndConditionsCode', V_PLATFORM_TC, 'Support palette'),
                ('orderingUnitOfMeasure', V_UOM_FACT, 'Unité de facture'),
                ('dataCarrierTypeCode', V_BARCODE, 'Code à barres (logistique)')]:
            inconnues = Counter()
            for r in L.rows:
                v = L.v(r, path)
                if v not in (None, '') and code(v) not in table:
                    inconnues[str(v)] += 1
            if inconnues:
                trouve = True
                print(f"   {titre} :")
                for v, n in inconnues.most_common():
                    print(f"      {n:4} × {v}")
    if not trouve:
        print("   Aucune valeur inconnue.")

    print()
    print("=" * 70)
    print("4. QUALITÉ DE LA DONNÉE SOURCE (à remonter au client, pas à corriger)")
    sans_marque = sum(1 for r in P.rows
                      if not any(code(P.v(r, 'partyInformationList.partyRoleCode', i)) == 'BRAND_OWNER'
                                 for i in range(P.n('partyInformationList.partyRoleCode'))))
    print(f"   {sans_marque:4} produits sans rôle BRAND_OWNER (propriétaire de la marque)")
    gln_ko = Counter()
    for path in ['contactInformationList.contactGLN', 'partyInformationList.partyGLN']:
        for r in P.rows:
            for i in range(P.n(path)):
                v = P.v(r, path, i)
                if v in (None, ''): continue
                d = str(v)
                ok = d.isdigit() and len(d) == 13 and \
                     (10 - sum(int(x) * (1 if j % 2 == 0 else 3) for j, x in enumerate(d[:-1])) % 10) % 10 == int(d[-1])
                if not ok: gln_ko[d] += 1
    if gln_ko:
        print("   GLN à clé de contrôle invalide (ils seront ignorés à l'écriture) :")
        for v, n in gln_ko.most_common():
            print(f"      {n:4} × {v}")
    else:
        print("      Tous les GLN sont valides.")
    wb.close()

if __name__ == '__main__':
    main()
