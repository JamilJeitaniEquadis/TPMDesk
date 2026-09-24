# Correspondance des champs

Le détail exécutable est dans `scripts/pipeline.py`, fonction `construire()`. Ce document
explique les choix, ce qu'un fichier de code ne dit pas.

## Comment lire un export SupplierXM

| Ligne | Contenu |
|---|---|
| 1 | Thème |
| 2 | Nom du champ (lisible) |
| 3 | Description |
| **4** | **Chemin technique — c'est la clé de repérage** |
| 5 | Type |
| 6 | Unité (sert à distinguer `grossWeight` en g de `grossWeight` en kg) |
| 7 | Exemple |
| 8+ | Données |

Les valeurs de liste ont la forme `Libellé ∣ CODE`, avec le séparateur U+2223 (et non une
barre verticale ordinaire). `code()` et `lab()` dans `pipeline.py` font l'extraction.

Onglets : `Product` (UVC), `Logistical units`, `Images`, `Documents`, `Code list`.

## Comment lire une extraction Gaia

| Ligne | Contenu |
|---|---|
| 1 | Identifiant Equadis du champ |
| 2 | Libellé |
| 3 | Module |
| 4 | Section |
| 5 | Nom technique GDSN |
| 6 | Langue (`Français` / `Anglais` / vide) |
| 7+ | Données |

Un champ se repère par le triplet **(identifiant, langue, rang d'occurrence)**. Le rang
compte les répétitions d'un champ répétable : type de peau, contacts, GTIN cross-sell.
`pipeline.py` cherche d'abord la colonne `Français`, puis celle sans langue.

**Les identifiants peuvent changer entre le template d'import et la plateforme.** Cas
constaté : la liste des ingrédients est `255` dans le template, `3706` dans la plateforme.
Le dictionnaire `ALIAS` de `pipeline.py` gère ces équivalences.

## Décisions de mapping notables

**GTIN** — écrit en texte, chaîne exacte de l'export, zéros non significatifs conservés
(`03614275040950`). Deux raisons : la recherche Excel fonctionne sur les deux formes, et
la traçabilité avec le fichier d'origine reste directe. Concerne aussi les GTIN croisés,
les GLN et les EAN de niveau inférieur.

**Libellé court (97)** — dérivé du libellé commercial long tronqué à 35 caractères, et non
du libellé interne du distributeur, qui est cryptique (`CN26 ADG EDT100ML+GD75ML+DEO.75ML`).

**Poids et dimensions** — l'export sert la même mesure dans plusieurs colonnes selon
l'unité. On prend la première colonne servie et on renseigne le code unité correspondant.
Pas de conversion sur l'onglet Produit, qui porte un code unité. **Conversion obligatoire
sur l'onglet Logistique**, dont les blocs PK sont figés en cm et kg.

**Contenance** — ordre de priorité mL, L, g, kg, pièce. Certains produits servent deux
unités (un coffret vaut « 1 pièce » et « 200 mL ») : la première de la liste gagne.

**Prix** — l'extraction n'a qu'un champ prix (2261). Il reçoit le prix catalogue d'achat.
Le prix de vente conseillé n'a pas de cible et part en annexe.

**Propriétaire de la marque (172/174)** — on parcourt les blocs `partyInformationList` et
on retient celui dont le rôle est `BRAND_OWNER`. Souvent absent de la source : c'est un
défaut à remonter, pas à combler.

**Indicateurs** — tous les produits de l'onglet `Product` sont des UVC (`EACH`), donc :
unité de base Oui, unité consommateur Oui, unité logistique Non, service Non, présentoir
garni Non, mesure variable Non. Unité commandable = Oui si `lifeCycle = PURCHASABLE`.

**Rubrique ICPE (1454)** — limitée à 35 caractères alors que la source porte
`4331 - Liquides inflammables de catégorie 2 ou catégorie 3`. On ne garde que le numéro
de rubrique.

## Hiérarchie logistique

L'export liste les unités logistiques à plat, reliées par `children.gtin` et
`children.quantity`. `chaine()` remonte depuis le GTIN de l'UVC :

```
UVC → lot (PACK) → carton (CASE) → palette (PALLET)
```

Profondeur constatée : jusqu'à trois niveaux au-dessus de l'UVC. Le nombre d'UVC cumulé
(PK17) est calculé en multipliant les quantités le long de la chaîne — la source ne le
porte pas.

**Attention au nombre de blocs du gabarit.** Une extraction à un seul bloc PK ne reçoit
que le niveau immédiatement au-dessus de l'UVC ; cartons supérieurs et palettes sont
perdus. Le dire explicitement dans la restitution.

Un piège déjà tombé : ne jamais mapper les blocs par « rang de colonne servie ». Si des
colonnes vides ont été retirées en amont, le rang glisse et on écrit les données de la
palette dans le bloc du carton. Le mapping se fait par rang de **niveau de hiérarchie**.

## Champs propriétaires du distributeur

Un export fait depuis le compte d'un distributeur porte ses attributs privés : codes ligne
et marque, code fournisseur interne, axe, classification marketing, prix de vente par zone,
TVA d'achat. Ils n'ont **aucune cible** dans le template standard.

Ne pas les forcer dans des champs GDSN qui veulent dire autre chose. Les livrer dans un
fichier annexe indexé par GTIN, et ouvrir une demande d'extension côté plateforme.
