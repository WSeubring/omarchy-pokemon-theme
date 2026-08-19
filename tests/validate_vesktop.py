#!/usr/bin/env python3
"""Assert the generated Vesktop CSS is well-formed and readable, always.

Discord parses the file with no feedback channel: a malformed declaration is
silently dropped and the client falls back to its stock grey for that token,
which shows up as a half-themed mess rather than an error. The generated
layers are validated value by value; the vendored base16 file is a committed
constant, so it gets structural checks (present, balanced, still expecting
the base16 slots we fill) rather than a re-review on every palette.

Same two passes as validate_contrast: every type palette, then a hue sweep at
the artwork-extraction corners, because the accent can be any colour a sprite
contains.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import palette  # noqa: E402
import vesktop  # noqa: E402
from oklch import _to_linear, oklch_to_hex  # noqa: E402

# base01 backs the chat column in the vendored mapping, so body text (base05)
# needs the full 4.5:1 against it; the accent (base0D) draws buttons and links
# and clears the 3.0 UI floor.
MIN_TEXT = 4.5
MIN_UI = 3.0

SWEEP_LC = ((0.10, 0.01), (0.35, 0.08), (0.55, 0.20), (0.90, 0.32))
SWEEP_KINDS = (["normal"], ["fire", "flying"])

HEX = re.compile(r"^#[0-9a-f]{6}$")
HSL = re.compile(r"^(\d+\.\d) (\d+\.\d)% (\d+\.\d)%$")


def relative_luminance(value):
    h = value.lstrip("#")
    r, g, b = (_to_linear(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hsl_to_rgb(h, s, light):
    s, light = s / 100.0, light / 100.0
    c = (1 - abs(2 * light - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = light - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x),
               (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return tuple(round((v + m) * 255) for v in (r, g, b))


def check(label, colors, failures):
    for step, value in vesktop._primary(colors).items():
        if not HEX.match(value):
            failures.append("%s: primary-%d is %r" % (label, step, value))
    brand = vesktop._brand(colors["accent"])
    for step, value in brand.items():
        if not HEX.match(value):
            failures.append("%s: brand-%d is %r" % (label, step, value))
    if brand[500] != colors["accent"]:
        failures.append("%s: brand-500 is not the accent" % label)

    base = dict(vesktop.base16(colors))
    for slot, value in base.items():
        if not HEX.match(value):
            failures.append("%s: %s is %r" % (label, slot, value))

    # The HSL twins Discord composes translucent layers from must decode to
    # the same pixels as their hex siblings, or the translucent UI sits on a
    # subtly different colour than the opaque UI.
    for step, value in vesktop._primary(colors).items():
        m = HSL.match(vesktop._hsl(value))
        if not m:
            failures.append("%s: primary-%d hsl malformed" % (label, step))
            continue
        got = hsl_to_rgb(*(float(v) for v in m.groups()))
        want = tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        if any(abs(a - b) > 1 for a, b in zip(got, want)):
            failures.append("%s: primary-%d hsl decodes to %s, hex is %s"
                            % (label, step, got, want))

    # base0F is this vendored file's body text, base04 its headers and
    # secondary text -- both must read like text, not like decoration.
    # base03 is the muted tier and only clears the UI floor, same as
    # Discord's own muted grey.
    bg = base["base01"]
    for slot, floor in (("base03", MIN_UI), ("base04", MIN_TEXT),
                        ("base05", MIN_TEXT), ("base06", MIN_TEXT),
                        ("base07", MIN_TEXT), ("base0F", MIN_TEXT),
                        ("base0D", MIN_UI)):
        ratio = contrast(base[slot], bg)
        if ratio < floor:
            failures.append("%s: %s contrast %.2f < %.2f on base01"
                            % (label, slot, ratio, floor))

    # base00-02 are the surface ladder, base03-07 the text ladder; each must
    # keep its ordering or Discord's panels and text tiers collapse into one
    # another.
    surfaces = [relative_luminance(base["base0%d" % i]) for i in range(3)]
    texts = [relative_luminance(base["base0%d" % i]) for i in range(3, 8)]
    if surfaces != sorted(surfaces):
        failures.append("%s: base00-02 surface ladder not monotonic" % label)
    if texts != sorted(texts):
        failures.append("%s: base03-07 text ladder not monotonic" % label)


def check_assembly(failures):
    """The full file, once: layer order and vendored expectations."""
    colors = palette.build(
        json.load(open(os.path.join(ROOT, "data", "type-colors.json"))),
        ["fire", "flying"])
    text = vesktop.css(colors, "# provenance\n")

    if text.count("{") != text.count("}"):
        failures.append("assembled css has unbalanced braces")
    if text.count("@name") != 1:
        failures.append("assembled css must carry exactly one metadata block")

    vendored = vesktop._vendored()
    tail = text[text.index(vendored) + len(vendored):] if vendored in text \
        else ""
    if not tail:
        failures.append("vendored base16 css missing from assembly")
    for slot, value in vesktop.base16(colors):
        if "--%s: %s;" % (slot, value) not in tail:
            failures.append("--%s not overridden after the vendored css"
                            % slot)
    # The override only works while the vendored file still derives the slots
    # it is meant to shadow; a re-vendored upstream that renames them would
    # otherwise fail silently.
    for slot in ("base00", "base05", "base0D", "base0F"):
        if "--%s:" % slot not in vendored:
            failures.append("vendored css no longer defines --%s" % slot)
    if "url(" in vendored or "@import" in vendored:
        failures.append("vendored css reaches for the network")


def main():
    def load(name):
        with open(os.path.join(ROOT, "data", name)) as fh:
            return json.load(fh)

    types, type_colors = load("types.json"), load("type-colors.json")
    failures = []

    check_assembly(failures)

    for name, kinds in types.items():
        check(name, palette.build(type_colors, kinds), failures)
    print("checked %d type palettes" % len(types))

    swept = 0
    for hue in range(0, 360, 2):
        for L, C in SWEEP_LC:
            source = oklch_to_hex(L, C, float(hue))
            for kinds in SWEEP_KINDS:
                label = "artwork %s L%.2f C%.2f" % (source, L, C)
                check(label, palette.build(type_colors, kinds, source),
                      failures)
                swept += 1
    print("swept %d artwork palettes" % swept)

    if failures:
        for f in failures[:40]:
            print("FAIL: %s" % f)
        more = len(failures) - 40
        if more > 0:
            print("... and %d more" % more)
        sys.exit(1)
    print("vesktop CSS OK")


if __name__ == "__main__":
    main()
