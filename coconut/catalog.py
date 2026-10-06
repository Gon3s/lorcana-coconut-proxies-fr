"""Pure catalogue parsing and non-destructive CSV refresh logic."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


CSV_COLUMNS = (
    "id", "name_en", "subtitle_en", "name_fr", "subtitle_fr",
    "effet_en", "effet_fr", "ref_image_detail", "ref_image_settings",
    "official_card_id", "ref_image_art_fr_hd",
)
SOURCE_COLUMNS = ("name_en", "subtitle_en", "ref_image_detail", "ref_image_settings")


def coconut_id(image_url: str) -> str:
    path = urlparse(image_url).path
    match = re.search(r"/coconut-cards/(\d{3})_[^/]+\.jpg$", path)
    if not match:
        raise ValueError(f"Cannot find a Coconut ID in {image_url!r}")
    return f"coconut-{match.group(1)}"


def normalize_label(value: str) -> str:
    value = value.replace("\u00ad", "").strip()
    value = value.strip('"“”')
    return " ".join(value.split())


def _by_id(cards: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for card in cards:
        identifier = coconut_id(card[key])
        if identifier in result:
            raise ValueError(f"Duplicate Coconut ID: {identifier}")
        result[identifier] = card
    return result


def source_rows(english_catalog: dict, french_catalog: dict) -> list[dict[str, str]]:
    """Import only EN labels from Coconut JSON; /fr labels are not localized."""
    english = english_catalog["coconut_cards"]
    french = _by_id(french_catalog["coconut_cards"], "card_detail_url")
    _by_id(english, "card_detail_url")  # Validate duplicate IDs.
    rows = []
    for card in english:
        identifier = coconut_id(card["card_detail_url"])
        if identifier not in french:
            raise ValueError(f"Missing French settings image for {identifier}")
        row = {column: "" for column in CSV_COLUMNS}
        row.update({
            "id": identifier,
            "name_en": normalize_label(card["name"]),
            "subtitle_en": normalize_label(card.get("subtitle", "")),
            "ref_image_detail": card["card_detail_url"],
            "ref_image_settings": french[identifier]["settings_thumbnail_url"],
        })
        rows.append(row)
    unexpected = set(french) - {row["id"] for row in rows}
    if unexpected:
        raise ValueError(f"French Coconut IDs missing in English catalogue: {sorted(unexpected)}")
    return rows


@dataclass(frozen=True)
class MergeResult:
    cards: list[dict[str, str]]
    added: list[str]
    changed: list[str]
    missing: list[str]


def merge_rows(existing: list[dict[str, str]], incoming: list[dict[str, str]]) -> MergeResult:
    old = _unique_rows(existing)
    new = _unique_rows(incoming)
    result = [dict(row) for row in existing]
    added = []
    changed = []
    for row in incoming:
        identifier = row["id"]
        if identifier not in old:
            result.append(dict(row))
            added.append(identifier)
        elif any(old[identifier][column] != row[column] for column in SOURCE_COLUMNS):
            changed.append(identifier)
    missing = [row["id"] for row in existing if row["id"] not in new]
    return MergeResult(result, added, changed, missing)


def _unique_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result = {}
    for row in rows:
        identifier = row["id"]
        if identifier in result:
            raise ValueError(f"Duplicate Coconut ID: {identifier}")
        result[identifier] = row
    return result


def read_cards(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(f"CSV columns must be: {', '.join(CSV_COLUMNS)}")
        rows = list(reader)
    _unique_rows(rows)
    if any(set(row) != set(CSV_COLUMNS) or None in row for row in rows):
        raise ValueError("Malformed CSV row")
    return rows


def write_cards(path: Path, rows: list[dict[str, str]]) -> None:
    _unique_rows(rows)
    for row in rows:
        if set(row) != set(CSV_COLUMNS):
            raise ValueError(f"Invalid CSV columns in {row.get('id', '<unknown>')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
