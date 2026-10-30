import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.request import Request

from coconut.download import (
    CATALOG_LIMIT, CATALOG_URLS, _OfficialRedirects, download_bytes, load_catalog,
)


class DownloadTests(unittest.TestCase):
    def test_download_sets_timeout_headers_and_reads_only_up_to_the_limit(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'123'
        with patch('coconut.download.build_opener') as opened:
            opened.return_value.open.return_value = response
            self.assertEqual(download_bytes(CATALOG_URLS['en'], 'application/json', 4), b'123')
        request = opened.return_value.open.call_args.args[0]
        self.assertEqual(request.get_header('Accept'), 'application/json')
        self.assertTrue(request.get_header('User-agent'))
        self.assertEqual(opened.return_value.open.call_args.kwargs['timeout'], 30)
        response.read.assert_called_once_with(5)

    def test_empty_and_oversized_downloads_are_rejected(self):
        for data in (b'', b'12345'):
            with self.subTest(data=data):
                response = MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = data
                with patch('coconut.download.build_opener') as opened:
                    opened.return_value.open.return_value = response
                    with self.assertRaisesRegex(ValueError, 'empty|limit'):
                        download_bytes(CATALOG_URLS['en'], 'application/json', 4)

    def test_unofficial_urls_are_rejected_before_connecting(self):
        for url in (
            'http://api.lorcana.ravensburger.com/card.jpg',
            'https://example.com/card.jpg',
            'https://api.lorcana.ravensburger.com.example.com/card.jpg',
            'https://user@api.lorcana.ravensburger.com/card.jpg',
            'https://api.lorcana.ravensburger.com:444/card.jpg',
        ):
            with self.subTest(url=url), patch('coconut.download.build_opener') as opened:
                with self.assertRaises(ValueError):
                    download_bytes(url, 'image/jpeg', 20)
                opened.assert_not_called()

    def test_redirect_to_an_unofficial_host_is_rejected_before_following(self):
        with self.assertRaisesRegex(ValueError, 'official'):
            _OfficialRedirects().redirect_request(
                Request(CATALOG_URLS['en']), io.BytesIO(), 302, 'redirect', {},
                'https://example.com/card.jpg',
            )

    def test_catalog_download_uses_json_limit_and_rejects_invalid_json(self):
        with patch('coconut.download.download_bytes', return_value=b'{"coconut_cards": []}') as fetch:
            self.assertEqual(load_catalog(None, 'en', True), {'coconut_cards': []})
            fetch.assert_called_once_with(CATALOG_URLS['en'], 'application/json', CATALOG_LIMIT)
        for data in (b'not json', b'[]', b'null'):
            with self.subTest(data=data), patch('coconut.download.download_bytes', return_value=data):
                with self.assertRaises(ValueError):
                    load_catalog(None, 'en', True)

    def test_local_catalog_is_bounded_and_does_not_claim_a_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'en.json'
            path.write_bytes(b'{"coconut_cards": []}')
            with patch('coconut.download.download_bytes') as fetch:
                self.assertEqual(load_catalog(path, 'en', False), {'coconut_cards': []})
                fetch.assert_not_called()
            with patch('coconut.download.CATALOG_LIMIT', 4):
                with self.assertRaisesRegex(ValueError, 'limit'):
                    load_catalog(path, 'en', False)
            with self.assertRaises(ValueError):
                load_catalog(path, 'en', True)


if __name__ == '__main__':
    unittest.main()
