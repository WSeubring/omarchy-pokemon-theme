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
SHINY_GLOW = 0.56
SPARKLE_COUNT = 7
SPARKLE_TINT = "#fff4cf"
# Points are needle-thin: equal-width strokes read as plus signs, not sparkles.
SPARKLE_WAIST = 0.10
SPARKLE_BLUR = 0.002
# Size and scatter scale with the render, so they hold at any resolution.
SPARKLE_SIZE = 0.042
# Sizes vary by this much of the base, squared, so most are small and a couple
# are large -- an even spread of sizes looks placed rather than scattered.
SPARKLE_MIN_SCALE = 0.30
# Sparkles ring the creature rather than landing on it: a big star across the
# chest reads as a defect, not as shine. Each one is pushed out until its points
# clear the sprite's measured footprint, plus this much of the short edge.
SPARKLE_CLEARANCE = 0.02
# How far beyond that clearance they can drift.
SPARKLE_DRIFT = 0.10
# Screened at less than full strength: the point is a glint, not a light source.
SPARKLE_OPACITY = 0.72


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


def _sparkles(seed, width, height, cx, cy, short, footprint):
    """A deterministic ring of sparkles around the creature at (cx, cy).

    Seeded by the Pokemon, so the same shiny always sparkles the same way -- a
    regenerated wallpaper should be the same wallpaper.

    `footprint` is the placed sprite's (half_width, half_height). Each sparkle is
    pushed out along its own angle until its points clear that ellipse, so a large
    one lands beside the creature instead of across it.
    """
    digest = hashlib.sha256(("sparkle:%s" % seed).encode()).digest()
    args = ["-size", "%dx%d" % (width, height), "xc:none",
            "-fill", SPARKLE_TINT, "-stroke", "none"]
    base = short * SPARKLE_SIZE
    clearance = short * SPARKLE_CLEARANCE
    hx, hy = footprint
    for i in range(SPARKLE_COUNT):
        angle = digest[i * 3] / 255 * 2 * math.pi
        drift = digest[i * 3 + 1] / 255 * short * SPARKLE_DRIFT
        scale = SPARKLE_MIN_SCALE + (digest[i * 3 + 2] / 255) ** 2
        size = int(base * scale)

        # Distance from the centre to the footprint's edge along this angle.
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        edge = math.hypot(hx * cos_a, hy * sin_a)
        radius = edge + size + clearance + drift

        # Clamped inside the canvas: a wide sprite pushes its ring out far, and
        # a star with its points cut off by the edge looks like a rendering fault.
        margin = size + 4
        x = min(max(int(cx + cos_a * radius), margin), width - margin)
        y = min(max(int(cy + sin_a * radius), margin), height - margin)
        args += _star(x, y, size, SPARKLE_WAIST)
    args += ["-blur", "0x%d" % max(1, int(short * SPARKLE_BLUR))]
    return args + ["-channel", "A", "-evaluate", "multiply",
                   "%.2f" % SPARKLE_OPACITY, "+channel"]


def _footprint(artwork, short):
    """The placed sprite's half-width and half-height, in pixels.

    Measured from the trimmed artwork (0.03s) rather than guessed from the target
    area: a wide Pokemon and a tall one of the same area need the sparkles pushed
    out by very different amounts.
    """
    target_area = (short * ARTWORK_FRACTION) ** 2
    try:
        out = subprocess.run(
            ["magick", artwork, "-trim", "+repage", "-format", "%w %h", "info:"],
            check=True, capture_output=True, text=True).stdout
        w, h = (int(v) for v in out.split())
    except (OSError, subprocess.CalledProcessError, ValueError):
        side = math.sqrt(target_area)
        return side / 2, side / 2
    scale = math.sqrt(target_area / float(w * h))
    return w * scale / 2, h * scale / 2


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
        # Screened over the ground, ringing the creature rather than covering it.
        footprint = (_footprint(artwork, short) if artwork
                     else (short * ARTWORK_FRACTION / 2,) * 2)
        args += ["("] + _sparkles(sparkle, width, height, cx, cy, short,
                                  footprint) + [
                 ")", "-gravity", "NorthWest", "-geometry", "+0+0",
                 "-compose", "screen", "-composite"]

    # JPEG q92 over lossless PNG, tried and rolled back: PNG with a Lanczos
    # upscale and dithered 8-bit gradients was technically cleaner but read
    # worse on screen -- the encoder's slight softening flatters the upscaled
    # artwork. At q92 ImageMagick already keeps 4:4:4 chroma.
    args += ["-quality", "92", out_path]
    _run(args)

    atomic.commit(out_path, final_path)
    return final_path
