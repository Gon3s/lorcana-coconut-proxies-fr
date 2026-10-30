"""Bounded downloads for the explicit preparation operation."""

import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


CATALOG_LIMIT = 32 * 1024 * 1024
IMAGE_LIMIT = 16 * 1024 * 1024
CATALOG_URLS = {
    language: f'https://api.lorcana.ravensburger.com/v3/catalog/{language}'
    for language in ('en', 'fr')
}


def validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'api.lorcana.ravensburger.com'
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('Preparation downloads require an official Ravensburger HTTPS URL')


class _OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def download_bytes(url: str, accept: str, limit: int) -> bytes:
    validate_download_url(url)
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 Coconut-review/1.0', 'Accept': accept})
    with build_opener(_OfficialRedirects()).open(request, timeout=30) as response:
        data = response.read(limit + 1)
    if not data or len(data) > limit:
        raise ValueError(f'Download is empty or exceeds the {limit}-byte limit')
    return data


def load_catalog(path: Path | None, language: str, fetch: bool) -> dict:
    if fetch:
        if path is not None:
            raise ValueError('Choose either --fetch or local catalogs, not both')
        data = download_bytes(CATALOG_URLS[language], 'application/json', CATALOG_LIMIT)
    else:
        if path is None:
            raise ValueError('Provide both --en and --fr, or use --fetch')
        with path.open('rb') as stream:
            data = stream.read(CATALOG_LIMIT + 1)
    if not data or len(data) > CATALOG_LIMIT:
        raise ValueError('Catalog is empty or exceeds the capture limit')
    catalog = json.loads(data)
    if not isinstance(catalog, dict):
        raise ValueError('Catalog must be a JSON object')
    return catalog
