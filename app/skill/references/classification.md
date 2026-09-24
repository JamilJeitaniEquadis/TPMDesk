# Champ 11 — la classification

C'est le point d'extension le plus fréquent : chaque nouvel export apporte en général deux
à quatre catégories produit inconnues. C'est aussi le seul endroit où la chaîne demande un
vrai jugement plutôt qu'une règle.

## Ce que la plateforme attend

Pas le code de brique GPC, mais le **chemin complet**, choisi dans une liste de 364 valeurs :

```
Rayon | Catégorie | Sous-catégorie | Segment | CODE - Libellé de la brique
```

Exemple :

```
Cosmétiques | Parfum | Parfum Homme | Eau de parfum homme | 10000365 - Parfums
```

La valeur écrite doit correspondre **au caractère près** à une entrée de la liste, espaces
compris — plusieurs entrées ont un espace double avant le séparateur. Toujours copier
depuis la liste, jamais retaper.

Le libellé du champ dans l'extraction est
`Rayon|Catégorie de produits|Sous Catégorie|Brique GPC` : les champs Rayon et Catégorie,
qui semblent absents du template, sont en fait portés par celui-ci.

## Comment la chaîne décide

Dans `pipeline.py`, par ordre de priorité :

1. **Règle coffret** — si la classification source commence par `COFFRET`, si la catégorie
   site web contient `Coffret`, **ou si le libellé produit contient « coffret »** :
   assortiment parfum si c'est un parfum ou un coffret alcool, sinon assortiment cosmétique.
   Le troisième critère a été ajouté après coup : deux produits portaient « Coffret » dans
   leur seul libellé, sans aucune classification source.
2. **Baume à lèvres** — classification source `BAUME LEVRES` → brique dédiée.
3. **`CLASSIF_KIND`** — chemin lié à une catégorie source précise, quand la brique seule ne
   suffit pas à choisir (un soin des yeux et une crème corps partagent la brique 10000356).
4. **`GPC` puis `CLASSIF`** — catégorie source → brique → chemin.

## Ajouter une catégorie

`inspect_export.py` les signale. Pour chacune :

1. **Regarder les produits réels**, pas seulement le libellé de la catégorie. La source se
   trompe : un « Accessoire de soin » était une huile de soin Shiseido, une « Hygiène bébé »
   était un parfum enfant IKKS, un « Complément alimentaire » était un complément bronzant
   oral — qui existe bel et bien dans la taxonomie, brique 10000731.
2. **Chercher dans la liste du champ 11** de l'extraction. Pour la lire :

```python
import re
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string as cif
wb = load_workbook('extraction.xlsx')
ws = wb['Produit']
col11 = next(c for c in range(1, ws.max_column + 1)
             if str(ws.cell(row=1, column=c).value) == '11')
lettre = ws.cell(row=1, column=col11).column_letter
for dv in ws.data_validations.dataValidation:
    if lettre in {re.match(r'([A-Z]+)', x).group(1) for x in str(dv.sqref).split()}:
        m = re.match(r"(Lists_\w+)!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", str(dv.formula1).strip('='))
        w = wb[m.group(1)]; c = cif(m.group(2))
        for r in range(int(m.group(3)), int(m.group(5)) + 1):
            v = w.cell(row=r, column=c).value
            if v and 'parfum' in str(v).lower():      # adapter le filtre
                print(v)
```

3. **Ajouter l'entrée** dans `GPC` + `CLASSIF`, ou dans `CLASSIF_KIND` si le choix dépend de
   la catégorie source et pas seulement de la brique.
4. **Le signaler dans la restitution** comme un arbitrage à valider, pas comme un acquis.

## Cas où la taxonomie ne colle pas

La brique 10000328 « Additifs pour Bain » n'existe dans cette taxonomie que sous l'hygiène
infantile. Des gels et huiles lavants adultes ont donc été reclassés en 10000330
« Nettoyage/Toilette/Savon - Personnel ».

Quand cela arrive : choisir l'entrée existante la plus proche, **ne pas inventer de chemin**
(il serait rejeté), et signaler le reclassement au client.

## Chemins déjà définis

Voir `CLASSIF` et `CLASSIF_KIND` dans `scripts/pipeline.py` : environ 25 chemins couvrant
parfums (par genre), coffrets, soins visage et corps, solaires, maquillage (teint, yeux,
lèvres, ongles), cheveux (shampooing, soin, coiffant, coloration), hygiène, rasage,
accessoires, parfum enfant et compléments bronzants oraux.
