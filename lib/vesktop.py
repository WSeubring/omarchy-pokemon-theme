"""Retint Vesktop (Discord) to the day's palette.

The heavy lifting is a vendored copy of base16-discord (data/
vencord-base16.css, MIT), the same base the community's Omarchy themes build
their vencord.theme.css on. It remaps 150+ Discord tokens -- including the
redesigned "visual refresh" UI, which no longer derives from the legacy
variable scales -- down to sixteen base16 slots, and this module's job is
just to fill those slots from the day's palette in a :root block appended
after it, which wins over the vendored derivations.

Regenerated `--primary-*` / `--brand-*` ladders (with the -hsl twins Discord
composes translucency from) ride along underneath, covering the derived
tokens the vendored file does not pin.

The file is a build product exactly like colors.toml -- the palette changes
daily, so it is written into the client's themes directory on every
generation rather than shipped as a static file. Vencord watches that
directory, so the rewrite lands live once the theme is enabled -- and the
generator enables it itself in the client's settings (see _enable).

Each scale step is generated at a pinned OKLCh lightness, the same move that
keeps colors.toml readable for all 905 Pokemon: hue and chroma come from the
day, the depth relationships between Discord's surfaces stay put.
"""

import json
import os

import atomic
from oklch import hex_to_oklch, oklch_to_hex

FILENAME = "pokemon.css"

# Vesktop native, Vesktop flatpak, and stock Discord with the Vencord mod.
# The same CSS works in all of them, and writing an extra file costs nothing,
# so every installed client gets one.
CONFIG_DIRS = (
    "~/.config/vesktop",
    "~/.var/app/dev.vencord.Vesktop/config/vesktop",
    "~/.config/Vencord",
)

# Neutral scale, lightness per step. The dark anchors reuse the exact L values
# NEUTRALS_DARK pins (600 = background, 630 = dark_background, 700 =
# darker_background, ...), so Discord's chrome sits on the same surfaces as
# the terminal; the rest interpolate Discord's own stock spacing between them.
PRIMARY_L = {
    130: 0.930, 160: 0.905, 200: 0.880, 230: 0.858, 260: 0.838,
    300: 0.800, 330: 0.720, 360: 0.660, 400: 0.560, 430: 0.500,
    460: 0.443, 500: 0.400, 530: 0.355, 560: 0.303, 600: 0.235,
    630: 0.200, 645: 0.192, 660: 0.186, 670: 0.181, 680: 0.176,
    700: 0.172, 730: 0.155, 800: 0.135, 900: 0.115,
}

# Light mode's scale, anchored the same way to NEUTRALS_LIGHT (600 =
# background 0.930, 630 = dark_background 0.895, 700 = darker_background
# 0.870); the low steps become the text end and the high end stays a shade
# below white so Discord's chrome keeps the palette's pastel cast.
PRIMARY_L_LIGHT = {
    130: 0.235, 160: 0.270, 200: 0.310, 230: 0.345, 260: 0.380,
    300: 0.430, 330: 0.510, 360: 0.580, 400: 0.660, 430: 0.720,
    460: 0.760, 500: 0.795, 530: 0.825, 560: 0.880, 600: 0.930,
    630: 0.895, 645: 0.890, 660: 0.885, 670: 0.880, 680: 0.876,
    700: 0.870, 730: 0.855, 800: 0.840, 900: 0.820,
}

BRAND_STEPS = (100, 130, 160, 200, 230, 260, 300, 330, 360, 400, 430, 460,
               500, 530, 560, 600, 630, 660, 700, 730, 760, 800, 830, 860,
               900)


def _neutral_chroma(L, mode="dark"):
    """Chroma for a neutral at lightness L.

    NEUTRALS_DARK's ladder rises from C 0.015 at its darkest to 0.050 at its
    lightest; a straight line through those endpoints keeps the generated
    steps on the same tint curve as the palette they sit between. The light
    ladder runs the other way: its pastel surfaces sit near 0.035 and its
    text end near 0.065, so the line flips.
    """
    t = max(0.0, min(1.0, (L - 0.17) / 0.70))
    if mode == "light":
        return 0.065 - 0.030 * t
    return 0.015 + 0.035 * t


def _primary(colors, mode="dark"):
    """{step: hex} for the neutral scale, tinted with the background's hue."""
    ladder = PRIMARY_L_LIGHT if mode == "light" else PRIMARY_L
    hue = hex_to_oklch(colors["background"])[2]
    return {step: oklch_to_hex(L, _neutral_chroma(L, mode), hue)
            for step, L in ladder.items()}


def _brand(accent):
    """{step: hex} for the accent scale, anchored so 500 *is* the accent.

    Discord's own scale steps by roughly 0.075 L per 100; the clamp keeps the
    far ends inside sRGB and the gamut mapper in oklch_to_hex walks chroma
    down where a light step at full chroma would not fit.
    """
    L, C, H = hex_to_oklch(accent)
    out = {}
    for step in BRAND_STEPS:
        if step == 500:
            out[step] = accent
            continue
        stepped = min(0.970, max(0.120, L + (500 - step) / 400.0 * 0.30))
        out[step] = oklch_to_hex(stepped, C, H)
    return out


def _hsl(value):
    """Hex to Discord's space-separated HSL component format.

    Discord composes translucent surfaces as hsl(var(--primary-630-hsl)/.6),
    so overriding only the hex variables would leave every translucent layer
    on the stock grey. Both spellings have to move together.
    """
    h = value.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hi, lo = max(r, g, b), min(r, g, b)
    light = (hi + lo) / 2.0
    if hi == lo:
        hue = sat = 0.0
    else:
        d = hi - lo
        sat = d / (2.0 - hi - lo) if light > 0.5 else d / (hi + lo)
        if hi == r:
            hue = ((g - b) / d) % 6.0
        elif hi == g:
            hue = (b - r) / d + 2.0
        else:
            hue = (r - g) / d + 4.0
        hue *= 60.0
    return "%.1f %.1f%% %.1f%%" % (hue, sat * 100.0, light * 100.0)


def _text_shade(colors, L):
    """A text grey at lightness L on the foreground's hue, for the slots the
    vendored CSS reads as muted/secondary text but the palette has no token
    for -- dark_foreground (L 0.52) disappears on Discord's larger surfaces.
    """
    _, C, H = hex_to_oklch(colors["foreground"])
    return oklch_to_hex(L, C, H)


def base16(colors, mode="dark"):
    """(slot, hex) rows for the vendored base theme, in slot order.

    Slot meanings read from how the vendored CSS actually spends them, which
    is close to but not quite canonical base16: 00-02 are the surface ladder
    (base00 the sidebars, base01 the chat, base02 floats and code), 03-07 the
    text ladder from muted to bright (03 doubles as hover/selection fills --
    the vendored ::selection puts base00 text on a base03 background, so a
    light 03 is the intended reading, not an accident), 08-0E the accents
    with base0D as *the* accent (brand, links, checkboxes), and 0F -- brown
    in canonical base16 -- is this file's *body text* (--text-normal and
    --text-primary), so it has to be the brightest foreground, not brown.
    """
    c = colors
    # The two generated text greys flip with the ground: dim-but-readable on
    # dark is 0.66/0.74, on light it is 0.60/0.50 (base04 the more legible).
    shade03, shade04 = (0.600, 0.500) if mode == "light" else (0.660, 0.740)
    return (
        ("base00", c["dark_background"]),
        ("base01", c["background"]),
        ("base02", c["lighter_background"]),
        ("base03", _text_shade(c, shade03)),
        ("base04", _text_shade(c, shade04)),
        ("base05", c["foreground"]),
        ("base06", c["light_foreground"]),
        ("base07", c["bright_foreground"]),
        ("base08", c["red"]),
        ("base09", c["orange"]),
        ("base0A", c["yellow"]),
        ("base0B", c["green"]),
        ("base0C", c["cyan"]),
        ("base0D", c["accent"]),
        ("base0E", c["magenta"]),
        ("base0F", c["bright_foreground"]),
    )


def _vendored():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "data", "vencord-base16.css")) as fh:
        return fh.read()


def css(colors, header="", mode="dark"):
    """The full theme file. `header` is the colors.toml provenance header."""
    lines = [
        "/**",
        " * @name Pokemon of the Day",
        " * @description Omarchy pokemon-theme palette, regenerated daily."
        " Do not edit by hand.",
        " * @author omarchy-pokemon-theme",
        " * @version 1.0.0",
        " */",
    ]
    for row in header.strip().splitlines():
        lines.append("/* %s */" % row.lstrip("# ").rstrip())
    lines.append("")

    lines.append(":root {")
    for step, value in sorted(_primary(colors, mode).items()):
        lines.append("  --primary-%d: %s;" % (step, value))
        lines.append("  --primary-%d-hsl: %s;" % (step, _hsl(value)))
    for step, value in sorted(_brand(colors["accent"]).items()):
        lines.append("  --brand-%d: %s;" % (step, value))
        lines.append("  --brand-%d-hsl: %s;" % (step, _hsl(value)))
    lines.append("}")

    lines.append("")
    lines.append(_vendored().rstrip())

    # After the vendored file so these :root declarations override its
    # var(--color..) derivations. The --colorNN ramp is still defined because
    # the vendored rule bodies reference some of them directly (color07 backs
    # --interactive-normal and --text-default; color00/05 feed the
    # .theme-light re-derivation) -- an undefined one leaves the declaration
    # invalid and the stock colour showing.
    lines.append("")
    lines.append(":root {")
    for slot, value in base16(colors, mode):
        lines.append("  --%s: %s;" % (slot, value))
    ramp = ("dark_background", "background", "lighter_background",
            "selection", "muted", "foreground", "light_foreground",
            "bright_foreground")
    for i, token in enumerate(ramp):
        lines.append("  --color%02d: %s;" % (i, colors[token]))
    lines.append("}")

    # A light base03 is right for text but loud where the vendored mapping
    # also spends it as a fill: hovers, disabled buttons, mention and brand
    # tints. Those go back to surface colours here; !important because the
    # vendored declarations carry it too and these come later.
    fixes = (
        ("--background-accent", colors["selection"]),
        ("--bg-brand", colors["selection"]),
        ("--background-mentioned",
         "color-mix(in srgb, %s 25%%, %s)"
         % (colors["accent"], colors["background"])),
        ("--background-mentioned-hover",
         "color-mix(in srgb, %s 35%%, %s)"
         % (colors["accent"], colors["background"])),
        ("--mention-background",
         "color-mix(in srgb, %s 25%%, %s)"
         % (colors["accent"], colors["background"])),
        ("--button-filled-brand-background-hover", "var(--brand-430)"),
        ("--button-secondary-background-hover", colors["selection"]),
        ("--button-secondary-background-disabled", colors["selection"]),
        ("--button-positive-background-hover", colors["selection"]),
        ("--button-positive-background-disabled", colors["selection"]),
        ("--button-danger-background-disabled", colors["selection"]),
        ("--menu-item-default-hover-bg", colors["lighter_background"]),
        ("--redesign-button-secondary-background",
         colors["lighter_background"]),
        ("--input-border", colors["muted"]),
        ("--checkbox-border-default", colors["muted"]),
        ("--status-warning-background", colors["selection"]),
        # Not in the vendored mapping at all.
        ("--background-nested-floating", colors["dark_background"]),
        ("--focus-primary", colors["accent"]),
        ("--brand-experiment", colors["accent"]),
    )
    lines.append("")
    lines.append(".theme-dark, .theme-light, .visual-refresh {")
    for key, value in fixes:
        lines.append("  %s: %s !important;" % (key, value))
    lines.append("}")
    return "\n".join(lines) + "\n"


def targets():
    """Theme files to write, one per installed client; [] when none.

    Existence of the client's config directory is the install check -- the
    themes/ subdirectory is created rather than required, since a fresh
    Vesktop only makes it on first visit to the themes settings page.
    """
    out = []
    for base in CONFIG_DIRS:
        base = os.path.expanduser(base)
        if not os.path.isdir(base):
            continue
        themes = os.path.join(base, "themes")
        os.makedirs(themes, exist_ok=True)
        out.append(os.path.join(themes, FILENAME))
        _enable(base)
    return out


def _enable(base):
    """Add the theme to Vencord's enabledThemes, so no manual toggle.

    Vencord reads settings/settings.json at startup only, and a *running*
    client rewrites the file from memory when it quits -- so an edit made
    while it is open can be lost. The generator runs daily, which makes this
    self-healing: the entry is re-added on the next roll and sticks the first
    time the client happens to be closed.

    A missing settings file means the client has never started; Vencord
    creates it with defaults on first run, and guessing at that schema here
    would risk more than the toggle saves, so first-run users toggle once.
    """
    path = os.path.join(base, "settings", "settings.json")
    try:
        with open(path) as fh:
            settings = json.load(fh)
    except (OSError, ValueError):
        return
    enabled = settings.setdefault("enabledThemes", [])
    if not isinstance(enabled, list) or FILENAME in enabled:
        return
    enabled.append(FILENAME)
    atomic.text(path, json.dumps(settings, indent=4) + "\n")
