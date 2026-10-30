"""Capture immutable candidate sources without accepting them into production."""

import hashlib
import io
import json
import os
import platform
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, __version__ as pillow_version

from .catalog import CSV_COLUMNS, SOURCE_COLUMNS, coconut_id, normalize_label, read_cards, source_rows
from .download import CATALOG_LIMIT, IMAGE_LIMIT, validate_download_url
from .review import PROPOSAL_FIELDS, SOURCE_COLUMNS as REVIEW_SOURCE_COLUMNS


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _record(name: str, data: bytes) -> dict:
    return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}


def _official_pair(english: dict, french: dict, identifier: str) -> dict | None:
    if not identifier:
        return None
    pair = {}
    for language, catalog in (('en', english), ('fr', french)):
        matches = [card for category in catalog['cards'].values() for card in category
                   if str(card['culture_invariant_id']) == identifier]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous {language} official card: {identifier}')
        pair[language] = matches[0]
    return pair


def _regular_art(card: dict) -> str:
    matches = [variant['detail_image_url'] for variant in card['variants']
               if variant['variant_id'] == 'Regular']
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous Regular art for the official card')
    return matches[0]


def _image(data: bytes, role: str) -> None:
    try:
        if not data or len(data) > IMAGE_LIMIT:
            raise ValueError('empty or oversized source')
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'JPEG':
                raise ValueError('source must be JPEG')
            if role == 'settings':
                width, height = image.size
                if width != height or not 1 <= width <= 2048:
                    raise ValueError('settings must be square and at most 2048 px')
            elif image.size != (1468, 2048):
                raise ValueError('source must be 1468 × 2048 px')
            image.load()  # JPEG verify() alone does not detect truncated pixel data.
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise ValueError(f'Invalid {role} image: {error}') from error


def _resume(folder: Path, selection: dict, baseline: dict | None, sources: dict) -> Path:
    try:
        receipt = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
        proposal = json.loads((folder / 'proposal.json').read_text(encoding='utf-8'))
        if (not isinstance(receipt, dict) or type(receipt.get('schema')) is not int
                or receipt['schema'] != 1):
            raise ValueError('Unmanaged review folder')
        if receipt['base_card'] != baseline:
            raise ValueError('CSV has changed; reconcile corrections in a new output folder')
        if receipt['selection'] != selection:
            raise ValueError('Selected catalog source changed; use a new output folder')
        if (not isinstance(proposal, dict) or set(proposal) != PROPOSAL_FIELDS
                or type(proposal['schema']) is not int or proposal['schema'] != 1
                or proposal['status'] not in ('draft', 'ready_for_review')
                or not isinstance(proposal['card'], dict)
                or set(proposal['card']) != set(CSV_COLUMNS)
                or proposal['card']['id'] != selection['source_row']['id']
                or proposal['base_card'] != baseline
                or proposal['sources'] != receipt['sources']):
            raise ValueError('Proposal no longer matches its capture; use a new output folder')
        if any(proposal['card'][REVIEW_SOURCE_COLUMNS[role]] != record['url']
               for role, record in sources.items()):
            raise ValueError('Proposal source references changed; use a new output folder')
        # Read only fixed, captured filenames; never follow a user-provided path.
        records = {**receipt['sources'], **receipt['catalogs']}
        expected_paths = {role: f'source-{role}.jpg' for role in sources}
        expected_paths.update({language: f'catalog-{language}.json' for language in ('en', 'fr')})
        if set(records) != set(expected_paths):
            raise ValueError('Invalid capture file roles')
        for role, record in records.items():
            path = folder / expected_paths[role]
            if record['path'] != expected_paths[role] or path.is_symlink():
                raise ValueError('Invalid captured path')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != record['sha256']:
                raise ValueError(f'Captured local file changed: {path.name}')
        if receipt['sources'] != sources:
            raise ValueError('Remote source image changed; use a new output folder')
    except (KeyError, TypeError, OSError) as error:
        raise ValueError(f'Existing review folder is incomplete or unmanaged: {folder.name}') from error
    return folder / 'proposal.json'


def _changes(root: Path, source: dict, baseline: dict | None, sources: dict) -> dict:
    fields = {} if baseline is None else {
        field: {'previous': baseline[field], 'incoming': source[field]}
        for field in SOURCE_COLUMNS if source[field] != baseline[field]
    }
    lock = json.loads((root / 'data' / 'sources.lock.json').read_text(encoding='utf-8'))
    if (not isinstance(lock, dict) or type(lock.get('schema')) is not int
            or lock['schema'] != 1 or not isinstance(lock.get('cards'), dict)
            or not isinstance(lock.get('files'), dict)):
        raise ValueError('Invalid published source lock')
    pinned = lock.get('cards', {}).get(source['id'], {})
    if (not isinstance(pinned, dict)
            or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                   for value in lock['files'].values())):
        raise ValueError('Invalid published source lock entries')
    images = {}
    for role, record in sources.items():
        previous = lock.get('files', {}).get(pinned.get(role))
        if previous and previous != record['sha256']:
            images[role] = {'previous': previous, 'incoming': record['sha256']}
    return {'fields': fields, 'images': images}


def verify_capture(root: Path, proposal_path: Path) -> tuple[dict, dict]:
    """Verify a local capture and its current CSV baseline, without fetching."""
    root = root.resolve()
    path = proposal_path if proposal_path.is_absolute() else root / proposal_path
    if (path.name != 'proposal.json' or path.is_symlink() or path.parent.is_symlink()
            or not path.resolve().is_relative_to(root / 'outputs')):
        raise ValueError('Expected a captured proposal.json under repository outputs/')
    try:
        receipt = json.loads((path.parent / 'capture.json').read_text(encoding='utf-8'))
        identifier = receipt['selection']['source_row']['id']
        current = {row['id']: row for row in read_cards(root / 'data' / 'coconut-cards.csv')}
        _resume(path.parent, receipt['selection'], current.get(identifier), receipt['sources'])
        proposal = json.loads(path.read_text(encoding='utf-8'))
        if any(not isinstance(value, str) for value in proposal['card'].values()):
            raise ValueError('Captured card fields must be strings')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Invalid captured proposal or receipt') from error
    return proposal, receipt


def prepare_review(root: Path, identifier: str, english: dict, french: dict,
                   output: Path, fetch_image, *, official_card_id: str = '',
                   catalog_origins: dict | None = None) -> Path:
    """Create a complete capture atomically, or verify an existing one read-only.

    An explicitly selected official ID proposes a match; it does not approve it.
    The injected image downloader keeps ordinary tests deterministic and offline.
    """
    if not re.fullmatch(r'coconut-\d{3}', identifier):
        raise ValueError(f'Invalid Coconut ID: {identifier}')
    root = root.resolve()
    output = output if output.is_absolute() else root / output
    output = output.resolve()
    if not output.is_relative_to(root / 'outputs'):
        raise ValueError('Candidate dossiers must stay under the repository outputs directory')
    folder = output / identifier
    if folder.is_symlink():
        raise ValueError('Candidate outputs must not be symbolic links')
    try:
        candidates = {row['id']: row for row in source_rows(english, french)}
        if identifier not in candidates:
            raise ValueError(f'Unknown Coconut ID: {identifier}')
        source = candidates[identifier]
        if coconut_id(source['ref_image_settings']) != identifier:
            raise ValueError(f'{identifier}: ID differs from settings source reference')
        current = {row['id']: row for row in read_cards(root / 'data' / 'coconut-cards.csv')}
        baseline = current.get(identifier)
        if baseline and official_card_id and official_card_id != baseline['official_card_id']:
            raise ValueError('Existing official association differs; review it separately')
        chosen = official_card_id or (baseline['official_card_id'] if baseline else '')
        pair = _official_pair(english, french, chosen)
        selection = {'source_row': source, 'official': pair}
        row = dict(baseline if baseline is not None else source)
        for field in ('ref_image_detail', 'ref_image_settings'):
            row[field] = source[field]
        if pair and baseline is None:
            row.update(official_card_id=chosen,
                       name_fr=normalize_label(pair['fr']['name']),
                       subtitle_fr=normalize_label(pair['fr'].get('subtitle', '')),
                       ref_image_art_fr_hd=_regular_art(pair['fr']))
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f'Invalid EN/FR catalog or CSV data for {identifier}') from error
    urls = {'detail': row['ref_image_detail'], 'settings': row['ref_image_settings']}
    if row['ref_image_art_fr_hd']:
        urls['art_fr_hd'] = row['ref_image_art_fr_hd']
    for url in urls.values():
        validate_download_url(url)
    staged = {}
    records = {}
    for role, url in urls.items():
        data = fetch_image(url)
        _image(data, role)
        name = f'source-{role}.jpg'
        staged[name] = data
        records[role] = {**_record(name, data), 'url': url}
    if folder.exists():
        return _resume(folder, selection, baseline, records)
    catalogs = {}
    for language, catalog in (('en', english), ('fr', french)):
        name = f'catalog-{language}.json'
        data = _json_bytes(catalog)
        if len(data) > CATALOG_LIMIT:
            raise ValueError(f'{language} catalog exceeds the capture limit')
        staged[name] = data
        catalogs[language] = {
            **_record(name, data), 'origin': (catalog_origins or {}).get(language, 'provided-json'),
        }
    proposal = {
        'schema': 1, 'status': 'draft', 'card': row, 'base_card': baseline,
        'uncertainties': [
            'Transcribe or recheck the EN effect against the candidate Coconut image.',
            'Translate or recheck the FR effect and Lorcana symbols.',
            'Confirm the official match and compare candidate source images.',
            'Generate and inspect the FR/EN card, page and PDF previews.',
        ],
        'match_evidence': '', 'sources': records, 'preview': {},
    }
    receipt = {
        'schema': 1, 'selection': selection, 'base_card': baseline,
        'sources': records, 'catalogs': catalogs,
        'changes_against_published': _changes(root, source, baseline, records),
        'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'tools': {'python': platform.python_version(), 'pillow': pillow_version},
    }
    staged['proposal.json'] = _json_bytes(proposal)
    staged['capture.json'] = _json_bytes(receipt)
    output.mkdir(parents=True, exist_ok=True)
    # All downloads and validation finish before a target dossier becomes visible.
    with tempfile.TemporaryDirectory(prefix=f'.{identifier}-', dir=output) as temporary:
        staging = Path(temporary)
        for name, data in staged.items():
            (staging / name).write_bytes(data)
        os.rename(staging, folder)
    return folder / 'proposal.json'
