"""What is currently written out: the day, the Pokemon, and why it was chosen.

One file, four space-separated fields: day, name, shiny, why. The timer, the boot catch-up and the
theme-set hook all fire independently, so they need a cheap way to agree that
the work is already done. The `why` field is also read from shell by the menu's `checked` condition, which
is why it stays a plain slug and stays *last*: new fields go before it, and the
condition can keep anchoring to the end of the line.

Kept outside the theme directory: `omarchy-theme-set` copies the whole theme on
every apply, and mutable state has no business being copied along with it.
"""

import os

import xdg

PATH = xdg.state("current")


def read():
    """Return (day, name, shiny, mode, why), with None for anything not on file.

    Tolerates the shorter files written by earlier versions: an upgrade should
    not force a regeneration, it should just decide nothing is shiny yet (three
    fields) or that the mode was dark (four fields).
    """
    try:
        with open(PATH) as fh:
            parts = fh.read().split()
    except OSError:
        parts = []
    if len(parts) == 3:
        parts.insert(2, "normal")
    if len(parts) == 4:
        parts.insert(3, "dark")
    parts += [None] * (5 - len(parts))
    day, pokemon, shiny, mode, why = parts[:5]
    return day, pokemon, shiny == "shiny", mode, why


def name():
    """The Pokemon currently written out, whatever day it was written for."""
    return read()[1]


def matches(day, pokemon, is_shiny, mode="dark"):
    """True if this exact day, Pokemon, finish and mode is already on file."""
    stamp, current, current_shiny, current_mode, _ = read()
    return (stamp == day and current == pokemon
            and current_shiny == is_shiny and current_mode == mode)


def write(day, pokemon, why, is_shiny=False, mode="dark"):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as fh:
        fh.write("%s %s %s %s %s\n"
                 % (day, pokemon, "shiny" if is_shiny else "normal", mode, why))
