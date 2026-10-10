# Instructions du dépôt Coconut

## Objectif

Ce dépôt maintient les cartes Coconut françaises et anglaises, leurs sources
verrouillées et leur rendu imprimable. `data/coconut-cards.csv` est la source
éditable des textes ; `data/sources.lock.json` et `assets/source/` rendent les
constructions reproductibles.

## Règles de modification

- Suivre `docs/SPEC.md` et `docs/MAINTENANCE.md` pour toute nouvelle carte ou
  révision de source.
- Ne jamais inventer une traduction, une transcription anglaise ou une
  association à une carte officielle. Une donnée non confirmée est une
  question bloquante.
- Préserver les textes relus lors d'un import. Une carte absente du catalogue
  distant est signalée, jamais supprimée automatiquement.
- Ne pas modifier les fichiers générés sous `dist/` ni les committer.
- N'accepter une nouvelle image ou une nouvelle empreinte qu'après comparaison
  humaine de la source. `sync-sources --accept-changes` exige cette validation.
- Ne pas modifier `AGENTS.md`, `.agents/` ou `.github/workflows/` dans une
  feature ordinaire. Ces fichiers de confiance passent par une PR dédiée et
  une validation humaine.
- Ne jamais déployer ni pousser sur `main`. Le merge et la revue visuelle des
  cartes, de la page et des PDF restent humains.

## Commandes de contrôle

Sur le runner local, préparer un environnement isolé depuis le fichier épinglé :

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

La CI peut continuer à utiliser `python -m pip install -r requirements.txt`
dans son environnement jetable.

Exécuter les contrôles déterministes avant et après une modification :

```bash
uv pip check --python .venv/bin/python
.venv/bin/python -m compileall -q coconut tests
git diff --check
.venv/bin/python -m unittest discover -s tests -v
node --test tests/site.test.js
.venv/bin/python -m coconut build --out dist
```

Le build ordinaire utilise seulement les sources locales. L'import distant est
une opération séparée, réservée aux tâches qui demandent explicitement une
mise à jour du catalogue :

```bash
.venv/bin/python -m coconut import --fetch --report import-report.json
```

Examiner alors `added`, `changed`, `detail_image_changed`, `official_changes`
et `missing` avant toute modification persistée. `import-report.json` reste un
artefact local ignoré par Git.

## Critères de livraison

- Les identifiants restent uniques et toutes les sources exigées sont
  présentes et verrouillées.
- Les tests Python et Node, le contrôle de dépendances et le build réussissent.
- Les cartes modifiées sont relues dans les deux langues, puis contrôlées dans
  les JPEG, la page et les PDF A4 avant fusion.
- La PR décrit les contrôles exécutés, les contrôles non exécutés et toute
  incertitude de traduction ou de source.
