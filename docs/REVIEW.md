# Relecture des cartes Coconut

Les retours français reçus le 6 octobre 2026 sont intégrés au CSV. Les sous-titres cités (Ariel, Stitch, Madrigal, Robin, Ursula, Nick, Dumbo, Blanche-Neige, Winnie, Mickey, Sisu et autres) y figuraient déjà ; ils sont également repris automatiquement dans la ligne « Jusqu'à 4 exemplaires ». Les corrections de ciblage, de zones et de terminologie ont été appliquées à l'effet Coconut, sans copier l'effet de la carte standard.

Les six pictogrammes de la planche de référence sont maintenant redessinés en vecteurs dans `coconut/icons.py`, sans utiliser les pixels ni le filigrane de la planche. Quatre apparaissent dans les effets actuels : `{cost}`, `{lore}`, `{strength}` et `{exert}`. L'hexagone de coût est distinct de la spirale `{ink}`. Les mots clés explicitement marqués sont en gras.

## Points de contrôle issus de la revue initiale

- La formulation des effets de Stitch (personnage choisi), du Chaudron (carte bannie), d'Aladdin & Génie (cartes que vous avez piochées) et de Sisu (tous les personnages).
- L'usage de « Combattant » sur Pat et de « Floodborn » sur La Plante, conformément aux retours reçus.
- Le rendu des quatre pictogrammes, des mots clés en gras, des crédits, du masque noir de coût et des planches A4 avec leur écart imprimé.
- `coconut-007` Mufasa : l'image Coconut verrouillée dit **2** cartes dans la réserve ; le PDF bêta antérieur en dit 3. Le CSV suit l'image verrouillée.
- `coconut-009` Blanche-Neige : confirmer la condition des sept personnages Sept Nains de noms différents et la portée des zones main/défausse/jeu.

Le site FR/EN est publié. Pour chaque nouvelle carte ou révision, relire les textes, les JPEG, les PDF et la bascule `?lang=en` avant fusion.

## Judy Hopps — Découvrant des indices (`coconut-029`)

- La source Coconut EN et l'illustration française haute résolution du numéro 156/204, set 10, représentent la même scène. L'identifiant officiel est `2345`.
- L'effet EN a été transcrit sur l'image Coconut détaillée ; l'effet de la carte standard est différent.
- Le texte français de l'effet a été validé par l'utilisateur le 19 octobre 2026.
- Les JPEG FR et EN, la page et la quatrième planche A4 de chaque PDF ont été générés. Ces sorties sont reconstruites par la CI à chaque PR.

## Maui — Demi-requin (`coconut-030`)

Les textes EN/FR, les sources et les rendus ont été validés par l'utilisateur
le 30 octobre 2026. Le [compte rendu de revue](reviews/coconut-030.md) conserve
les textes approuvés, les références, les empreintes et les étapes vérifiées.
