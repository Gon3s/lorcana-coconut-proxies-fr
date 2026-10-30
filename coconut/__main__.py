"""Command-line catalogue, build and proposal review operations."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from .catalog import SOURCE_COLUMNS, merge_rows, read_cards, source_rows, write_cards
from .check import format_check_summary, review_manifest


CATALOG_URLS = {
    "en": "https://api.lorcana.ravensburger.com/v3/catalog/en",
    "fr": "https://api.lorcana.ravensburger.com/v3/catalog/fr",
}


def _fetch_bytes(url: str, accept: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": accept})
    with urlopen(request, timeout=30) as response:
        return response.read()


def _json_source(path: str | None, locale: str, fetch: bool) -> dict:
    if fetch:
        return json.loads(_fetch_bytes(CATALOG_URLS[locale], "application/json"))
    if not path:
        raise ValueError(f"Provide --{locale} or --fetch")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _official_changes(previous: list[dict[str, str]], french: dict) -> dict:
    official = {str(card["culture_invariant_id"]): card
                for category in french["cards"].values() for card in category}
    changes = {}
    for row in previous:
        key = row["official_card_id"]
        if not key:
            continue
        card = official.get(key)
        if card is None:
            changes[row["id"]] = {"status": "missing_official_card", "official_card_id": key}
            continue
        variants = card.get("variants", [])
        regular = next((variant.get("detail_image_url", "") for variant in variants
                        if variant.get("variant_id") == "Regular"), "")
        observed = {"name_fr": card["name"], "subtitle_fr": card.get("subtitle", ""),
                    "ref_image_art_fr_hd": regular}
        differences = {field: {"previous": row[field], "incoming": value}
                       for field, value in observed.items() if row[field] != value}
        if differences:
            changes[row["id"]] = differences
    return changes


def import_catalog(root: Path, english: dict, french: dict,
                   image_hashes: dict[str, str] | None = None,
                   persist: bool = True) -> dict:
    csv_path = root / "data" / "coconut-cards.csv"
    previous = read_cards(csv_path) if csv_path.exists() else []
    incoming = source_rows(english, french)
    merged = merge_rows(previous, incoming)
    old_by_id = {row["id"]: row for row in previous}
    new_by_id = {row["id"]: row for row in incoming}
    changes = {}
    for identifier in merged.changed:
        changes[identifier] = {
            column: {"previous": old_by_id[identifier][column], "incoming": new_by_id[identifier][column]}
            for column in SOURCE_COLUMNS
            if old_by_id[identifier][column] != new_by_id[identifier][column]
        }
    image_changes = {}
    if image_hashes is not None:
        lock_path = root / "data" / "sources.lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {"cards": {}, "files": {}}
        for row in incoming:
            identifier = row["id"]
            pinned = lock["cards"].get(identifier, {}).get("detail")
            if pinned and image_hashes[row["ref_image_detail"]] != lock["files"][pinned]:
                image_changes[identifier] = {"url": row["ref_image_detail"],
                                             "pinned_sha256": lock["files"][pinned],
                                             "incoming_sha256": image_hashes[row["ref_image_detail"]]}
    if persist and (merged.added or not csv_path.exists()):
        write_cards(csv_path, merged.cards)
    official_changes = _official_changes(previous, french) if "cards" in french else {}
    return {"added": merged.added, "changed": changes, "detail_image_changed": image_changes,
            "detail_images_checked": image_hashes is not None,
            "official_changes": official_changes, "missing": merged.missing,
            "review_required": bool(merged.added or changes or image_changes or official_changes or merged.missing)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or refresh Coconut proxies")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    imported = commands.add_parser("import", help="Refresh CSV without replacing translations or EN changes")
    imported.add_argument("--en", help="Local English catalog JSON")
    imported.add_argument("--fr", help="Local French catalog JSON")
    imported.add_argument("--fetch", action="store_true", help="Download both catalogs from Ravensburger")
    imported.add_argument("--check-images", action="store_true", help="Compare remote detailed JPEGs with the pinned hashes")
    imported.add_argument("--report", type=Path, default=Path("import-report.json"))
    checking = commands.add_parser("check", help="Compare current catalogs without changing the CSV")
    checking.add_argument("--en", help="Local English catalog JSON")
    checking.add_argument("--fr", help="Local French catalog JSON")
    checking.add_argument("--fetch", action="store_true", help="Download both catalogs from Ravensburger")
    checking.add_argument("--report", type=Path, default=Path("check-report.json"))
    checking.add_argument("--summary", type=Path, help="Write a Markdown summary")
    checking.add_argument("--review-manifest", type=Path, help="Write source metadata for new cards")
    building = commands.add_parser("build", help="Build site from pinned local sources")
    building.add_argument("--out", type=Path, default=Path("dist"))
    syncing = commands.add_parser("sync-sources", help="Download and lock images named by the reviewed CSV")
    syncing.add_argument("--accept-changes", action="store_true", help="Replace changed pinned images after review")
    reviewing = commands.add_parser("review-check", help="Check a complete proposal before human review (read-only)")
    reviewing.add_argument("proposal", type=Path, help="Path to proposal.json, relative to --root or absolute")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "review-check":
        from .review import validate_review

        path = args.proposal if args.proposal.is_absolute() else root / args.proposal
        try:
            proposal = json.loads(path.read_text(encoding="utf-8"))
            rows = read_cards(root / "data" / "coconut-cards.csv")
            validate_review(proposal, path.parent, rows)
        except (OSError, ValueError) as error:
            parser.error(f"Review not ready: {error}")
        print(f"{proposal['card']['id']}: ready for human review; not human approval.")
    elif args.command == "import":
        english = _json_source(args.en, "en", args.fetch)
        french = _json_source(args.fr, "fr", args.fetch)
        image_hashes = None
        if args.fetch or args.check_images:
            image_hashes = {}
            for row in source_rows(english, french):
                url = row["ref_image_detail"]
                image_hashes[url] = hashlib.sha256(_fetch_bytes(url, "image/jpeg")).hexdigest()
        report = import_catalog(root, english, french, image_hashes)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Import report: {args.report}")
        print(f"Added: {len(report['added'])}, EN changes: {len(report['changed'])}, "
              f"image changes: {len(report['detail_image_changed'])}, "
              f"FR official changes: {len(report['official_changes'])}, missing: {len(report['missing'])}")
    elif args.command == "check":
        english = _json_source(args.en, "en", args.fetch)
        french = _json_source(args.fr, "fr", args.fetch)
        report = import_catalog(root, english, french, persist=False)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.review_manifest:
            manifest = review_manifest(report, english, french)
            args.review_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
        summary = format_check_summary(report, english, french)
        if args.summary:
            args.summary.write_text(summary, encoding="utf-8")
        print(summary)
    elif args.command == "build":
        from .build import build_site

        destination = args.out if args.out.is_absolute() else root / args.out
        build_site(root, destination)
        print(f"Built: {destination}")
    elif args.command == "sync-sources":
        from .sources import sync_sources

        rows = read_cards(root / "data" / "coconut-cards.csv")
        def fetch_bytes(url):
            return _fetch_bytes(url, "image/jpeg")
        lock = sync_sources(root, rows, fetch_bytes, args.accept_changes)
        print(f"Pinned {len(lock['files'])} source images")


if __name__ == "__main__":
    main()
