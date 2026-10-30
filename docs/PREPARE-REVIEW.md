# Capturer les sources d'une carte

Cette commande prépare un **brouillon local**. Elle ne transcrit pas l'effet,
ne le traduit pas et n'accepte aucune nouvelle source dans le verrou publié.
La commande Codex manuelle sera ajoutée dans l'itération suivante.

## Créer un dossier

Depuis le dépôt, avec les dépendances installées :

```bash
rtk proxy python -m coconut prepare-review coconut-030 --fetch
```

Le résultat se trouve dans `outputs/reviews/coconut-030/`. Le parent est
modifiable avec `--out`, mais doit rester sous `outputs/` dans le dépôt.
Tout `outputs/` est ignoré par Git : les captures ne sont pas ajoutées à une
PR par inadvertance. La sélection des fichiers de la PR viendra avec les
étapes suivantes de préparation.

Pour utiliser des catalogues déjà enregistrés :

```bash
rtk proxy python -m coconut prepare-review coconut-030 --en catalog-en.json --fr catalog-fr.json
```

Ces deux options remplacent seulement le téléchargement des catalogues : les
images sont toujours téléchargées. Les chemins relatifs des catalogues et de
`--out` sont résolus depuis `--root`, ou depuis la racine courante par défaut.
Les catalogues locaux ne sont pas présentés comme téléchargés par la commande.

## Contenu de la capture

| Fichier | Usage |
| --- | --- |
| `proposal.json` | Brouillon au contrat de revue : textes à compléter, références et questions non résolues |
| `capture.json` | Sources sélectionnées, base CSV, empreintes, différences avec la publication, date UTC et versions Python/Pillow |
| `catalog-en.json`, `catalog-fr.json` | Catalogues complets utilisés au premier passage, réencodés en JSON UTF-8 avec clés triées |
| `source-detail.jpg` | Image portant l'effet Coconut EN à transcrire |
| `source-settings.jpg` | Référence carrée de l'illustration couleur |
| `source-art_fr_hd.jpg` | Présent seulement lorsqu'une association officielle est déjà connue ou explicitement proposée |

Les empreintes des catalogues portent sur les fichiers JSON réencodés de la
capture, pas sur les octets bruts de la réponse HTTP. `origin` indique l'URL
officielle lors de `--fetch`, ou `provided-json` pour un fichier fourni.

Pour une nouvelle carte, les effets EN/FR et les noms FR restent vides.
L'option `--official-card-id` permet de proposer explicitement une association
par identifiant commun aux catalogues standard EN/FR. L'identifiant doit
exister sans ambiguïté dans les deux catalogues ; une image FR de variante
`Regular` doit être disponible. Les noms FR et l'image HD sont alors des
**candidats à relire**, sans preuve de correspondance automatique.

Pour une carte déjà publiée, la commande reprend sa base CSV, ses textes relus
et son association officielle existante. Elle actualise uniquement les deux
références de sources Coconut dans le brouillon, selon le catalogue capturé.
Les changements de libellés EN sont signalés dans `capture.json`, sans
remplacer les textes relus. Les données officielles observées restent visibles
dans `selection.official`, sans écraser les noms FR éditoriaux ni la référence
HD déjà enregistrée. Une autre association officielle se traite séparément.

## Relancer sans perdre les corrections

Relancer exactement la commande de création. Elle recharge les catalogues,
télécharge les images candidates et compare leur contenu à la capture.

Si les sources sélectionnées et la base CSV sont identiques, elle vérifie les
empreintes locales puis revient sans écrire : les effets corrigés, les
questions de revue et les aperçus éventuellement ajoutés restent intacts.
Les catalogues capturés au premier passage ne sont pas remplacés par une
nouvelle version lorsqu'une modification sans rapport apparaît ailleurs.

Une source sélectionnée, une image, une référence ou la base CSV différente
bloque la reprise. Un fichier local corrompu n'est pas réparé silencieusement.
Pour examiner une nouvelle révision, utiliser un autre parent, par exemple :

```bash
rtk proxy python -m coconut prepare-review coconut-030 --fetch --out outputs/reviews-revision-2
```

L'ancien dossier reste disponible pour comparaison et réconciliation manuelle
des corrections. Il n'existe pas d'option d'écrasement forcé. Proposer une
association officielle après une première capture sans association nécessite
aussi un nouveau parent de capture.

## Erreurs et limites

- Une carte inconnue, un doublon ou une paire EN/FR manquante bloque la capture.
- Les téléchargements utilisent uniquement l'hôte officiel de l'API en HTTPS,
  sans identifiants dans les URL. Une redirection vers un autre hôte est refusée
  avant de la suivre. Un changement officiel de CDN nécessitera une adaptation
  explicite de cette règle.
- Chaque lecture JSON est limitée à 32 Mio et chaque image à 16 Mio. Le délai
  de socket est de 30 secondes ; il ne constitue pas un délai total de l'opération.
- Les images doivent être des JPEG décodables. L'image détaillée et l'art HD
  doivent faire 1468 × 2048 px ; la référence couleur doit être carrée, avec
  un côté compris entre 1 et 2048 px. Elle n'est pas agrandie pour l'impression.
- Tous les téléchargements sont vérifiés avant la publication atomique du
  dossier local. Une panne ou un échec de validation ne laisse pas de dossier
  cible partiellement rempli et ne modifie pas les fichiers de production.

La commande retourne 0 pour une capture réussie ou une reprise inchangée,
et 2 pour une erreur de préparation. Les tests ordinaires utilisent des
catalogues et JPEG synthétiques sans appeler l'API.

`changes_against_published` signale les écarts des libellés/références Coconut
et les empreintes d'images différentes du verrou existant. Ce signalement
n'accepte pas les nouveaux octets et ne prouve aucune fidélité des textes.

Le brouillon reste refusé par `review-check` tant que le texte, la justification
officielle, les sources manquantes, les questions et les aperçus ne sont pas
complétés. Voir le [contrat de proposition](REVIEW-PROPOSAL.md). L'acceptation
humaine des sources et des traductions, la génération des aperçus et les
contrôles de PR restent nécessaires avant toute publication.
