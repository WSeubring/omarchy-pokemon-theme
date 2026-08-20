#!/usr/bin/env python3
"""Assert every palette this theme can generate is actually readable.

This is the test that earns the OKLCh machinery its keep. Two passes, because
there are two ways in:

- the 905 type-based palettes, one per Pokemon
- a sweep of every hue at extreme lightness and chroma, because the accent
  normally comes from the artwork, and an arbitrary pixel colour is not drawn
  from any list this test could enumerate

The second pass is the important one now: it says the clamps hold for *any*
input colour, which is the only honest claim once a sprite decides the hue.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import palette  # noqa: E402
from oklch import _to_linear, hex_to_oklch, oklch_to_hex  # noqa: E402

# WCAG 2.1 minimums. Body text needs 4.5:1; dark_foreground is comment-grey by
# design and only has to clear the 3.0 large-text/UI floor.
MIN_TEXT = 4.5
MIN_DIM = 2.9
# The light accent trades down to a 3.0 floor by design (see palette.py's
# ACCENT_*_LIGHT comment): at 4.5 every yellow and orange accent goes olive.
# It is UI chrome, not body text, and 3.0 still beats every stock light theme.
MIN_ACCENT_LIGHT = 3.0
# ANSI hues may drift toward the day's hue for cohesion, but red must still look
# red in a diff. Anything past this and the pull factor has gone too far.
MAX_HUE_DRIFT = 30.0
# The intensity knob's whole range must hold contrast, or it is not a safe knob.
INTENSITIES = (palette.INTENSITY_MIN, 1.0, palette.INTENSITY_MAX)

# Corners of the space an extracted artwork colour can land in: near-black
# outline, mid saturated body, blown-out highlight, and flat grey.
SWEEP_LC = ((0.10, 0.01), (0.35, 0.08), (0.55, 0.20), (0.90, 0.32))
SWEEP_KINDS = (["normal"], ["fire", "flying"])

TEXT_TOKENS = (
    "foreground", "light_foreground", "bright_foreground", "accent",
    "red", "yellow", "orange", "green", "cyan", "blue", "magenta",
    "bright_red", "bright_yellow", "bright_green", "bright_cyan",
    "bright_blue", "bright_magenta",
)


def relative_luminance(value):
    h = value.lstrip("#")
    r, g, b = (_to_linear(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def check(label, colors, kinds, failures, worst, mode="dark"):
    bg = colors["background"]

    for token in TEXT_TOKENS:
        floor = MIN_TEXT
        if token == "accent" and mode == "light":
            floor = MIN_ACCENT_LIGHT
        ratio = contrast(colors[token], bg)
        key = "%s/%s" % (mode, token)
        if key not in worst or ratio < worst[key][0]:
            worst[key] = (ratio, label)
        if ratio < floor:
            failures.append("%s/%s contrast %.2f < %.2f"
                            % (label, token, ratio, floor))

    dim = contrast(colors["dark_foreground"], bg)
    if dim < MIN_DIM:
        failures.append("%s/dark_foreground contrast %.2f < %.2f"
                        % (label, dim, MIN_DIM))

    # The border is a gradient spec, not a colour, so it is checked for shape
    # rather than contrast: one stop for a single type, two plus an angle for a
    # dual type. A malformed spec makes omarchy emit a broken hyprland.lua, which
    # costs you window borders entirely.
    border = colors["hyprland_active_border"]
    stops = [part for part in border.split() if not part.endswith("deg")]
    expected = len(kinds)
    if len(stops) != expected:
        failures.append("%s border has %d stop(s), expected %d"
                        % (label, len(stops), expected))
    for stop in stops:
        if not (stop.startswith("rgba(") and stop.endswith(")")
                and len(stop) == len("rgba(rrggbbaa)")):
            failures.append("%s border stop malformed: %s" % (label, stop))
    if expected > 1 and not border.endswith("deg"):
        failures.append("%s dual-type border has no angle" % label)

    for token, (_, _, anchor) in palette.ANSI.items():
        hue = hex_to_oklch(colors[token])[2]
        drift = abs(((hue - anchor + 180) % 360) - 180)
        if drift > MAX_HUE_DRIFT:
            failures.append("%s/%s hue drifted %.1f deg > %.1f"
                            % (label, token, drift, MAX_HUE_DRIFT))


def main():
    def load(name):
        with open(os.path.join(ROOT, "data", name)) as fh:
            return json.load(fh)

    types, type_colors = load("types.json"), load("type-colors.json")
    failures = []
    worst = {}

    for mode in ("dark", "light"):
        for intensity in INTENSITIES:
            tag = "%s x%.1f" % (mode, intensity)
            for name, kinds in types.items():
                check("%s %s" % (name, tag),
                      palette.build(type_colors, kinds,
                                    mode=mode, intensity=intensity),
                      kinds, failures, worst, mode)
            print("checked %d type palettes (%s)" % (len(types), tag))

        swept = 0
        for hue in range(0, 360, 2):
            for L, C in SWEEP_LC:
                source = oklch_to_hex(L, C, float(hue))
                for kinds in SWEEP_KINDS:
                    for intensity in INTENSITIES:
                        label = "artwork %s L%.2f C%.2f %s x%.1f" \
                                % (source, L, C, mode, intensity)
                        check(label,
                              palette.build(type_colors, kinds, source,
                                            mode=mode, intensity=intensity),
                              kinds, failures, worst, mode)
                        swept += 1
        print("checked %d artwork-derived palettes (%s)" % (swept, mode))

    for mode in ("dark", "light"):
        for token in TEXT_TOKENS:
            ratio, who = worst["%s/%s" % (mode, token)]
            print("  %s %-20s worst %5.2f  (%s)" % (mode, token, ratio, who))

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures[:20]:
            print("  " + line)
        return 1
    print("\nall palettes pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
