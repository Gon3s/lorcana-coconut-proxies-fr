import tempfile
import unittest
from pathlib import Path

from coconut.__main__ import import_catalog
from coconut.catalog import CSV_COLUMNS, read_cards, write_cards


def coconut(number, name, detail_suffix='a'):
    return {'name': name, 'subtitle': 'Subtitle',
            'card_detail_url': f'https://host/coconut-cards/{number:03d}_{detail_suffix}.jpg',
            'settings_thumbnail_url': f'https://host/coconut-cards/{number:03d}_settings.jpg'}


class ImportTests(unittest.TestCase):
    def test_source_revision_reports_change_without_overwriting_existing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv = root / 'data' / 'coconut-cards.csv'
            previous = {column: '' for column in CSV_COLUMNS}
            previous.update(id='coconut-001', name_en='Ariel', name_fr='ARIEL',
                            effet_en='Old effect', effet_fr='Effet relu',
                            ref_image_detail='https://host/coconut-cards/001_a.jpg',
                            ref_image_settings='https://host/coconut-cards/001_settings.jpg',
                            official_card_id='2')
            write_cards(csv, [previous])
            en = {'coconut_cards': [coconut(1, 'Ariel', 'b')]}
            fr = {'coconut_cards': [coconut(1, 'Ariel')]}
            report = import_catalog(root, en, fr)
            self.assertIn('coconut-001', report['changed'])
            self.assertEqual(read_cards(csv), [previous])

    def test_new_card_is_appended_for_translation_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            en = {'coconut_cards': [coconut(1, 'Ariel')]}
            fr = {'coconut_cards': [coconut(1, 'Ariel')]}
            report = import_catalog(root, en, fr)
            self.assertEqual(report['added'], ['coconut-001'])
            self.assertEqual(read_cards(root / 'data' / 'coconut-cards.csv')[0]['effet_fr'], '')


if __name__ == '__main__':
    unittest.main()
