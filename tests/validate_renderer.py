#!/usr/bin/env python3
"""Check the two states that leave the desktop gray are recognised.

Both are invisible until someone looks at their screen, and neither reports
anything anywhere: the background plugin sits under every window with no chrome
of its own, and a symlink pointing at a deleted staging directory is still a
symlink. So the recogniser is what gets tested, on hand-written shell configs
that stand in for the states real installs end up in.

The repairs themselves shell out to omarchy and are not exercised here; what is
tested is that they are asked for exactly when they are needed, and never on a
healthy desktop -- a spurious repair would cycle the real background through a
transition on every timer run.

Runs entirely on temporary files; the real shell config is never read.
"""

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import renderer  # noqa: E402

SANDBOX = tempfile.mkdtemp(prefix="pokemon-theme-renderer-")

# What the shell writes once the handover has gone through properly: the clone
# listed, the stock renderer disabled, and the restore armed.
HEALTHY = {
    "plugins": [{"id": "pokemon.background"}, {"id": "pokemon.lock"}],
    "disabledPlugins": ["omarchy.background", "omarchy.lock"],
    "cloneSourceRestores": ["pokemon.background", "pokemon.lock"],
}

# What install.sh used to leave behind: it disabled the stock renderer itself,
# so the shell never armed the restore for the clone. Note pokemon.lock, which
# was installed the ordinary way, has its entry -- that asymmetry is the tell.
ONE_WAY = {
    "plugins": [{"id": "pokemon.background"}, {"id": "pokemon.lock"}],
    "disabledPlugins": ["omarchy.background", "omarchy.lock"],
    "cloneSourceRestores": ["pokemon.lock"],
}

# The gray screen itself: the stock renderer off, the clone gone with it.
NO_RENDERER = {
    "plugins": [{"id": "pokemon.lock"}],
    "disabledPlugins": ["omarchy.background", "omarchy.lock"],
}

# A desktop that never took the handover: nothing here is ours to repair.
STOCK = {"plugins": [{"id": "pokemon.lock"}], "disabledPlugins": ["omarchy.lock"]}


def write_json(name, data):
    path = os.path.join(SANDBOX, name)
    with open(path, "w") as fh:
        json.dump(data, fh)
    return path


def touch(name):
    path = os.path.join(SANDBOX, name)
    with open(path, "w") as fh:
        fh.write("x")
    return path


def plugin_dir(name, with_manifest=True):
    path = os.path.join(SANDBOX, name)
    os.makedirs(path, exist_ok=True)
    if with_manifest:
        with open(os.path.join(path, "manifest.json"), "w") as fh:
            json.dump({"id": renderer.CLONE_ID}, fh)
    return path


def main():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append("%s: got %r, expected %r" % (label, got, want))
        print("  %-60s %s" % (label, "ok" if got == want else "FAILED"))

    # The healthy states, where a repair would be the bug.
    check("a proper handover needs no repair",
          renderer.diagnose(HEALTHY, True), None)
    check("a stock desktop is left alone",
          renderer.diagnose(STOCK, False), None)
    check("a stock desktop with our plugin sitting unused is left alone",
          renderer.diagnose(STOCK, True), None)

    # The two broken ones.
    check("a one-way handover is re-armed",
          renderer.diagnose(ONE_WAY, True), renderer.REARM)
    check("a disabled stock renderer with no clone is restored",
          renderer.diagnose(NO_RENDERER, True), renderer.RESTORE)
    check("a clone that is enabled but no longer installed is restored",
          renderer.diagnose(HEALTHY, False), renderer.RESTORE)
    check("a one-way handover whose plugin went missing is restored",
          renderer.diagnose(ONE_WAY, False), renderer.RESTORE)

    # An unreadable or absent shell config must not be read as "everything is
    # disabled" -- that would fire a repair on a desktop that never had one.
    missing = os.path.join(SANDBOX, "nope.json")
    check("a missing shell config reads as empty",
          renderer.read_config(missing), {})
    with open(os.path.join(SANDBOX, "broken.json"), "w") as fh:
        fh.write("{not json")
    check("an unparseable shell config reads as empty",
          renderer.read_config(os.path.join(SANDBOX, "broken.json")), {})
    check("a JSON array is not mistaken for a config",
          renderer.read_config(write_json("array.json", [1, 2])), {})
    check("an empty config needs no repair",
          renderer.diagnose({}, True), None)

    # The shell writes plugin entries as objects; older configs used bare ids.
    check("a plugin entry object reads as enabled",
          renderer.is_enabled(HEALTHY, renderer.CLONE_ID), True)
    check("a bare plugin id reads as enabled",
          renderer.is_enabled({"plugins": ["pokemon.background"]},
                              renderer.CLONE_ID), True)
    check("a plugin that is not listed reads as disabled",
          renderer.is_enabled(NO_RENDERER, renderer.CLONE_ID), False)

    # Presence is judged by the manifest: a symlinked plugin whose checkout has
    # been moved leaves a directory entry that resolves to nothing.
    check("a plugin directory with a manifest counts as installed",
          renderer.clone_installed(plugin_dir("plugin-ok")), True)
    check("a plugin directory without a manifest does not",
          renderer.clone_installed(plugin_dir("plugin-bare", False)), False)
    check("a plugin directory that is not there does not",
          renderer.clone_installed(os.path.join(SANDBOX, "plugin-gone")), False)

    # The background symlink. A working link is left alone; a dangling one takes
    # the staged copy first, since that is what an apply would have chosen.
    staged = touch("staged.jpg")
    theme = touch("theme.jpg")
    live = os.path.join(SANDBOX, "background")
    os.symlink(staged, live)
    check("a link that resolves is left alone",
          renderer.link_repair_target(live, (staged, theme)), None)

    os.remove(staged)
    check("a dangling link falls back to the theme's own copy",
          renderer.link_repair_target(live, (staged, theme)), theme)
    check("a dangling link with nothing to point at stays dangling",
          renderer.link_repair_target(live, (staged,)), None)
    check("a link that was never made is repaired too",
          renderer.link_repair_target(os.path.join(SANDBOX, "no-link"),
                                      (theme,)), theme)
    check("no candidates at all is not an error",
          renderer.link_repair_target(live, ()), None)

    shutil.rmtree(SANDBOX, ignore_errors=True)
    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("background renderer and link checks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
