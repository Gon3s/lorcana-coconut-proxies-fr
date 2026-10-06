import tempfile
import unittest
from pathlib import Path

from PIL import Image

from coconut.build import compose_card, render_html, validate_rows
from coconut.catalog import CSV_COLUMNS


def card(**overrides):
    result = {column: 'value' for column in CSV_COLUMNS}
    result.update(id='coconut-001', name_fr='Ariel', subtitle_fr='Chanteuse',
                  effet_fr='Gagnez 1 {lore}.', ref_image_detail='https://host/coconut-cards/001_a.jpg',
                  ref_image_art_fr_hd='https://host/set1/1_b.jpg', official_card_id='2')
    result.update(overrides)
    return result


class BuildTests(unittest.TestCase):
    def test_missing_french_text_blocks_build(self):
        with self.assertRaisesRegex(ValueError, 'coconut-001.*effet_fr'):
            validate_rows([card(effet_fr='')])

    def test_invalid_id_blocks_build(self):
        with self.assertRaisesRegex(ValueError, 'Invalid Coconut ID'):
            validate_rows([card(id='1')])

    def test_card_uses_hd_art_and_repaints_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            detail = root / 'detail.jpg'
            art = root / 'art.jpg'
            Image.new('RGB', (1468, 2048), '#888888').save(detail)
            Image.new('RGB', (1468, 2048), '#ff3311').save(art)
            fonts = Path(__file__).parents[1] / 'assets' / 'fonts'
            output = compose_card(card(), detail, art, fonts)
            self.assertEqual(output.size, (1468, 2048))
            self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(output.getpixel((700, 500)), (255, 51, 17))))
            self.assertNotEqual(output.getpixel((500, 1450)), (136, 136, 136))

    def test_long_rules_fail_instead_of_becoming_tiny(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('detail.jpg', 'art.jpg'):
                Image.new('RGB', (1468, 2048), '#888888').save(root / name)
            fonts = Path(__file__).parents[1] / 'assets' / 'fonts'
            with self.assertRaisesRegex(ValueError, 'overflow'):
                compose_card(card(effet_fr='texte ' * 1500), root / 'detail.jpg', root / 'art.jpg', fonts)

    def test_html_contains_every_card_and_no_base64(self):
        html = render_html([card(), card(id='coconut-002', name_fr='Stitch')])
        self.assertIn('images/coconut-001.jpg', html)
        self.assertIn('images/coconut-002.jpg', html)
        self.assertNotIn('base64,', html)
        css = (Path(__file__).parents[1] / 'web' / 'style.css').read_text(encoding='utf-8')
        self.assertIn('gap:1px', css)


if __name__ == '__main__':
    unittest.main()
