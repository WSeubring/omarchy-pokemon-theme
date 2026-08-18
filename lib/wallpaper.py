"""Compose the daily wallpaper with ImageMagick.

The artwork is prepared and composited as its own layer over a procedurally
generated ground rather than baked into it. That separation is deliberate: a
future animated background plugin needs the sprite addressable on its own.
"""

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


def _run(args):
    subprocess.run(args, check=True, capture_output=True)


def _shift(hex_color, dl=0.0, dc=0.0):
    L, C, H = hex_to_oklch(hex_color)
    return oklch_to_hex(max(0.0, L + dl), max(0.0, C + dc), H)


def render(artwork, colors, out_path, width, height, glow=0.45):
    """Build the wallpaper. `artwork` may be None -- the ground stands alone.

    One ImageMagick invocation, composited beside the destination and renamed into
    place. The layers were separate files once, which cost eight times as long:
    writing and re-reading a 2400x2400 RGBA intermediate dwarfed the drawing.
    Placement is gravity-relative for the same reason -- centring a layer on a
    point needs no measurement of the layer.
    """
    short = min(width, height)
    final_path, out_path = out_path, atomic.image_scratch(out_path)
    ground = colors["darker_background"]
    top = _shift(colors["dark_background"], dl=0.04, dc=0.008)

    # Offsets are from the canvas centre, since that is what -gravity Center
    # measures from.
    dx = int(width * ARTWORK_CENTER[0]) - width // 2
    dy = int(height * ARTWORK_CENTER[1]) - height // 2
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

    args += ["-quality", "92", out_path]
    _run(args)

    atomic.commit(out_path, final_path)
    return final_path
