"""Inline rules typography shared by every generated card.

CSV markup is deliberately small: **keyword** and named rules symbols.
The symbols are drawn as vectors so the build does not depend on OS glyphs.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageDraw, ImageFont

from .icons import ICONS, icon_mask


SYMBOLS = ICONS
MARKUP = re.compile(r'\*\*([^*]+)\*\*|\{([a-z]+)\}')


@dataclass(frozen=True)
class Span:
    kind: str
    text: str


def parse_word(word: str) -> tuple[Span, ...]:
    """Parse one whitespace-delimited word, retaining adjacent punctuation."""
    spans = []
    position = 0
    for match in MARKUP.finditer(word):
        if match.start() > position:
            spans.append(Span('text', word[position:match.start()]))
        if match.group(1) is not None:
            spans.append(Span('bold', match.group(1)))
        else:
            symbol = match.group(2)
            if symbol not in SYMBOLS:
                raise ValueError(f'Unknown rules symbol: {symbol}')
            spans.append(Span('icon', symbol))
        position = match.end()
    if position < len(word):
        spans.append(Span('text', word[position:]))
    if any('{' in span.text or '}' in span.text or '**' in span.text
           for span in spans if span.kind == 'text'):
        raise ValueError(f'Invalid rules markup: {word}')
    return tuple(spans)


def _faces(fonts: Path, size: int) -> dict[str, ImageFont.FreeTypeFont]:
    return {
        'text': ImageFont.truetype(fonts / 'BarlowCondensed-Regular.ttf', size),
        'bold': ImageFont.truetype(fonts / 'BarlowCondensed-Bold.ttf', size),
    }


def _span_width(draw: ImageDraw.ImageDraw, span: Span,
                faces: dict[str, ImageFont.FreeTypeFont], size: int) -> float:
    return size * 0.92 if span.kind == 'icon' else draw.textlength(span.text, font=faces[span.kind])



def layout_rules(draw: ImageDraw.ImageDraw, text: str, fonts: Path,
                 size: int, width: int) -> list[tuple[list[tuple[Span, ...]], float]]:
    """Wrap mixed-weight text and symbols without dropping explicit paragraphs."""
    faces = _faces(fonts, size)
    space = draw.textlength(' ', font=faces['text'])
    lines = []
    for paragraph in text.split('\n'):
        words = []
        line_width = 0.0
        for raw_word in paragraph.split():
            word = parse_word(raw_word)
            word_width = sum(_span_width(draw, span, faces, size) for span in word)
            if word_width > width:
                raise ValueError(f'Word too wide: {raw_word}')
            needed = word_width + (space if words else 0)
            if words and line_width + needed > width:
                lines.append((words, line_width))
                words, line_width, needed = [], 0.0, word_width
            words.append(word)
            line_width += needed
        lines.append((words, line_width))
    return lines


def draw_icon(draw: ImageDraw.ImageDraw, symbol: str, x: float, y: float,
              size: int, fill: tuple[int, int, int]) -> None:
    """Draw an antialiased vector icon onto the card rules area."""
    x, y = int(round(x)), int(round(y))
    draw.bitmap((x, y), icon_mask(symbol, size), fill=fill)


def draw_rule_lines(draw: ImageDraw.ImageDraw,
                    lines: list[tuple[list[tuple[Span, ...]], float]],
                    x: int, y: int, fonts: Path, size: int, step: int,
                    fill: tuple[int, int, int]) -> None:
    faces = _faces(fonts, size)
    space = draw.textlength(' ', font=faces['text'])
    for line_number, (words, _) in enumerate(lines):
        cursor = float(x)
        for word_number, word in enumerate(words):
            if word_number:
                cursor += space
            for span in word:
                if span.kind == 'icon':
                    icon_size = round(size * .83)
                    draw_icon(draw, span.text, cursor, y + line_number*step + 7,
                              icon_size, fill)
                else:
                    draw.text((cursor, y + line_number*step), span.text,
                              font=faces[span.kind], fill=fill)
                cursor += _span_width(draw, span, faces, size)
