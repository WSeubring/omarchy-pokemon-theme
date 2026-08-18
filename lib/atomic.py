"""Write a file so no reader ever sees it half-written.

Every file this theme generates is read by something else, often while it is being
written: `omarchy-theme-set` copies the whole theme directory, the shell loads the
wallpaper, and the daily timer can fire mid-run. A plain open-and-write truncates
first, so a reader arriving in that window gets an empty or partial file -- a blank
wallpaper, or a palette with no accent. Writing beside the target and renaming
makes the swap atomic: a reader sees either the old file or the new one.

The temporary name matters more than it looks. `omarchy-theme-set` picks the
day's wallpaper by globbing `backgrounds/*.jpg`, so a temporary file ending in
.jpg becomes a *second candidate* -- and since that chooser cycles through the
candidates it finds, the desktop can end up showing the half-built one, or a
symlink to a file that has since been renamed away. So the placement name ends in
".new" and matches no image glob.

ImageMagick wants the opposite: it takes its output format from the extension, and
writing to "today.jpg.new" makes it guess -- quietly emitting PNG bytes into a
file named .jpg. `image_scratch` keeps the extension for that case, and is only
safe in a directory nothing scans for images.
"""

import os


def text(path, content):
    """Replace `path` with `content`, atomically."""
    tmp = scratch(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    commit(tmp, path)


def scratch(path):
    """A temporary name beside `path` that no image glob will match."""
    return path + ".new"


def image_scratch(path):
    """A temporary name beside `path` that keeps its extension, for ImageMagick."""
    stem, dot, extension = path.rpartition(".")
    if not dot or "/" in extension:
        return scratch(path)
    return "%s.new.%s" % (stem, extension)


def commit(tmp, path):
    """Rename a finished temporary file onto its real path."""
    os.replace(tmp, path)
