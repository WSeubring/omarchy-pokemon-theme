#!/usr/bin/env python3
"""Check the wallpaper lands as one finished JPEG and nothing else.

Two bugs live here, and neither announces itself:

- `omarchy-theme-set` chooses the day's wallpaper by globbing the theme's
  backgrounds directory for image files, and cycles through whatever it finds. A
  temporary file ending in .jpg therefore becomes a second candidate: the desktop
  can show a half-built image, or a symlink to one that has been renamed away.
- ImageMagick takes its output format from the extension, so writing to a
  temporary name ending in ".new" makes it guess -- it emits PNG bytes into a file
  named .jpg, quietly tripling the size.

The two pull in opposite directions, which is why both names are tested. Those
checks are pure string work and always run. The render itself needs ImageMagick 7
and is skipped without it -- CI runners ship ImageMagick 6, whose binary is
`convert`, and the name checks are the half that caught both bugs anyway.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import atomic  # noqa: E402
import palette  # noqa: E402
import wallpaper  # noqa: E402

IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp")


def main():
    failures = []

    # The placement name must match no image glob, or omarchy will offer it as a
    # wallpaper candidate.
    placed = atomic.scratch("/theme/backgrounds/131-2560x1600.jpg")
    for pattern in IMAGE_GLOBS:
        if glob.fnmatch.fnmatch(os.path.basename(placed), pattern):
            failures.append("scratch name %r matches the image glob %r"
                            % (os.path.basename(placed), pattern))

    # The ImageMagick name must keep the extension, or the format is a guess.
    drawn = atomic.image_scratch("/cache/wallpapers/131-100x100.jpg")
    if not drawn.endswith(".jpg"):
        failures.append("image scratch name %r lost its extension" % drawn)
    if drawn == "/cache/wallpapers/131-100x100.jpg":
        failures.append("image scratch name is the destination itself")

    if shutil.which("magick") is None:
        print("checked the scratch names; ImageMagick 7 absent, skipping the render")
        return _report(failures)

    sandbox = tempfile.mkdtemp(prefix="pokemon-theme-render-")
    backgrounds = os.path.join(sandbox, "backgrounds")
    os.makedirs(backgrounds)
    target = os.path.join(backgrounds, "131-320x200.jpg")

    colors = palette.build({"water": "#6390F0", "ice": "#96D9D6"}, ["water", "ice"])
    # No artwork: the render still has to produce a complete file, and this keeps
    # the test offline.
    wallpaper.render(None, colors, target, 320, 200)

    if not os.path.exists(target):
        failures.append("render produced no file at the destination")
    else:
        kind = subprocess.run(["magick", "identify", "-format", "%m", target],
                              capture_output=True, text=True).stdout.strip()
        if kind != "JPEG":
            failures.append("render wrote %s into a .jpg" % (kind or "nothing"))

    # A shiny render must differ from a normal one, and must be reproducible:
    # regenerating a wallpaper should give back the same wallpaper, sparkles in
    # the same places.
    plain = os.path.join(sandbox, "plain.jpg")
    shiny_a = os.path.join(sandbox, "shiny-a.jpg")
    shiny_b = os.path.join(sandbox, "shiny-b.jpg")
    wallpaper.render(None, colors, plain, 320, 200)
    wallpaper.render(None, colors, shiny_a, 320, 200, sparkle="6-shiny")
    wallpaper.render(None, colors, shiny_b, 320, 200, sparkle="6-shiny")
    if open(shiny_a, "rb").read() == open(plain, "rb").read():
        failures.append("a shiny render is identical to a normal one")
    if open(shiny_a, "rb").read() != open(shiny_b, "rb").read():
        failures.append("the same shiny rendered differently twice")
    other = os.path.join(sandbox, "shiny-other.jpg")
    wallpaper.render(None, colors, other, 320, 200, sparkle="94-shiny")
    if open(other, "rb").read() == open(shiny_a, "rb").read():
        failures.append("two different Pokemon sparkle identically")

    leftovers = sorted(name for name in os.listdir(backgrounds)
                       if name != os.path.basename(target))
    if leftovers:
        failures.append("render left files behind: %s" % ", ".join(leftovers))

    print("checked the scratch names and one %dx%d render" % (320, 200))
    shutil.rmtree(sandbox, ignore_errors=True)
    return _report(failures)


def _report(failures):
    if failures:
        print("\n%d FAILURE(S):" % len(failures))
        for line in failures:
            print("  " + line)
        return 1
    print("wallpaper output ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
