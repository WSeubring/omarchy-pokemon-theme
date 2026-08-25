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
import sys
import time
import urllib.error
import urllib.request

import xdg
from oklch import hex_to_oklch

URL = ("https://raw.githubusercontent.com/PokeAPI/sprites/master"
       "/sprites/pokemon/other/official-artwork/%s%d.png")
# Outside the theme directory on purpose: `omarchy-theme-set` copies the whole
# theme into a staging dir on every apply, and a growing cache would be copied
# along with it.
CACHE = xdg.cache("artwork")


def accent(dex_id, is_shiny=False, path=None):
    """The creature's cached artwork accent, fetching artwork if needed.
    None -- meaning "fall back to the type colour" -- when offline.

    `path` is artwork already in hand, so a caller that needs both the file and
    the colour does not pay for -- or report -- a second failed fetch."""
    path = path or fetch(dex_id, is_shiny)
    if not path:
        return None
    return cached(path, path.rsplit(".", 1)[0] + ".accent")


# The daily timer catches up as soon as the machine wakes, which is often before
# DNS answers, and a fetch that fails there costs the day its creature. So a
# failed attempt is retried a few times rather than given up on.
ATTEMPTS = 4
RETRY_WAIT = 10


def fetch(dex_id, is_shiny=False):
    """Return a cached artwork path, or None if it cannot be had."""
    os.makedirs(CACHE, exist_ok=True)
    slug = "%d%s" % (dex_id, "-shiny" if is_shiny else "")
    path = os.path.join(CACHE, "%s.png" % slug)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    url = URL % ("shiny/" if is_shiny else "", dex_id)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = resp.read()
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == ATTEMPTS:
                print("artwork unavailable (%s)" % exc, file=sys.stderr)
                return None
            time.sleep(RETRY_WAIT)
    tmp = path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    return path

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
