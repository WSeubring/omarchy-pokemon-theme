"""Deciding which Pokemon a given day gets, and the two ways to override it.

Three sources, each with a different lifetime:

- a name passed on the command line, which becomes the pin for today
- `today`, a pin that expires on its own at midnight
- `pokemon` in the user config, which holds until removed

The today-only pin is a file holding "<date> <name> [shiny]" and is consulted
only while the date still matches. Shininess rides along with the name because a
shiny found by rerolling has to survive the timer and the theme-set hook
regenerating over it -- deriving it again from the odds would lose it. That is deliberately not a timestamp to compare against:
there is nothing to expire, nothing to clean up, and no way for it to leak into
tomorrow if the machine is asleep at midnight.
"""

import collections
import os

import config
import schedule
import shiny as shiny_odds
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


# What the day resolved to, and why. A record rather than a widening tuple: every
# caller wants the name, most want the types, and only the generator cares about
# the finish.
Choice = collections.namedtuple("Choice", "dex_id name types source shiny")


def read_today(day):
    """(name, shiny) pinned for `day`, or (None, False)."""
    try:
        with open(PATH) as fh:
            fields = fh.read().split()
        stamp, name = fields[0], fields[1]
    except (OSError, IndexError):
        return None, False
    if stamp != day:
        return None, False
    return name, "shiny" in fields[2:]


def write_today(day, name, is_shiny=False):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as fh:
        fh.write("%s %s%s\n" % (day, name, " shiny" if is_shiny else ""))


def clear_today():
    """Remove the today-only pin. True if there was one."""
    try:
        os.remove(PATH)
        return True
    except OSError:
        return False


def resolve(day, dex, types, requested=None, force_shiny=None):
    """Decide the day's Pokemon. Returns a Choice.

    `force_shiny` overrides the odds -- True from --shiny, False from --no-shiny. Left as None, a pin gets exactly the same chance of
    being shiny as the daily roll does: choosing the Pokemon is not choosing how
    it looks.

    Raises ValueError for a name that is not in the dex, so a typo in the config
    or on the command line is reported rather than silently ignored.
    """
    name, source, was_shiny = None, ROLL, False

    if requested:
        name, source = requested, REQUESTED
    else:
        today, was_shiny = read_today(day)
        permanent = config.pinned()
        if today:
            name, source = today, TODAY
        elif permanent:
            name, source, was_shiny = permanent, CONFIG, False

    if name is None:
        dex_id, name, kinds = schedule.pick(day, dex, types)
    else:
        name = name.lower()
        if name not in types:
            raise ValueError("unknown pokemon: %s" % name)
        dex_id, kinds = dex.index(name) + 1, types[name]

    if force_shiny is None:
        # A pin set earlier today keeps whatever it was pinned as; anything else
        # asks the odds.
        is_shiny = was_shiny or shiny_odds.rolled(day, name)
    else:
        is_shiny = force_shiny
    return Choice(dex_id, name, kinds, source, is_shiny)
