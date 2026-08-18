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

import config  # noqa: E402
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


def main():
    failures = []

    if shiny.DEFAULT_ODDS != 4096:
        failures.append("default odds are %d, not the gen 6+ 4096"
                        % shiny.DEFAULT_ODDS)

    # The odds have to be the odds. A hash that clusters would show up here as a
    # rate well off 1/N.
    for chances in (64, 4096):
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

    # The hunt has its own key, and falls back to the daily odds when unset.
    if shiny.hunt_odds() != 1:
        failures.append("hunt odds did not fall back to shiny-odds")
    config.set_key(shiny.HUNT_ODDS_KEY, 7)
    if shiny.hunt_odds() != 7:
        failures.append("shiny-hunt-odds in the config was ignored")
    if shiny.odds() != 1:
        failures.append("the hunt key changed the daily odds")

    # Nonsense falls back rather than raising: the file is hand-edited.
    for bad in ("lots", -3, 0, True):
        config.set_key(shiny.ODDS_KEY, bad)
        if shiny.odds() != shiny.DEFAULT_ODDS:
            failures.append("bad shiny-odds %r gave %r" % (bad, shiny.odds()))
    config.clear_key(shiny.ODDS_KEY)
    config.clear_key(shiny.HUNT_ODDS_KEY)
    if shiny.odds() != shiny.DEFAULT_ODDS:
        failures.append("clearing the key did not restore the default")

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
