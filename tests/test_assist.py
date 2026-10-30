import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from coconut.assist import suggest_effects, validate_suggestion
from coconut.__main__ import main
from coconut.catalog import write_cards
from coconut.prepare import prepare_review


REPOSITORY = Path(__file__).resolve().parents[1]
IDENTIFIER = 'coconut-999'


class AssistTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        write_cards(self.root / 'data' / 'coconut-cards.csv', [])
        (self.root / 'data' / 'sources.lock.json').write_text(
            '{"schema":1,"cards":{},"files":{}}', encoding='utf-8')
        for name in ('lorcana-glossary.json',):
            (self.root / 'data' / name).write_bytes((REPOSITORY / 'data' / name).read_bytes())
        (self.root / 'prompts').mkdir()
        (self.root / 'prompts' / 'coconut-effects.md').write_bytes(
            (REPOSITORY / 'prompts' / 'coconut-effects.md').read_bytes())
        catalog = {'coconut_cards': [{
            'name': 'Synthetic test', 'subtitle': '',
            'card_detail_url': 'https://api.lorcana.ravensburger.com/coconut-cards/999_detail.jpg',
            'settings_thumbnail_url': 'https://api.lorcana.ravensburger.com/coconut-cards/999_settings.jpg',
        }]}
        def image(url):
            stream = io.BytesIO()
            size = (256, 256) if 'settings' in url else (1468, 2048)
            Image.new('RGB', size, 'navy').save(stream, 'JPEG')
            return stream.getvalue()
        self.proposal_path = prepare_review(
            self.root, IDENTIFIER, catalog, catalog, Path('outputs/reviews'), image)
        self.folder = self.proposal_path.parent
        self.answer = {'schema': 1, 'card_id': IDENTIFIER,
                       'effet_en': 'Pay 2 {cost} to exert chosen character.',
                       'effet_fr': 'Payez 2 {cost} pour épuiser un personnage choisi.',
                       'uncertainties': []}
        self.invocations = []
        self.runner = Mock(side_effect=self.run_cli)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def run_cli(self, command, **kwargs):
        self.invocations.append((command, kwargs))
        if '--version' in command:
            return subprocess.CompletedProcess(command, 0, 'codex-cli 0.153.2', '')
        if command[-2:] == ['login', 'status']:
            return subprocess.CompletedProcess(command, 0, '', 'Logged in using ChatGPT')
        path = Path(command[command.index('--output-last-message') + 1])
        path.write_text(json.dumps(self.answer, ensure_ascii=False), encoding='utf-8')
        return subprocess.CompletedProcess(command, 0)

    def suggest(self, **kwargs):
        return suggest_effects(self.root, self.proposal_path, runner=self.runner, **kwargs)

    def snapshot_production(self):
        return {path.name: path.read_bytes() for path in (self.root / 'data').iterdir()}

    def test_valid_response_is_a_separate_suggestion_and_never_an_approval(self):
        before = self.proposal_path.read_bytes()
        production = self.snapshot_production()
        path = self.suggest()
        record = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(record['state'], 'suggested')
        self.assertEqual(record['suggestion'], self.answer)
        self.assertEqual(self.proposal_path.read_bytes(), before)
        self.assertEqual(self.snapshot_production(), production)
        self.assertNotIn('approved', record)
        command, options = self.invocations[-1]
        self.assertEqual(command[command.index('--sandbox') + 1], 'read-only')
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--output-schema', command)
        self.assertIn('--image', command)
        self.assertIn('--ephemeral', command)
        self.assertFalse(options.get('shell', False))
        self.assertEqual(options['timeout'], 180)

    def test_manual_corrections_survive_multiple_attempts(self):
        proposal = json.loads(self.proposal_path.read_text(encoding='utf-8'))
        proposal['card']['effet_fr'] = 'Correction manuelle à conserver.'
        self.proposal_path.write_text(json.dumps(proposal), encoding='utf-8')
        before = self.proposal_path.read_bytes()
        first = self.suggest()
        second = self.suggest()
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())
        self.assertEqual(self.proposal_path.read_bytes(), before)

    def test_uncertainty_is_archived_but_does_not_succeed(self):
        self.answer['uncertainties'] = ['The target on the source image is unclear.']
        with self.assertRaisesRegex(ValueError, 'uncertaint'):
            self.suggest()
        results = list(self.folder.glob('codex-attempts/*/result.json'))
        self.assertEqual(len(results), 1)
        self.assertEqual(json.loads(results[0].read_text())['state'], 'needs_review')

    def test_invalid_response_fields_or_types_are_rejected(self):
        for field, value in (('schema', True), ('card_id', 'coconut-998'),
                             ('effet_en', ''), ('effet_fr', None), ('uncertainties', 'none')):
            with self.subTest(field=field):
                answer = copy.deepcopy(self.answer)
                answer[field] = value
                with self.assertRaises(ValueError):
                    validate_suggestion(answer, IDENTIFIER)
        self.answer['official_card_id'] = 'an invented association'
        with self.assertRaises(ValueError):
            validate_suggestion(self.answer, IDENTIFIER)

    def test_missing_or_changed_symbols_and_broken_markup_are_rejected(self):
        for french in ('Sans symbole.', 'Payez 2 {ink}.', 'Payez 2 {unknown}.', '**Broken'):
            with self.subTest(french=french):
                answer = dict(self.answer, effet_fr=french)
                with self.assertRaisesRegex(ValueError, 'symbol|markup'):
                    validate_suggestion(answer, IDENTIFIER)

    def test_invalid_json_preserves_the_proposal(self):
        before = self.proposal_path.read_bytes()
        def invalid(command, **kwargs):
            if 'exec' not in command:
                return self.run_cli(command, **kwargs)
            output = Path(command[command.index('--output-last-message') + 1])
            output.write_text('not JSON', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0)
        with self.assertRaisesRegex(ValueError, 'JSON'):
            suggest_effects(self.root, self.proposal_path, runner=invalid)
        self.assertEqual(self.proposal_path.read_bytes(), before)

    def test_duplicate_json_fields_are_not_silently_overridden(self):
        def duplicate(command, **kwargs):
            if 'exec' not in command:
                return self.run_cli(command, **kwargs)
            output = Path(command[command.index('--output-last-message') + 1])
            encoded = json.dumps(self.answer)
            output.write_text(encoded[:-1] + ', "effet_fr": "Overridden text 2 {cost}."}', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0)
        with self.assertRaisesRegex(ValueError, 'JSON'):
            suggest_effects(self.root, self.proposal_path, runner=duplicate)

    def test_timeout_leaves_an_explained_failed_attempt(self):
        def timeout(command, **kwargs):
            if 'exec' not in command:
                return self.run_cli(command, **kwargs)
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])
        with self.assertRaisesRegex(ValueError, 'timed out'):
            suggest_effects(self.root, self.proposal_path, runner=timeout, timeout=5)
        record = json.loads(next(self.folder.glob('codex-attempts/*/result.json')).read_text())
        self.assertEqual(record['state'], 'failed')

    def test_missing_codex_or_non_chatgpt_login_is_rejected_before_a_model_call(self):
        with self.assertRaisesRegex(ValueError, 'Codex.*not found'):
            suggest_effects(self.root, self.proposal_path, runner=Mock(side_effect=FileNotFoundError()))
        def api_login(command, **kwargs):
            if command[-2:] == ['login', 'status']:
                return subprocess.CompletedProcess(command, 0, 'Logged in using an API key', '')
            return self.run_cli(command, **kwargs)
        with self.assertRaisesRegex(ValueError, 'ChatGPT'):
            suggest_effects(self.root, self.proposal_path, runner=api_login)
        self.assertFalse((self.folder / 'codex-attempts').exists())

    def test_cli_error_does_not_echo_possible_credentials(self):
        def failure(command, **kwargs):
            if 'exec' not in command:
                return self.run_cli(command, **kwargs)
            return subprocess.CompletedProcess(command, 1, '', 'SENSITIVE_TEST_VALUE')
        with self.assertRaisesRegex(ValueError, 'Codex failed') as stopped:
            suggest_effects(self.root, self.proposal_path, runner=failure)
        self.assertNotIn('SENSITIVE_TEST_VALUE', str(stopped.exception))

    def test_changed_source_blocks_before_calling_codex(self):
        (self.folder / 'source-detail.jpg').write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError, 'local.*changed'):
            self.suggest()
        self.runner.assert_not_called()

    def test_proposal_edited_during_inference_is_not_given_a_successful_result(self):
        def edit(command, **kwargs):
            result = self.run_cli(command, **kwargs)
            if 'exec' in command:
                proposal = json.loads(self.proposal_path.read_text())
                proposal['card']['effet_fr'] = 'Correction pendant le traitement.'
                self.proposal_path.write_text(json.dumps(proposal), encoding='utf-8')
            return result
        with self.assertRaisesRegex(ValueError, 'changed'):
            suggest_effects(self.root, self.proposal_path, runner=edit)
        self.assertIn('Correction pendant', self.proposal_path.read_text())

    def test_ci_is_refused_and_no_api_key_is_passed_to_the_child(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}):
            with self.assertRaisesRegex(ValueError, 'manual|CI'):
                self.suggest()
        self.runner.assert_not_called()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'TEST_KEY', 'CODEX_API_KEY': 'TEST_KEY'}):
            self.suggest()
        for _, options in self.invocations:
            self.assertNotIn('OPENAI_API_KEY', options['env'])
            self.assertNotIn('CODEX_API_KEY', options['env'])

    def test_manual_command_reports_a_suggestion_and_blocks_uncertainty(self):
        arguments = ['coconut', '--root', str(self.root), 'codex-suggest', str(self.proposal_path)]
        with patch('coconut.assist.subprocess.run', side_effect=self.run_cli):
            with patch('sys.argv', arguments), redirect_stdout(io.StringIO()) as output:
                main()
        self.assertIn('suggestion', output.getvalue())
        self.answer['uncertainties'] = ['Synthetic review question']
        with patch('coconut.assist.subprocess.run', side_effect=self.run_cli):
            with patch('sys.argv', arguments), redirect_stderr(io.StringIO()) as errors:
                with self.assertRaises(SystemExit) as stopped:
                    main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertNotIn('Traceback', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
