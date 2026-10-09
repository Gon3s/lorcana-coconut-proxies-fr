"""Clean, scale-independent redraws of the six labelled Lorcana symbols.

The reference sheet is used only to identify silhouettes. Its watermarked
pixels are not copied into these masks. Pillow is the sole build dependency.
"""

import math
from functools import lru_cache

from PIL import Image, ImageDraw


ICONS = frozenset({'cost', 'lore', 'strength', 'exert', 'ink', 'willpower'})
SUPERSAMPLE = 6


def _curve(start, control_a, control_b, end, steps=18):
    """Sample a cubic curve for the rounded silhouettes."""
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1 - t
        points.append((
            u**3*start[0] + 3*u*u*t*control_a[0] + 3*u*t*t*control_b[0] + t**3*end[0],
            u**3*start[1] + 3*u*u*t*control_a[1] + 3*u*t*t*control_b[1] + t**3*end[1],
        ))
    return points


@lru_cache(maxsize=128)
def icon_mask(symbol: str, size: int) -> Image.Image:
    """Return an antialiased L mask with transparent surrounding pixels."""
    if symbol not in ICONS:
        raise ValueError(f'Unknown rules symbol: {symbol}')
    if size < 1:
        raise ValueError('Icon size must be positive')
    resolution = size * SUPERSAMPLE
    scale = resolution / 100
    mask = Image.new('L', (resolution, resolution), 0)
    draw = ImageDraw.Draw(mask)

    def polygon(points, fill=255):
        draw.polygon([(round(x*scale), round(y*scale)) for x, y in points], fill=fill)

    def ellipse(box, fill):
        draw.ellipse(tuple(round(v*scale) for v in box), fill=fill)

    if symbol == 'cost':
        polygon([(50, 2), (96, 25), (96, 75), (50, 98), (4, 75), (4, 25)])
        polygon([(50, 20), (80, 35), (80, 65), (50, 80), (20, 65), (20, 35)], 0)

    elif symbol == 'lore':
        top, right, bottom, left = (50, 1), (99, 50), (50, 99), (1, 50)
        outline = (
            _curve(top, (58, 27), (77, 37), right) +
            _curve(right, (77, 63), (58, 73), bottom) +
            _curve(bottom, (42, 73), (23, 63), left) +
            _curve(left, (23, 37), (42, 27), top)
        )
        polygon(outline)
        polygon([(50, 34), (67, 50), (50, 66), (33, 50)], 0)

    elif symbol == 'strength':
        rays = []
        for index in range(16):
            angle = -math.pi/2 + index*math.pi/8
            radius = 49 if index % 2 == 0 else 35
            rays.append((50 + radius*math.cos(angle), 50 + radius*math.sin(angle)))
        polygon(rays)
        ellipse((29, 29, 71, 71), 0)

    elif symbol == 'exert':
        polygon([(50, 2), (94, 25), (94, 75), (50, 98), (6, 75), (6, 25)])
        polygon([(50, 18), (80, 34), (80, 66), (50, 82), (20, 66), (20, 34)], 0)
        draw.arc(tuple(round(v*scale) for v in (29, 29, 71, 71)), 55, 325,
                 fill=255, width=max(1, round(12*scale)))
        polygon([(77, 25), (79, 53), (53, 39)])

    elif symbol == 'ink':
        blade = (
            _curve((50, 2), (73, 3), (91, 21), (97, 45)) +
            _curve((97, 45), (83, 39), (72, 31), (61, 33)) +
            _curve((61, 33), (50, 36), (48, 51), (54, 61)) +
            _curve((54, 61), (32, 54), (35, 31), (50, 2))
        )
        for rotation in (0, 2*math.pi/3, 4*math.pi/3):
            c, s = math.cos(rotation), math.sin(rotation)
            polygon([(50 + (x-50)*c - (y-50)*s,
                      50 + (x-50)*s + (y-50)*c) for x, y in blade])

    else:  # willpower
        polygon([(18, 4), (41, 4), (50, 15), (59, 4), (82, 4),
                 (96, 22), (88, 49), (94, 65), (50, 98),
                 (6, 65), (12, 49), (4, 22)])
        polygon([(50, 83), (18, 60), (20, 28), (39, 21), (50, 31),
                 (61, 21), (80, 28), (82, 60)], 0)
        polygon([(50, 75), (26, 57), (27, 35), (40, 29), (50, 39),
                 (60, 29), (73, 35), (74, 57)])

    return mask.resize((size, size), Image.Resampling.LANCZOS)
