"""Emit the theme's `shell.lock.toml`, pinning the lock screen to the day.

omarchy-lock-pokemon already supports pinning via `lock.pokemon-name`, so
aligning the two needs no change to the plugin -- the theme just names the day's
Pokemon and the lock screen stops rolling its own.

The catch is that `omarchy-theme-set-templates` *replaces* a section rather than
merging keys, so this file has to restate every `[lock]` token the stock
shell.toml.tpl generates. Colour tokens are emitted as hex from the day's
palette; the two border tokens stay as literal `hyprland.*` references so they
keep tracking the Hyprland gradient instead of being frozen here.
"""

# Mirrors the [lock] block of default/themed/shell.toml.tpl. Values that are not
# colours are copied verbatim so the lock screen keeps the stock feel.
BACKGROUND_ALPHA = 0.8
BORDER_ALPHA = 1.0
SELECTION_ALPHA = 0.45
# The template's `{{ mix foreground background 34% }}`.
PLACEHOLDER_MIX = 0.34


def mix(start, end, amount):
    """Blend two hex colours the way omarchy's own `mix_color` does.

    Deliberately plain sRGB interpolation with round-half-up, not the OKLCh
    blending used elsewhere here: the point is to match the generated value the
    stock template would have produced, not to improve on it.
    """
    a = start.lstrip("#")
    b = end.lstrip("#")
    out = []
    for i in (0, 2, 4):
        sa, sb = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(int(sa * (1 - amount) + sb * amount + 0.5))
    return "#%02x%02x%02x" % tuple(out)


def section(colors, pokemon_name, header=""):
    placeholder = mix(colors["foreground"], colors["background"],
                      PLACEHOLDER_MIX)
    rows = (
        # Pinning the name is the whole point of this file; everything below it
        # only exists because the override replaces the section wholesale.
        ("pokemon-name", '"%s"' % pokemon_name),
        ("background", '"%s"' % colors["background"]),
        ("background-alpha", BACKGROUND_ALPHA),
        ("text", '"%s"' % colors["foreground"]),
        ("placeholder", '"%s"' % placeholder),
        ("text-error", '"%s"' % colors["red"]),
        ("border", '"hyprland.active-border"'),
        ("border-active", '"hyprland.active-border"'),
        ("border-error", '"%s"' % colors["red"]),
        ("border-alpha", BORDER_ALPHA),
        ("selection", '"%s"' % colors["accent"]),
        ("selection-alpha", SELECTION_ALPHA),
    )
    width = max(len(key) for key, _ in rows)
    # The section header comes first and the comments after it: the splice in
    # omarchy-theme-set-templates strips the `[lock]` line and re-emits it above
    # whatever follows, so anything written above it would be relocated anyway.
    lines = ["[lock]"]
    if header:
        lines.append(header.rstrip("\n"))
    for key, value in rows:
        lines.append("%-*s = %s" % (width, key, value))
    return "\n".join(lines) + "\n"
