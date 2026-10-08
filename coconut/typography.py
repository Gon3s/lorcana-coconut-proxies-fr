"""Inline rules typography shared by every generated card.

CSV markup is deliberately small: **keyword** and {ink}/{lore}/{strength}/{exert}.
The symbols are drawn as vectors so the build does not depend on OS glyphs.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageDraw, ImageFont


SYMBOLS = frozenset(('ink', 'lore', 'strength', 'exert'))
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
    """Draw readable approximations of the four Lorcana rules symbols."""
    if symbol not in SYMBOLS:
        raise ValueError(f'Unknown rules symbol: {symbol}')
    x, y = int(round(x)), int(round(y))
    s = size
    stroke = max(3, round(s * .095))
    if symbol == 'ink':
        points = [(x + s*.50, y + s*.06), (x + s*.91, y + s*.28),
                  (x + s*.91, y + s*.73), (x + s*.50, y + s*.95),
                  (x + s*.09, y + s*.73), (x + s*.09, y + s*.28)]
        draw.line(points + [points[0]], fill=fill, width=stroke, joint='curve')
    elif symbol == 'lore':
        points = [(x + s*.50, y + s*.03), (x + s*.88, y + s*.50),
                  (x + s*.50, y + s*.97), (x + s*.12, y + s*.50)]
        draw.line(points + [points[0]], fill=fill, width=stroke, joint='curve')
        draw.polygon([(x + s*.50, y + s*.27), (x + s*.70, y + s*.53),
                      (x + s*.50, y + s*.72)], fill=fill)
    elif symbol == 'strength':
        draw.ellipse((x+s*.24, y+s*.24, x+s*.76, y+s*.76), outline=fill, width=stroke)
        for dx, dy in ((0,-1), (1,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1)):
            draw.line((x+s*(.5+.28*dx), y+s*(.5+.28*dy),
                       x+s*(.5+.44*dx), y+s*(.5+.44*dy)), fill=fill, width=stroke)
    else:
        points = [(x+s*.50,y+s*.03), (x+s*.90,y+s*.26), (x+s*.90,y+s*.73),
                  (x+s*.50,y+s*.97), (x+s*.10,y+s*.73), (x+s*.10,y+s*.26)]
        bold_stroke = max(4, round(s * .13))
        draw.line(points + [points[0]], fill=fill, width=bold_stroke, joint='curve')
        draw.arc((x+s*.28,y+s*.30,x+s*.72,y+s*.74), 55, 325,
                 fill=fill, width=bold_stroke)
        draw.polygon([(x+s*.78,y+s*.25), (x+s*.80,y+s*.51),
                      (x+s*.55,y+s*.35)], fill=fill)


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
