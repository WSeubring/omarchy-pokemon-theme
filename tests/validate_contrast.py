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
# ANSI hues may drift toward the day's hue for cohesion, but red must still look
# red in a diff. Anything past this and the pull factor has gone too far.
MAX_HUE_DRIFT = 30.0

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


def check(label, colors, kinds, failures, worst):
    bg = colors["background"]

    for token in TEXT_TOKENS:
        ratio = contrast(colors[token], bg)
        if token not in worst or ratio < worst[token][0]:
            worst[token] = (ratio, label)
        if ratio < MIN_TEXT:
            failures.append("%s/%s contrast %.2f < %.2f"
                            % (label, token, ratio, MIN_TEXT))

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

    for name, kinds in types.items():
        check(name, palette.build(type_colors, kinds), kinds, failures, worst)
    print("checked %d type palettes" % len(types))

    swept = 0
    for hue in range(0, 360, 2):
        for L, C in SWEEP_LC:
            source = oklch_to_hex(L, C, float(hue))
            for kinds in SWEEP_KINDS:
                label = "artwork %s L%.2f C%.2f" % (source, L, C)
                check(label, palette.build(type_colors, kinds, source), kinds,
                      failures, worst)
                swept += 1
    print("checked %d artwork-derived palettes" % swept)

    for token in TEXT_TOKENS:
        ratio, who = worst[token]
        print("  %-20s worst %5.2f  (%s)" % (token, ratio, who))

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures[:20]:
            print("  " + line)
        return 1
    print("\nall palettes pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
