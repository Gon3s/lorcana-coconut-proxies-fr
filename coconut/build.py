"""Deterministic Coconut card composition and printable site generation."""

import html
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .catalog import read_cards
from .sources import verify_lock
from .typography import draw_rule_lines, layout_rules


CARD_SIZE = (1468, 2048)
REQUIRED = ("name_en", "name_fr", "effet_en", "effet_fr", "ref_image_detail",
            "ref_image_settings", "ref_image_art_fr_hd", "official_card_id")


def validate_rows(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("No Coconut cards in CSV")
    identifiers = set()
    for row in rows:
        identifier = row["id"]
        if not re.fullmatch(r"coconut-\d{3}", identifier):
            raise ValueError(f"Invalid Coconut ID: {identifier}")
        if identifier in identifiers:
            raise ValueError(f"Duplicate Coconut ID: {identifier}")
        identifiers.add(identifier)
        for key in REQUIRED:
            if not row[key].strip():
                raise ValueError(f"{identifier}: missing {key}")


def _face(fonts: Path, weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(fonts / f"BarlowCondensed-{weight}.ttf", size)


def _fit(draw: ImageDraw.ImageDraw, text: str, fonts: Path, weight: str,
         width: int, maximum: int, minimum: int) -> ImageFont.FreeTypeFont:
    for size in range(maximum, minimum - 1, -1):
        face = _face(fonts, weight, size)
        if draw.textlength(text, font=face) <= width:
            return face
    raise ValueError(f"Text too wide: {text}")


def _wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont,
          width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=face) <= width:
                current = candidate
            elif current:
                lines.append(current)
                current = word
            else:
                raise ValueError(f"Word too wide: {word}")
        lines.append(current)
    return lines


def _black_cost_silhouette(source: Image.Image) -> set[tuple[int, int]]:
    """Keep the blank black Coconut cost emblem when replacing the artwork."""
    pixels = source.load()
    seen = set()
    queue = [(110, 120)]
    while queue:
        x, y = queue.pop()
        if (x, y) in seen or not (0 <= x < 305 and 65 <= y < 310):
            continue
        if max(pixels[x, y]) > 42:
            continue
        seen.add((x, y))
        queue.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    if len(seen) < 12000:
        return set()
    # The black emblem touches the source card's black border. Flood fill alone
    # would preserve a rectangular patch over the new full-color illustration.
    return {(x, y) for x, y in seen
            if ((x - 105) / 185) ** 2 + ((y - 105) / 185) ** 2 <= 1}


def compose_card(row: dict[str, str], detail_path: Path, art_path: Path,
                 fonts: Path, language: str = "fr") -> Image.Image:
    if language not in ("fr", "en"):
        raise ValueError(f"Unsupported language: {language}")
    with Image.open(detail_path) as image:
        source = image.convert("RGB")
    with Image.open(art_path) as image:
        art = image.convert("RGB")
    if source.size != CARD_SIZE or art.size != CARD_SIZE:
        raise ValueError(f"{row['id']}: source images must be 1468 × 2048 px")
    output = source.copy()
    # Standard card art ends above its title band; extend only the artwork.
    painted_art = art.crop((61, 68, 1409, 1050)).resize((1348, 1032), Image.Resampling.LANCZOS)
    output.paste(painted_art, (61, 68))
    old_pixels, new_pixels = source.load(), output.load()
    for x, y in _black_cost_silhouette(source):
        new_pixels[x, y] = old_pixels[x, y]

    draw = ImageDraw.Draw(output)
    left = source.getpixel((350, 1278))
    right = source.getpixel((1300, 1278))
    draw.rectangle((62, 1105, 1408, 1291), fill=right)
    if max(abs(a - b) for a, b in zip(left, right)) > 25:
        draw.polygon(((62, 1105), (730, 1105), (510, 1291), (62, 1291)), fill=left)
    title = row[f"name_{language}"].upper()
    draw.text((82, 1112), title,
              font=_fit(draw, title, fonts, "Bold", 1250, 88, 48), fill="white")
    if row[f"subtitle_{language}"]:
        subtitle = row[f"subtitle_{language}"]
        draw.text((83, 1207), subtitle,
                  font=_fit(draw, subtitle, fonts, "SemiBold", 1260, 52, 37), fill="white")

    # Repaint the entire rules field, so a former EN line can never show through.
    draw.rectangle((62, 1370, 1408, 1903), fill=(235, 235, 234))
    deck_name = row[f"name_{language}"]
    if row[f"subtitle_{language}"]:
        deck_name += (" – " if language == "fr" else " - ") + row[f"subtitle_{language}"]
    note = (f"(Jusqu'à 4 exemplaires de « {deck_name} » dans votre deck.)"
            if language == "fr" else
            f"(You can have up to 4 copies of {deck_name} in your deck.)")
    for body_size in range(54, 35, -1):
        note_face = _face(fonts, "Italic", min(45, body_size - 4))
        note_lines = _wrap(draw, note, note_face, 1290)
        body_lines = layout_rules(draw, row[f"effet_{language}"], fonts, body_size, 1290)
        if len(note_lines) > 2:
            continue
        note_step, body_step = 50, int(body_size * 1.18)
        body_y = 1415 + len(note_lines) * note_step + 26
        if body_y + len(body_lines) * body_step <= 1890:
            break
    else:
        raise ValueError(f"{row['id']}: {language.upper()} rules overflow the card")
    for index, line in enumerate(note_lines):
        draw.text((82, 1415 + index * note_step), line, font=note_face, fill=(28, 28, 28))
    draw_rule_lines(draw, body_lines, 82, body_y, fonts, body_size, body_step, (14, 14, 14))
    return output


def render_html(rows: list[dict[str, str]]) -> str:
    pages = (len(rows) + 8) // 9
    parts = [f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cartes Coconut en français</title><link rel="stylesheet" href="style.css"></head><body>
<header><div><p class="eyebrow">Disney Lorcana · Format Coconut</p><h1 id="page-title">Cartes Coconut en français</h1>
<p id="page-summary">{len(rows)} cartes · {pages} planches A4 · 63 × 88 mm · traductions non officielles</p></div>
<div class="header-actions"><nav class="languages" aria-label="Langue / Language"><a id="lang-fr" href="?lang=fr" aria-current="page">FR</a><a id="lang-en" href="?lang=en">EN</a></nav>
<a id="pdf-link" class="pdf" href="planches-a4.pdf">Télécharger le PDF</a>
<button type="button" id="print" class="print" onclick="window.print()">Imprimer les planches</button></div></header>
<main aria-label="Planches Coconut">''']
    for page in range(pages):
        parts.append(f'<div class="sheet-wrap"><section class="sheet" aria-label="Planche {page+1} sur {pages}">')
        for row in rows[page * 9:(page + 1) * 9]:
            labels = {language: row[f"name_{language}"] +
                      (" — " + row[f"subtitle_{language}"] if row[f"subtitle_{language}"] else "")
                      for language in ("fr", "en")}
            escaped = html.escape(labels["fr"], quote=True)
            english = html.escape(labels["en"], quote=True)
            path = f'images/{row["id"]}.jpg'
            parts.append(f'<button type="button" class="card" data-id="{row["id"]}" data-name-fr="{escaped}" data-name-en="{english}" aria-label="Agrandir {escaped}"><img loading="lazy" src="{path}" alt="{escaped}"></button>')
        parts.append(f'</section><p class="page-label">Planche {page+1} / {pages}</p></div>')
    parts.append('''</main><dialog id="zoom" aria-label="Carte agrandie"><div class="modal-head"><strong id="zoom-title"></strong><button type="button" id="close">Fermer</button></div><img id="zoom-image" alt=""></dialog>
<script src="site.js"></script></body></html>''')
    return "\n".join(parts)


def _preview_pdf(images: list[Image.Image], path: Path) -> None:
    # 300 dpi A4. A 1 CSS px separation prints as approximately 3 dots.
    card_w, card_h, gap = 744, 1039, 3
    page_w, page_h = 2480, 3508
    x0 = (page_w - (card_w * 3 + gap * 2)) // 2
    y0 = (page_h - (card_h * 3 + gap * 2)) // 2
    pages = []
    for start in range(0, len(images), 9):
        page = Image.new("RGB", (page_w, page_h), "white")
        for offset, card in enumerate(images[start:start + 9]):
            x = x0 + offset % 3 * (card_w + gap)
            y = y0 + offset // 3 * (card_h + gap)
            page.paste(card.resize((card_w, card_h), Image.Resampling.LANCZOS), (x, y))
        pages.append(page)
    pages[0].save(path, "PDF", save_all=True, append_images=pages[1:], resolution=300)
    # Pillow writes the current time in these two fixed-width fields.
    binary = path.read_bytes()
    binary = re.sub(rb"/(CreationDate|ModDate) \(D:\d{14}Z\)",
                    lambda match: b"/" + match.group(1) + b" (D:20000101000000Z)", binary)
    path.write_bytes(binary)


def build_site(root: Path, destination: Path) -> None:
    rows = read_cards(root / "data" / "coconut-cards.csv")
    validate_rows(rows)
    lock = json.loads((root / "data" / "sources.lock.json").read_text(encoding="utf-8"))
    verify_lock(root, lock)
    if set(lock["cards"]) != {row["id"] for row in rows}:
        raise ValueError("Source lock card IDs do not match CSV")
    for row in rows:
        references = lock.get("refs", {}).get(row["id"], {})
        for column in ("ref_image_detail", "ref_image_settings", "ref_image_art_fr_hd", "official_card_id"):
            if references.get(column) != row[column]:
                raise ValueError(f"{row['id']}: {column} differs from pinned source reference")
    destination.mkdir(parents=True, exist_ok=True)
    images_dir = destination / "images"
    images_dir.mkdir(exist_ok=True)
    fonts = root / "assets" / "fonts"
    for language in ("fr", "en"):
        rendered = []
        language_images = images_dir if language == "fr" else images_dir / "en"
        language_images.mkdir(exist_ok=True)
        for row in rows:
            sources = lock["cards"][row["id"]]
            card = compose_card(row, root / sources["detail"], root / sources["art_fr_hd"], fonts, language)
            card.save(language_images / f'{row["id"]}.jpg', quality=90, subsampling=0, optimize=True)
            rendered.append(card)
        pdf_name = "planches-a4.pdf" if language == "fr" else "planches-a4-en.pdf"
        _preview_pdf(rendered, destination / pdf_name)
    (destination / "index.html").write_text(render_html(rows), encoding="utf-8")
    for name in ("style.css", "site.js"):
        (destination / name).write_bytes((root / "web" / name).read_bytes())
    for font in ("Regular", "SemiBold", "Bold"):
        (destination / f"BarlowCondensed-{font}.ttf").write_bytes((fonts / f"BarlowCondensed-{font}.ttf").read_bytes())
    (destination / "OFL.txt").write_bytes((fonts / "OFL.txt").read_bytes())
