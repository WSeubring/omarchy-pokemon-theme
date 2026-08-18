"""Whether the day's Pokemon shows up shiny, and at what odds.

The daily roll is deterministic, like the Pokemon itself: the same day and the
same name always agree about being shiny, so the timer, the boot catch-up and the
theme-set hook cannot disagree about what today looks like.

One roll a day is the unit that matters here, not one encounter: the canonical
1-in-4096 would put a shiny day about once a decade, which is indistinguishable
from never. 1 in 14 -- roughly a fortnight -- is often enough to be a thing that
happens and rare enough to still register when it does. Set it to taste; the hunt
has its own key for going looking on purpose.
"""

import hashlib
import random

import config

# 1 in N, per day. About once a fortnight.
DEFAULT_ODDS = 14
# A hunt is a deliberate act, so it gets its own key -- someone who wants to
# actually find one can shorten it without touching what a normal day feels like.
DEFAULT_HUNT_ODDS = DEFAULT_ODDS
ODDS_KEY = "shiny-odds"
HUNT_ODDS_KEY = "shiny-hunt-odds"


def odds():
    """Odds for the daily roll, as N in "1 in N"."""
    return config.positive_int(ODDS_KEY, DEFAULT_ODDS)


def hunt_odds():
    return config.positive_int(HUNT_ODDS_KEY, odds())


def rolled(day, name, chances=None):
    """True if `name` is shiny on `day`. Deterministic, and independent of the
    draw that chose the Pokemon -- a pin gets the same chance as the daily roll.
    """
    chances = odds() if chances is None else chances
    if chances <= 1:
        return chances == 1
    key = "shiny:%s:%s" % (day, name)
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big") % chances == 0


def hunted(chances=None):
    """Roll a hunt. Genuinely random: the point is that trying again is worth it."""
    chances = hunt_odds() if chances is None else chances
    if chances <= 1:
        return chances == 1
    return random.randrange(chances) == 0
