import unittest
import re
from pathlib import Path

from coconut.catalog import read_cards


class ReviewedCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv = Path(__file__).parents[1] / 'data' / 'coconut-cards.csv'
        cls.cards = {row['id']: row for row in read_cards(csv)}

    def test_targeting_and_zone_corrections(self):
        self.assertIn('un personnage choisi gagne +1 {lore}', self.cards['coconut-004']['effet_fr'])
        self.assertIn('vous pouvez le placer depuis votre défausse', self.cards['coconut-027']['effet_fr'])
        self.assertIn('que vous avez piochée', self.cards['coconut-023']['effet_fr'])
        self.assertIn('Tous les personnages', self.cards['coconut-016']['effet_fr'])

    def test_reviewed_terminology(self):
        self.assertEqual(self.cards['coconut-027']['name_fr'], 'Le Chaudron Magique')
        self.assertIn('**Combattant**', self.cards['coconut-026']['effet_fr'])
        self.assertIn('**Floodborn**', self.cards['coconut-024']['effet_fr'])
        self.assertIn('épuisées', self.cards['coconut-007']['effet_fr'])
        self.assertIn('épuiser', self.cards['coconut-011']['effet_fr'])

    def test_all_source_symbols_are_present_in_the_french_rules(self):
        for card in self.cards.values():
            english = set(re.findall(r'\{(ink|lore|strength|exert)\}', card['effet_en']))
            french = set(re.findall(r'\{(ink|lore|strength|exert)\}', card['effet_fr']))
            self.assertTrue(english <= french, card['id'])


if __name__ == '__main__':
    unittest.main()
