#!/usr/bin/env python3
"""Check the menu block splices in cleanly and comes out cleanly.

omarchy-menu.jsonc is shared with every other tool that adds rows, so a bad
character does not just break this theme's four rows -- it takes the whole file
down, and with it every other tool's entries. That happened during development:
a double quote inside a `checked` condition invalidated all 362 entries at once.

Runs the installer against a sandbox HOME, so the real menu file is never read
or written.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALLER = os.path.join(ROOT, "bin", "pokemon-theme-menu-install")

# A pre-existing file with another tool's generated block, to prove the splice
# leaves foreign content alone.
EXISTING = """{
  // >>> other tool: generated, do not edit >>>
  "other": {"icon":"x","label":"Other","action":"true"},
  "other.thing": {"icon":"y","label":"Thing","action":"echo hi"}
  // <<< other tool <<<
}
"""

REQUIRED = ("pokemon", "pokemon.pick", "pokemon.random", "pokemon.hunt",
            "pokemon.pin", "pokemon.daily")


def strip_jsonc(raw):
    kept = [l for l in raw.split("\n") if not l.lstrip().startswith("//")]
    return re.sub(r",(\s*[}\]])", r"\1", "\n".join(kept))


def run(home, *args):
    env = dict(os.environ, HOME=home)
    return subprocess.run([INSTALLER, *args], env=env,
                          capture_output=True, text=True)


def main():
    sandbox = tempfile.mkdtemp(prefix="pokemon-theme-menu-")
    menu_dir = os.path.join(sandbox, ".config", "omarchy", "extensions")
    os.makedirs(menu_dir)
    menu = os.path.join(menu_dir, "omarchy-menu.jsonc")
    failures = []

    try:
        # 1. Splicing into a file that already has someone else's block.
        with open(menu, "w") as fh:
            fh.write(EXISTING)
        original = open(menu).read()

        result = run(sandbox)
        if result.returncode != 0:
            failures.append("install failed: %s" % result.stderr.strip())

        text = open(menu).read()
        try:
            parsed = json.loads(strip_jsonc(text))
        except json.JSONDecodeError as exc:
            failures.append("result is not valid JSONC: %s" % exc)
            parsed = {}

        for key in REQUIRED:
            if key not in parsed:
                failures.append("missing row: %s" % key)

        for key in ("other", "other.thing"):
            if key not in parsed:
                failures.append("clobbered another tool's row: %s" % key)

        # 2. The bug class that took the file down: conditions live inside JSON
        # strings, so a double quote in one is fatal.
        for key, row in parsed.items():
            if not key.startswith("pokemon"):
                continue
            for field in ("when", "checked"):
                value = row.get(field, "")
                if '"' in value:
                    failures.append("%s.%s contains a double quote: %s"
                                    % (key, field, value))
            if not row.get("when"):
                failures.append("%s has no `when`, so it would show under every "
                                "theme" % key)

        # 3. Idempotent.
        run(sandbox)
        if open(menu).read() != text:
            failures.append("second install changed the file")

        # 4. Removal puts the file back. Compared modulo a trailing comma: the
        # splice may have added one to the entry above its block, and omarchy's
        # own stripJsonc discards trailing commas, so leaving it is harmless.
        run(sandbox, "--remove")
        after = open(menu).read()
        if strip_jsonc(after) != strip_jsonc(original):
            failures.append("--remove did not restore the original content")
        try:
            leftover = json.loads(strip_jsonc(after))
            if any(k.startswith("pokemon") for k in leftover):
                failures.append("--remove left rows behind")
            if "other.thing" not in leftover:
                failures.append("--remove dropped another tool's row")
        except json.JSONDecodeError as exc:
            failures.append("--remove left invalid JSONC: %s" % exc)

        # 5. Creates a usable file from nothing.
        os.remove(menu)
        run(sandbox)
        try:
            fresh = json.loads(strip_jsonc(open(menu).read()))
            if "pokemon" not in fresh:
                failures.append("fresh install produced no rows")
        except (json.JSONDecodeError, OSError) as exc:
            failures.append("fresh install produced nothing usable: %s" % exc)

        print("checked splice, idempotency, removal and fresh install")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("menu block ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
