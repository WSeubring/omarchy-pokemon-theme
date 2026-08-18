"""What is currently written out: the day, the Pokemon, and why it was chosen.

One file, three space-separated fields. The timer, the boot catch-up and the
theme-set hook all fire independently, so they need a cheap way to agree that
the work is already done. The `why` field is also read from shell by the menu's
`checked` condition, which is why it stays a plain trailing slug.

Kept outside the theme directory: `omarchy-theme-set` copies the whole theme on
every apply, and mutable state has no business being copied along with it.
"""

import os

import xdg

PATH = xdg.state("current")


def read():
    """Return (day, name, why), with None for anything not on file."""
    try:
        with open(PATH) as fh:
            parts = fh.read().split()
    except OSError:
        parts = []
    parts += [None] * (3 - len(parts))
    return tuple(parts[:3])


def name():
    """The Pokemon currently written out, whatever day it was written for."""
    return read()[1]


def matches(day, pokemon):
    """True if this exact day-and-Pokemon is what is already on file."""
    stamp, current, _ = read()
    return stamp == day and current == pokemon


def write(day, pokemon, why):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as fh:
        fh.write("%s %s %s\n" % (day, pokemon, why))
