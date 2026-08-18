#!/usr/bin/env python3
"""Check the pin precedence, and that a today-only pin really expires.

Four sources decide the day's Pokemon and they have different lifetimes, so the
failure modes are quiet ones: a pin that outlives the day it was set for, or a
permanent pin that a stale today-file keeps shadowing forever.

Runs against temporary XDG directories so it never reads or writes the real
config or state.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both modules resolve their paths from the environment at import time, so this
# has to happen before they are imported.
SANDBOX = tempfile.mkdtemp(prefix="pokemon-theme-pins-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(SANDBOX, "config")
os.environ["XDG_STATE_HOME"] = os.path.join(SANDBOX, "state")

sys.path.insert(0, os.path.join(ROOT, "lib"))

import config  # noqa: E402
import pins  # noqa: E402

TODAY, TOMORROW = "2026-08-18", "2026-08-19"


def main():
    with open(os.path.join(ROOT, "data", "dex.json")) as fh:
        dex = json.load(fh)
    with open(os.path.join(ROOT, "data", "types.json")) as fh:
        types = json.load(fh)

    failures = []

    def check(label, expect_name, expect_source, day=TODAY, requested=None):
        _, name, _, source = pins.resolve(day, dex, types, requested)
        ok = (expect_name is None or name == expect_name) and source == expect_source
        if not ok:
            failures.append("%s: got %s [%s], expected %s [%s]"
                            % (label, name, source, expect_name, expect_source))
        print("  %-38s %-12s %s" % (label, name, source))
        return name

    print("checked in %s" % SANDBOX)
    rolled = check("clean: the date's own roll", None, pins.ROLL)

    check("explicit name wins", "mew", pins.REQUESTED, requested="mew")

    pins.write_today(TODAY, "gengar")
    check("today-only pin wins over roll", "gengar", pins.TODAY)
    check("explicit name still wins over it", "mew", pins.REQUESTED, requested="mew")
    check("today-only pin does not reach tomorrow", None, pins.ROLL, day=TOMORROW)

    config.set_key("pokemon", "lapras")
    check("today-only pin outranks config", "gengar", pins.TODAY)
    check("config applies tomorrow", "lapras", pins.CONFIG, day=TOMORROW)

    pins.clear_today()
    check("config applies once today expires", "lapras", pins.CONFIG)

    config.clear_key("pokemon")
    back = check("unpinned returns to the roll", None, pins.ROLL)
    if back != rolled:
        failures.append("unpinning did not restore the original roll")

    # A typo must be reported, not silently swapped for a random Pokemon.
    for bad in ("pikchu", "", "Mr Mime"):
        config.set_key("pokemon", bad or "x")
        if not bad:
            config.clear_key("pokemon")
            continue
        try:
            pins.resolve(TODAY, dex, types)
            failures.append("accepted unknown name %r" % bad)
        except ValueError:
            pass
    config.clear_key("pokemon")

    # Case should not matter, since these get typed by hand.
    _, name, _, _ = pins.resolve(TODAY, dex, types, "PIKACHU")
    if name != "pikachu":
        failures.append("case-insensitive lookup failed: %s" % name)

    shutil.rmtree(SANDBOX, ignore_errors=True)

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("\npin precedence ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
