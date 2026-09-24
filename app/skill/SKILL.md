---
name: "marionnaud-gaia-migration"
description: Migre un catalogue produit d'un export SupplierXM/Salsify vers le format d'une extraction Gaia (Equadis) - mapping des champs, conversion des valeurs, reconstruction de la hiérarchie logistique, génération du data.xml des visuels, et contrôle avant dépôt. À utiliser dès qu'il est question d'un export SupplierXM, Salsify, Equadis ou Gaia, d'un template ou d'une extraction Gaia, d'un rapport d'intégration Gaia, de Marionnaud, ou plus généralement de la reprise d'un catalogue produit d'un pool de données vers un autre - même si l'utilisateur dit seulement "mappe ce fichier", "remplis le template", "pourquoi ces erreurs à l'import" ou envoie deux Excel sans explication. Couvre aussi la migration des visuels et documents vers le format XML Equadis.
---

# Migration SupplierXM → Gaia

Chaîne complète de reprise d'un catalogue depuis un export SupplierXM (Salsify) vers le
format d'import Gaia (Equadis). Construite et éprouvée sur la migration Marionnaud :
8 exports, 1 833 produits, intégrés après correction des rejets réels de la plateforme.

## Ce que la chaîne fait

`export SupplierXM (.xlsx)` → `fichier au format extraction Gaia (.xlsx), prêt à déposer`

Elle mappe environ 100 champs produit et 40 champs logistiques, convertit toutes les
valeurs de liste, reconstruit la hiérarchie de palettisation, applique les corrections
imposées par la plateforme, puis contrôle le résultat sur trois niveaux avant livraison.

## Règle d'or

**Ne jamais enregistrer le classeur cible avec openpyxl.** L'extraction Gaia est produite
par Apache POI et contient un onglet `Validation Key`, des commentaires et des dessins.
Un `wb.save()` reconstruit tout le paquet, supprime `sharedStrings.xml`, renomme les
commentaires, et **Gaia refuse le fichier**. `scripts/pipeline.py` écrit directement dans
le XML du .xlsx : seuls `sheet1.xml`, `sheet2.xml` et `sharedStrings.xml` changent.
`scripts/validate.py` le vérifie. Si un autre fichier du paquet a bougé, c'est un bug.

## Déroulé

### 1. Reconnaissance — toujours en premier

```bash
python scripts/inspect_export.py --export nouvel_export.xlsx [--ref export_deja_traite.xlsx]
```

Sort quatre choses : la structure (les exports Salsify n'ont pas tous les mêmes colonnes),
**les catégories produit sans chemin de classification**, **les valeurs de liste inconnues**,
et les défauts de la donnée source (GLN invalides, propriétaire de marque manquant).

Les points 2 et 3 sont bloquants : une catégorie sans chemin laisse le champ 11 vide, une
valeur inconnue est écrite comme vide. Dans les deux cas la donnée disparaît sans erreur.
Compléter `CLASSIF`, `CLASSIF_KIND`, `GPC` ou les tables `V_*` de `scripts/pipeline.py`
avant de continuer — voir `references/classification.md` pour choisir un chemin.

### 2. Génération

```bash
python scripts/pipeline.py --export export.xlsx --template extraction_gaia.xlsx \
                           --out sortie.xlsx --report anomalies.json
```

Le `--template` est une extraction faite depuis Gaia pour le compte concerné. Elle sert de
gabarit : la chaîne n'y ajoute aucune colonne, elle remplit les lignes à partir de la
ligne 7 et duplique le squelette de la dernière ligne si l'export contient plus de produits
que le gabarit n'a de lignes.

### 3. Contrôle — avant de déposer, jamais après

```bash
python scripts/validate.py --file sortie.xlsx --template extraction_gaia.xlsx
```

Code retour 0 = déposable. Sinon la liste des violations, ligne par ligne.

### 4. Visuels et documents (si l'export en contient)

```bash
python scripts/build_media_xml.py --export export.xlsx --outdir dossier_sortie/
```

Produit `data_images.xml` et `data_documents.xml` au format Equadis, plus un manifeste CSV.
Lire `references/media.md` avant, notamment pour choisir entre hébergement dans Gaia
(archive + `fileName`) et hors Gaia (`externalUrl`).

### 5. Restitution

Livrer le fichier, le journal d'anomalies, et distinguer nettement :

- ce que la chaîne a corrigé (valeurs converties, textes tronqués, GLN écartés) ;
- ce qui relève d'un défaut de la donnée source, à remonter au client ;
- ce qui a été arbitré et demande validation (nouveaux chemins de classification).

## Après un rapport d'intégration Gaia

Un rapport en erreur est une information, pas un échec. Procéder ainsi :

1. Regrouper les messages par type — il y en a rarement plus de trois ou quatre distincts.
2. Pour chacun, trancher : défaut de la source, ou trou dans la chaîne ?
3. Si c'est un trou dans la chaîne, corriger **et** ajouter le contrôle correspondant à
   `validate.py`, pour que ce type d'erreur ne puisse plus repasser.
4. Appliquer la correction à **tous** les fichiers non encore déposés, pas seulement à celui
   qui a échoué.

`references/platform-quirks.md` liste les rejets déjà rencontrés et leur cause.

## Fichiers de référence

| Fichier | Quand le lire |
|---|---|
| `references/mapping.md` | Comprendre ou modifier une correspondance de champ |
| `references/classification.md` | Ajouter un chemin pour une nouvelle catégorie produit (le cas le plus fréquent) |
| `references/platform-quirks.md` | Un rejet Gaia, ou avant de toucher à l'écriture du fichier |
| `references/media.md` | Visuels et documents |
| `assets/field_limits.json` | Longueurs maximales du dictionnaire Gaia (80 champs) |

## Pièges à connaître

- **Les lettres de colonnes de l'export ne sont pas stables.** Salsify n'exporte que les
  colonnes servies : 150 à 290 colonnes selon l'export. Tout repérage se fait par le chemin
  technique en ligne 4. Ne jamais coder une lettre de colonne en dur.
- **Les longueurs déclarées dans le classeur ne suffisent pas.** Certains champs (98, 101)
  n'y ont aucune règle mais sont contrôlés par la plateforme. D'où `assets/field_limits.json`.
- **Les GLN de la source sont parfois des numéros complétés par des zéros.** Tester la clé
  de contrôle GS1 avant d'écrire, sinon la plateforme rejette le produit entier.
- **Les GTIN s'écrivent en texte**, chaîne exacte de l'export, zéros non significatifs
  conservés — sinon Excel les affiche en notation scientifique et la recherche ne trouve rien.
- **Les dates s'écrivent en jj/mm/aaaa**, pas en aaaa-mm-jj.
- **Un gabarit à un seul bloc de palettisation fait perdre les niveaux supérieurs.** Le
  signaler explicitement plutôt que de le laisser passer.
- **Une extraction est liée au compte dont elle provient.** Si elle n'a pas de colonne `gln`,
  les produits seront chargés sous ce compte. Le vérifier avant une mise en production.
