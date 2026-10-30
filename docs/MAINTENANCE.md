# Maintenance du pipeline Coconut

## Architecture

- `coconut/catalog.py` : lecture du catalogue, identifiants et fusion non destructive du CSV.
- `coconut/sources.py` : téléchargement contrôlé et vérification des SHA-256 des images locales.
- `coconut/build.py` : composition des JPEG FR et EN, page HTML et deux PDF A4.
- `data/coconut-cards.csv` : textes et références éditables ; `data/sources.lock.json` : version vérifiée des références et des fichiers.
- `assets/source/` : 30 images Coconut détaillées et 30 cartes françaises haute résolution ; `assets/fonts/` : Barlow Condensed avec sa licence OFL.

Le build ne contacte pas l'API. Une modification de `effet_fr` ou `effet_en` affecte seulement le rendu de sa langue lors de la prochaine construction. Deux builds avec les mêmes fichiers donnent les mêmes sorties. `?lang=fr` (ou aucune option) affiche le français ; `?lang=en` affiche l'anglais. Le lien PDF et l'impression suivent cette sélection.

## Vérification automatique du catalogue

Le workflow **Build Coconut cards and deploy Pages** interroge les catalogues EN/FR chaque samedi à partir de 08:17 UTC (09:17 en hiver, 10:17 en été à Paris ; GitHub peut retarder le démarrage). Le job `check-catalog` écrit un résumé et dépose le rapport JSON ainsi que `pending-coconuts.json` dans l'artefact `coconut-catalog-check`. Le contrôle reste en lecture seule. Une erreur de l'API arrête le build planifié et le déploiement.

Si une nouvelle carte apparaît, `review-new-cards` ouvre ou actualise une PR brouillon sur la branche `automation/review-new-coconuts`. Le fichier `reviews/pending-coconuts.json` ne contient que l'identifiant, le titre et le sous-titre EN, et les URL source. Il ne préremplit aucune transcription, traduction ou association à une carte officielle. Une personne complète la PR en suivant la procédure ci-dessous et relit les deux langues et les PDF avant fusion. Le push résultant sur `main` publie alors la nouvelle carte. Le build planifié publie seulement les cartes déjà validées et verrouillées dans `main`.

Le manifeste temporaire `/pending-coconuts.json` est ignoré par Git à la racine. Sa copie `reviews/pending-coconuts.json` doit rester suivable pour que l'action puisse ouvrir la PR de revue.

**Prérequis GitHub :** dans **Settings → Actions → General → Workflow permissions**, activer **Allow GitHub Actions to create and approve pull requests**. Sans cette option, le job de création de la PR échoue lorsque de nouvelles cartes sont détectées. Le jeton de `review-new-cards` est limité à `contents: write` et `pull-requests: write` ; les autres jobs gardent leurs permissions propres.

En local, lancer `python -m coconut check --fetch --report check-report.json`. Cette commande compare les noms et références de la source, mais ne télécharge pas les JPEG détaillés. Pour vérifier aussi les octets des images, utiliser la procédure d'import ci-dessous. Une nouvelle carte doit toujours suivre la relecture et la synchronisation décrites dans la section suivante avant publication.

## Nouvelle carte ou révision de source

Le [contrat des dossiers de proposition](REVIEW-PROPOSAL.md) et la commande
en lecture seule `python -m coconut review-check chemin/vers/proposal.json`
permettent de vérifier un dossier complet avant sa revue humaine. La
capture initiale des dossiers est décrite dans le [guide de préparation](PREPARE-REVIEW.md).
Le [traitement manuel avec Codex](MANUAL-CODEX.md) produit des suggestions
séparées ; le branchement du contrôle dans GitHub Actions reste à venir.
La procédure actuelle ci-dessous reste applicable.

1. Lancer `python -m coconut import --fetch --report import-report.json`. Examiner `added`, `changed`, `detail_image_changed`, `official_changes` et `missing`.
2. Pour une nouvelle carte, identifier la carte standard correspondante dans le catalogue FR en comparant nom, sous-titre, identifiant et illustration. Compléter `official_card_id`, `ref_image_art_fr_hd`, `name_fr`, `subtitle_fr`, `effet_en` et `effet_fr` dans le CSV. Relire `effet_en` directement sur l'image Coconut détaillée. Les symboles s'écrivent `{cost}`, `{lore}`, `{strength}` et `{exert}` dans les deux langues. `{cost}` est l'hexagone creux, distinct de la spirale d'encre. Dans `effet_fr`, `**Boost**` met le mot clé en gras ; le générateur dessine les quatre symboles, même si la police ne les contient pas. Ne pas utiliser le texte des règles de la carte standard comme effet Coconut.
3. Pour une révision, comparer l'ancien JPEG verrouillé au nouveau et noter la nouvelle transcription EN et la traduction FR approuvées. Modifier manuellement les colonnes EN et les URL concernées dans le CSV. Les lignes disparues ne sont pas supprimées automatiquement.
4. Après cette revue, lancer `python -m coconut sync-sources`. La commande vérifie les dimensions, télécharge toutes les références du CSV et refuse de remplacer un fichier dont les octets ont changé. Si le changement a été approuvé, relancer avec `--accept-changes`. Le verrou des SHA-256 et des URL est alors mis à jour.
5. Lancer les tests et `python -m coconut build --out dist`. Inspecter le JPEG de chaque carte modifiée, les deux PDF et la page avec `?lang=fr` puis `?lang=en`. Demander la revue de la pull request avant fusion.

Un changement de `name_fr` ou `subtitle_fr` éditorial ne nécessite pas `sync-sources` tant que les URL et l'identifiant officiel restent les mêmes. Si l'association à une carte standard change, mettre à jour les références puis synchroniser les sources.

## GitHub Actions et runner local

Le job `deploy` doit vérifier explicitement `!cancelled()` et la réussite de
`build`. Lors d'une fusion, `check-catalog` est normalement ignoré ; sans
fonction de statut explicite dans la condition de déploiement, GitHub peut
ignorer ce dernier malgré un build réussi. Un workflow vert ne prouve donc
pas une publication : vérifier le job `deploy`, le déploiement enregistré et
le contenu réellement servi. Les cas fusion, build manuel, contrôle seul,
PR, échec et annulation sont couverts par `tests/test_pages_workflow.py`.

Chaque pull request utilise `ubuntu-latest`, lance les tests et le build, puis fournit l'artefact `coconut-preview`. Elle ne publie pas le site. Un push sur `main` reconstruit le site puis déploie l'intégralité de `dist/` sur GitHub Pages. Le samedi, un contrôle réussi précède le build et le déploiement des cartes validées. `workflow_dispatch` avec `operation: build` lance un build manuel ; `operation: check` lance le contrôle et peut ouvrir une PR brouillon sur `main` ; `operation: weekly` lance le contrôle suivi du build et du déploiement sur `main`.

Pour utiliser le mini serveur personnel lors d'un déclenchement manuel :

1. Dans **Settings → Actions → Runners** du dépôt GitHub, créer un runner **Linux x64** pour ce dépôt. Suivre les commandes affichées par GitHub sur le serveur personnel avec un compte non privilégié. Le jeton d'enregistrement est temporaire et ne doit pas être enregistré dans ce dépôt.
2. Ajouter le label personnalisé `coconut-pages` ; les labels automatiques `self-hosted`, `Linux` et `X64` doivent être présents. Laisser `actions/setup-python` et `actions/setup-node` installer Python 3.12 et Node 20 pour les tests et le build.
3. Démarrer le runner comme service et vérifier qu'il apparaît **Idle** sur GitHub. Dans **Actions → Build Coconut cards and deploy Pages → Run workflow**, choisir `runner: local`. Cette option n'est pas utilisée par les pull requests.

Le job de déploiement GitHub Pages reste sur un runner GitHub hébergé ; le runner local ne construit que l'artefact. Prévoir assez de disque pour les 60 JPEG sources, les 60 JPEG générés et les deux PDF.
