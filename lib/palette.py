"""Build a colors.toml palette from a Pokemon's types.

Only *hue* comes from the Pokemon. Lightness is pinned to a ladder measured
from the stock Catppuccin and Tokyo Night themes, and chroma is clamped to a
readable band. That split is what keeps all 905 days legible: a flat grey
Magnemite and a neon Pikachu differ in hue and nothing else structural.
"""

from oklch import blend_hue, hex_to_oklch, oklch_to_hex

# Neutral ladder: (L, C) at the accent hue. Averaged from the two stock themes,
# whose neutrals all sit within ~10 degrees of one hue -- that unity is what
# reads as "a theme" rather than "some colours".
NEUTRALS_DARK = {
    "darker_background": (0.172, 0.015),
    "dark_background": (0.200, 0.020),
    "background": (0.235, 0.026),
    "lighter_background": (0.303, 0.034),
    "selection": (0.355, 0.036),
    "muted": (0.443, 0.045),
    "dark_foreground": (0.523, 0.048),
    "foreground": (0.800, 0.046),
    "light_foreground": (0.838, 0.048),
    "bright_foreground": (0.872, 0.050),
}

# Canonical ANSI anchors: (L, C, hue). Hue must stay near these or diff output
# and syntax highlighting stop being readable at a glance, so the Pokemon only
# nudges them (see HUE_PULL).
ANSI = {
    "red": (0.740, 0.145, 6.0),
    "orange": (0.790, 0.100, 32.0),
    "yellow": (0.850, 0.092, 81.0),
    "green": (0.828, 0.126, 136.0),
    "cyan": (0.752, 0.086, 196.0),
    "blue": (0.740, 0.124, 262.0),
    "magenta": (0.790, 0.108, 318.0),
    "brown": (0.480, 0.054, 33.0),
}

BRIGHT = ("red", "yellow", "green", "cyan", "blue", "magenta")

# The accent keeps its native lightness inside a band rather than being pinned.
# Pinning it outright turned every yellow into mustard: hue 95 simply does not
# read as "electric" below L 0.85, while a violet at that L is washed out. The
# band is wide enough to preserve type identity and still clear WCAG AA against
# the pinned backgrounds -- verified across all 905 by tests/validate_contrast.py.
ACCENT_L_MIN, ACCENT_L_MAX = 0.660, 0.865
ACCENT_C_MIN, ACCENT_C_MAX = 0.090, 0.170

# Hyprland's active-window border, as a two-stop gradient for a dual type -- the
# same treatment omarchy-lock-pokemon gives its card border. Omarchy resolves
# this key into both hyprland.lua and shell.toml's hyprland.active-border, so one
# gradient reaches window borders, notifications, popups, menus and the lock card.
# Alpha matches the stock themes that ship a gradient (hackerman, solitude).
BORDER_ALPHA = "ee"
BORDER_ANGLE = 45

# How far the ANSI hues rotate toward the day's hue. Enough to feel cohesive,
# far short of making red look orange.
HUE_PULL = 0.15
# Second type tints the mid-greys only, so a dual type is visible in the UI
# chrome without fighting the primary accent.
SECONDARY_KEYS = ("lighter_background", "selection", "muted")


def _readable(hex_color):
    """Lift a type colour into the accent's readable band, keeping its hue.

    Shared with the accent so a border stop and the accent agree: several type
    colours (dark, ghost, steel) are too dim or too flat to read as a border
    against the palette's own background at their native lightness.
    """
    L, C, H = hex_to_oklch(hex_color)
    return oklch_to_hex(
        min(max(L, ACCENT_L_MIN), ACCENT_L_MAX),
        min(max(C, ACCENT_C_MIN), ACCENT_C_MAX),
        H,
    )


def _border(accent, type_colors, types):
    """A one- or two-stop Hyprland gradient spec: the accent, then the second type.

    The first stop is whatever the accent came from -- the creature's own colour
    when the artwork was readable, its primary type otherwise -- so the border
    always agrees with the rest of the palette. The second stop stays type-based:
    it is there to say "this one is also a poison type", which is a fact about the
    category, not about the pixels.
    """
    stops = [accent]
    if len(types) > 1:
        stops.append(_readable(type_colors[types[1]]))
    spec = " ".join("rgba(%s%s)" % (s.lstrip("#"), BORDER_ALPHA) for s in stops)
    if len(stops) < 2:
        return spec
    return "%s %ddeg" % (spec, BORDER_ANGLE)


def build(type_colors, types, accent_source=None):
    """types: 1-2 type names, in order. Returns {token: hex}.

    `accent_source` is a hex colour to take the accent from -- the creature's
    dominant artwork colour -- instead of its primary type. Only hue and a
    clamped lightness survive either way, so the two paths differ in identity,
    not in readability.
    """
    out = {}
    out["accent"] = _readable(accent_source or type_colors[types[0]])
    h_primary = hex_to_oklch(out["accent"])[2]
    h_secondary = h_primary
    if len(types) > 1:
        h_secondary = hex_to_oklch(type_colors[types[1]])[2]

    out["hyprland_active_border"] = _border(out["accent"], type_colors, types)

    for token, (L, C) in NEUTRALS_DARK.items():
        hue = h_secondary if token in SECONDARY_KEYS else h_primary
        out[token] = oklch_to_hex(L, C, hue)

    # Pull toward whichever type hue each ANSI anchor is already closer to, so a
    # dual type contributes both hues rather than averaging into one.
    for token, (L, C, base_h) in ANSI.items():
        target = min(
            (h_primary, h_secondary),
            key=lambda t: abs(((t - base_h + 180) % 360) - 180),
        )
        hue = blend_hue(base_h, target, HUE_PULL)
        out[token] = oklch_to_hex(L, C, hue)
        if token in BRIGHT:
            out["bright_" + token] = oklch_to_hex(L + 0.050, C + 0.012, hue)

    return out


ORDER = (
    "accent", "selection", "muted",
    "hyprland_active_border",
    None,
    "background", "dark_background", "darker_background", "lighter_background",
    None,
    "foreground", "dark_foreground", "light_foreground", "bright_foreground",
    None,
    "red", "yellow", "orange", "green", "cyan", "blue", "magenta", "brown",
    None,
    "bright_red", "bright_yellow", "bright_green", "bright_cyan",
    "bright_blue", "bright_magenta",
)


def to_toml(colors, header=""):
    lines = [header] if header else []
    lines.append('mode = "dark"')
    lines.append("")
    for token in ORDER:
        if token is None:
            lines.append("")
        else:
            lines.append('%s = "%s"' % (token, colors[token]))
    return "\n".join(lines).rstrip() + "\n"
