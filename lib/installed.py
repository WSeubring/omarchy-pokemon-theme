"""What of the Pokemon desktop is already on this machine.

The installer and both setup wizards ask the same questions, so they share
one answer: presence is judged by the artefact each component leaves behind,
not by remembering what an earlier run did -- a user who installed the lock
screen by hand, or removed the greeting, should see the truth.
"""

import os
import shutil

HOME = os.path.expanduser("~")
THEME_LINK = os.path.join(HOME, ".config/omarchy/themes/pokemon")
BACKGROUND_PLUGIN = os.path.join(HOME, ".config/omarchy/plugins/pokemon.background")
LOCK_PLUGIN = os.path.join(HOME, ".config/omarchy/plugins/pokemon.lock")
MENU_FILE = os.path.join(HOME, ".config/omarchy/extensions/omarchy-menu.jsonc")
# The theme omarchy has applied, which is not the same question as which theme
# this repo last generated files for: the desktop can be wearing Tokyo Night
# while today's Pokemon sits ready on disk.
ACTIVE_THEME = os.path.join(HOME, ".local/state/omarchy/current/theme.name")


def _menu_rows():
    try:
        with open(MENU_FILE) as fh:
            return "pokemon-theme" in fh.read()
    except OSError:
        return False


def active_theme():
    """The slug of the theme omarchy has applied, or None if it cannot be read."""
    try:
        with open(ACTIVE_THEME) as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def detect():
    """{component: bool} for everything the installer can put in place."""
    return {
        "theme": os.path.exists(THEME_LINK),
        "animation": os.path.exists(BACKGROUND_PLUGIN),
        "menu": _menu_rows(),
        "lock": os.path.exists(LOCK_PLUGIN),
        "greeting": shutil.which("pokedex-greeting") is not None,
    }
