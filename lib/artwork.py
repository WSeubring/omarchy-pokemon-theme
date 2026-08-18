"""The creature's own dominant colour, taken from its artwork.

The type colours are a category: every fire type gets the same red, so Charizard
and Magmar theme identically. The artwork knows better -- Charizard is orange,
Lapras is a specific blue -- so the palette's hue comes from the sprite when the
sprite is available, and falls back to the type colour when it is not.

Only the hue is taken. Lightness and chroma still come from palette.py's ladder,
so an extracted colour cannot make a theme unreadable no matter what it is.

Quantizing costs an ImageMagick call, so the answer is cached next to the artwork
it was derived from and computed once per Pokemon, ever.
"""

import os
import re
import subprocess

from oklch import hex_to_oklch

# Enough bins to separate a body colour from its outline and highlights, few
# enough that a body does not fragment into six shades of itself.
BINS = 8
# Below this the pixel is effectively transparent padding, not the creature.
ALPHA_THRESHOLD = "50%"
# Outlines sit near black and specular highlights near white. Both are large,
# flat and uninformative, so their share of the artwork is discounted rather
# than excluded -- a genuinely black Pokemon still has to score something.
USABLE_L = (0.25, 0.90)
OFF_LADDER_PENALTY = 0.25

_HISTOGRAM = re.compile(
    r"\s*(\d+):\s*\([\d.,\s]+\)\s+(#[0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?")


def dominant(path):
    """The artwork's most theme-worthy colour as hex, or None.

    "Most theme-worthy" is coverage times chroma: the largest region wins, but a
    grey one loses to a smaller saturated one, because a palette built from grey
    is a palette with no identity. Ties are broken by whichever came first out of
    the quantizer, which orders by count.
    """
    bins = _bins(path)
    if not bins:
        return None
    total = sum(count for count, _ in bins)
    best_score, best = 0.0, None
    for count, color in bins:
        L, C, _ = hex_to_oklch(color)
        usable = 1.0 if USABLE_L[0] <= L <= USABLE_L[1] else OFF_LADDER_PENALTY
        score = (count / total) * C * usable
        if score > best_score:
            best_score, best = score, color
    return best


def cached(path, cache_path=None):
    """`dominant()`, remembered. The artwork never changes, so neither does this."""
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path) as fh:
                value = fh.read().strip()
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
                return value
        except OSError:
            pass

    color = dominant(path)
    if color is None or not cache_path:
        return color

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = cache_path + ".part"
    with open(tmp, "w") as fh:
        fh.write(color + "\n")
    os.replace(tmp, cache_path)
    return color


def _bins(path):
    """Quantize to a handful of colours: [(pixel_count, hex)], opaque only."""
    try:
        out = subprocess.run(
            ["magick", path, "-trim", "+repage",
             # Binarise alpha first: the quantizer would otherwise mix the
             # anti-aliased edge into the body colour it is meant to find.
             "-alpha", "on", "-channel", "A", "-threshold", ALPHA_THRESHOLD,
             "+channel", "-colors", str(BINS),
             "-format", "%c", "histogram:info:-"],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []

    bins = []
    for line in out.splitlines():
        found = _HISTOGRAM.match(line)
        if not found:
            continue
        count, color, alpha = found.groups()
        if alpha is not None and int(alpha, 16) < 128:
            continue
        bins.append((int(count), color))
    return bins
