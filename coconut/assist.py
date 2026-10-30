"""Manual Codex suggestions, isolated from production and human corrections."""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from .prepare import verify_capture
from .typography import parse_word


TEXT_LIMIT = 8000
RESPONSE_LIMIT = 64 * 1024
SUGGESTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'schema': {'type': 'integer', 'enum': [1]},
        'card_id': {'type': 'string'},
        'effet_en': {'type': 'string', 'maxLength': TEXT_LIMIT},
        'effet_fr': {'type': 'string', 'maxLength': TEXT_LIMIT},
        'uncertainties': {'type': 'array', 'maxItems': 20,
                          'items': {'type': 'string', 'minLength': 1, 'maxLength': 1000}},
    },
    'required': ['schema', 'card_id', 'effet_en', 'effet_fr', 'uncertainties'],
}


def validate_suggestion(value: dict, identifier: str) -> None:
    """Enforce the local contract even if the CLI claims schema compliance."""
    if not isinstance(value, dict) or set(value) != set(SUGGESTION_SCHEMA['required']):
        raise ValueError('Invalid Codex response fields')
    if type(value['schema']) is not int or value['schema'] != 1 or value['card_id'] != identifier:
        raise ValueError('Invalid Codex schema or card ID')
    doubts = value['uncertainties']
    if (not isinstance(doubts, list) or len(doubts) > 20
            or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                   for item in doubts)):
        raise ValueError('Invalid Codex uncertainties')
    symbols = {}
    for field in ('effet_en', 'effet_fr'):
        text = value[field]
        if not isinstance(text, str) or len(text) > TEXT_LIMIT or (not text.strip() and not doubts):
            raise ValueError(f'Invalid or empty Codex {field}')
        symbols[field] = Counter(span.text for word in text.split() for span in parse_word(word)
                                 if span.kind == 'icon')
    if not doubts and symbols['effet_en'] != symbols['effet_fr']:
        raise ValueError('EN/FR rules symbol counts differ')


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _write_result(path: Path, value: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON field: {key}')
        result[key] = value
    return result


def _preflight(codex: str, runner, environment: dict) -> str:
    options = dict(capture_output=True, text=True, encoding='utf-8', errors='replace',
                   timeout=15, check=False, env=environment)
    try:
        version = runner([codex, '--version'], **options)
        login = runner([codex, 'login', 'status'], **options)
    except FileNotFoundError as error:
        raise ValueError('Codex executable not found; install it or use --codex') from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('Codex preflight failed or timed out') from error
    if version.returncode:
        raise ValueError('Codex version check failed')
    if login.returncode or 'Logged in using ChatGPT' not in ((login.stdout or '') + (login.stderr or '')):
        raise ValueError('Sign in with ChatGPT using codex login --device-auth')
    return (version.stdout or '').strip()


def suggest_effects(root: Path, proposal_path: Path, *, codex: str = 'codex',
                    model: str | None = None, timeout: int = 180,
                    runner=None) -> Path:
    """Record a separate suggestion; never edit proposal.json, the CSV or locks."""
    if any(os.environ.get(key, '').lower() not in ('', '0', 'false')
           for key in ('CI', 'GITHUB_ACTIONS', 'GITLAB_CI')):
        raise ValueError('ChatGPT assistance is a manual operation, unavailable in CI')
    if type(timeout) is not int or not 1 <= timeout <= 900:
        raise ValueError('Codex timeout must be between 1 and 900 seconds')
    root = root.resolve()
    proposal_path = proposal_path if proposal_path.is_absolute() else root / proposal_path
    proposal, receipt = verify_capture(root, proposal_path)
    proposal_path = proposal_path.resolve()
    if proposal['status'] != 'draft':
        raise ValueError('Codex assistance requires a draft; do not reset a prepared review')
    original = proposal_path.read_bytes()
    prompt = (root / 'prompts' / 'coconut-effects.md').read_text(encoding='utf-8')
    glossary = json.loads((root / 'data' / 'lorcana-glossary.json').read_text(encoding='utf-8'))
    if (not isinstance(glossary, dict) or type(glossary.get('schema')) is not int
            or glossary['schema'] != 1):
        raise ValueError('Invalid project glossary')
    context = {'proposal': proposal, 'glossary': glossary,
               'capture_sha256': hashlib.sha256(_json_bytes(receipt)).hexdigest()}
    environment = dict(os.environ)
    for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
        environment.pop(key, None)
    runner = runner or subprocess.run
    codex = str(Path(codex).expanduser())
    attempts = proposal_path.parent / 'codex-attempts'
    if attempts.is_symlink() or not attempts.resolve().is_relative_to(proposal_path.parent):
        raise ValueError('Unsafe Codex attempts directory')
    version = _preflight(codex, runner, environment)
    attempt = attempts / uuid4().hex
    attempt.mkdir(parents=True, exist_ok=False)
    # Attach a private snapshot of the verified source, rather than a mutable path.
    image_path = attempt / 'source-detail.jpg'
    image_path.write_bytes((proposal_path.parent / 'source-detail.jpg').read_bytes())
    input_bytes = _json_bytes(context)
    (attempt / 'input.json').write_bytes(input_bytes)
    (attempt / 'prompt.txt').write_bytes(prompt.encode('utf-8'))
    schema_path = attempt / 'response.schema.json'
    schema_path.write_bytes(_json_bytes(SUGGESTION_SCHEMA))
    answer_path = attempt / 'raw-response.json'
    result_path = attempt / 'result.json'
    metadata = {'schema': 1, 'input_sha256': hashlib.sha256(input_bytes).hexdigest(),
                'prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
                'response_schema_sha256': hashlib.sha256(schema_path.read_bytes()).hexdigest(),
                'codex_version': version, 'requested_model': model}
    _write_result(result_path, {**metadata, 'state': 'running'})
    command = [codex, '--ask-for-approval', 'never', 'exec', '--sandbox', 'read-only',
               '--ignore-user-config', '--skip-git-repo-check', '--ephemeral',
               '--config', 'web_search="disabled"', '--cd', str(attempt),
               '--image', str(image_path), '--output-schema', str(schema_path),
               '--output-last-message', str(answer_path)]
    if model:
        command.extend(['--model', model])
    command.append('-')
    try:
        completed = runner(command, input=prompt + '\n\nUNTRUSTED CONTEXT JSON:\n' + input_bytes.decode('utf-8'),
                           text=True, encoding='utf-8', timeout=timeout, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment)
        if completed.returncode:
            raise ValueError('Codex failed; check login, quota, connection and CLI compatibility')
        if answer_path.is_symlink() or not answer_path.is_file() or answer_path.stat().st_size > RESPONSE_LIMIT:
            raise ValueError('Missing or oversized Codex JSON response')
        try:
            answer = json.loads(answer_path.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError) as error:
            raise ValueError('Invalid Codex JSON response') from error
        validate_suggestion(answer, proposal['card']['id'])
        verify_capture(root, proposal_path)
        if proposal_path.read_bytes() != original:
            raise ValueError('Proposal changed during Codex inference; rerun against current corrections')
    except subprocess.TimeoutExpired as error:
        _write_result(result_path, {**metadata, 'state': 'failed', 'reason': 'timeout'})
        raise ValueError(f'Codex timed out; attempt saved at {result_path}') from error
    except (OSError, ValueError) as error:
        _write_result(result_path, {**metadata, 'state': 'failed', 'reason': str(error)})
        raise ValueError(f'{error}; attempt saved at {result_path}') from error
    state = 'needs_review' if answer['uncertainties'] else 'suggested'
    _write_result(result_path, {**metadata, 'state': state, 'suggestion': answer})
    if state == 'needs_review':
        raise ValueError(f'Codex reported uncertainties; review the attempt at {result_path}')
    return result_path
