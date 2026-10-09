# Relecture des cartes Coconut

Les retours français reçus le 6 octobre 2026 sont intégrés au CSV. Les sous-titres cités (Ariel, Stitch, Madrigal, Robin, Ursula, Nick, Dumbo, Blanche-Neige, Winnie, Mickey, Sisu et autres) y figuraient déjà ; ils sont également repris automatiquement dans la ligne « Jusqu'à 4 exemplaires ». Les corrections de ciblage, de zones et de terminologie ont été appliquées à l'effet Coconut, sans copier l'effet de la carte standard.

Les six pictogrammes de la planche de référence sont maintenant redessinés en vecteurs dans `coconut/icons.py`, sans utiliser les pixels ni le filigrane de la planche. Quatre apparaissent dans les effets actuels : `{cost}`, `{lore}`, `{strength}` et `{exert}`. L'hexagone de coût est distinct de la spirale `{ink}`. Les mots clés explicitement marqués sont en gras.

## À confirmer sur le nouvel aperçu avant fusion

- La formulation des effets de Stitch (personnage choisi), du Chaudron (carte bannie), d'Aladdin & Génie (cartes que vous avez piochées) et de Sisu (tous les personnages).
- L'usage de « Combattant » sur Pat et de « Floodborn » sur La Plante, conformément aux retours reçus.
- Le rendu des quatre pictogrammes, des mots clés en gras, des crédits, du masque noir de coût et des trois planches A4 avec leur écart imprimé.
- `coconut-007` Mufasa : l'image Coconut verrouillée dit **2** cartes dans la réserve ; le PDF bêta antérieur en dit 3. Le CSV suit l'image verrouillée.
- `coconut-009` Blanche-Neige : confirmer la condition des sept personnages Sept Nains de noms différents et la portée des zones main/défausse/jeu.

La version française a été validée puis publiée. Pour l'extension bilingue, relire les textes EN, une image et le PDF EN ainsi que la bascule `?lang=en` avant fusion.
