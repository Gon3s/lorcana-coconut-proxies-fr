"""Pinned local image sources used for reproducible builds."""

import hashlib
import io
import json
from datetime import date
from pathlib import Path

from PIL import Image


def _safe_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe source path: {name}")
    return path


def create_lock(root: Path, cards: dict[str, dict[str, str]]) -> dict:
    files = {}
    for paths in cards.values():
        for name in paths.values():
            if not name:
                continue
            path = _safe_path(root, name)
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"schema": 1, "cards": cards, "files": dict(sorted(files.items()))}


def verify_lock(root: Path, lock: dict) -> None:
    if lock.get("schema") != 1:
        raise ValueError("Unsupported source lock schema")
    for name, expected in lock["files"].items():
        path = _safe_path(root, name)
        if not path.is_file():
            raise ValueError(f"Missing locked source: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Source checksum changed: {name}")
    for identifier, paths in lock["cards"].items():
        for role in ("detail", "art_fr_hd"):
            name = paths.get(role)
            if not name or name not in lock["files"]:
                raise ValueError(f"Missing locked {role} for {identifier}")


def sync_sources(root: Path, rows: list[dict[str, str]], fetch_bytes,
                 accept_changes: bool = False) -> dict:
    """Stage all source downloads, then pin them only after successful validation."""
    staged = {}
    cards = {}
    refs = {}
    for row in rows:
        identifier = row["id"]
        cards[identifier] = {}
        refs[identifier] = {field: row[field] for field in
                            ("ref_image_detail", "ref_image_settings", "ref_image_art_fr_hd", "official_card_id")}
        for role, field in (("detail", "ref_image_detail"), ("art_fr_hd", "ref_image_art_fr_hd")):
            url = row[field]
            if not url:
                raise ValueError(f"{identifier}: missing {field}")
            name = f"assets/source/{identifier}-{role}.jpg"
            data = fetch_bytes(url)
            try:
                with Image.open(io.BytesIO(data)) as image:
                    if image.size != (1468, 2048):
                        raise ValueError(f"{identifier}: {role} must be 1468 × 2048 px")
                    image.verify()
            except OSError as error:
                raise ValueError(f"{identifier}: invalid {role} image") from error
            path = root / name
            if path.exists() and path.read_bytes() != data and not accept_changes:
                raise ValueError(f"{identifier}: changed {role} image; rerun with --accept-changes after review")
            staged[name] = data
            cards[identifier][role] = name
    for name, data in staged.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    lock_path = root / "data" / "sources.lock.json"
    previous = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    lock = create_lock(root, cards)
    lock["refs"] = refs
    if "catalog_sha256" in previous:
        lock["catalog_sha256"] = previous["catalog_sha256"]
    lock["verified_at"] = date.today().isoformat()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock
