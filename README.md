# Cartes Coconut en français et en anglais

Ce dépôt génère les 27 cartes Coconut actuellement publiées par Disney Lorcana avec leurs illustrations en couleur et les **règles Coconut** en français ou en anglais. Les cartes finales font 1468 × 2048 px. Chaque langue dispose de trois planches A4 de neuf cartes (63 × 88 mm, écart visible de 1 px), d'un zoom et d'un PDF.

La page française est l'URL par défaut, ou `?lang=fr`. Ajouter `?lang=en` à l'URL pour afficher les titres, effets, images et planches anglaises. Les boutons **FR** et **EN** font le même changement. Le bouton d'impression et le lien PDF utilisent la langue affichée.

Les traductions sont non officielles. Les images et marques appartiennent à leurs ayants droit ; ce projet n'est affilié ni à Disney ni à Ravensburger.

## Corriger une traduction

1. Ouvrir [`data/coconut-cards.csv`](data/coconut-cards.csv) en UTF-8. Modifier `name_fr`, `subtitle_fr` ou `effet_fr` sur la ligne identifiée par `id`. Pour corriger la transcription anglaise après revue de la source, modifier `effet_en`. Ne pas modifier les images générées.
2. Relire `effet_en` sur le JPEG source (`assets/source/<id>-detail.jpg`) ; l'effet d'une carte standard peut être différent.
3. Construire et vérifier visuellement la carte et la planche concernées :

   ```bash
   python -m pip install -r requirements.txt
   python -m unittest discover -s tests -v
   node --test tests/site.test.js
   python -m coconut build --out dist
   python -m http.server 8000 -d dist
   ```

4. Ouvrir `http://localhost:8000/?lang=fr` puis `http://localhost:8000/?lang=en`, agrandir une carte dans chaque langue et contrôler `dist/planches-a4.pdf` et `dist/planches-a4-en.pdf`. À l'impression depuis le navigateur, choisir A4, 100 %, marges nulles et arrière-plans imprimés.
5. Ouvrir une pull request. L'Action construit et fournit l'artefact **coconut-preview** contenant la page, les 54 JPEG et les deux PDF. Une personne relit le CSV et le rendu avant fusion. Après fusion sur `main`, l'Action publie tout `dist/` sur GitHub Pages.

Le site publié est [lorcana-coconut-proxies-fr](https://gon3s.github.io/lorcana-coconut-proxies-fr/).

## Données et sources

Le CSV est la seule source éditable des textes FR et EN. Les colonnes `ref_image_detail`, `ref_image_settings` et `ref_image_art_fr_hd` gardent les URL de provenance ; les fichiers utilisés par la construction sont les JPEG locaux sous `assets/source/`, avec leurs SHA-256 dans `data/sources.lock.json`. Ainsi, un changement du serveur distant ne modifie pas une reconstruction ordinaire.

`settings_thumbnail_url` sert de référence de cadrage : son image carrée de 256 px ne sert pas à l'impression. La composition extrait l'illustration du JPEG français haute résolution, conserve le cadre et les crédits Coconut, puis repeint entièrement le titre et les règles dans chaque langue. Le texte trop long ou une référence manquante arrête la construction.

Dans `effet_en`, `{cost}`, `{lore}`, `{strength}` et `{exert}` transcrivent les symboles imprimés. `{cost}` désigne l'hexagone creux des coûts ; la spirale `{ink}` est un autre symbole et n'apparaît pas dans ces effets. Les mêmes marqueurs dans `effet_fr` dessinent des pictogrammes lors du build ; ils ne dépendent pas de la présence de glyphes dans la police. Les six symboles de la planche (`cost`, `lore`, `strength`, `exert`, `ink`, `willpower`) sont redessinés en vecteurs dans `coconut/icons.py` ; aucun pixel de la planche filigranée n'est utilisé. Entourer un mot clé de `**` pour le mettre en gras, par exemple `**Boost**`. Garder la ponctuation hors des astérisques. Un marqueur inconnu fait échouer le build. La ligne « Jusqu'à 4 exemplaires » est produite automatiquement avec le titre et le sous-titre FR ; elle ne figure donc pas dans les champs `effet_*`.

## Vérifier une mise à jour du catalogue

```bash
python -m coconut import --fetch --report import-report.json
```

L'import compare les catalogues EN/FR et les images détaillées à leurs empreintes verrouillées. Il ajoute de nouvelles cartes avec les champs FR vides, conserve toutes les lignes et traductions existantes, et écrit un rapport des changements EN, des illustrations, des noms officiels FR et des cartes disparues. Il ne remplace pas automatiquement un texte déjà relu. Pour travailler avec des fichiers JSON déjà téléchargés : `python -m coconut import --en catalog-en.json --fr catalog-fr.json --report import-report.json`. Ajouter `--check-images` pour comparer aussi les JPEG distants.

Le processus complet pour une nouvelle carte ou une révision de source figure dans [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md). La [spécification](docs/SPEC.md) explique les choix et critères d'acceptation. Le [suivi de relecture](docs/REVIEW.md) indique les corrections reçues et les points restants avant fusion.
