import subprocess
import tempfile
import unittest
from pathlib import Path


class ReviewTrackingTests(unittest.TestCase):
    def test_review_manifest_is_trackable_but_local_report_is_ignored(self):
        ignore_rules = (Path(__file__).resolve().parents[1] / '.gitignore').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '--quiet', directory], check=True)
            (root / '.gitignore').write_bytes(ignore_rules)
            for path, ignored in [('pending-coconuts.json', True),
                                  ('reviews/pending-coconuts.json', False),
                                  ('outputs/reviews/coconut-030/proposal.json', True),
                                  ('reviews/coconut-030/proposal.json', False)]:
                with self.subTest(path=path):
                    result = subprocess.run(
                        ['git', '-C', directory, 'check-ignore', '--no-index', '-q', path],
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0 if ignored else 1)
