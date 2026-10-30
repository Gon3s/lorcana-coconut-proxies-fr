# Dossier de proposition d'une carte

Le dossier rassemble ce qu'une personne doit relire avant d'intégrer une
nouvelle carte ou une révision. Il reste séparé du CSV publié et du verrou
des sources de production. La [capture relançable des sources](PREPARE-REVIEW.md)
est disponible avec `prepare-review`. Le traitement des textes avec Codex et
l'intégration à la CI seront ajoutés dans les prochaines itérations du plan.

## États et commande

| État | Signification | Résultat de `review-check` |
| --- | --- | --- |
| Détection | Le manifeste `reviews/pending-coconuts.json` contient des références seulement | Refusé : ce n'est pas une proposition complète |
| `draft` | Une proposition est en cours de préparation | Refusé, même si tous les fichiers sont présents |
| `ready_for_review` | Le préparateur demande une revue des sources, des textes et des rendus | Réussi uniquement si les contrôles ci-dessous passent |
| Approbation humaine | Revue de PR et des fichiers par une personne | Aucun champ JSON ne confère cette approbation |

Le préparateur écrit un brouillon local sous
`outputs/reviews/coconut-030/proposal.json`. Il peut être incomplet, avec
seulement deux sources et aucun aperçu. Une fois complété, la commande de
contrôle de préparation est :

```bash
rtk proxy python -m coconut review-check outputs/reviews/coconut-030/proposal.json
```

Un chemin relatif est résolu depuis la racine du dépôt. Pour utiliser une
autre racine contenant `data/coconut-cards.csv`, placer `--root` avant le
sous-programme :

```bash
rtk proxy python -m coconut --root chemin-du-depot review-check chemin/vers/proposal.json
```

La commande ne contacte aucun service, ne lance pas Codex, n'écrit aucun
fichier et n'applique aucune traduction. Le code de sortie vaut 0 pour un
dossier prêt à relire, 2 pour un dossier refusé ou illisible. Une erreur
indique le champ, le fichier ou l'identifiant concerné. La réussite rappelle
explicitement qu'elle ne vaut pas approbation humaine.

## Contrat JSON, version 1

Les champs ci-dessous sont obligatoires ; les champs supplémentaires sont
refusés afin de rendre les erreurs de saisie visibles.

| Champ racine | Contenu |
| --- | --- |
| `schema` | Entier `1` |
| `status` | `draft` pendant la préparation, `ready_for_review` pour demander la revue |
| `card` | Objet contenant exactement les colonnes de `data/coconut-cards.csv`, toutes sous forme de chaînes |
| `base_card` | `null` pour une nouvelle carte ; copie exacte de sa ligne CSV actuelle pour une révision |
| `uncertainties` | Liste de questions de lecture, traduction ou association ; doit être vide pour passer |
| `match_evidence` | Justification non vide du choix de la carte officielle et de son illustration ; à relire humainement |
| `sources` | Trois fichiers candidats : `detail`, `settings`, `art_fr_hd` |
| `preview` | Empreinte des entrées et références des aperçus à relire |

`card` reprend les colonnes définies par `coconut.catalog.CSV_COLUMNS` :
`id`, `name_en`, `subtitle_en`, `name_fr`, `subtitle_fr`, `effet_en`,
`effet_fr`, `ref_image_detail`, `ref_image_settings`, `official_card_id`,
`ref_image_art_fr_hd`. Les sous-titres peuvent être vides. Les autres champs
requis par le build doivent être renseignés. Les identifiants des deux URL
Coconut doivent correspondre à `id`. Les trois références d'image doivent
être des URL HTTPS sans identifiants de connexion.

Chaque entrée de `sources` possède exactement `path`, `sha256` et `url`.
Les URL sont identiques aux champs correspondants de `card` :

| Rôle | Référence CSV |
| --- | --- |
| `detail` | `ref_image_detail` : image portant l'effet Coconut EN |
| `settings` | `ref_image_settings` : référence de cadrage couleur |
| `art_fr_hd` | `ref_image_art_fr_hd` : illustration officielle haute résolution proposée |

`preview` possède exactement `inputs_sha256` et `files`. `files` contient
les cinq rôles `card_fr`, `card_en`, `pdf_fr`, `pdf_en` et `page` ; chaque
entrée possède exactement `path` et `sha256`. Ces références doivent mener
aux JPEG des deux langues, aux PDF et à la page HTML de l'aperçu.

Tous les chemins de fichier sont relatifs au dossier contenant
`proposal.json`, avec des séparateurs `/`. Les chemins absolus, lecteurs
Windows, traversées `..` et liens résolus hors de ce dossier sont refusés.
Chaque fichier doit exister, être non vide et correspondre au SHA-256 déclaré, écrit avec
64 chiffres hexadécimaux minuscules.

## Conservation des corrections et péremption des aperçus

Pour une révision, `base_card` est la ligne **avant** modification et `card`
la proposition **après** modification. Une différence entre `base_card` et
la ligne actuellement dans le CSV bloque la revue : une correction a pu être
faite depuis la préparation et doit être réconciliée explicitement. Une
proposition avec `base_card: null` ne peut pas remplacer une ligne existante.
Le contrôle ne fusionne jamais les textes lui-même.

Le générateur de propositions utilisera
`coconut.review.review_input_digest(proposal)` pour remplir
`preview.inputs_sha256` après avoir produit l'aperçu. L'empreinte porte sur
`card`, `base_card`, `sources` et `match_evidence`, sérialisés en JSON UTF-8,
clés triées, sans espaces et sans échappement ASCII forcé.

Changer un texte, une source, une référence, la justification ou la base de
révision rend l'aperçu périmé. Le réordonnancement des clés JSON ne le fait
pas. Il faut reconstruire les sorties puis mettre à jour leurs empreintes et
celle des entrées ; ne pas recopier seulement une nouvelle empreinte pour
faire passer le contrôle.

## Limites de cette première itération

La commande contrôle la structure, les champs requis, le balisage des règles,
la base CSV, le confinement des chemins et les empreintes. Elle réutilise
les exigences du build et le parseur des six pictogrammes existants, sans
introduire une deuxième liste de symboles.

Elle ne décode pas les JPEG ou PDF et ne vérifie pas les liens internes de
l'aperçu. Les empreintes attestent la cohérence des octets déclarés, pas leur
format ni leur correspondance réelle avec les textes. Le futur préparateur
devra générer les aperçus depuis les mêmes entrées et vérifier leurs formats,
dimensions et débordements. La relecture humaine reste nécessaire pour la
fidélité de l'effet, la traduction, l'illustration et le rendu imprimé.

À ce stade, le workflow GitHub n'appelle pas encore `review-check` : cette
commande ne protège donc pas encore la fusion d'un manifeste incomplet.
La protection sera intégrée dans la PR dédiée aux workflows. Le préparateur
fournit un brouillon local ; la transcription, la traduction et les aperçus
restent à réaliser. Les tests ordinaires utilisent des données synthétiques.
