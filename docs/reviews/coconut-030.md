# Maui — Demi-requin (`coconut-030`)

Les textes EN/FR, la correspondance des sources, les JPEG et les planches PDF
ont été explicitement validés par l'utilisateur le 30 octobre 2026. Cette
validation autorise l'intégration dans la branche de revue ; la publication
reste déclenchée par la fusion humaine de la PR.

## Identité et illustration

- EN : **Maui — Half-Shark**, 124/204 EN 6.
- FR : **Maui — Demi-requin**, 124/204 FR 6.
- Identifiant commun de carte standard : **1323**.
- Illustration : **Alexandria Neonakis**.
- Les sources Coconut, la référence carrée couleur et l'illustration HD FR
  montrent la même pose de requin, le crochet levé, les feuilles et les embruns.
  Seule l'illustration est reprise de la carte standard ; ses effets ne le sont pas.

## Effet Coconut validé

EN :

> During your turn, you pay 1 {cost} less for the first action with cost 4 or more you play.

FR :

> Pendant votre tour, vous payez 1 {cost} de moins pour la première action coûtant 4 ou plus que vous jouez.

`{cost}` représente l'hexagone creux imprimé après le chiffre 1. La restriction
porte sur la première action coûtant 4 ou plus, et non sur la première action
jouée sans condition de coût. La ligne des quatre exemplaires est générée
avec le nom et le sous-titre de la langue affichée.

## Provenance

| Source | URL | SHA-256 des octets comparés |
| --- | --- | --- |
| Coconut EN | [Image détaillée](https://api.lorcana.ravensburger.com/images/en/coconut-cards/030_9d4036353713492ab6ed40ee57735cbab2b443c2.jpg) | `baa2d94e477a2e997f5e7c94064d53c7dffb28270adbc68b1ce39d05bab7893a` |
| Référence couleur | [Image carrée FR](https://api.lorcana.ravensburger.com/images/fr/coconut-cards/030_ebe5299e117101bd9f59e9b069fcae11d32cc095.jpg) | `038fbf625def548c6bd0ee9a8942e7fa5ddc99f470092981231e9ab71f6dc31d` |
| Art HD FR | [Carte standard FR](https://api.lorcana.ravensburger.com/images/fr/set6/124_5436564d0a1f117876993c28a5cdd53756aa805d.jpg) | `78bda1bc0a8beb3551a5318386a79aefdef5af08826261a775941a1c01a0f2f8` |

Les images détaillée et HD sont conservées dans `assets/source/` et verrouillées
dans `data/sources.lock.json`. La référence carrée sert à la comparaison du
cadrage, pas à l'impression. Les octets des 58 sources précédemment publiées
sont conservés à l'identique ; aucun rafraîchissement distant de ces sources
n'a été accepté lors de cet ajout.

## Parcours vérifié

1. Détection de Maui, puis capture des catalogues et des images candidates.
2. Suggestion séparée par Codex CLI 0.153.2, lancé manuellement avec ChatGPT.
3. Relecture de la transcription sur l'image Coconut et proposition FR
   harmonisée avec « Pendant votre tour ».
4. Correspondance standard EN/FR par identifiant 1323 et comparaison visuelle.
5. Construction dans une copie isolée de 30 cartes : JPEG FR/EN, page bilingue
   et deux PDF A4 de quatre pages. Maui apparaît en troisième position sur la
   quatrième planche. Les JPEG et cette planche ont été inspectés visuellement.
6. Validation humaine des textes, des sources et des rendus, puis ajout au CSV
   et au verrou de production sur la branche de PR.

Le contrôle technique du dossier a été exécuté contre la base de 29 cartes,
avant l'ajout. Après intégration, cette capture devient un historique : sa
`base_card: null` ne doit pas être réutilisée contre le CSV contenant déjà Maui.
Une future révision doit commencer par une nouvelle capture avec sa base CSV.

Le manifeste d'attente de Maui est retiré lors de son intégration. La revue et
la fusion de la PR ainsi que le contrôle du site réellement publié restent
les dernières étapes ; ce document ne les déclare pas accomplis.
