#!/usr/bin/env python3
"""Check every name the theme can pin is one pokemon-colorscripts accepts.

data/dex.json was taken from pokemon-colorscripts' own pokemon.json, so the two
agree by construction today. They can drift: if that package renames or drops an
entry, `lock.pokemon-name` would point at nothing and the lock screen would show
no sprite at all -- silently, and only on the day that Pokemon came up.

Skipped when pokemon-colorscripts is not installed; it is optional for the
theme, which only needs it for the lock screen.
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if shutil.which("pokemon-colorscripts") is None:
        print("pokemon-colorscripts not installed; skipping")
        return 0

    with open(os.path.join(ROOT, "data", "dex.json")) as fh:
        dex = json.load(fh)

    rejected = [
        name for name in dex
        if subprocess.run(["pokemon-colorscripts", "-n", name],
                          capture_output=True).returncode != 0
    ]

    print("checked %d names" % len(dex))
    if rejected:
        print("\n%d REJECTED by pokemon-colorscripts:" % len(rejected))
        for name in rejected[:20]:
            print("  " + name)
        return 1
    print("all names resolve to a sprite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
