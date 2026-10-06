# Spécification — cartes Coconut en français

**Statut :** implémentation initiale sur la branche de travail ; revue du CSV et du rendu requise avant fusion.

**Périmètre :** importer les données Coconut, permettre la correction des traductions dans un CSV, générer les cartes imprimables et publier la page GitHub Pages.

## 1. Résultat attendu

- Une carte par entrée Coconut, avec l'illustration française en couleur, le titre et le sous-titre français, et **l'effet Coconut** traduit en français. Les effets d'une carte Lorcana standard ne remplacent jamais l'effet Coconut.
- Des JPEG de 1468 × 2048 px, une page HTML avec zoom, et des planches A4 de neuf cartes au format 63 × 88 mm. L'espace visible entre cartes reste de 1 px, y compris à l'impression.
- La ligne autorisant jusqu'à quatre exemplaires est produite automatiquement à partir du titre et du sous-titre français.
- La mention « PROXY FR » n'apparaît pas sur les cartes. Le cartouche `[FORMAT COCONUT]`, les icônes d'encre et les crédits de l'image source sont conservés. Le filigrane « FOR BETA TEST ONLY » situé sur l'illustration grise est remplacé avec celle-ci ; la révision bêta inscrite dans les crédits reste visible.
- Un changement validé du CSV reconstruit les JPEG et la page, puis publie le site après fusion sur `main`. Une exécution manuelle est également possible.

## 2. Sources et autorité

| Source | Usage | Limite constatée |
| --- | --- | --- |
| `catalog/en` → `coconut_cards` | Identifiant, titre et sous-titre EN, URL de l'image Coconut détaillée | Aucun effet sous forme de texte |
| `card_detail_url` de la carte Coconut EN | Source faisant foi pour `effet_en`, la présentation et la révision Coconut | Texte peint dans le JPEG : transcription et relecture initiales nécessaires |
| `catalog/fr` → `coconut_cards` → `settings_thumbnail_url` | Référence de cadrage et contrôle de correspondance de l'illustration en couleur | L'échantillon Ariel fait 256 × 256 px ; résolution insuffisante pour l'image imprimée |
| `catalog/fr` → cartes standard associées | Titre et sous-titre officiels FR, illustration correspondante en haute résolution | Association à vérifier par identifiant de carte et contrôle visuel |
| PDF bêta des cartes et règles | Contexte et aide à la relecture | Le PDF des cartes couvre 18 cartes, alors que le catalogue examiné en contient 27 ; il peut décrire une révision antérieure |

Le bloc `coconut_cards` du catalogue `/fr` contient actuellement les mêmes `name` et `subtitle` anglais que le catalogue `/en` pour les 27 cartes examinées. Il ne doit donc pas préremplir les champs FR. Par exemple, il indique `Moana / Curious Explorer`, et non `Vaiana / Exploratrice curieuse`.

**Règle en cas de divergence :** l'image Coconut détaillée correspondant à la révision enregistrée fait foi pour l'effet EN. Exemple vérifié : le PDF bêta dit que Mufasa place trois cartes dans la réserve d'encre, tandis que l'image Coconut actuelle en indique deux. Une modification de la source doit être signalée avant toute mise à jour du CSV.

Les URL restent dans le CSV pour la traçabilité. Les fichiers sources effectivement utilisés pour construire le site sont conservés localement avec leurs empreintes SHA-256 : une reconstruction ordinaire ne doit pas changer si l'API distante change ou devient indisponible.

## 3. CSV éditable

Fichier proposé : `data/coconut-cards.csv`, encodé en UTF-8. Une ligne logique représente une carte. Les virgules et guillemets dans les textes respectent les règles CSV usuelles ; les champs d'effet ne contiennent pas la ligne commune « jusqu'à quatre exemplaires ».

| Colonne | Rôle |
| --- | --- |
| `id` | Identifiant Coconut stable, par exemple `coconut-002`, tiré du préfixe numérique de l'URL de l'image détaillée ; jamais la position dans la liste |
| `name_en`, `subtitle_en` | Titre et sous-titre de `coconut_cards` EN, normalisés sans césure invisible ni guillemets décoratifs |
| `name_fr`, `subtitle_fr` | Noms officiels du catalogue français associé, préremplis puis relus ; modifiables dans le CSV |
| `effet_en` | Transcription relue de l'image Coconut détaillée EN |
| `effet_fr` | Traduction française éditable de cet effet |
| `ref_image_detail` | URL de l'image Coconut détaillée qui justifie le texte EN et fournit le gabarit |
| `ref_image_settings` | URL du carré couleur `settings_thumbnail_url`, utilisé pour contrôler le cadrage |
| `official_card_id` | Identifiant commun de la carte standard associée dans les catalogues EN/FR |
| `ref_image_art_fr_hd` | URL de la carte standard française en haute résolution dont seule l'illustration est extraite |

Un fichier technique `data/sources.lock.json` enregistre les empreintes des images sources, la version du catalogue importé et la date de vérification. Il n'est pas destiné à la traduction. Les symboles non textuels d'un effet EN sont transcrits avec des marqueurs documentés, par exemple `{ink}` ou `{lore}`, puis relus sur l'image source.

## 4. Import initial et mises à jour futures

1. Lire les catalogues EN et FR et apparier chaque carte Coconut à la carte standard correspondante. L'identifiant Coconut doit être unique ; l'identifiant de la carte standard sert à retrouver le nom et l'illustration français.
2. Créer le CSV une fois. Transcrire `effet_en` depuis les 27 images détaillées, avec une vérification humaine. Remplir et relire `name_fr`, `subtitle_fr` et `effet_fr` avant publication. Un OCR peut aider la saisie, mais son résultat brut n'est pas une source validée.
3. Lors d'un nouvel import, **conserver tous les champs FR existants**. Ajouter les nouveaux identifiants avec traduction FR à compléter. Comparer les sources EN et leurs empreintes ; produire un rapport des changements plutôt que remplacer silencieusement `name_en`, `subtitle_en` ou `effet_en`.
4. Si une source EN change, une personne confirme la nouvelle transcription et décide si la traduction FR doit être revue. Une carte disparue de l'API est signalée, pas supprimée automatiquement du CSV.

L'import et la reconstruction sont deux opérations distinctes. Modifier le CSV ne relance pas un import distant ; construire le site n'écrase jamais le CSV.

## 5. Génération

- Un générateur versionné dans le dépôt lit le CSV et les images sources verrouillées. Il compose l'illustration haute résolution dans le gabarit Coconut, puis dessine les textes FR avec la police Barlow Condensed fournie avec sa licence.
- `settings_thumbnail_url` sert à vérifier que la bonne scène et le bon cadrage ont été choisis. Ses 256 px ne sont pas agrandis silencieusement pour l'impression. Si aucune illustration haute résolution correcte n'est trouvée, la génération échoue avec une erreur expliquant la carte concernée.
- Le générateur recrée entièrement les zones de titre et de règles à partir du CSV : aucune ancienne traduction ne doit rester peinte sous la nouvelle. Les textes trop longs déclenchent une erreur de débordement ou une revue explicite, plutôt qu'une réduction illisible.
- La sortie de construction est un dossier `dist/` contenant `index.html`, `images/` et les autres ressources nécessaires. Les images finales générées ne sont pas modifiées à la main et n'ont pas besoin d'être commitées ; leurs sources, le CSV, le générateur et ses dépendances épinglées le sont.
- Le nombre de planches est calculé selon le nombre de cartes. Pour l'état actuel : 27 cartes, trois planches A4. Une dernière planche partielle reste possible si de nouvelles cartes sont ajoutées.

## 6. GitHub Actions et runner

| Événement | Action attendue |
| --- | --- |
| Pull request | Valider le CSV et les sources, construire le site, vérifier les dimensions et les débordements, fournir un aperçu téléchargeable des cartes et des trois planches A4. Ne pas publier GitHub Pages. |
| Push sur `main` | Refaire la même construction depuis les sources versionnées, publier **tout** `dist/` sur GitHub Pages. Toute correction validée du CSV apparaît ainsi sur le site. |
| `workflow_dispatch` | Permettre une reconstruction ou un déploiement manuel d'une révision de confiance, sans réimport automatique de l'API. |

La validation des PR utilise un runner GitHub hébergé. Le runner local Linux x64 de `192.168.1.23` peut être proposé pour les constructions ou déploiements manuels et les changements de confiance sur `main`, avec les labels `self-hosted`, `Linux`, `X64`, `coconut-pages`. Il ne reçoit pas les PR publiques non approuvées. Le fonctionnement du générateur et ses dépendances doivent être identiques sur les deux runners.

L'action Pages actuelle ne copie que `index.html`. Elle devra être remplacée ou adaptée pour publier `dist/` en entier, notamment les JPEG dans `images/`.

## 7. Critères d'acceptation

- Chaque identifiant est unique ; tous les champs et fichiers requis sont présents. Une source modifiée ou une traduction FR manquante bloque la publication et nomme la carte concernée.
- `name_fr` et `subtitle_fr` correspondent à la carte standard française choisie, sauf correction explicitement documentée. Chaque `effet_fr` correspond à l'`effet_en` de la révision verrouillée, sans emprunter les règles de la carte standard.
- Les 27 JPEG actuels montrent une illustration en couleur nette, aucun texte EN résiduel, aucune mention « PROXY FR » et aucun texte coupé. Le zoom affiche exactement la carte imprimée.
- Les planches imprimées ont trois colonnes de cartes de 63 × 88 mm, neuf cartes par A4 pour l'état actuel, et la séparation de 1 px prévue. Un aperçu PDF est relu avant fusion.
- Deux constructions avec les mêmes entrées produisent le même contenu. Tous les liens d'image de la page publiée fonctionnent ; une modification de `effet_fr` dans le CSV change la carte concernée après fusion sur `main`.

## 8. Documentation à livrer avec l'implémentation

Le README expliquera comment corriger une ligne du CSV, lancer l'import de vérification, construire et prévisualiser localement, demander une revue, puis retrouver le déploiement GitHub Pages. Un guide séparé décrira l'installation et les labels du runner local ainsi que la marche à suivre pour une nouvelle carte Coconut ou une révision de source EN.
