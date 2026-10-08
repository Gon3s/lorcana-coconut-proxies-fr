import unittest

from coconut.icons import ICONS, icon_mask


class IconTests(unittest.TestCase):
    def test_all_symbols_from_the_reference_sheet_have_clean_shapes(self):
        self.assertEqual(ICONS, frozenset({
            'cost', 'lore', 'strength', 'exert', 'ink', 'willpower',
        }))
        for symbol in ICONS:
            with self.subTest(symbol=symbol):
                mask = icon_mask(symbol, 96)
                self.assertEqual(mask.size, (96, 96))
                self.assertEqual(mask.getextrema(), (0, 255))
                self.assertIsNotNone(mask.getbbox())

    def test_framed_symbols_keep_their_centers_open(self):
        for symbol in ('cost', 'lore', 'strength', 'exert'):
            with self.subTest(symbol=symbol):
                self.assertEqual(icon_mask(symbol, 96).getpixel((48, 48)), 0)

    def test_print_size_icons_are_not_empty(self):
        for symbol in ICONS:
            with self.subTest(symbol=symbol):
                self.assertIsNotNone(icon_mask(symbol, 36).getbbox())


if __name__ == '__main__':
    unittest.main()
