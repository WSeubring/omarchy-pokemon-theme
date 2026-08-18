"""Compose the daily wallpaper with ImageMagick.

The artwork is prepared and composited as its own layer over a procedurally
generated ground rather than baked into it. That separation is deliberate: a
future animated background plugin needs the sprite addressable on its own.
"""

import hashlib
import math
import os
import subprocess

import atomic
from oklch import hex_to_oklch, oklch_to_hex

# The trimmed creature is scaled to a target *area*, expressed as this fraction
# of the short edge squared. Fitting to a bounding box instead made wide, flat
# Pokemon (Muk, Magnemite) look far smaller than tall ones (Pikachu) even though
# both filled their box; matching area matches how large they actually read.
# Official artwork also ships with heavy transparent padding, so it must be
# trimmed first or the scale varies wildly between Pokemon.
ARTWORK_FRACTION = 0.44
# Where the creature sits, as a fraction of the canvas. Off to one side leaves
# the left of the desktop clear, which is where windows and icons land.
ARTWORK_CENTER = (0.68, 0.56)
GLOW_FRACTION = 1.5

# A shiny day should look like one from across the room, so it gets a brighter
# halo and a scatter of four-pointed sparkles -- the same visual language the
# games use, and the same one omarchy-lock-pokemon uses on the lock screen.
SHINY_GLOW = 0.62
SPARKLE_COUNT = 8
SPARKLE_TINT = "#fff4cf"
# Points are needle-thin: equal-width strokes read as plus signs, not sparkles.
SPARKLE_WAIST = 0.10
SPARKLE_BLUR = 0.002
# Size and scatter scale with the render, so they hold at any resolution.
SPARKLE_SIZE = 0.060
SPARKLE_SPREAD = 0.30
# Sizes vary by this much of the base, squared, so most are small and a couple
# are large -- an even spread of sizes looks placed rather than scattered.
SPARKLE_MIN_SCALE = 0.30


def _run(args):
    subprocess.run(args, check=True, capture_output=True)


def _shift(hex_color, dl=0.0, dc=0.0):
    L, C, H = hex_to_oklch(hex_color)
    return oklch_to_hex(max(0.0, L + dl), max(0.0, C + dc), H)


def _star(x, y, size, waist):
    """Two crossed needles: the classic four-point sparkle."""
    thickness = max(1, int(size * waist))
    return [
        "-draw", "polygon %d,%d %d,%d %d,%d %d,%d"
                 % (x, y - size, x + thickness, y, x, y + size, x - thickness, y),
        "-draw", "polygon %d,%d %d,%d %d,%d %d,%d"
                 % (x - size, y, x, y - thickness, x + size, y, x, y + thickness),
    ]


def _sparkles(seed, width, height, cx, cy, short):
    """A deterministic scatter of sparkles around (cx, cy).

    Seeded by the Pokemon, so the same shiny always sparkles the same way -- a
    regenerated wallpaper should be the same wallpaper.
    """
    digest = hashlib.sha256(("sparkle:%s" % seed).encode()).digest()
    args = ["-size", "%dx%d" % (width, height), "xc:none",
            "-fill", SPARKLE_TINT, "-stroke", "none"]
    base = short * SPARKLE_SIZE
    spread = short * SPARKLE_SPREAD
    for i in range(SPARKLE_COUNT):
        angle = digest[i * 3] / 255 * 2 * math.pi
        radius = (0.30 + digest[i * 3 + 1] / 255 * 0.70) * spread
        scale = SPARKLE_MIN_SCALE + (digest[i * 3 + 2] / 255) ** 2
        args += _star(int(cx + math.cos(angle) * radius),
                      # Flattened vertically: the creature is wider than tall.
                      int(cy + math.sin(angle) * radius * 0.8),
                      int(base * scale), SPARKLE_WAIST)
    return args + ["-blur", "0x%d" % max(1, int(short * SPARKLE_BLUR))]


def render(artwork, colors, out_path, width, height, glow=0.45, sparkle=None):
    """Build the wallpaper. `artwork` may be None -- the ground stands alone.

    `sparkle` is the seed for a shiny day's sparkles; None leaves them out.

    One ImageMagick invocation, composited beside the destination and renamed into
    place. The layers were separate files once, which cost eight times as long:
    writing and re-reading a 2400x2400 RGBA intermediate dwarfed the drawing.
    Placement is gravity-relative for the same reason -- centring a layer on a
    point needs no measurement of the layer.
    """
    short = min(width, height)
    final_path, out_path = out_path, atomic.image_scratch(out_path)
    if sparkle is not None:
        glow = SHINY_GLOW
    ground = colors["darker_background"]
    top = _shift(colors["dark_background"], dl=0.04, dc=0.008)

    # Offsets are from the canvas centre, since that is what -gravity Center
    # measures from.
    cx = int(width * ARTWORK_CENTER[0])
    cy = int(height * ARTWORK_CENTER[1])
    dx, dy = cx - width // 2, cy - height // 2
    gsize = int(short * GLOW_FRACTION)

    # Vertical gradient, lighter at the top so the desktop has a horizon.
    args = ["magick", "-size", "%dx%d" % (width, height),
            "gradient:%s-%s" % (top, ground)]

    # Accent halo centred on the creature. `-none` fades to transparent so it
    # lays over the gradient without a visible edge.
    args += ["(", "-size", "%dx%d" % (gsize, gsize),
             "radial-gradient:%s-none" % colors["accent"],
             "-alpha", "set", "-channel", "A",
             "-evaluate", "multiply", "%.3f" % glow, "+channel", ")",
             "-gravity", "Center", "-geometry", "%+d%+d" % (dx, dy),
             "-compose", "screen", "-composite"]

    if artwork:
        # Trim the padding, then scale to a fixed pixel area. `N@` is
        # ImageMagick's area-preserving resize.
        target_area = int((short * ARTWORK_FRACTION) ** 2)
        args += ["(", artwork, "-trim", "+repage",
                 "-resize", "%d@" % target_area, ")",
                 "-gravity", "Center", "-geometry", "%+d%+d" % (dx, dy),
                 "-compose", "over", "-composite"]

    if sparkle is not None:
        # Screened over the creature, not behind it: sparkles in front are what
        # make it read as shiny rather than as a lit background.
        args += ["("] + _sparkles(sparkle, width, height, cx, cy, short) + [
                 ")", "-gravity", "NorthWest", "-geometry", "+0+0",
                 "-compose", "screen", "-composite"]

    args += ["-quality", "92", out_path]
    _run(args)

    atomic.commit(out_path, final_path)
    return final_path
