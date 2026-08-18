#!/usr/bin/env python3
"""Check the shiny odds: honest, configurable, and stable across a day.

Three things can go quietly wrong here. Odds that are not really the odds, so a
"1 in 4096" event happens monthly. A roll that is not deterministic, so the timer
and the theme-set hook disagree and the desktop flickers between finishes. And a
config value that is silently ignored, which is the worst kind of setting.

Runs against a temporary XDG config directory, so the real config is never read
or written.
"""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both modules resolve their paths from the environment at import time, so the
# sandbox has to be in place before they are imported.
SANDBOX = tempfile.mkdtemp(prefix="pokemon-theme-shiny-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(SANDBOX, "config")
os.environ["XDG_STATE_HOME"] = os.path.join(SANDBOX, "state")

sys.path.insert(0, os.path.join(ROOT, "lib"))

import ambient  # noqa: E402
import config  # noqa: E402
import lockscreen  # noqa: E402
import shiny  # noqa: E402

# Enough draws that a rate off by a factor of two cannot hide, few enough that
# the test stays instant.
DRAWS = 400_000
TOLERANCE = 0.25


def rate(chances, draws=DRAWS):
    """Observed hits per draw, over distinct day/name pairs."""
    hits = sum(1 for i in range(draws)
               if shiny.rolled("2026-%02d-%02d" % (i % 12 + 1, i % 28 + 1),
                               "mon%d" % i, chances))
    return hits / draws


def _value(section, key):
    """The value of `key` in a rendered TOML section. Keys are padded to align."""
    for line in section.splitlines():
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip()
    return None


def main():
    failures = []

    # A day is the unit, so the default is a fortnight rather than the canonical
    # per-encounter number. Guard the range, not the exact value: something that
    # drifted to 4096 (a decade) or to 2 (twice a week) would be a mistake.
    if not 7 <= shiny.DEFAULT_ODDS <= 60:
        failures.append("default odds of 1 in %d are not roughly a fortnight"
                        % shiny.DEFAULT_ODDS)

    # The odds have to be the odds. A hash that clusters would show up here as a
    # rate well off 1/N.
    for chances in (14, 64, 4096):
        observed = rate(chances)
        expected = 1 / chances
        if abs(observed - expected) > expected * TOLERANCE:
            failures.append("1 in %d drew 1 in %.0f"
                            % (chances, 1 / max(observed, 1e-9)))
        print("  1 in %-6d observed 1 in %6.0f" % (chances, 1 / max(observed, 1e-9)))

    # Same day, same name, same answer -- however many times anything asks.
    if len({shiny.rolled("2026-08-18", "gengar", 8) for _ in range(50)}) != 1:
        failures.append("the daily roll is not deterministic")

    # A shiny day must not depend on which source picked the Pokemon, only on
    # the day and the name.
    pinned = shiny.rolled("2026-08-18", "gengar", 8)
    if pinned != shiny.rolled("2026-08-18", "gengar", 8):
        failures.append("the roll depends on something other than day and name")

    # Degenerate odds are usable rather than crashing: 1 means always.
    if not shiny.rolled("2026-08-18", "gengar", 1):
        failures.append("odds of 1 in 1 did not produce a shiny")
    if shiny.rolled("2026-08-18", "gengar", 0):
        failures.append("odds of 0 produced a shiny")

    # The config has to actually reach the roll.
    config.set_key(shiny.ODDS_KEY, 1)
    if shiny.odds() != 1:
        failures.append("shiny-odds in the config was ignored: %r" % shiny.odds())
    if not shiny.rolled("2026-08-18", "gengar"):
        failures.append("configured odds of 1 did not produce a shiny")

    # Nonsense falls back rather than raising: the file is hand-edited.
    for bad in ("lots", -3, 0, True):
        config.set_key(shiny.ODDS_KEY, bad)
        if shiny.odds() != shiny.DEFAULT_ODDS:
            failures.append("bad shiny-odds %r gave %r" % (bad, shiny.odds()))
    config.clear_key(shiny.ODDS_KEY)
    if shiny.odds() != shiny.DEFAULT_ODDS:
        failures.append("clearing the key did not restore the default")

    # A shiny day has to reach the other two surfaces, not just the wallpaper:
    # the ambient plugin's twinkles, and the lock screen's own sparkle.
    effects = {"fire": {"effect": "embers"}, "flying": {"effect": "gusts"}}
    colors = {"fire": "#EE8130", "flying": "#A98FF3"}
    plain = ambient.section(effects, colors, ["fire", "flying"])
    lit = ambient.section(effects, colors, ["fire", "flying"], is_shiny=True)
    if ambient.SHINY_EFFECT not in lit:
        failures.append("a shiny day did not switch the ambient effect")
    if ambient.SHINY_EFFECT in plain:
        failures.append("an ordinary day got the shiny ambient effect")
    if _value(lit, "effect-intensity") != str(ambient.SHINY_INTENSITY):
        failures.append("a shiny day did not turn the motion up: %s"
                        % _value(lit, "effect-intensity"))

    palette_colors = {"foreground": "#eeeeee", "background": "#191919",
                      "red": "#e06c75", "accent": "#d47075"}
    lock_lit = lockscreen.section(palette_colors, "charizard", is_shiny=True)
    lock_plain = lockscreen.section(palette_colors, "charizard")
    if _value(lock_lit, "pokemon-shiny") != '"always"':
        failures.append("a shiny day did not tell the lock screen")
    if 'pokemon-shiny' in lock_plain:
        failures.append("an ordinary day pinned the lock screen's own roll")

    shutil.rmtree(SANDBOX, ignore_errors=True)

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("\nshiny odds ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
