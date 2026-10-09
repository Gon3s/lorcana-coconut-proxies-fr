import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from coconut.typography import draw_icon, layout_rules, parse_word


FONTS = Path(__file__).parents[1] / 'assets' / 'fonts'


class TypographyTests(unittest.TestCase):
    def test_keyword_and_symbol_markup_preserve_punctuation(self):
        self.assertEqual(
            [(part.kind, part.text) for part in parse_word('**Boost**,+1{lore}.')],
            [('bold', 'Boost'), ('text', ',+1'), ('icon', 'lore'), ('text', '.')],
        )

    def test_unknown_symbol_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown rules symbol'):
            parse_word('{unknown}')
        self.assertEqual(parse_word('{ink}')[0].text, 'ink')

    def test_layout_respects_mixed_style_width_and_paragraphs(self):
        draw = ImageDraw.Draw(Image.new('RGB', (300, 200), 'white'))
        lines = layout_rules(draw, '**Boost** +1 {lore}\nPuis piochez.', FONTS, 50, 190)
        self.assertGreaterEqual(len(lines), 2)
        self.assertTrue(any(words and words[0][0].text == 'Puis' for words, _ in lines))
        self.assertTrue(all(width <= 190 for _, width in lines))

    def test_all_symbols_render_without_a_font_glyph(self):
        image = Image.new('RGB', (360, 70), 'white')
        draw = ImageDraw.Draw(image)
        for index, symbol in enumerate(('cost', 'lore', 'strength', 'exert', 'ink', 'willpower')):
            draw_icon(draw, symbol, 8 + index * 58, 8, 48, (0, 0, 0))
            self.assertLess(image.crop((8 + index * 58, 8, 56 + index * 58, 56)).getextrema()[0][0], 255)

    def test_redrawn_exert_arrow_keeps_its_tip_and_open_center(self):
        image = Image.new('L', (100, 100), 255)
        draw_icon(ImageDraw.Draw(image), 'exert', 10, 10, 80, 0)
        self.assertLess(image.getpixel((72, 30)), 128)
        self.assertEqual(image.getpixel((50, 50)), 255)

    def test_redrawn_icons_do_not_cover_the_card_with_a_white_box(self):
        for symbol in ('cost', 'lore', 'strength', 'exert', 'ink', 'willpower'):
            image = Image.new('RGB', (80, 80), (230, 230, 230))
            draw_icon(ImageDraw.Draw(image), symbol, 10, 10, 60, (0, 0, 0))
            self.assertEqual(image.getpixel((12, 12)), (230, 230, 230), symbol)


if __name__ == '__main__':
    unittest.main()
