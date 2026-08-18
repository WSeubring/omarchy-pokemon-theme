"""Map a calendar date to a Pokemon.

Deterministic and stateless: every machine that asks about the same day gets the
same answer, with no shared state to sync and nothing to drift.
"""

import hashlib
from datetime import date, timedelta

# With 905 Pokemon a plain hash draws the same one on consecutive days often
# enough to notice (once every ~2.5 years), and a theme that does not visibly
# change reads as broken. Re-roll against the last few days to avoid it.
AVOID_RECENT_DAYS = 3


def raw_index(day, count, salt=0):
    key = day if salt == 0 else "%s#%d" % (day, salt)
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big") % count


def pick(day, dex, types):
    """Return (dex_id, name, types) for `day`, an ISO date string."""
    count = len(dex)

    # Compare against the neighbours' *unsalted* draws. Using their final draws
    # would mean recursing back through the calendar for no real gain: a day
    # whose own draw was bumped colliding with today is vanishingly unlikely.
    recent = set()
    try:
        today = date.fromisoformat(day)
    except ValueError:
        today = None
    if today is not None:
        for back in range(1, AVOID_RECENT_DAYS + 1):
            earlier = (today - timedelta(days=back)).isoformat()
            recent.add(raw_index(earlier, count))

    index = raw_index(day, count)
    # Bounded: the salt only has to step past a handful of excluded indices.
    for salt in range(1, AVOID_RECENT_DAYS + 2):
        if index not in recent:
            break
        index = raw_index(day, count, salt)

    name = dex[index]
    return index + 1, name, types[name]
