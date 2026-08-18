"""Deciding which Pokemon a given day gets, and the two ways to override it.

Three sources, each with a different lifetime:

- a name passed on the command line, which becomes the pin for today
- `today`, a pin that expires on its own at midnight
- `pokemon` in the user config, which holds until removed

The today-only pin is a file holding "<date> <name>" and is consulted only while
the date still matches. That is deliberately not a timestamp to compare against:
there is nothing to expire, nothing to clean up, and no way for it to leak into
tomorrow if the machine is asleep at midnight.
"""

import os

import config
import schedule
import xdg

PATH = xdg.state("override")

# Sources, in the order they win. Used for the line the generator prints, so
# "why is today a Lapras" is answerable without reading any files.
ROLL = "today's roll"
REQUESTED = "requested"
TODAY = "pinned for today"
CONFIG = "pinned in config"

# Written into the state file as a third field so other things -- the menu's
# `checked` conditions in particular -- can ask "is this the plain daily roll?"
# without re-deriving the answer from three separate files.
SLUGS = {ROLL: "roll", REQUESTED: "requested", TODAY: "today", CONFIG: "config"}


def read_today(day):
    """The name pinned for `day`, or None."""
    try:
        with open(PATH) as fh:
            stamp, name = fh.read().split()[:2]
    except (OSError, ValueError):
        return None
    return name if stamp == day else None


def write_today(day, name):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as fh:
        fh.write("%s %s\n" % (day, name))


def clear_today():
    """Remove the today-only pin. True if there was one."""
    try:
        os.remove(PATH)
        return True
    except OSError:
        return False


def resolve(day, dex, types, requested=None):
    """Decide the day's Pokemon. Returns (dex_id, name, kinds, source).

    Raises ValueError for a name that is not in the dex, so a typo in the config
    or on the command line is reported rather than silently ignored.
    """
    name, source = None, ROLL

    if requested:
        name, source = requested, REQUESTED
    else:
        today = read_today(day)
        if today:
            name, source = today, TODAY
        elif config.pinned():
            name, source = config.pinned(), CONFIG

    if name is None:
        dex_id, name, kinds = schedule.pick(day, dex, types)
        return dex_id, name, kinds, source

    name = name.lower()
    if name not in types:
        raise ValueError("unknown pokemon: %s" % name)
    return dex.index(name) + 1, name, types[name], source
