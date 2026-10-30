import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coconut.catalog import CSV_COLUMNS, write_cards
from coconut.review import review_input_digest, validate_review


REPOSITORY = Path(__file__).resolve().parents[1]


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        # Synthetic data only: no proposed translation of a real card.
        self.card = dict.fromkeys(CSV_COLUMNS, '')
        self.card.update(
            id='coconut-999', name_en='Test', name_fr='Essai',
            effet_en='Pay 2 {cost}.', effet_fr='Payez 2 {cost}.',
            official_card_id='999',
            ref_image_detail='https://example.com/coconut-cards/999_detail.jpg',
            ref_image_settings='https://example.com/coconut-cards/999_settings.jpg',
            ref_image_art_fr_hd='https://example.com/official.jpg',
        )
        self.proposal = {
            'schema': 1, 'status': 'ready_for_review',
            'card': dict(self.card), 'base_card': None, 'uncertainties': [],
            'match_evidence': 'Synthetic matching reference for the test fixture.',
            'sources': {}, 'preview': {},
        }
        for role, column in (
            ('detail', 'ref_image_detail'), ('settings', 'ref_image_settings'),
            ('art_fr_hd', 'ref_image_art_fr_hd'),
        ):
            self.proposal['sources'][role] = {
                **self.artifact(f'{role}.jpg', f'synthetic {role}'.encode()),
                'url': self.card[column],
            }
        self.proposal['preview'] = {
            'inputs_sha256': review_input_digest(self.proposal),
            'files': {role: self.artifact(name, f'synthetic {role}'.encode())
                      for role, name in (
                          ('card_fr', 'fr.jpg'), ('card_en', 'en.jpg'),
                          ('pdf_fr', 'fr.pdf'), ('pdf_en', 'en.pdf'),
                          ('page', 'index.html'),
                      )},
        }

    def artifact(self, name, data):
        (self.folder / name).write_bytes(data)
        return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}

    def check(self, existing=()):
        validate_review(self.proposal, self.folder, list(existing))

    def test_complete_proposal_is_ready_for_human_review_without_writes(self):
        before = {path.name: path.read_bytes() for path in self.folder.iterdir()}
        original = copy.deepcopy(self.proposal)
        self.check()
        self.assertEqual(self.proposal, original)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.folder.iterdir()})

    def test_detection_manifest_cannot_pass_as_prepared_card(self):
        with self.assertRaisesRegex(ValueError, 'proposal fields'):
            validate_review({'schema': 1, 'cards': [self.card]}, self.folder, [])

    def test_draft_and_self_approved_states_do_not_pass(self):
        for status in ('draft', 'approved', '', None):
            with self.subTest(status=status):
                self.proposal['status'] = status
                with self.assertRaisesRegex(ValueError, 'ready_for_review'):
                    self.check()

    def test_missing_text_or_official_match_blocks_review(self):
        for field in ('name_en', 'name_fr', 'effet_en', 'effet_fr', 'official_card_id'):
            with self.subTest(field=field):
                self.proposal['card'][field] = '  '
                with self.assertRaisesRegex(ValueError, field):
                    self.check()
                self.proposal['card'][field] = self.card[field]
        self.proposal['match_evidence'] = ' '
        with self.assertRaisesRegex(ValueError, 'match_evidence'):
            self.check()

    def test_uncertainty_blocks_review_even_with_all_files_present(self):
        self.proposal['uncertainties'] = ['Unclear target on the source image']
        with self.assertRaisesRegex(ValueError, 'Unclear target'):
            self.check()

    def test_unknown_symbol_and_malformed_markup_block_review(self):
        for text in ('Pay 2 {unknown}.', 'Pay {COST}.', '**Unclosed'):
            with self.subTest(text=text):
                self.proposal['card']['effet_en'] = text
                with self.assertRaisesRegex(ValueError, 'symbol|markup'):
                    self.check()

    def test_missing_source_and_preview_are_rejected(self):
        for section, role in (('sources', 'detail'), ('preview', 'pdf_en')):
            with self.subTest(section=section):
                records = (self.proposal[section] if section == 'sources'
                           else self.proposal['preview']['files'])
                record = records[role]
                path = self.folder / record['path']
                data = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, 'Missing review file'):
                    self.check()
                path.write_bytes(data)

    def test_source_and_preview_tampering_invalidate_their_hashes(self):
        for role in ('detail', 'card_fr'):
            with self.subTest(role=role):
                records = (self.proposal['sources'] if role == 'detail'
                           else self.proposal['preview']['files'])
                path = self.folder / records[role]['path']
                data = path.read_bytes()
                path.write_bytes(b'changed after preparation')
                with self.assertRaisesRegex(ValueError, 'checksum changed'):
                    self.check()
                path.write_bytes(data)

    def test_empty_source_or_preview_is_not_a_complete_review_file(self):
        for section, role in (('sources', 'detail'), ('preview', 'page')):
            with self.subTest(section=section):
                proposal = copy.deepcopy(self.proposal)
                records = (proposal[section] if section == 'sources'
                           else proposal['preview']['files'])
                path = self.folder / records[role]['path']
                data = path.read_bytes()
                records[role].update(self.artifact(path.name, b''))
                proposal['preview']['inputs_sha256'] = review_input_digest(proposal)
                try:
                    with self.assertRaisesRegex(ValueError, 'Empty review file'):
                        validate_review(proposal, self.folder, [])
                finally:
                    path.write_bytes(data)

    def test_corrected_text_invalidates_previous_preview(self):
        self.proposal['card']['effet_fr'] = 'Texte corrigé, à reconstruire.'
        with self.assertRaisesRegex(ValueError, 'preview.*stale'):
            self.check()

    def test_replaced_source_invalidates_preview_even_when_new_hash_is_correct(self):
        self.proposal['sources']['detail'].update(
            self.artifact('detail.jpg', b'new candidate source bytes'))
        with self.assertRaisesRegex(ValueError, 'preview.*stale'):
            self.check()

    def test_changed_matching_evidence_requires_a_new_preview_record(self):
        self.proposal['match_evidence'] = 'A different matching justification.'
        with self.assertRaisesRegex(ValueError, 'preview.*stale'):
            self.check()

    def test_reordered_json_keys_do_not_invalidate_a_preview(self):
        self.proposal['card'] = dict(reversed(list(self.proposal['card'].items())))
        self.check()

    def test_source_url_must_match_the_proposed_csv(self):
        self.proposal['sources']['detail']['url'] = 'https://example.com/other.jpg'
        with self.assertRaisesRegex(ValueError, 'detail.*URL'):
            self.check()

    def test_coconut_reference_must_match_card_identifier(self):
        self.proposal['card']['id'] = 'coconut-998'
        with self.assertRaisesRegex(ValueError, 'ID.*detail'):
            self.check()

    def test_paths_cannot_read_outside_the_review_folder(self):
        for name in ('../outside.jpg', '/outside.jpg', 'C:/outside.jpg', r'..\outside.jpg'):
            with self.subTest(path=name):
                self.proposal['sources']['detail']['path'] = name
                with self.assertRaisesRegex(ValueError, 'Unsafe review path'):
                    self.check()

    def test_revision_compares_with_exact_current_csv_without_overwriting_it(self):
        baseline = dict(self.card, effet_fr='Texte déjà relu.')
        self.proposal['base_card'] = dict(baseline)
        self.proposal['preview']['inputs_sha256'] = review_input_digest(self.proposal)
        existing = [dict(baseline)]
        self.check(existing)
        self.assertEqual(existing, [baseline])
        existing[0]['effet_fr'] = 'Correction reçue depuis la préparation.'
        with self.assertRaisesRegex(ValueError, 'CSV.*changed'):
            self.check(existing)

    def test_new_card_cannot_replace_an_existing_translation(self):
        with self.assertRaisesRegex(ValueError, 'CSV.*changed'):
            self.check([dict(self.card, effet_fr='Texte relu à préserver.')])

    def test_invalid_json_types_fail_with_explanations(self):
        for field, value in (
            ('schema', True), ('card', []), ('sources', []),
            ('uncertainties', 'none'), ('preview', []),
        ):
            with self.subTest(field=field):
                proposal = copy.deepcopy(self.proposal)
                proposal[field] = value
                with self.assertRaises(ValueError):
                    validate_review(proposal, self.folder, [])

    def test_unknown_fields_and_missing_roles_are_rejected(self):
        for section, key in (('sources', 'settings'), ('preview', 'pdf_en')):
            with self.subTest(section=section):
                proposal = copy.deepcopy(self.proposal)
                records = (proposal[section] if section == 'sources'
                           else proposal['preview']['files'])
                del records[key]
                with self.assertRaisesRegex(ValueError, 'fields'):
                    validate_review(proposal, self.folder, [])
        self.proposal['approved_by'] = 'not an actual GitHub review'
        with self.assertRaisesRegex(ValueError, 'proposal fields'):
            self.check()

    def test_command_is_read_only_and_returns_nonzero_for_incomplete_review(self):
        csv = self.folder / 'data' / 'coconut-cards.csv'
        write_cards(csv, [dict(self.card, id='coconut-998')])
        before = csv.read_bytes()
        path = self.folder / 'proposal.json'
        for status, expected in (('ready_for_review', 0), ('draft', 2)):
            with self.subTest(status=status):
                self.proposal['status'] = status
                path.write_text(json.dumps(self.proposal), encoding='utf-8')
                result = subprocess.run(
                    [sys.executable, '-m', 'coconut', '--root', str(self.folder),
                     'review-check', str(path)],
                    cwd=REPOSITORY, capture_output=True, text=True, encoding='utf-8',
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(csv.read_bytes(), before)
                if expected == 0:
                    self.assertIn('human approval', result.stdout)


if __name__ == '__main__':
    unittest.main()
