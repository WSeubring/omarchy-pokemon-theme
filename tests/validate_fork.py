#!/usr/bin/env python3
"""Say when omarchy's background plugin has moved on without ours.

`plugins/background/Background.qml` is upstream's file with an ambient layer
added -- the wallpaper images, the theme transition and the reveal mask are
carried verbatim, and they reach into the shell's own singletons (`Color`,
`Util`, `Style`, `ScreenMoveRemap`). A rename in any of those is a plugin that
throws on load, and because installing ours hands the background layer over from
`omarchy.background`, the result is a gray desktop with nothing in any log to
say why.

So the fork records the checksum of the file it was taken from, and this checks
the installed copy against it. It reports rather than fails: an upstream change
may well be in code this fork does not carry, and a theme's test suite has no
business breaking every time omarchy ships a release. What it buys is that the
drift is *visible* before someone's desktop goes gray, instead of after.

Skipped where omarchy is not installed, which is most CI.
"""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(ROOT, "plugins", "background", "UPSTREAM")


def read_record(path=RECORD):
    """The `key = value` lines from the record, as a dict."""
    fields = {}
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
    except OSError:
        return fields
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main(record_path=None):
    record = read_record(record_path or RECORD)
    missing = [key for key in ("path", "sha256") if not record.get(key)]
    if missing:
        print("plugins/background/UPSTREAM is missing: %s" % ", ".join(missing))
        return 1

    upstream = record["path"]
    if not os.path.exists(upstream):
        print("omarchy's copy is not on this machine (%s); skipped" % upstream)
        return 0

    found = digest(upstream)
    if found == record["sha256"]:
        print("fork is level with omarchy %s" % record.get("version", "?"))
        return 0

    print("upstream has changed since this fork was taken from omarchy %s"
          % record.get("version", "?"))
    print("  recorded: %s" % record["sha256"])
    print("  installed: %s" % found)
    print("  diff it, re-apply the ambient blocks if the change touches them,")
    print("  and update plugins/background/UPSTREAM:")
    print("    diff -u %s \\\n         %s"
          % (upstream, os.path.join(ROOT, "plugins/background/Background.qml")))
    # Deliberately not a failure: see the module docstring.
    return 0


if __name__ == "__main__":
    sys.exit(main())
