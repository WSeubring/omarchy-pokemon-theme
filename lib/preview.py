"""Terminal rendering for the installer's live previews.

Two kinds of picture, both plain ANSI so they work in any truecolor terminal
with nothing installed beyond the theme's own dependencies:

- palette strips: one line summarising a generated palette (ground, text,
  accent, ANSI colours, selection)
- sprites: the official artwork itself, downscaled by ImageMagick and drawn
  as half-block cells, two pixels per character

The sprite path goes through the same artwork cache the generator uses, so
the wizard's downloads are the theme's downloads.
"""

import subprocess

import artwork
import palette
from oklch import hex_to_oklch

RESET = "\x1b[0m"


def _rgb(value):
    h = value.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fg(value):
    return "\x1b[38;2;%d;%d;%dm" % _rgb(value)


def bg(value):
    return "\x1b[48;2;%d;%d;%dm" % _rgb(value)


def strip(colors):
    """One palette as a compact strip: text, accent, ANSI dots, selection."""
    ground = bg(colors["background"])
    parts = [ground, fg(colors["foreground"]), " Aa "]
    parts += [fg(colors["dark_foreground"]), "dim "]
    parts += [fg(colors["accent"]), "accent "]
    for token in ("red", "yellow", "green", "cyan", "blue", "magenta"):
        parts += [fg(colors[token]), "●"]
    parts += [" ", bg(colors["selection"]), fg(colors["foreground"]),
              " sel ", ground, " ", RESET]
    return "".join(parts)


def predicted_mode(type_colors, kinds):
    """What mode = "pokemon" would pick, from the type colour (offline)."""
    L = hex_to_oklch(type_colors[kinds[0]])[0]
    return "light" if L >= palette.LIGHT_ACCENT_L else "dark"


def sprite(dex_id, height=14):
    """The official artwork as half-block lines, [] when it cannot be had.

    `height` is in terminal rows; each row carries two pixel rows via the
    upper-half-block, so the image is resized to 2*height pixels tall.
    """
    path = artwork.fetch(dex_id)
    if not path:
        return []
    px_h = height * 2
    px_w = px_h * 2  # artwork is square; terminal cells are ~1:2
    try:
        raw = subprocess.run(
            ["magick", path, "-trim", "+repage", "-background", "none",
             "-resize", "%dx%d" % (px_w, px_h),
             "-gravity", "center", "-extent", "%dx%d" % (px_w, px_h),
             "-depth", "8", "rgba:-"],
            check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    if len(raw) != px_w * px_h * 4:
        return []

    def px(x, y):
        i = (y * px_w + x) * 4
        r, g, b, a = raw[i:i + 4]
        return (r, g, b) if a >= 128 else None

    lines = []
    for row in range(height):
        cells = []
        for x in range(px_w):
            top, bot = px(x, row * 2), px(x, row * 2 + 1)
            if top is None and bot is None:
                cells.append(RESET + " ")
            elif top is not None and bot is not None:
                cells.append("\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm▀"
                             % (top + bot))
            elif top is not None:
                cells.append(RESET + "\x1b[38;2;%d;%d;%dm▀" % top)
            else:
                cells.append(RESET + "\x1b[38;2;%d;%d;%dm▄" % bot)
        lines.append("".join(cells) + RESET)
    return lines
