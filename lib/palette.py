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

# The light ladder is not the dark one flipped: it carries far more chroma in
# the ground (a pastel wash of the day's hue -- stock light themes sit near
# C 0.010, where every Pokemon reads as the same off-white) and its foregrounds
# keep a visible cast of the hue too. Lightness values are solved, not
# averaged: each sits under the worst-case ceiling for its contrast floor
# against this background across all 360 background hues.
NEUTRALS_LIGHT = {
    "darker_background": (0.870, 0.033),
    "dark_background": (0.895, 0.033),
    "background": (0.930, 0.035),
    "lighter_background": (0.880, 0.037),
    "selection": (0.825, 0.039),
    "muted": (0.735, 0.041),
    "dark_foreground": (0.595, 0.045),
    "foreground": (0.365, 0.065),
    "light_foreground": (0.325, 0.067),
    "bright_foreground": (0.275, 0.069),
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

# Same hues on a light ground: darker and punchier, each L a solved 4.5:1
# ceiling against the light background (worst case over background hues) minus
# a margin for the hue pull. The chroma bump is what stops "dark enough to
# read" from collapsing into "all the same brown".
ANSI_LIGHT = {
    "red": (0.520, 0.190, 6.0),
    "orange": (0.510, 0.140, 32.0),
    "yellow": (0.495, 0.130, 81.0),
    "green": (0.485, 0.140, 136.0),
    "cyan": (0.485, 0.100, 196.0),
    "blue": (0.500, 0.160, 262.0),
    "magenta": (0.510, 0.150, 318.0),
    "brown": (0.420, 0.060, 33.0),
}

BRIGHT = ("red", "yellow", "green", "cyan", "blue", "magenta")

# The accent keeps its native lightness inside a band rather than being pinned.
# Pinning it outright turned every yellow into mustard: hue 95 simply does not
# read as "electric" below L 0.85, while a violet at that L is washed out. The
# band is wide enough to preserve type identity and still clear WCAG AA against
# the pinned backgrounds -- verified across all 905 by tests/validate_contrast.py.
ACCENT_L_MIN, ACCENT_L_MAX = 0.660, 0.865
ACCENT_C_MIN, ACCENT_C_MAX = 0.090, 0.170

# Light mode trades the accent's AA down to a 3.0 floor on purpose: at 4.5:1
# against a light ground every yellow and orange goes olive, which is the
# mustard problem all over again. 3.0 still beats every stock light theme's
# accent floor, and the ceiling 0.585 sits under the solved worst-case 0.605
# for 3.0:1 against the light background. Text stays at 4.5 -- the accent is
# chrome (borders, prompt, focus), not body copy.
ACCENT_L_MIN_LIGHT, ACCENT_L_MAX_LIGHT = 0.450, 0.585
ACCENT_C_MIN_LIGHT, ACCENT_C_MAX_LIGHT = 0.100, 0.210

# Intensity is a chroma multiplier over the whole palette, clamped to a range
# verified against both ladders by tests/validate_contrast.py. Lightness is
# untouched, which is why the knob cannot break contrast: on these grounds,
# chroma barely moves relative luminance.
INTENSITY_MIN, INTENSITY_MAX = 0.4, 1.6
CHROMA_CEILING = 0.32

# In "pokemon" mode, an accent at or above this OKLCh lightness earns the
# creature a light day. Sits in the natural gap in the accents' distribution:
# cream-and-yellow creatures (Pikachu, Mew, Milcery) land well above it, the
# mid-tone majority well below, so the answer is rarely a coin flip.
LIGHT_ACCENT_L = 0.80


def mode_for(accent_source):
    """The mode a creature earns in "pokemon" mode, from its accent colour.

    The one place this rule lives -- the generator, the wizards and the setup
    page all predict the same answer through it. No accent stays dark.
    """
    if not accent_source:
        return "dark"
    L = hex_to_oklch(accent_source)[0]
    return "light" if L >= LIGHT_ACCENT_L else "dark"

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


def _bands(mode):
    if mode == "light":
        return (ACCENT_L_MIN_LIGHT, ACCENT_L_MAX_LIGHT,
                ACCENT_C_MIN_LIGHT, ACCENT_C_MAX_LIGHT)
    return ACCENT_L_MIN, ACCENT_L_MAX, ACCENT_C_MIN, ACCENT_C_MAX


def _readable(hex_color, mode="dark"):
    """Lift a type colour into the accent's readable band, keeping its hue.

    Shared with the accent so a border stop and the accent agree: several type
    colours (dark, ghost, steel) are too dim or too flat to read as a border
    against the palette's own background at their native lightness.
    """
    lmin, lmax, cmin, cmax = _bands(mode)
    L, C, H = hex_to_oklch(hex_color)
    return oklch_to_hex(
        min(max(L, lmin), lmax),
        min(max(C, cmin), cmax),
        H,
    )


def _border(accent, type_colors, types, mode="dark"):
    """A one- or two-stop Hyprland gradient spec: the accent, then the second type.

    The first stop is whatever the accent came from -- the creature's own colour
    when the artwork was readable, its primary type otherwise -- so the border
    always agrees with the rest of the palette. The second stop stays type-based:
    it is there to say "this one is also a poison type", which is a fact about the
    category, not about the pixels.
    """
    stops = [accent]
    if len(types) > 1:
        stops.append(_readable(type_colors[types[1]], mode))
    spec = " ".join("rgba(%s%s)" % (s.lstrip("#"), BORDER_ALPHA) for s in stops)
    if len(stops) < 2:
        return spec
    return "%s %ddeg" % (spec, BORDER_ANGLE)


def _scale_chroma(colors, intensity):
    """Multiply every token's chroma; lightness (and so contrast) stays put.

    The border spec is rebuilt from its own stops so the window border keeps
    agreeing with the accent it was derived from.
    """
    out = {}
    for token, value in colors.items():
        if token == "hyprland_active_border":
            continue
        L, C, H = hex_to_oklch(value)
        out[token] = oklch_to_hex(L, min(C * intensity, CHROMA_CEILING), H)
    parts = []
    for part in colors["hyprland_active_border"].split():
        if part.endswith("deg"):
            parts.append(part)
            continue
        L, C, H = hex_to_oklch("#" + part[5:11])  # rgba(rrggbbaa)
        scaled = oklch_to_hex(L, min(C * intensity, CHROMA_CEILING), H)
        parts.append("rgba(%s%s)" % (scaled.lstrip("#"), BORDER_ALPHA))
    out["hyprland_active_border"] = " ".join(parts)
    return out


def clamp_intensity(value):
    return min(max(value, INTENSITY_MIN), INTENSITY_MAX)


def build(type_colors, types, accent_source=None, mode="dark", intensity=1.0):
    """types: 1-2 type names, in order. Returns {token: hex}.

    `accent_source` is a hex colour to take the accent from -- the creature's
    dominant artwork colour -- instead of its primary type. Only hue and a
    clamped lightness survive either way, so the two paths differ in identity,
    not in readability.
    """
    neutrals = NEUTRALS_LIGHT if mode == "light" else NEUTRALS_DARK
    ansi = ANSI_LIGHT if mode == "light" else ANSI

    out = {}
    out["accent"] = _readable(accent_source or type_colors[types[0]], mode)
    h_primary = hex_to_oklch(out["accent"])[2]
    h_secondary = h_primary
    if len(types) > 1:
        h_secondary = hex_to_oklch(type_colors[types[1]])[2]

    out["hyprland_active_border"] = _border(out["accent"], type_colors, types,
                                            mode)

    for token, (L, C) in neutrals.items():
        hue = h_secondary if token in SECONDARY_KEYS else h_primary
        out[token] = oklch_to_hex(L, C, hue)

    # Pull toward whichever type hue each ANSI anchor is already closer to, so a
    # dual type contributes both hues rather than averaging into one.
    for token, (L, C, base_h) in ansi.items():
        target = min(
            (h_primary, h_secondary),
            key=lambda t: abs(((t - base_h + 180) % 360) - 180),
        )
        hue = blend_hue(base_h, target, HUE_PULL)
        out[token] = oklch_to_hex(L, C, hue)
        if token in BRIGHT:
            # Bright means "more contrast": up on a dark ground, down on a
            # light one.
            dL = -0.040 if mode == "light" else 0.050
            out["bright_" + token] = oklch_to_hex(L + dL, C + 0.012, hue)

    intensity = clamp_intensity(intensity)
    if intensity != 1.0:
        out = _scale_chroma(out, intensity)
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


def to_toml(colors, header="", mode="dark"):
    lines = [header] if header else []
    lines.append('mode = "%s"' % mode)
    lines.append("")
    for token in ORDER:
        if token is None:
            lines.append("")
        else:
            lines.append('%s = "%s"' % (token, colors[token]))
    return "\n".join(lines).rstrip() + "\n"
