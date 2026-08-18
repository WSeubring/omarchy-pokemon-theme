"""The user's own config file, for settings meant to outlive a single day.

Separate from the theme directory on purpose: the theme is generated output and
`omarchy theme install` will happily delete and re-clone it, which would take a
hand-written config with it.

Reading uses tomllib; writing is line-oriented rather than a re-serialise, so
comments and any keys this version does not know about survive being edited.
"""

import os
import tomllib

import xdg

PATH = xdg.config("config.toml")

TEMPLATE = """\
# omarchy-pokemon-theme

# Pin one Pokemon permanently. Commented out means a new one each day.
# Set it with: bin/pokemon-theme-gen --pin <name>
# pokemon = "pikachu"
"""


def read():
    """Return the config as a dict. Missing or unreadable file gives {}."""
    try:
        with open(PATH, "rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        # A typo in a hand-edited config should not stop the theme generating;
        # falling back to the daily roll is the harmless outcome.
        print("ignoring %s: %s" % (PATH, exc))
        return {}


def pinned():
    value = read().get("pokemon")
    return str(value).strip().lower() if value else None


def set_key(key, value):
    """Set `key` to a quoted string, preserving the rest of the file."""
    lines = _lines()
    rendered = '%s = "%s"' % (key, value)
    out, replaced = [], False
    for line in lines:
        stripped = line.strip()
        # Replace an active assignment; leave a commented example in place so
        # the file keeps documenting itself.
        if not stripped.startswith("#") and stripped.startswith(key) and "=" in stripped:
            if stripped.split("=", 1)[0].strip() == key:
                if not replaced:
                    out.append(rendered)
                    replaced = True
                continue
        out.append(line)
    if not replaced:
        out.append(rendered)
    _write(out)


def clear_key(key):
    """Remove an active assignment for `key`. Returns True if one was removed."""
    lines = _lines()
    out, removed = [], False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#") and stripped.startswith(key) and "=" in stripped:
            if stripped.split("=", 1)[0].strip() == key:
                removed = True
                continue
        out.append(line)
    if removed:
        _write(out)
    return removed


def _lines():
    try:
        with open(PATH) as fh:
            return fh.read().splitlines()
    except FileNotFoundError:
        return TEMPLATE.splitlines()


def _write(lines):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")
