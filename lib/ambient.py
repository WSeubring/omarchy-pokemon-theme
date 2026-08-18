"""Emit the theme's `shell.background.toml`, driving the ambient plugin.

The plugin knows nothing about Pokemon -- it takes effect names, a tint and an
intensity. Resolving types to effects happens here, so the plugin stays a
generic ambient-background renderer and this file stays the only place that
knows a Gengar should be surrounded by wisps.

Written unconditionally, even when the plugin is not installed. The section is
inert without it, and writing it anyway means installing the plugin later needs
no regeneration.
"""

import tomlout
from tomlout import quote

# The plugin's own default is off, so a theme that says nothing animates nothing.
# This is the value written when the user opts in.
DEFAULT_INTENSITY = 0.55
DEFAULT_VARIANT = 1
# The second type's layer sits behind the first at reduced density.
SECONDARY_STRENGTH = 0.5
# Motion on the desktop is a background detail, not a focal point: it should be
# noticeable when you look at an empty workspace and invisible otherwise.
PAUSE_WHEN_COVERED = "true"
PAUSE_ON_BATTERY = "low"
PAUSE_ON_BATTERY_BELOW = 30


def section(type_effects, type_colors, types, enabled=True,
            intensity=DEFAULT_INTENSITY, header=""):
    """Build the `[background]` block for a Pokemon's types."""
    primary = type_effects[types[0]]["effect"]
    secondary = ""
    secondary_tint = ""
    if len(types) > 1:
        secondary = type_effects[types[1]]["effect"]
        secondary_tint = type_colors[types[1]]

    rows = (
        ("effects", quote("show" if enabled else "hide")),
        ("effect-primary", quote(primary)),
        ("effect-secondary", quote(secondary)),
        ("effect-secondary-strength", SECONDARY_STRENGTH),
        ("effect-intensity", intensity),
        ("effect-variant", DEFAULT_VARIANT),
        # Shapes take the type colour rather than the palette accent: the accent
        # is lightness-clamped for text contrast, which is the wrong trade-off
        # for a few translucent shapes drifting over a dark wallpaper.
        ("effect-tint", quote(type_colors[types[0]])),
        ("effect-secondary-tint", quote(secondary_tint)),
        ("pause-when-covered", quote(PAUSE_WHEN_COVERED)),
        ("pause-on-battery", quote(PAUSE_ON_BATTERY)),
        ("pause-on-battery-below", PAUSE_ON_BATTERY_BELOW),
    )
    return tomlout.section("background", rows, header)
