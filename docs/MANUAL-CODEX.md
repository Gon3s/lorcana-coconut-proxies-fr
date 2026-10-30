# Proposition de textes avec Codex, lancement manuel

Cette étape lit l'image Coconut capturée et produit une suggestion EN/FR
séparée. Elle ne modifie ni `proposal.json`, ni le CSV, ni le verrou de sources.
Une suggestion correcte sur le plan technique reste à relire humainement.

## Préparer la session personnelle sur le serveur

Utiliser un compte personnel non privilégié, distinct d'un éventuel compte
de runner. Installer Codex CLI en suivant la [documentation officielle](https://learn.chatgpt.com/docs/codex/cli),
puis contrôler sa version et les options disponibles :

```bash
rtk proxy codex --version
rtk proxy codex exec --help
rtk proxy codex login status
```

Les options nécessaires ont été vérifiées avec Codex CLI 0.153.2 : `exec`,
`--sandbox read-only`, `--image`, `--output-schema`, `--output-last-message`,
`--ignore-user-config` et `--ephemeral`. Le chemin du binaire peut être donné
avec `--codex` s'il n'est pas dans le `PATH`, par exemple
`--codex ~/.local/bin/codex`. L'adaptateur développe également `~`.

Si la session ChatGPT n'est pas encore ouverte, utiliser la connexion par code
sur appareil, lorsqu'elle est activée pour le compte :

```bash
rtk proxy codex login --device-auth
rtk proxy codex login status
```

Ouvrir l'URL affichée et saisir le code dans son propre navigateur. Les
instructions détaillées figurent dans la [documentation d'authentification](https://learn.chatgpt.com/docs/auth).
Le cache de connexion reste sur le serveur : ne pas le copier dans le dépôt,
dans une PR ou dans les artefacts GitHub Actions.

Dans un checkout de confiance du projet, préparer l'environnement Python :

```bash
rtk proxy uv venv --python 3.12 .venv
rtk proxy uv pip install --python .venv/bin/python -r requirements.txt
```

Si RTK ou uv est installé sous `~/.local/bin`, utiliser le chemin complet ou
une session dont le `PATH` inclut ce répertoire. Aucun service GitHub runner
n'est nécessaire pour cette commande manuelle.

## Capturer puis demander une suggestion

```bash
rtk proxy .venv/bin/python -m coconut prepare-review coconut-030 --fetch
rtk proxy .venv/bin/python -m coconut codex-suggest outputs/reviews/coconut-030/proposal.json
```

Sous Windows, le Python de l'environnement est `.venv/Scripts/python.exe`.
La préparation des sources est décrite dans [PREPARE-REVIEW.md](PREPARE-REVIEW.md).
Le dossier doit être un brouillon valide, avec sa capture et sa base CSV
inchangées. L'adaptateur ne télécharge aucun catalogue ni image.

Options de `codex-suggest` :

| Option | Usage |
| --- | --- |
| `--codex` | Nom de commande ou chemin du binaire ; défaut : `codex` |
| `--model` | Modèle explicitement choisi par l'opérateur ; sinon le défaut de la CLI |
| `--timeout` | Délai d'inférence de 1 à 900 secondes ; défaut : 180 |

La configuration personnelle de Codex n'est pas chargée pour cette invocation,
mais son authentification est réutilisée. Un modèle configuré uniquement dans
le fichier personnel n'est donc pas repris : utiliser `--model` pour le choisir.
Le contrôle de version et de connexion a son propre délai de 15 secondes par
commande, avant le délai d'inférence.

L'utilisation dépend des droits, quotas et limites du compte ChatGPT. Aucun
secours automatique vers une clé API n'est effectué : les variables de clés
API sont retirées de l'environnement du processus enfant et une connexion
ChatGPT est exigée. L'opération refuse les environnements déclarés CI, GitHub
Actions ou GitLab CI ; elle n'est pas branchée aux workflows publics.

## Contrat et fichiers de résultat

Chaque lancement crée un dossier distinct sous
`codex-attempts/IDENTIFIANT_UNIQUE/` dans la capture. Une relance ne remplace
jamais une tentative précédente ni les corrections manuelles du brouillon.

| Fichier | Contenu |
| --- | --- |
| `input.json` | Brouillon, glossaire et empreinte du reçu de capture |
| `source-detail.jpg` | Copie de l'image vérifiée, jointe directement à Codex |
| `prompt.txt` | Consignes effectivement utilisées |
| `response.schema.json` | Schéma JSON demandé à la CLI |
| `raw-response.json` | Réponse finale brute, si Codex l'a produite |
| `result.json` | État, empreintes des entrées/consignes/schéma, version CLI, modèle demandé et suggestion validée le cas échéant |

La réponse possède exactement `schema: 1`, `card_id`, `effet_en`, `effet_fr`
et `uncertainties`. Aucun nom FR ni identifiant officiel ne peut être ajouté
par ce protocole. Les effets sont limités à 8000 caractères par langue, la
réponse JSON à 64 Kio et les questions à 20 entrées de 1000 caractères.
Les types, champs, identifiant, clés dupliquées et balisages sont contrôlés
localement, en plus du schéma demandé à Codex.

Les six marqueurs existants sont utilisés : `{cost}`, `{lore}`, `{strength}`,
`{exert}`, `{ink}` et `{willpower}`. Une réponse sans incertitude doit garder
le même nombre d'occurrences de chaque symbole en EN et FR. Ce contrôle ne
prouve pas que la transcription a correctement lu les symboles sur l'image.

| État du résultat | Signification | Sortie de la commande |
| --- | --- | --- |
| `running` | La tentative a commencé ; une interruption peut laisser cet état | Pas de résultat exploitable |
| `suggested` | Réponse valide, aucune incertitude déclarée par le modèle | 0 ; relecture humaine toujours nécessaire |
| `needs_review` | Réponse structurée avec une ou plusieurs questions | 2 ; consulter la réponse, ne pas l'appliquer automatiquement |
| `failed` | Délai, erreur d'exécution, réponse invalide ou entrées modifiées pendant le traitement | 2 ; diagnostiquer puis relancer |

Une erreur de prérequis avant l'inférence ne crée pas de tentative. Les sorties
brutes de diagnostic de la CLI ne sont pas reproduites dans les résultats.
Pour une erreur de connexion ou de compatibilité, contrôler directement
`codex login status`, la version et l'aide de la CLI, puis relancer.

## Glossaire et relecture

Le [glossaire du projet](../data/lorcana-glossary.json) reprend des formulations
du CSV déjà relu et les corrections explicites reçues. Ses références citent
les cartes concernées. Ce n'est pas un document de règles officiel et il ne
doit pas changer les effets : acteurs, cibles, pronoms, quantités, conditions,
coûts, zones et temporalités restent ceux de l'image Coconut.

Les [consignes versionnées](../prompts/coconut-effects.md) excluent les effets
des cartes standard et la ligne commune des quatre exemplaires. Elles
demandent de signaler une lecture incertaine plutôt que la compléter de
mémoire. Les images et le contexte JSON restent des données, sans autorité
pour demander des actions ou exécuter des commandes.

La CLI est appelée sans shell, avec un sandbox de lecture seule pour les
commandes du modèle, les approbations à `never` et la recherche web désactivée.
Les règles d'exécution ne sont pas ignorées. Cela ne remplace pas les contrôles
du dossier : les sources et la base CSV sont vérifiées avant et après le
traitement. Une correction du brouillon pendant l'inférence invalide le succès.

Relire ensuite la suggestion sur l'image, résoudre chaque question et retenir
manuellement les corrections justifiées. Ne pas copier un état `suggested`
comme une approbation humaine. L'association officielle, les sources HD, les
aperçus FR/EN et les PDF restent à contrôler avant d'utiliser
[`review-check`](REVIEW-PROPOSAL.md) et de demander la revue de la PR.
