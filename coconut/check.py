"""Human-readable summary for a read-only Coconut catalogue check."""

from .catalog import SOURCE_COLUMNS, source_rows


def review_manifest(report: dict, english: dict, french: dict) -> dict:
    """Capture source metadata without claiming translations or official matches."""
    added = set(report["added"])
    fields = ("id", *SOURCE_COLUMNS)
    cards = [{field: row[field] for field in fields}
             for row in source_rows(english, french) if row["id"] in added]
    if {card["id"] for card in cards} != added:
        raise ValueError("New card IDs are missing from the catalog")
    return {"schema": 1, "cards": cards}


def format_check_summary(report: dict, english: dict, french: dict) -> str:
    incoming = {row["id"]: row for row in source_rows(english, french)}
    added = report["added"]
    lines = ["# Contrôle du catalogue Coconut", ""]
    if added:
        count = len(added)
        lines.append(f"## {count} nouvelle carte{'s' if count > 1 else ''} à relire")
        lines.append("")
        for identifier in added:
            card = incoming[identifier]
            title = " — ".join(part for part in (card["name_en"], card["subtitle_en"]) if part)
            lines.append(f"- **{identifier}** : {title}")
    else:
        lines.append("## Aucune nouvelle carte Coconut")
    lines.extend(["", "| Autres changements | Nombre / statut |", "| --- | ---: |"])
    for label, key in (
        ("Données EN ou références", "changed"),
        ("Images détaillées", "detail_image_changed"),
        ("Cartes officielles FR", "official_changes"),
        ("Cartes absentes du catalogue", "missing"),
    ):
        value = ("Non vérifiées" if key == "detail_image_changed"
                 and not report.get("detail_images_checked", False) else str(len(report[key])))
        lines.append(f"| {label} | {value} |")
    lines.extend(["", "Le rapport JSON contient les identifiants et les valeurs à comparer.", ""])
    return "\n".join(lines)
