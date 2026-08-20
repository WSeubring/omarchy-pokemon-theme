"""The user's own config file, for settings meant to outlive a single day.

Separate from the theme directory on purpose: the theme is generated output and
`omarchy theme install` will happily delete and re-clone it, which would take a
hand-written config with it.

Reading uses tomllib; writing is line-oriented rather than a re-serialise, so
comments and any keys this version does not know about survive being edited.
"""

import os
import tomllib

import palette
import xdg

PATH = xdg.config("config.toml")

TEMPLATE = """\
# omarchy-pokemon-theme

# Pin one Pokemon permanently. Commented out means a new one each day.
# Set it with: bin/pokemon-theme-gen --pin <name>
# pokemon = "pikachu"

# Shiny odds, as 1 in N, rolled once a day and once per reroll. The default is
# 14 -- about once a fortnight. Set it to 4096 for canonical full odds, which
# works out to roughly once a decade.
# shiny-odds = 14

# Colour scheme: "dark" (default), "light", "auto" to follow the clock, or
# "pokemon" to let the day's creature decide -- a bright accent (Pikachu,
# Mew) gets the light theme, everything else stays dark.
# mode = "auto"

# When mode = "auto": light from this time, dark from that time (HH:MM).
# light-from = "08:00"
# dark-from = "20:00"

# Colour intensity, a chroma multiplier from 0.4 (near-monochrome) to 1.6
# (saturated). Applies to both dark and light palettes.
# intensity = 1.0
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


def positive_int(key, default):
    """A whole number above zero from the config, or `default`.

    A nonsense value falls back rather than raising: the config is hand-edited,
    and a typo in the shiny odds should not stop the desktop having a theme.
    """
    value = read().get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        if value is not None:
            print("ignoring %s = %r in %s: want a whole number above zero"
                  % (key, value, PATH))
        return default
    return value


def mode():
    """"dark", "light", "auto" or "pokemon" from the config; else "dark"."""
    value = str(read().get("mode", "")).strip().lower()
    if value in ("dark", "light", "auto", "pokemon"):
        return value
    if value:
        print('ignoring mode = %r in %s: '
              'want "dark", "light", "auto" or "pokemon"' % (value, PATH))
    return "dark"


def flip_time(key, default):
    """An "HH:MM" from the config as (hour, minute), or `default`."""
    value = read().get(key)
    if value is None:
        value = default
    try:
        hour, minute = (int(v) for v in str(value).split(":"))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return hour, minute
    except ValueError:
        pass
    print("ignoring %s = %r in %s: want HH:MM" % (key, value, PATH))
    return tuple(int(v) for v in default.split(":"))


def intensity():
    """The chroma multiplier from the config, clamped to the safe range."""
    value = read().get("intensity", 1.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        print("ignoring intensity = %r in %s: want a number" % (value, PATH))
        return 1.0
    return palette.clamp_intensity(float(value))


def set_key(key, value):
    """Set `key`, preserving the rest of the file.

    Numbers are written bare and everything else quoted, so a value written
    here reads back as the type it was set as -- a quoted "4096" would come back
    a string and be rejected by positive_int(), a quoted "1.3" by intensity().
    """
    if isinstance(value, bool):
        rendered = '%s = "%s"' % (key, value)
    elif isinstance(value, int):
        rendered = "%s = %d" % (key, value)
    elif isinstance(value, float):
        rendered = "%s = %s" % (key, ("%.2f" % value).rstrip("0").rstrip("."))
    else:
        rendered = '%s = "%s"' % (key, value)
    kept, replaced = [], False
    for line in _lines():
        if _assigns(line, key):
            # Replace the first active assignment and drop any duplicates. A
            # commented example is left in place so the file keeps documenting
            # itself.
            if not replaced:
                kept.append(rendered)
                replaced = True
            continue
        kept.append(line)
    if not replaced:
        kept.append(rendered)
    _write(kept)


def clear_key(key):
    """Remove an active assignment for `key`. Returns True if one was removed."""
    lines = _lines()
    kept = [line for line in lines if not _assigns(line, key)]
    removed = len(kept) != len(lines)
    if removed:
        _write(kept)
    return removed


def _assigns(line, key):
    """True for an uncommented `key = ...` line."""
    stripped = line.strip()
    if stripped.startswith("#") or "=" not in stripped:
        return False
    return stripped.split("=", 1)[0].strip() == key


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
