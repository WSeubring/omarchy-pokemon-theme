"""Compose the daily wallpaper with ImageMagick.

The artwork is prepared and composited as its own layer over a procedurally
generated ground rather than baked into it. That separation is deliberate: a
future animated background plugin needs the sprite addressable on its own.
"""

import os
import subprocess

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


def _size_of(path):
    out = subprocess.run(["magick", "identify", "-format", "%w %h", path],
                         check=True, capture_output=True, text=True).stdout
    w, h = out.split()
    return int(w), int(h)


def render(artwork, colors, out_path, width, height, glow=0.45):
    """Build the wallpaper. `artwork` may be None -- the ground stands alone."""
    short = min(width, height)
    ground = colors["darker_background"]
    top = _shift(colors["dark_background"], dl=0.04, dc=0.008)

    tmp = out_path + ".layers"
    os.makedirs(tmp, exist_ok=True)
    base = os.path.join(tmp, "base.png")
    glow_img = os.path.join(tmp, "glow.png")
    sprite = os.path.join(tmp, "sprite.png")
    made = [base, glow_img]

    # Vertical gradient, lighter at the top so the desktop has a horizon.
    _run(["magick", "-size", "%dx%d" % (width, height),
          "gradient:%s-%s" % (top, ground), base])

    cx = int(width * ARTWORK_CENTER[0])
    cy = int(height * ARTWORK_CENTER[1])

    # Accent halo centred on the creature. `-none` fades to transparent so it
    # lays over the gradient without a visible edge.
    gsize = int(short * GLOW_FRACTION)
    _run(["magick", "-size", "%dx%d" % (gsize, gsize),
          "radial-gradient:%s-none" % colors["accent"],
          "-alpha", "set", "-channel", "A",
          "-evaluate", "multiply", "%.3f" % glow, "+channel", glow_img])

    layers = ["magick", base, "(", glow_img, ")",
              "-geometry", "%+d%+d" % (cx - gsize // 2, cy - gsize // 2),
              "-compose", "screen", "-composite"]

    if artwork:
        target_area = int((short * ARTWORK_FRACTION) ** 2)
        # Trim the padding, then scale to a fixed pixel area. `N@` is
        # ImageMagick's area-preserving resize.
        _run(["magick", artwork, "-trim", "+repage",
              "-resize", "%d@" % target_area, sprite])
        made.append(sprite)
        sw, sh = _size_of(sprite)
        layers += ["(", sprite, ")",
                   "-geometry", "%+d%+d" % (cx - sw // 2, cy - sh // 2),
                   "-compose", "over", "-composite"]

    layers += ["-quality", "92", out_path]
    _run(layers)

    for path in made:
        if os.path.exists(path):
            os.remove(path)
    os.rmdir(tmp)
    return out_path
