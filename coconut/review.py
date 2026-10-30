"""Read-only checks for proposed cards, before human review and acceptance.

Candidate files belong to the proposal folder, not to the production source
lock. A successful check proves completeness and consistency, not fidelity of
the translation, image correspondence, or human approval.
"""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlparse

from .catalog import CSV_COLUMNS, coconut_id
from .typography import parse_word


PROPOSAL_FIELDS = {
    'schema', 'status', 'card', 'base_card', 'uncertainties',
    'match_evidence', 'sources', 'preview',
}
SOURCE_COLUMNS = {
    'detail': 'ref_image_detail',
    'settings': 'ref_image_settings',
    'art_fr_hd': 'ref_image_art_fr_hd',
}
PREVIEW_ROLES = {'card_fr', 'card_en', 'pdf_fr', 'pdf_en', 'page'}


def _fields(value: object, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f'{label} fields must be: {", ".join(sorted(expected))}')


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Missing or invalid {label}')


def _row(value: object, label: str) -> None:
    _fields(value, set(CSV_COLUMNS), label)
    for field, text in value.items():
        if not isinstance(text, str):
            raise ValueError(f'{label}.{field} must be a string')


def review_input_digest(proposal: dict) -> str:
    """Bind preview metadata to the exact proposed text, sources and baseline.

    This is an integrity link for a future trusted preview generator to write;
    it is neither a signature nor evidence of a human review.
    """
    inputs = {key: proposal[key] for key in (
        'card', 'base_card', 'sources', 'match_evidence',
    )}
    data = json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _artifact(folder: Path, record: dict, label: str) -> None:
    name = record['path']
    _text(name, f'{label}.path')
    if ('\\' in name or PureWindowsPath(name).drive
            or PurePosixPath(name).is_absolute()
            or '..' in PurePosixPath(name).parts):
        raise ValueError(f'Unsafe review path: {name}')
    root = folder.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Unsafe review path: {name}')
    expected = record['sha256']
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError(f'{label}: invalid SHA-256')
    if not path.is_file():
        raise ValueError(f'Missing review file: {name}')
    if path.stat().st_size == 0:
        raise ValueError(f'Empty review file: {name}')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError(f'Review file checksum changed: {name}')


def validate_review(proposal: dict, folder: Path, current_cards: list[dict]) -> None:
    """Reject incomplete/stale proposals without modifying files or CSV rows."""
    _fields(proposal, PROPOSAL_FIELDS, 'proposal')
    if type(proposal['schema']) is not int or proposal['schema'] != 1:
        raise ValueError('Unsupported review schema; expected integer 1')
    if proposal['status'] != 'ready_for_review':
        raise ValueError('Review status must be ready_for_review; a draft cannot pass')
    row = proposal['card']
    _row(row, 'card')
    # Reuse production requirements rather than maintain a second card contract.
    from .build import validate_rows

    validate_rows([row])
    for field in ('effet_en', 'effet_fr'):
        for word in row[field].split():
            parse_word(word)
    for field in ('ref_image_detail', 'ref_image_settings', 'ref_image_art_fr_hd'):
        url = urlparse(row[field])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError(f'{row["id"]}: invalid HTTPS URL in {field}')
    if any(coconut_id(row[field]) != row['id']
           for field in ('ref_image_detail', 'ref_image_settings')):
        raise ValueError(f'{row["id"]}: ID differs from detail/settings source reference')
    baseline = proposal['base_card']
    if baseline is not None:
        _row(baseline, 'base_card')
        if baseline['id'] != row['id']:
            raise ValueError('base_card ID differs from proposed card')
    existing = {card['id']: card for card in current_cards}
    if len(existing) != len(current_cards):
        raise ValueError('Duplicate Coconut ID in current CSV')
    if existing.get(row['id']) != baseline:
        raise ValueError(f'{row["id"]}: current CSV has changed; refresh the review baseline')
    uncertainties = proposal['uncertainties']
    if not isinstance(uncertainties, list) or any(
        not isinstance(item, str) or not item.strip() for item in uncertainties
    ):
        raise ValueError('uncertainties must be a list of non-empty strings')
    if uncertainties:
        raise ValueError(f'{row["id"]}: unresolved uncertainties: {"; ".join(uncertainties)}')
    _text(proposal['match_evidence'], 'match_evidence')
    _fields(proposal['sources'], set(SOURCE_COLUMNS), 'sources')
    for role, column in SOURCE_COLUMNS.items():
        record = proposal['sources'][role]
        _fields(record, {'path', 'sha256', 'url'}, f'sources.{role}')
        if record['url'] != row[column]:
            raise ValueError(f'{role}: source URL differs from proposed CSV')
        _artifact(folder, record, f'sources.{role}')
    preview = proposal['preview']
    _fields(preview, {'inputs_sha256', 'files'}, 'preview')
    if preview['inputs_sha256'] != review_input_digest(proposal):
        raise ValueError(f'{row["id"]}: preview is stale; rebuild after changing inputs')
    _fields(preview['files'], PREVIEW_ROLES, 'preview.files')
    for role, record in preview['files'].items():
        _fields(record, {'path', 'sha256'}, f'preview.{role}')
        _artifact(folder, record, f'preview.{role}')
