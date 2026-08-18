#!/usr/bin/env python3
"""Check the date -> Pokemon mapping is stable, spread out, and repeat-free."""

import json
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import schedule  # noqa: E402

YEARS = 5


def main():
    def load(name):
        with open(os.path.join(ROOT, "data", name)) as fh:
            return json.load(fh)

    dex, types = load("dex.json"), load("types.json")
    failures = []

    day = date(2026, 1, 1)
    picks = []
    for _ in range(365 * YEARS):
        picks.append(schedule.pick(day.isoformat(), dex, types)[1])
        day += timedelta(days=1)

    # No repeat inside the avoidance window -- the visible failure mode is the
    # desktop appearing not to have changed overnight.
    window = schedule.AVOID_RECENT_DAYS
    for i in range(1, len(picks)):
        for back in range(1, min(window, i) + 1):
            if picks[i] == picks[i - back]:
                failures.append("repeat after %d day(s) at index %d: %s"
                                % (back, i, picks[i]))

    # Stability: the same date must always resolve to the same Pokemon.
    for probe in ("2026-08-18", "2027-01-01", "2030-12-25"):
        first = schedule.pick(probe, dex, types)
        for _ in range(5):
            if schedule.pick(probe, dex, types) != first:
                failures.append("unstable pick for %s" % probe)
                break

    # Coverage: a heavily biased hash would show up as few distinct draws.
    distinct = len(set(picks))
    if distinct < len(dex) * 0.75:
        failures.append("only %d distinct of %d over %d years"
                        % (distinct, len(dex), YEARS))

    print("%d days, %d distinct Pokemon of %d" % (len(picks), distinct, len(dex)))
    print("no repeat within %d day(s): %s" % (window, "ok" if not failures else "FAILED"))

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures[:10]:
            print("  " + line)
        return 1
    print("schedule ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
