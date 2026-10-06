import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from coconut.sources import create_lock, sync_sources, verify_lock


class SourceTests(unittest.TestCase):
    def test_lock_detects_changed_or_missing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'assets' / 'a.jpg').write_bytes(b'card')
            lock = create_lock(root, {'coconut-001': {'detail': 'assets/a.jpg', 'art_fr_hd': 'assets/a.jpg'}})
            self.assertEqual(lock['files']['assets/a.jpg'], hashlib.sha256(b'card').hexdigest())
            verify_lock(root, lock)
            (root / 'assets' / 'a.jpg').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'assets/a.jpg'):
                verify_lock(root, lock)

    def test_paths_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Unsafe source path'):
                create_lock(Path(directory), {'coconut-001': {'detail': '../outside.jpg'}})

    def test_sync_requires_review_before_replacing_a_pinned_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            picture = io.BytesIO()
            Image.new('RGB', (1468, 2048), '#123456').save(picture, format='JPEG')
            row = {'id': 'coconut-001', 'official_card_id': '2',
                   'ref_image_detail': 'https://host/detail.jpg',
                   'ref_image_settings': 'https://host/settings.jpg',
                   'ref_image_art_fr_hd': 'https://host/art.jpg'}
            sync_sources(root, [row], lambda _: picture.getvalue())
            picture2 = io.BytesIO()
            Image.new('RGB', (1468, 2048), '#654321').save(picture2, format='JPEG')
            with self.assertRaisesRegex(ValueError, 'changed detail image'):
                sync_sources(root, [row], lambda _: picture2.getvalue())
            verify_lock(root, __import__('json').loads((root / 'data/sources.lock.json').read_text()))
