# Visuels et documents

Les images et les documents ne passent pas par le classeur : ils s'intègrent via un fichier
`data.xml` au format Equadis. `scripts/build_media_xml.py` le génère.

## Deux modes, à trancher avant de produire quoi que ce soit

**Hébergé dans Equadis** — on dépose `images.zip` + `data.xml`, chaque bloc portant un
`<fileName>` correspondant à un fichier de l'archive. Durable, mais il faut récupérer les
fichiers depuis l'ancien pool.

**Hébergé hors Equadis** — on ne dépose que `data.xml`, chaque bloc portant un
`<externalUrl>`. Beaucoup plus rapide.

Le script produit les deux : `data_images.xml` / `data_documents.xml` en mode URL, et
`repli_data_*_avec_zip.xml` en mode archive.

**La question à poser avant de choisir** : en mode URL, le moteur télécharge-t-il le fichier
et le stocke-t-il, ou conserve-t-il seulement le lien ? Si c'est la seconde réponse, les
visuels restent hébergés chez l'ancien pool et tombent le jour où l'accès est coupé — ce qui
vide la migration de son sens. Dans le doute, télécharger les fichiers en sauvegarde :
`Telechargement_visuels.csv` et le script de téléchargement existent pour ça.

## Structure d'un bloc

Racine `<images>`, un `<image>` par visuel ou document. Champs obligatoires : `gtin`,
`title`, `fileName` ou `externalUrl`, `referencedFileTypeCode`, `horizontalAngle`,
`fileEffectiveStartDateTime` (jj/mm/aaaa), `contentDescription`, `mainSideShown`,
`definition`, `targetMarket`, `isPrimaryFile`.

## Gestion libre et externalID

Utiliser la **gestion libre** avec un `<externalID>` unique par visuel, et
`<action>ADD_OR_UPDATE</action>`. Sans `externalID`, le moteur ajoute les visuels à chaque
dépôt : rejouer un import crée des doublons.

L'URL de l'ancien pool se termine par un UUID (`59b0ed3e-….jpg`) : c'est un `externalID`
tout trouvé, stable et unique.

## Correspondances

| Source | Cible |
|---|---|
| `isPackshot` | `isPrimaryFile` — un seul packshot par produit, à vérifier |
| `contentType` | `contentDescription` (`TYPE_CONTENU_*`) et `referencedFileTypeCode` |
| `angleHorizontal` / `angleVertical` | `horizontalAngle` / `verticalAngle` |
| `productFace` | `mainSideShown` |
| `fileType` (standard / haute) | `definition` |
| `webOptimizedType` = visuel épuré, ou PNG | `isFileBackgroundTransparent` |
| documents type FDS | `IMAGE_SAFETY_DATA_SHEET` |

Métadonnées manquantes : valeurs par défaut (`ANGLE_CENTRE`, `ANGLE_NON_APPLICABLE`,
`DEFINITION_STANDARD` déduite de la largeur en pixels), toutes tracées dans le journal.

## Points de friction

**Résolution.** Le guide annonce 900 à 2400 DPI. Les visuels d'un catalogue réel sont
typiquement en 2000 × 2000 px à 72, 96 ou 300 DPI, donc sous le plancher annoncé. Faire
confirmer que le contrôle porte sur les dimensions en pixels et non sur le DPI **avant** de
déposer un lot entier.

**Champs obligatoires sans objet pour un PDF.** `horizontalAngle`, `mainSideShown`,
`definition` et `contentDescription` n'ont aucun sens pour une fiche de sécurité. Valeurs
par défaut appliquées ; demander une dérogation.

**Deux fichiers plutôt qu'un.** Séparer visuels et documents garde les rapports
d'intégration lisibles.
