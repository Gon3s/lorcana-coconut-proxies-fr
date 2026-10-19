import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from coconut.__main__ import _fetch_bytes, _json_source, import_catalog
from coconut.catalog import CSV_COLUMNS, read_cards, write_cards
from coconut.check import format_check_summary


def coconut(number, name, detail_suffix='a'):
    return {'name': name, 'subtitle': 'Subtitle',
            'card_detail_url': f'https://host/coconut-cards/{number:03d}_{detail_suffix}.jpg',
            'settings_thumbnail_url': f'https://host/coconut-cards/{number:03d}_settings.jpg'}


class ImportTests(unittest.TestCase):
    def test_image_fetch_sends_jpeg_client_headers(self):
        with patch('coconut.__main__.urlopen', return_value=BytesIO(b'jpeg')) as opened:
            self.assertEqual(_fetch_bytes('https://host/card.jpg', 'image/jpeg'), b'jpeg')
        request = opened.call_args.args[0]
        self.assertEqual(request.get_header('Accept'), 'image/jpeg')
        self.assertTrue(request.get_header('User-agent'))

    def test_catalog_fetch_sends_json_client_headers(self):
        with patch('coconut.__main__.urlopen', return_value=BytesIO(b'{"coconut_cards": []}')) as opened:
            self.assertEqual(_json_source(None, 'en', True), {'coconut_cards': []})
        request = opened.call_args.args[0]
        self.assertEqual(request.get_header('Accept'), 'application/json')
        self.assertTrue(request.get_header('User-agent'))

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

    def test_check_reports_new_card_without_changing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv = root / 'data' / 'coconut-cards.csv'
            previous = {column: '' for column in CSV_COLUMNS}
            previous.update(id='coconut-001', name_en='Ariel', name_fr='Ariel',
                            effet_fr='Texte relu',
                            ref_image_detail='https://host/coconut-cards/001_a.jpg',
                            ref_image_settings='https://host/coconut-cards/001_settings.jpg')
            write_cards(csv, [previous])
            before = csv.read_bytes()
            en = {'coconut_cards': [coconut(1, 'Ariel'), coconut(2, 'Merida')]}
            fr = {'coconut_cards': [coconut(1, 'Ariel'), coconut(2, 'Merida')]}

            report = import_catalog(root, en, fr, persist=False)

            self.assertEqual(report['added'], ['coconut-002'])
            self.assertTrue(report['review_required'])
            self.assertEqual(csv.read_bytes(), before)
            summary = format_check_summary(report, en, fr)
            self.assertIn('coconut-002', summary)
            self.assertIn('Merida', summary)
            self.assertIn('1 nouvelle carte', summary)
            self.assertIn('Non vérifiées', summary)

    def test_check_summary_clearly_reports_no_new_card(self):
        report = {'added': [], 'changed': {}, 'detail_image_changed': {},
                  'official_changes': {}, 'missing': [], 'review_required': False}
        summary = format_check_summary(report, {'coconut_cards': []}, {'coconut_cards': []})
        self.assertIn('Aucune nouvelle carte Coconut', summary)


if __name__ == '__main__':
    unittest.main()
