#!/usr/bin/env python3
"""Check the state file's contract, and when a run is allowed to apply.

Both halves guard bugs that only show up a day later, on someone else's machine:

- A wallpaper rendered while the artwork host was unreachable has no creature on
  it, and the state file is what decides whether the next run repairs it or
  reports "already current" until tomorrow.
- Applying the theme is also how omarchy *switches* to it, so a background run
  that applies unconditionally takes the desktop off whatever theme the user
  actually chose.

The state file is also read from shell: the menu's `checked` condition anchors to
the last field, so the `why` slug has to stay last however many fields are added.

Runs against a temporary XDG_STATE_HOME so the real state file is untouched.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# state.py resolves its path from the environment at import time.
SANDBOX = tempfile.mkdtemp(prefix="pokemon-theme-state-")
os.environ["XDG_STATE_HOME"] = os.path.join(SANDBOX, "state")

sys.path.insert(0, os.path.join(ROOT, "lib"))

import state  # noqa: E402

TODAY, TOMORROW = "2026-08-25", "2026-08-26"


def load_gen():
    """Import the generator as a module; it is a script, so it has no name."""
    path = os.path.join(ROOT, "bin", "pokemon-theme-gen")
    # No .py extension, so the loader has to be named rather than guessed.
    spec = importlib.util.spec_from_loader(
        "pokemon_theme_gen",
        importlib.machinery.SourceFileLoader("pokemon_theme_gen", path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_raw(line):
    os.makedirs(os.path.dirname(state.PATH), exist_ok=True)
    with open(state.PATH, "w") as fh:
        fh.write(line + "\n")


def main():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append("%s: got %r, expected %r" % (label, got, want))
        print("  %-52s %s" % (label, "ok" if got == want else "FAILED"))

    # A full render is current, and stays current for the same inputs only.
    state.write(TODAY, "typhlosion", "roll", False, "dark", True)
    check("a complete run reads as current",
          state.matches(TODAY, "typhlosion", False, "dark", True), True)
    check("tomorrow is not current",
          state.matches(TOMORROW, "typhlosion", False, "dark", True), False)
    check("another Pokemon is not current",
          state.matches(TODAY, "mew", False, "dark", True), False)
    check("a mode flip is not current",
          state.matches(TODAY, "typhlosion", False, "light", True), False)
    check("a shiny of the same Pokemon is not current",
          state.matches(TODAY, "typhlosion", True, "dark", True), False)

    # The regression: artwork missing, so the wallpaper has no creature on it.
    # The next run has to rebuild it rather than report "already current".
    state.write(TODAY, "typhlosion", "roll", False, "dark", False)
    check("a creature-less wallpaper is not current once artwork returns",
          state.matches(TODAY, "typhlosion", False, "dark", True), False)
    check("a creature-less wallpaper is current while still offline",
          state.matches(TODAY, "typhlosion", False, "dark", False), True)

    # The menu reads the last field from shell.
    with open(state.PATH) as fh:
        fields = fh.read().split()
    check("why is still the last field", fields[-1], "roll")
    check("the file is one line of six fields", len(fields), 6)

    # An older, shorter file says nothing about the artwork, so it must not be
    # taken for a complete render: one regeneration repairs a wallpaper written
    # before the field existed.
    write_raw("%s typhlosion normal dark roll" % TODAY)
    check("a pre-upgrade five-field file is not current",
          state.matches(TODAY, "typhlosion", False, "dark", True), False)
    check("a pre-upgrade file still reports its Pokemon", state.name(),
          "typhlosion")
    write_raw("%s typhlosion normal roll" % TODAY)
    check("a four-field file reads as dark", state.read()[3], "dark")
    write_raw("%s typhlosion roll" % TODAY)
    check("a three-field file reads as not shiny", state.read()[2], False)
    os.remove(state.PATH)
    check("no state file at all is not current",
          state.matches(TODAY, "typhlosion", False, "dark", True), False)

    # Applying switches the desktop's theme, so a background run must not.
    gen = load_gen()
    check("a timer run applies while Pokemon is worn",
          gen.should_apply("pokemon", False), True)
    check("a timer run leaves another theme alone",
          gen.should_apply("tokyo-night", False), False)
    check("picking a Pokemon by hand applies over another theme",
          gen.should_apply("tokyo-night", True), True)
    check("no recorded theme applies, which is how the first one lands",
          gen.should_apply(None, False), True)
    check("the installer's --apply switches from another theme",
          gen.should_apply("tokyo-night", True), True)

    shutil.rmtree(SANDBOX, ignore_errors=True)
    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("state and apply rules ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
