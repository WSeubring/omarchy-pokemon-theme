"""XDG base directories, resolved once.

Every module here keeps state, cache or config under the project's own name, and
each did its own `os.environ.get(...) or expanduser(...)` dance. One place means
one behaviour -- and one place to look when a path moves.
"""

import os

NAME = "omarchy-pokemon-theme"


def _base(var, default):
    return os.environ.get(var) or os.path.expanduser(default)


def config(*parts):
    return os.path.join(_base("XDG_CONFIG_HOME", "~/.config"), NAME, *parts)


def state(*parts):
    return os.path.join(_base("XDG_STATE_HOME", "~/.local/state"), NAME, *parts)


def cache(*parts):
    return os.path.join(_base("XDG_CACHE_HOME", "~/.cache"), NAME, *parts)
