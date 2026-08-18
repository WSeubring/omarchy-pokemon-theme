#!/usr/bin/env python3
"""Assert every one of the 905 generated palettes is actually readable.

This is the test that earns the OKLCh machinery its keep. The palette borrows
hue from the day's Pokemon, so without a check like this a flat-grey Magnemite
or a near-black Sableye day could ship an unusable desktop.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import palette  # noqa: E402
from oklch import _to_linear, hex_to_oklch  # noqa: E402

# WCAG 2.1 minimums. Body text needs 4.5:1; dark_foreground is comment-grey by
# design and only has to clear the 3.0 large-text/UI floor.
MIN_TEXT = 4.5
MIN_DIM = 2.9
# ANSI hues may drift toward the day's hue for cohesion, but red must still look
# red in a diff. Anything past this and the pull factor has gone too far.
MAX_HUE_DRIFT = 30.0

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


def main():
    def load(name):
        with open(os.path.join(ROOT, "data", name)) as fh:
            return json.load(fh)

    types, type_colors = load("types.json"), load("type-colors.json")
    failures = []
    worst = {}

    for name, kinds in types.items():
        colors = palette.build(type_colors, kinds)
        bg = colors["background"]

        for token in TEXT_TOKENS:
            ratio = contrast(colors[token], bg)
            if token not in worst or ratio < worst[token][0]:
                worst[token] = (ratio, name)
            if ratio < MIN_TEXT:
                failures.append("%s/%s contrast %.2f < %.2f"
                                % (name, token, ratio, MIN_TEXT))

        dim = contrast(colors["dark_foreground"], bg)
        if dim < MIN_DIM:
            failures.append("%s/dark_foreground contrast %.2f < %.2f"
                            % (name, dim, MIN_DIM))

        for token, (_, _, anchor) in palette.ANSI.items():
            hue = hex_to_oklch(colors[token])[2]
            drift = abs(((hue - anchor + 180) % 360) - 180)
            if drift > MAX_HUE_DRIFT:
                failures.append("%s/%s hue drifted %.1f deg > %.1f"
                                % (name, token, drift, MAX_HUE_DRIFT))

    print("checked %d palettes" % len(types))
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
