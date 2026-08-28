"""Who paints the desktop, and whether that can be undone.

Two things stand between this theme and a gray screen, and both live outside the
theme directory:

- `omarchy.background` is the stock renderer. Our ambient clone replaces it, and
  the shell disables the stock one on its own when a plugin whose manifest names
  `clonedFrom` is enabled -- recording the id in `cloneSourceRestores` so that
  disabling the clone hands the desktop back. Disabling the source *by hand*
  first skips that bookkeeping (PluginRegistry only arms the restore when the
  source was still enabled), and the handover becomes one-way: removing the
  clone then leaves nothing rendering the background at all.
- `~/.local/state/omarchy/current/background` is a symlink into the staged copy
  of the theme. `omarchy-theme-set` only re-points it when it finds an image to
  point it at; a theme whose wallpaper has not been generated yet leaves it
  aimed at the directory the apply just deleted.

Neither breaks loudly. The desktop just goes flat gray, which is why the
generator checks both on every run: the daily timer is the one thing guaranteed
to come back around.
"""

import json
import os
import shutil
import subprocess

CLONE_ID = "pokemon.background"
SOURCE_ID = "omarchy.background"

HOME = os.path.expanduser("~")
SHELL_CONFIG = os.path.join(HOME, ".config/omarchy/shell.json")
PLUGIN_DIR = os.path.join(HOME, ".config/omarchy/plugins", CLONE_ID)
BACKGROUND_LINK = os.path.join(HOME, ".local/state/omarchy/current/background")
STATE_BACKGROUNDS = os.path.join(HOME,
                                 ".local/state/omarchy/current/theme/backgrounds")

# What diagnose() can find. Slugs rather than sentences so the caller decides
# how loud to be about it.
RESTORE = "restore"
REARM = "rearm"


def read_config(path=SHELL_CONFIG):
    """The shell's config as a dict; {} if it cannot be read or parsed."""
    try:
        with open(path) as fh:
            config = json.load(fh)
    except (OSError, ValueError):
        return {}
    return config if isinstance(config, dict) else {}


def _ids(config, key):
    return [entry for entry in config.get(key, []) if isinstance(entry, str)]


def is_disabled(config, plugin_id):
    return plugin_id in _ids(config, "disabledPlugins")


def is_enabled(config, plugin_id):
    """True if `plugin_id` has an entry in the shell's plugin list.

    A plugin is listed when it is enabled and dropped when it is not, so the
    entry is the whole answer -- `disabledPlugins` only exists to switch off the
    first-party plugins that would otherwise load by default.
    """
    for entry in config.get("plugins", []):
        if isinstance(entry, dict) and entry.get("id") == plugin_id:
            return True
        if entry == plugin_id:
            return True
    return False


def restores_source(config, plugin_id):
    return plugin_id in _ids(config, "cloneSourceRestores")


def diagnose(config, clone_installed):
    """What is wrong with the background handover, or None if nothing is.

    RESTORE -- the stock renderer is switched off and the clone is not there to
    take over: nothing is painting the desktop.
    REARM -- the clone is rendering, but the shell was never told to hand the
    desktop back when it goes away, so removing it would gray the screen.
    """
    if not is_disabled(config, SOURCE_ID):
        return None
    if not clone_installed or not is_enabled(config, CLONE_ID):
        return RESTORE
    if not restores_source(config, CLONE_ID):
        return REARM
    return None


def clone_installed(plugin_dir=PLUGIN_DIR):
    """True if the ambient plugin is present and loadable.

    The manifest is checked rather than the directory: a symlinked plugin whose
    checkout has moved leaves a directory entry that resolves to nothing, and a
    plugin without a manifest is not in the shell's catalog either way.
    """
    return os.path.exists(os.path.join(plugin_dir, "manifest.json"))


def _plugin(*args):
    """Run `omarchy plugin ...`; False if the CLI is missing or refuses."""
    if not shutil.which("omarchy"):
        return False
    try:
        subprocess.run(["omarchy", "plugin"] + list(args), check=True,
                       capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def repair(verbose=True):
    """Put the background handover back in a state the shell can undo.

    Both repairs start by enabling the stock renderer: that is the only path
    through PluginRegistry that clears `disabledPlugins` *and* drops a stale
    clone entry, and enabling the clone afterwards is then a normal handover
    that arms the restore. Returns the slug repaired, or None.
    """
    problem = diagnose(read_config(), clone_installed())
    if problem is None:
        return None
    if verbose:
        print("background renderer: %s" % (
            "nothing is rendering the desktop; restoring %s" % SOURCE_ID
            if problem == RESTORE else
            "%s cannot be handed back; re-arming the handover" % SOURCE_ID))
    if not _plugin("enable", SOURCE_ID):
        if verbose:
            print("could not restore %s; run: omarchy plugin enable %s"
                  % (SOURCE_ID, SOURCE_ID))
        return None
    if problem == REARM:
        _plugin("enable", CLONE_ID)
    return problem


def link_repair_target(link=BACKGROUND_LINK, candidates=()):
    """The first candidate worth pointing `link` at, or None to leave it alone.

    None when the link already resolves to a file that exists: re-pointing a
    working link would only cycle the desktop through a transition for nothing.
    """
    if os.path.exists(os.path.realpath(link)):
        return None
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def repair_link(background, verbose=True):
    """Re-point the current-background symlink if it aims at nothing.

    `background` is the wallpaper in the theme directory. The staged copy is
    preferred where it exists, because that is what `omarchy-theme-set` would
    have chosen and what the next apply will compare against.
    """
    staged = os.path.join(STATE_BACKGROUNDS, os.path.basename(background))
    target = link_repair_target(candidates=(staged, background))
    if target is None:
        return None
    if not shutil.which("omarchy-theme-bg-set"):
        return None
    try:
        subprocess.run(["omarchy-theme-bg-set", target], check=True,
                       capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if verbose:
        print("background link pointed at nothing; repointed at %s" % target)
    return target
