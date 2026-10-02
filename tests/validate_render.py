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
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import atomic  # noqa: E402
import config  # noqa: E402
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

    # The caption draws something, and only when asked.
    captioned = os.path.join(sandbox, "captioned.jpg")
    wallpaper.render(None, colors, captioned, 320, 200,
                     caption=wallpaper.label(131, "lapras"))
    if open(captioned, "rb").read() == open(plain, "rb").read():
        failures.append("a captioned render is identical to a bare one")
    for dex_id, name, want in ((6, "charizard", "#006 Charizard"),
                               (29, "nidoran-f", "#029 Nidoran\u2640"),
                               (250, "ho-oh", "#250 Ho-Oh"),
                               (785, "tapu-koko", "#785 Tapu Koko")):
        if wallpaper.label(dex_id, name) != want:
            failures.append("label for %s is %r, want %r"
                            % (name, wallpaper.label(dex_id, name), want))

    # On by default; a written false must read back as false, not as the
    # string "False" (which is truthy).
    config.PATH = os.path.join(sandbox, "config.toml")
    if not config.caption():
        failures.append("the caption is off without a config")
    config.set_key("caption", False)
    if config.caption():
        failures.append("caption = false in the config was ignored")
    gen = _load_gen()
    if gen.variant_slug(False, "dark", 1.0, True) == \
            gen.variant_slug(False, "dark", 1.0, False):
        failures.append("toggling the caption keeps the wallpaper's name")

    leftovers = sorted(name for name in os.listdir(backgrounds)
                       if name != os.path.basename(target))
    if leftovers:
        failures.append("render left files behind: %s" % ", ".join(leftovers))

    failures += _cache_checks(sandbox, colors)

    print("checked the scratch names and one %dx%d render" % (320, 200))
    shutil.rmtree(sandbox, ignore_errors=True)
    return _report(failures)


def _cache_checks(sandbox, colors):
    """A creature-less render must never enter the wallpaper cache.

    The cache is keyed by Pokemon, finish, palette and size -- not by whether
    the artwork host answered. So a wallpaper composited while the fetch failed
    is the bare ground, and caching it serves that back for as long as the entry
    survives: months, on a machine that revisits the Pokemon.
    """
    failures = []
    gen = _load_gen()
    backgrounds = os.path.join(sandbox, "theme-backgrounds")
    cache = os.path.join(sandbox, "wallpaper-cache")
    os.makedirs(backgrounds)
    os.makedirs(cache)
    gen.BACKGROUNDS, gen.WALLPAPERS = backgrounds, cache

    art = os.path.join(sandbox, "art.png")
    subprocess.run(["magick", "-size", "64x64", "xc:none", "-fill", "#e8622a",
                    "-draw", "circle 32,32 32,8", art], check=True)

    placed = gen.wallpaper_for(157, False, colors, 320, 200, art=None)
    if not os.path.exists(placed):
        failures.append("a creature-less run placed no wallpaper")
    if os.listdir(cache):
        failures.append("a creature-less render was cached: %s"
                        % ", ".join(os.listdir(cache)))

    placed = gen.wallpaper_for(157, False, colors, 320, 200, art=art)
    cached = os.listdir(cache)
    if len(cached) != 1:
        failures.append("a normal render cached %d files, expected 1"
                        % len(cached))
    if os.path.exists(placed) and os.path.getsize(placed) == 0:
        failures.append("the placed wallpaper is empty")
    leftovers = [name for name in os.listdir(backgrounds)
                 if name != os.path.basename(placed)]
    if leftovers:
        failures.append("the backgrounds directory kept %s"
                        % ", ".join(leftovers))
    return failures


def _load_gen():
    """Import the generator as a module; it is a script, so it has no name."""
    path = os.path.join(ROOT, "bin", "pokemon-theme-gen")
    spec = importlib.util.spec_from_loader(
        "pokemon_theme_gen",
        importlib.machinery.SourceFileLoader("pokemon_theme_gen", path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
