# Maintenance du pipeline Coconut

## Architecture

- `coconut/catalog.py` : lecture du catalogue, identifiants et fusion non destructive du CSV.
- `coconut/sources.py` : téléchargement contrôlé et vérification des SHA-256 des images locales.
- `coconut/build.py` : composition des JPEG, page HTML et PDF A4.
- `data/coconut-cards.csv` : textes et références éditables ; `data/sources.lock.json` : version vérifiée des références et des fichiers.
- `assets/source/` : 27 images Coconut détaillées et 27 cartes françaises haute résolution ; `assets/fonts/` : Barlow Condensed avec sa licence OFL.

Le build ne contacte pas l'API. Une modification de `effet_fr` affecte seulement le rendu produit par la prochaine construction. Deux builds avec les mêmes fichiers donnent les mêmes sorties.

## Nouvelle carte ou révision de source

1. Lancer `python -m coconut import --fetch --report import-report.json`. Examiner `added`, `changed`, `detail_image_changed`, `official_changes` et `missing`.
2. Pour une nouvelle carte, identifier la carte standard correspondante dans le catalogue FR en comparant nom, sous-titre, identifiant et illustration. Compléter `official_card_id`, `ref_image_art_fr_hd`, `name_fr`, `subtitle_fr`, `effet_en` et `effet_fr` dans le CSV. Relire `effet_en` directement sur l'image Coconut détaillée. Les symboles s'écrivent `{ink}`, `{lore}`, `{strength}` et `{exert}` dans les deux langues. Dans `effet_fr`, `**Boost**` met le mot clé en gras ; le générateur dessine les quatre symboles, même si la police ne les contient pas. Ne pas utiliser le texte des règles de la carte standard comme effet Coconut.
3. Pour une révision, comparer l'ancien JPEG verrouillé au nouveau et noter la nouvelle transcription EN et la traduction FR approuvées. Modifier manuellement les colonnes EN et les URL concernées dans le CSV. Les lignes disparues ne sont pas supprimées automatiquement.
4. Après cette revue, lancer `python -m coconut sync-sources`. La commande vérifie les dimensions, télécharge toutes les références du CSV et refuse de remplacer un fichier dont les octets ont changé. Si le changement a été approuvé, relancer avec `--accept-changes`. Le verrou des SHA-256 et des URL est alors mis à jour.
5. Lancer les tests et `python -m coconut build --out dist`. Inspecter le JPEG de chaque carte modifiée, les planches PDF et la page. Demander la revue de la pull request avant fusion.

Un changement de `name_fr` ou `subtitle_fr` éditorial ne nécessite pas `sync-sources` tant que les URL et l'identifiant officiel restent les mêmes. Si l'association à une carte standard change, mettre à jour les références puis synchroniser les sources.

## GitHub Actions et runner local

Chaque pull request utilise `ubuntu-latest`, lance les tests et le build, puis fournit l'artefact `coconut-preview`. Elle ne publie pas le site. Un push sur `main` reconstruit le site puis déploie l'intégralité de `dist/` sur GitHub Pages. `workflow_dispatch` lance aussi un build manuel ; sur `main`, il déclenche également le déploiement.

Pour utiliser la machine `192.168.1.23` lors d'un déclenchement manuel :

1. Dans **Settings → Actions → Runners** du dépôt GitHub, créer un runner **Linux x64** pour ce dépôt. Suivre les commandes affichées par GitHub sur `192.168.1.23` avec un compte non privilégié. Le jeton d'enregistrement est temporaire et ne doit pas être enregistré dans ce dépôt.
2. Ajouter le label personnalisé `coconut-pages` ; les labels automatiques `self-hosted`, `Linux` et `X64` doivent être présents. Installer Python 3.12 et laisser `actions/setup-python` gérer l'interpréteur du job.
3. Démarrer le runner comme service et vérifier qu'il apparaît **Idle** sur GitHub. Dans **Actions → Build Coconut cards and deploy Pages → Run workflow**, choisir `runner: local`. Cette option n'est pas utilisée par les pull requests.

Le job de déploiement GitHub Pages reste sur un runner GitHub hébergé ; le runner local ne construit que l'artefact. Prévoir assez de disque pour les 54 JPEG sources, les 27 JPEG générés et le PDF.
