import tempfile
import unittest
from pathlib import Path

from coconut.catalog import (
    CSV_COLUMNS,
    coconut_id,
    merge_rows,
    normalize_label,
    read_cards,
    source_rows,
    write_cards,
)


def coconut_card(number, name, subtitle, locale):
    return {
        "name": name,
        "subtitle": subtitle,
        "card_detail_url": f"https://example.test/images/{locale}/coconut-cards/{number:03d}_detail.jpg",
        "settings_thumbnail_url": f"https://example.test/images/{locale}/coconut-cards/{number:03d}_settings.jpg",
    }


class CatalogTests(unittest.TestCase):
    def test_ids_and_labels_are_stable(self):
        self.assertEqual(coconut_id("https://host/coconut-cards/002_hash.jpg"), "coconut-002")
        self.assertEqual(normalize_label('  "Poca\u00adhontas"  '), "Pocahontas")
        with self.assertRaises(ValueError):
            coconut_id("https://host/no-id.jpg")

    def test_fr_coconut_json_is_not_trusted_as_a_translation(self):
        english = {"coconut_cards": [coconut_card(2, "Moana", '"Curious Explorer"', "en")]}
        french = {"coconut_cards": [coconut_card(2, "Moana", '"Curious Explorer"', "fr")]}
        rows = source_rows(english, french)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name_en"], "Moana")
        self.assertEqual(rows[0]["subtitle_en"], "Curious Explorer")
        self.assertEqual(rows[0]["name_fr"], "")
        self.assertEqual(rows[0]["ref_image_detail"], english["coconut_cards"][0]["card_detail_url"])
        self.assertEqual(rows[0]["ref_image_settings"], french["coconut_cards"][0]["settings_thumbnail_url"])

    def test_refresh_preserves_translations_and_reports_source_changes(self):
        previous = {key: "" for key in CSV_COLUMNS}
        previous.update({
            "id": "coconut-002", "name_en": "Ariel", "subtitle_en": "Spectacular Singer",
            "name_fr": "ARIEL", "subtitle_fr": "Chanteuse exceptionnelle",
            "effet_en": "Old English effect", "effet_fr": "Effet français, relu.",
            "ref_image_detail": "https://host/coconut-cards/002_old.jpg",
            "ref_image_settings": "https://host/coconut-cards/002_settings.jpg",
        })
        incoming = [
            {**previous, "ref_image_detail": "https://host/coconut-cards/002_new.jpg", "effet_fr": ""},
            {**{key: "" for key in CSV_COLUMNS}, "id": "coconut-003", "name_en": "Stitch"},
        ]
        result = merge_rows([previous], incoming)
        self.assertEqual(result.cards[0], previous)
        self.assertEqual(result.cards[0]["effet_fr"], "Effet français, relu.")
        self.assertEqual(result.added, ["coconut-003"])
        self.assertEqual(result.changed, ["coconut-002"])
        self.assertEqual(result.missing, [])
        self.assertEqual(len(result.cards), 2)

    def test_removed_api_card_is_reported_and_not_deleted(self):
        previous = {key: "" for key in CSV_COLUMNS}
        previous["id"] = "coconut-001"
        result = merge_rows([previous], [])
        self.assertEqual(result.cards, [previous])
        self.assertEqual(result.missing, ["coconut-001"])

    def test_csv_round_trip_keeps_french_punctuation(self):
        row = {key: "" for key in CSV_COLUMNS}
        row.update({"id": "coconut-002", "name_fr": "Vaiana", "effet_fr": 'Piochez une carte, puis dites « oui ».\nFin.'})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cards.csv"
            write_cards(path, [row])
            self.assertEqual(read_cards(path), [row])


if __name__ == "__main__":
    unittest.main()
