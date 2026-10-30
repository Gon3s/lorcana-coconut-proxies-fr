import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from coconut.catalog import CSV_COLUMNS, read_cards, write_cards
from coconut.prepare import prepare_review
from coconut.__main__ import main
from coconut.sources import create_lock


HOST = 'https://api.lorcana.ravensburger.com'
IDENTIFIER = 'coconut-999'
DETAIL = f'{HOST}/images/en/coconut-cards/999_detail.jpg'
SETTINGS = f'{HOST}/images/fr/coconut-cards/999_settings.jpg'
ART = f'{HOST}/images/fr/official.jpg'


def jpeg(size=(1468, 2048), color='navy', format='JPEG'):
    stream = io.BytesIO()
    Image.new('RGB', size, color).save(stream, format=format)
    return stream.getvalue()


class PrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detail = jpeg()
        cls.settings = jpeg((256, 256))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'outputs' / 'reviews'
        self.folder = self.output / IDENTIFIER
        self.csv = self.root / 'data' / 'coconut-cards.csv'
        write_cards(self.csv, [])
        (self.root / 'data' / 'sources.lock.json').write_text(
            '{"schema":1,"cards":{},"files":{}}', encoding='utf-8')
        self.catalogs = {}
        for language in ('en', 'fr'):
            self.catalogs[language] = {
                'coconut_cards': [{
                    'name': 'Synthetic test', 'subtitle': 'Source label',
                    'card_detail_url': DETAIL if language == 'en' else SETTINGS,
                    'settings_thumbnail_url': SETTINGS,
                }],
                'cards': {'characters': [{
                    'culture_invariant_id': 999,
                    'name': 'Synthetic official' if language == 'en' else 'Essai officiel',
                    'subtitle': 'Synthetic subtitle',
                    'variants': [{'variant_id': 'Regular', 'detail_image_url': ART}],
                }]},
            }
        self.images = {DETAIL: self.detail, SETTINGS: self.settings, ART: self.detail}
        self.fetch = Mock(side_effect=lambda url: self.images[url])

    def prepare(self, **kwargs):
        return prepare_review(
            self.root, IDENTIFIER, self.catalogs['en'], self.catalogs['fr'],
            self.output, self.fetch, **kwargs,
        )

    def snapshot(self, folder):
        return {str(path.relative_to(folder)): path.read_bytes()
                for path in folder.rglob('*') if path.is_file()}

    def reviewed_row(self):
        row = dict.fromkeys(CSV_COLUMNS, '')
        row.update(id=IDENTIFIER, name_en='Reviewed EN', name_fr='Nom relu',
                   effet_en='Reviewed EN effect.', effet_fr='Effet déjà relu.',
                   ref_image_detail=DETAIL, ref_image_settings=SETTINGS,
                   official_card_id='999', ref_image_art_fr_hd=ART)
        return row

    def test_new_card_creates_only_a_draft_with_real_sources_and_catalog_snapshots(self):
        before = self.snapshot(self.root / 'data')
        path = self.prepare()
        self.assertEqual(path, self.folder / 'proposal.json')
        proposal = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(proposal['status'], 'draft')
        self.assertIsNone(proposal['base_card'])
        self.assertEqual(set(proposal['card']), set(CSV_COLUMNS))
        for field in ('name_fr', 'subtitle_fr', 'effet_en', 'effet_fr', 'official_card_id'):
            self.assertEqual(proposal['card'][field], '')
        self.assertEqual(set(proposal['sources']), {'detail', 'settings'})
        for role, data in (('detail', self.detail), ('settings', self.settings)):
            record = proposal['sources'][role]
            self.assertEqual((self.folder / record['path']).read_bytes(), data)
            self.assertEqual(record['sha256'], hashlib.sha256(data).hexdigest())
        self.assertTrue(proposal['uncertainties'])
        for language in ('en', 'fr'):
            catalog = json.loads((self.folder / f'catalog-{language}.json').read_text(encoding='utf-8'))
            self.assertEqual(catalog, self.catalogs[language])
        self.assertEqual(self.snapshot(self.root / 'data'), before)

    def test_explicit_official_id_is_a_candidate_match_not_an_approval(self):
        path = self.prepare(official_card_id='999')
        proposal = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(proposal['card']['name_fr'], 'Essai officiel')
        self.assertEqual(proposal['card']['official_card_id'], '999')
        self.assertIn('art_fr_hd', proposal['sources'])
        self.assertEqual(proposal['status'], 'draft')
        self.assertEqual(proposal['match_evidence'], '')
        self.assertEqual(read_cards(self.csv), [])

    def test_rerun_preserves_corrections_and_does_not_rewrite_any_files(self):
        path = self.prepare()
        proposal = json.loads(path.read_text(encoding='utf-8'))
        proposal['card']['effet_fr'] = 'Correction manuelle à conserver.'
        proposal['uncertainties'] = ['Question à conserver.']
        path.write_text(json.dumps(proposal, ensure_ascii=False), encoding='utf-8')
        before = self.snapshot(self.folder)
        self.assertEqual(self.prepare(), path)
        self.assertEqual(self.snapshot(self.folder), before)

    def test_unrelated_catalog_change_does_not_overwrite_the_captured_snapshot(self):
        self.prepare()
        before = self.snapshot(self.folder)
        self.catalogs['en']['unrelated_metadata'] = 'New unrelated information'
        self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)

    def test_unknown_or_malformed_identifier_is_rejected_without_fetch_or_output(self):
        for identifier in ('coconut-998', '../coconut-999', '999'):
            with self.subTest(identifier=identifier):
                with self.assertRaisesRegex(ValueError, 'ID|Unknown'):
                    prepare_review(self.root, identifier, self.catalogs['en'],
                                   self.catalogs['fr'], self.output, self.fetch)
                self.fetch.assert_not_called()
        self.assertFalse(self.folder.exists())

    def test_missing_french_pair_and_duplicate_ids_are_rejected(self):
        for problem in ('missing', 'duplicate'):
            with self.subTest(problem=problem):
                french = copy.deepcopy(self.catalogs['fr'])
                french['coconut_cards'] = ([] if problem == 'missing'
                                          else french['coconut_cards'] * 2)
                with self.assertRaises(ValueError):
                    prepare_review(self.root, IDENTIFIER, self.catalogs['en'],
                                   french, self.output, self.fetch)
        self.fetch.assert_not_called()

    def test_settings_reference_must_belong_to_the_selected_coconut(self):
        other = SETTINGS.replace('999_', '998_')
        self.catalogs['fr']['coconut_cards'][0]['settings_thumbnail_url'] = other
        self.images[other] = self.settings
        with self.assertRaisesRegex(ValueError, 'ID.*settings'):
            self.prepare()
        self.fetch.assert_not_called()
        self.assertFalse(self.folder.exists())

    def test_unknown_or_ambiguous_official_card_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'official'):
            self.prepare(official_card_id='998')
        self.catalogs['fr']['cards']['characters'] *= 2
        with self.assertRaisesRegex(ValueError, 'official'):
            self.prepare(official_card_id='999')
        self.assertFalse(self.folder.exists())

    def test_bad_image_or_dimensions_leave_no_partial_dossier(self):
        for data in (b'not an image', jpeg((30, 40)), jpeg(format='PNG'), self.detail[:-500]):
            with self.subTest(size=len(data)):
                self.images[DETAIL] = data
                with self.assertRaisesRegex(ValueError, 'detail'):
                    self.prepare()
                self.assertFalse(self.folder.exists())

    def test_non_square_settings_are_rejected(self):
        self.images[SETTINGS] = jpeg((256, 128))
        with self.assertRaisesRegex(ValueError, 'settings'):
            self.prepare()
        self.assertFalse(self.folder.exists())

    def test_network_error_after_first_download_leaves_no_partial_dossier(self):
        self.fetch.side_effect = [self.detail, TimeoutError('Synthetic timeout')]
        before = self.snapshot(self.root / 'data')
        with self.assertRaisesRegex((ValueError, OSError), 'timeout|Timeout'):
            self.prepare()
        self.assertFalse(self.folder.exists())
        self.assertEqual(self.snapshot(self.root / 'data'), before)

    def test_image_revision_at_same_url_is_reported_without_replacing_old_dossier(self):
        self.prepare()
        before = self.snapshot(self.folder)
        self.images[DETAIL] = jpeg(color='green')
        with self.assertRaisesRegex(ValueError, 'changed.*new output'):
            self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)

    def test_label_revision_and_csv_correction_do_not_replace_the_dossier(self):
        self.prepare()
        before = self.snapshot(self.folder)
        self.catalogs['en']['coconut_cards'][0]['name'] = 'Revised source label'
        with self.assertRaisesRegex(ValueError, 'changed.*new output'):
            self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)
        self.catalogs['en']['coconut_cards'][0]['name'] = 'Synthetic test'
        row = dict.fromkeys(CSV_COLUMNS, '')
        row.update(id=IDENTIFIER, effet_fr='Texte validé depuis la préparation.')
        write_cards(self.csv, [row])
        with self.assertRaisesRegex(ValueError, 'CSV.*changed'):
            self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)

    def test_modified_local_source_is_detected_instead_of_repaired_silently(self):
        path = self.prepare()
        proposal = json.loads(path.read_text(encoding='utf-8'))
        (self.folder / proposal['sources']['detail']['path']).write_bytes(b'local edit')
        before = self.snapshot(self.folder)
        with self.assertRaisesRegex(ValueError, 'local.*changed'):
            self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)

    def test_changed_proposal_reference_cannot_reuse_a_capture_of_another_image(self):
        path = self.prepare()
        proposal = json.loads(path.read_text(encoding='utf-8'))
        proposal['card']['ref_image_detail'] = DETAIL.replace('detail', 'other')
        path.write_text(json.dumps(proposal), encoding='utf-8')
        before = self.snapshot(self.folder)
        with self.assertRaisesRegex(ValueError, 'Proposal source references'):
            self.prepare()
        self.assertEqual(self.snapshot(self.folder), before)

    def test_existing_translations_are_copied_without_accepting_candidate_sources(self):
        row = self.reviewed_row()
        write_cards(self.csv, [row])
        before = self.snapshot(self.root / 'data')
        proposal = json.loads(self.prepare().read_text(encoding='utf-8'))
        self.assertEqual(proposal['base_card'], row)
        for field in ('name_en', 'name_fr', 'effet_en', 'effet_fr'):
            self.assertEqual(proposal['card'][field], row[field])
        self.assertEqual(self.snapshot(self.root / 'data'), before)

    def test_output_must_stay_in_outputs_and_existing_unmanaged_folder_is_not_overwritten(self):
        for output in (self.root / 'data', self.root / 'assets', self.root / '..'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, 'outputs'):
                    prepare_review(self.root, IDENTIFIER, self.catalogs['en'],
                                   self.catalogs['fr'], output, self.fetch)
        self.folder.mkdir(parents=True)
        (self.folder / 'keep.txt').write_text('keep', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual((self.folder / 'keep.txt').read_text(), 'keep')

    def test_candidate_revision_is_reported_against_published_hash_without_acceptance(self):
        write_cards(self.csv, [self.reviewed_row()])
        source = self.root / 'assets' / 'source' / 'published.jpg'
        source.parent.mkdir(parents=True)
        source.write_bytes(jpeg(color='green'))
        lock = create_lock(self.root, {IDENTIFIER: {'detail': 'assets/source/published.jpg'}})
        lock_path = self.root / 'data' / 'sources.lock.json'
        lock_path.write_text(json.dumps(lock), encoding='utf-8')
        before = self.snapshot(self.root / 'data')
        published = self.snapshot(self.root / 'assets')
        self.prepare()
        receipt = json.loads((self.folder / 'capture.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['changes_against_published']['images']['detail'], {
            'previous': lock['files']['assets/source/published.jpg'],
            'incoming': hashlib.sha256(self.detail).hexdigest(),
        })
        self.assertEqual(self.snapshot(self.root / 'data'), before)
        self.assertEqual(self.snapshot(self.root / 'assets'), published)

    def test_publish_failure_leaves_no_target_and_preserves_production(self):
        before = self.snapshot(self.root / 'data')
        with patch('coconut.prepare.os.rename', side_effect=OSError('Synthetic disk error')):
            with self.assertRaisesRegex(OSError, 'disk error'):
                self.prepare()
        self.assertFalse(self.folder.exists())
        self.assertEqual(self.snapshot(self.root / 'data'), before)

    def test_invalid_published_lock_is_an_explained_error_without_partial_output(self):
        (self.root / 'data' / 'sources.lock.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source lock'):
            self.prepare()
        self.assertFalse(self.folder.exists())

    def test_command_creates_the_draft_and_reports_errors_without_writing_production(self):
        for language in ('en', 'fr'):
            (self.root / f'{language}.json').write_text(
                json.dumps(self.catalogs[language]), encoding='utf-8')
        arguments = ['coconut', '--root', str(self.root), 'prepare-review', IDENTIFIER,
                     '--en', 'en.json', '--fr', 'fr.json']
        before = self.snapshot(self.root / 'data')
        with patch('coconut.download.download_bytes', side_effect=lambda url, *_: self.images[url]):
            with patch('sys.argv', arguments), redirect_stdout(io.StringIO()):
                main()
        self.assertTrue((self.folder / 'proposal.json').is_file())
        self.assertEqual(self.snapshot(self.root / 'data'), before)
        with patch('sys.argv', arguments), redirect_stderr(io.StringIO()) as errors:
            with patch('coconut.download.download_bytes', side_effect=TimeoutError('Synthetic timeout')):
                with self.assertRaises(SystemExit) as stopped:
                    main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertNotIn('Traceback', errors.getvalue())
        self.assertIn('timeout', errors.getvalue())

    def test_command_rejects_missing_or_mixed_catalog_arguments_before_downloading(self):
        for options in ([], ['--en', 'en.json'], ['--fetch', '--fr', 'fr.json']):
            with self.subTest(options=options), patch('coconut.download.download_bytes') as fetch:
                arguments = ['coconut', '--root', str(self.root), 'prepare-review', IDENTIFIER, *options]
                with patch('sys.argv', arguments), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as stopped:
                        main()
                self.assertEqual(stopped.exception.code, 2)
                fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
