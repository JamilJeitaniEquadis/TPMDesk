# Comportements de la plateforme et rejets déjà rencontrés

Tout ce qui suit vient de rejets réels, pas de la documentation.

## Écriture du fichier

### Ne jamais enregistrer avec openpyxl

L'extraction Gaia est produite par **Apache POI**. Elle contient un onglet `Validation Key`,
deux fichiers de commentaires, quatre fichiers de dessins et un `sharedStrings.xml`.

Un `wb.save()` d'openpyxl reconstruit le paquet : `sharedStrings.xml` disparaît (les chaînes
passent en inline), `xl/comments1.xml` devient `xl/comments/comment1.xml`, les VML sont
remplacés, un `theme1.xml` apparaît. **Gaia renvoie « fichier invalide ».**

Méthode correcte, implémentée dans `pipeline.py` :

1. Dézipper le gabarit.
2. Modifier `sheet1.xml`, `sheet2.xml` et compléter `sharedStrings.xml` (en mettant à jour
   `count` et `uniqueCount`).
3. Rezipper **dans l'ordre d'origine** des entrées.

Résultat attendu : exactement trois fichiers modifiés sur 21. `validate.py` le vérifie et
alerte si un autre a bougé.

### Ajouter des lignes

Le gabarit ne contient que les lignes de l'extraction d'origine (souvent 10). Pour en écrire
plus : dupliquer le squelette XML de la dernière ligne en changeant les références (`A16` →
`A17`…), vider les valeurs en conservant les styles, puis étendre `<dimension>` et les
plages `sqref` des validations.

### Format des cellules

- **Identifiants en texte** (`t="s"` + `number_format = '@'`) : GTIN, GLN, EAN. Sinon Excel
  affiche `1.23142E+12` et la recherche échoue.
- **Dates en `jj/mm/aaaa`**. Message de rejet : « doit contenir une date valide au format
  (jj/mm/aaaa) ». Concerne 46, 2230, 2231, 2234, 2264, PK71, PK72.

## Rejets rencontrés et leur cause

| Message | Cause | Correction |
|---|---|---|
| « fichier invalide » | Enregistrement openpyxl | Écriture XML directe |
| « doit contenir une date valide (jj/mm/aaaa) » | Dates en aaaa-mm-jj | Conversion à l'écriture |
| « n'est pas une valeur autorisée » sur unités | `Gramme` au lieu de `Gramme (g)` | Libellés de la liste de la plateforme |
| idem sur devise | `EUR` au lieu de `Euro` | idem |
| idem sur nomenclature | `Intrastat nomenclature combinée` inexistant | `Intrastat` |
| idem sur support palette | `Non réutilisable/perdu` | `Non réutilisable (perdu)` |
| idem sur unité de facture | `Pièce` absent de la liste PK47 | `UVC` |
| « ne peut pas dépasser (35) caractères » (champ 98) | Longueur non déclarée dans le classeur | `assets/field_limits.json` |
| « GLN transmis n'est pas valide » | Numéro complété par des zéros | Test de clé GS1 avant écriture |

## Les trois sources de contrôle

Aucune ne suffit seule — c'est la leçon principale.

1. **Les règles du classeur** (236 validations). Ne couvrent pas tous les champs : rien
   pour 98 ni 185_4.
2. **Le dictionnaire de champs** (`assets/field_limits.json`, 80 longueurs). Comble le trou
   précédent.
3. **La clé de contrôle GS1** sur les champs GLN. Formule pour 13 chiffres : somme des
   12 premiers pondérés 1, 3, 1, 3… ; le 13e doit valoir `(10 - somme % 10) % 10`.

Après chaque rejet d'un type nouveau, ajouter le contrôle correspondant à `validate.py`.

## Import en force

La plateforme peut importer sans bloquer sur les erreurs. Cela supprime le risque de blocage
mais crée un risque plus sournois : **aucun rapport d'erreur, donc aucune alerte.** Le
contrôle avant dépôt remplace le rapport de rejet. Trier les champs par coût de correction :
identifiants, hiérarchie et classification d'abord (une erreur impose un rechargement), textes
marketing et facettes ensuite (corrigeables dans l'interface).

## Extraction liée à un compte

Une extraction faite depuis le compte d'un fournisseur ne porte pas de colonne `gln` : elle
est implicitement rattachée à ce compte. Charger des produits d'un autre acteur à travers ce
gabarit les range sous le mauvais compte. Symptôme visible dans le rapport d'intégration :
les produits étrangers au compte reviennent sans nom ni marque.

Pour une mise en production, exiger une extraction du bon compte. Rejouer la chaîne dessus
est une simple réexécution.

## Défauts récurrents de la donnée source

À remonter au client plutôt qu'à corriger :

- **Propriétaire de la marque absent** : de 12 % à 82 % des produits selon l'export.
- **GLN complétés par des zéros** : `0000000347331`, `0034733110100`.
- **Libellés réduits au nom de la marque** : libellé long, dénomination de vente et libellé
  court valant tous « Clinique ». Visible par le consommateur.
- **Cartons déclarés deux fois** avec des GTIN différents et une quantité identique.
- **Catégories source erronées** : une huile de soin classée en accessoire.
