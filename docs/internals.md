# Internals

Design notes for anyone working on the theme. The user-facing story is in the
[README](../README.md).

## How the palette is built

The hue comes from the creature's own artwork. The sprite is quantized to
eight colours and scored by coverage times chroma, so the winner is the largest
region that actually has a colour: Charizard's orange belly rather than fire
red, Umbreon's yellow rings rather than its black body. A flat-grey Magnemite
scores nothing worth having, and the clamps below carry it.

Type colours remain the fallback (no network, no artwork) and still own the
second border stop, which is a statement about category rather than pixels.
`--type-hue` opts a run back into the old type-only behaviour.

Whichever source wins, the Pokémon supplies **hue and nothing else**. Lightness
and chroma come from a fixed ladder measured off the stock Catppuccin and Tokyo
Night themes, whose neutral tokens all sit within about ten degrees of a single
hue; that unity is what reads as "a theme" rather than "some colours".

This split is the whole trick. Naively recolouring a theme from artwork gives
you a usable desktop on a Charizard day and an unreadable one on a Magnemite
day. Pinning the ladder and substituting only the hue means all 905 days are
structurally identical and differ only in colour.

Three places deliberately bend that rule:

- **The accent keeps its own lightness**, clamped to `[0.66, 0.865]`. Pinning
  it outright turned every yellow into mustard: hue 95 does not read as
  "electric" below L 0.85, while a violet up there is washed out. Inside the
  band the canonical type colour usually passes through untouched; electric
  really is `#f7d02c`.
- **ANSI colours rotate 15% toward the day's hue**, so the palette feels
  cohesive, but no further. Red has to still look red in a diff.
- **A second type tints the mid-greys** and pulls whichever ANSI anchors are
  closer to it, so a dual type shows up in the UI chrome without fighting the
  primary accent.

Everything happens in [OKLCh](https://bottosson.github.io/posts/oklab/), where
lightness is perceptually uniform, so "pin L" actually means "keep the same
apparent brightness" instead of "keep the same number".

### Dual types

Just under half the 905 are dual-type (449), so this is the common case rather
than an edge case. Both types are used, in three places:

| | Primary type | Second type |
| --- | --- | --- |
| Borders | first gradient stop | second stop, at 45° |
| Palette | accent, backgrounds, foregrounds | mid-greys (`lighter_background`, `selection`, `muted`) |
| ANSI | anchors nearer the primary hue | anchors nearer its own hue |
| Ambient motion | front layer, full intensity | layer behind it, half intensity, own tint |

The borders are the most visible of these, and the same treatment
omarchy-lock-pokemon gives its card. A dual type sets `hyprland_active_border`
in `colors.toml` to a two-stop gradient, which omarchy resolves into both
`hyprland.lua` and `shell.toml`'s `hyprland.active-border`, so one line reaches
window borders, notifications, popups, menus and the lock card together:

```toml
hyprland_active_border = "rgba(9f82c6ee) rgba(c867c5ee) 45deg"
```

Both stops go through the same readable-band clamp as the accent, because
several type colours (dark, ghost, steel) are too dim at their native lightness
to read as a border against the palette's own background.

## How the day is decided

Four sources, most specific first; the generator prints which one it used:

| Source | Lifetime |
| --- | --- |
| `--pokemon NAME` or `--random` | today, then expires |
| A pin set earlier today | today, then expires |
| `pokemon` in the config | until unpinned |
| The date's own roll | that day only |

The today-only pin is a file holding `<date> <name>`, consulted only while the
date still matches. Nothing expires it and nothing cleans it up; a stale one
simply stops applying, which is what you want on a laptop that was asleep at
midnight.

The config lives outside the theme directory deliberately: `omarchy theme
install` deletes and re-clones the theme, which would take a config inside it.
A hand edit takes effect on the next run without `--force`.

The daily roll is a systemd user timer at 00:05 with `Persistent=true`, so a
laptop that was asleep across midnight catches up when it wakes. Switching to
the theme by hand also regenerates via the theme-set hook.

## Shiny mechanics

The unit of the odds is a day, not an encounter; the canonical 1-in-4096 would
mean about once a decade, indistinguishable from never. The roll is
deterministic per day and name, so the timer, the boot catch-up and the
theme-set hook all agree about today, and every Pokémon gets its own roll,
which is why rerolling doubles as the hunt.

Shiny artwork is a separate fetch and a separate cache entry, as is the colour
extracted from it, so a shiny day never reuses the normal palette. A shiny that
turns up is written to the today-pin so the timer cannot regenerate it away.

The wallpaper sparkles ring the creature rather than landing on it: the placed
sprite is measured (0.03s) and each sparkle is pushed out along its own angle
until its points clear that footprint, so a wide Muk and a tall Gengar both get
a ring that fits them. They are seeded by the Pokémon, so regenerating a
wallpaper gives back the same wallpaper. A dual type gives up its second
ambient effect on a shiny day; being shiny is the more interesting fact about
it.

## The ambient background plugin

Motion needs a Quickshell plugin, which lives in `~/.config/omarchy/plugins/`
rather than in a theme directory, so the repo ships both halves and
`install.sh` links the plugin in. The plugin is a clone of `omarchy.background`
with an ambient layer added; the wallpaper images, theme transition and reveal
mask are upstream code untouched. Installing it disables the stock renderer,
and `omarchy plugin enable omarchy.background` hands the desktop back.

The generator writes `effects = "show"` into `shell.background.toml` unless run
with `--no-animation`. Without the plugin the section is inert, so installing
the plugin later needs no regeneration.

It pauses rather than burning battery all day: a lock screen animates for five
seconds, a desktop would animate for eight hours. Motion stops when the focused
workspace has any windows and when the battery is discharging below 30%.
Paused means the `Loader`s deactivate and the shapes leave the scene graph, not
that they animate behind a zero opacity.

## The lock screen file

The generated `shell.lock.toml` restates every `[lock]` colour token rather
than just the Pokémon name, because `omarchy-theme-set-templates` replaces a
section wholesale instead of merging keys; a file with only `pokemon-name` in
it would drop the rest of the lock screen's palette. The two border tokens stay
as literal `hyprland.*` references so they keep tracking the Hyprland gradient.
`--no-lock-sync` stops the theme writing the file at all.

## The menu rows

The picker pipes all 905 names into `omarchy-menu-select`, so the menu's own
fuzzy search is the autocomplete. That deliberately avoids writing 905 rows
into `omarchy-menu.jsonc`, and avoids needing a custom menu provider: the
provider table lives in the menu plugin's QML and cannot be extended from a
config file, so an unknown provider name is silently ignored.

The rows are spliced into `~/.config/omarchy/extensions/omarchy-menu.jsonc`
between sentinel comments and nothing outside them is touched, the same
convention `omarchy-gitlab-menu-sync` uses. Re-running is idempotent and
`--remove` restores the file byte for byte:

```bash
bin/pokemon-theme-menu-install            # add or refresh the rows
bin/pokemon-theme-menu-install --remove   # take them out again
```

The rows carry a `when` condition, so the whole section is hidden unless this
theme is the active one.

## Atomic writes and the two temp-name traps

Generated files are replaced by rename, never written in place: everything
this theme writes is read by something else, often mid-write. Two traps live
in the temporary name, pulling opposite ways. `omarchy-theme-set` picks the
wallpaper by globbing `backgrounds/*.jpg` and cycles through what it finds, so
a temp file ending in .jpg becomes a rival candidate; the desktop can show a
half-built image or a symlink to one already renamed away. ImageMagick,
meanwhile, infers its output format from the extension, so a temp name ending
in `.new` makes it write PNG bytes into a file called .jpg. Hence the two
helpers in `lib/atomic.py`, and `tests/validate_render.py` to keep them honest.

The wallpaper is named per Pokémon and size (`131-2560x1600.jpg`) rather than a
constant `today.jpg`: the shell's background layer caches by path, so a fixed
name with changing content leaves stale pixels behind and flashes the previous
Pokémon on the next swap.

## Performance notes

Switching Pokémon used to leave the previous one on screen for about three
seconds. Three things were behind it, all now fixed: the wallpaper was
composited through 2400x2400 PNG intermediates (2.3s, versus 0.3s for the same
thing in a single ImageMagick pass), `colors.toml` was written before that
render so the theme directory spent seconds describing two different Pokémon,
and the composite is now cached per Pokémon and resolution, so a revisit is a
rename.

Artwork is fetched once per Pokémon from the
[PokeAPI sprites](https://github.com/PokeAPI/sprites) repo and cached under
`~/.cache/omarchy-pokemon-theme/`, outside the theme directory, because `theme
set` copies the whole theme into a staging dir on every apply. With no network
the palette and the ground still render; only the creature is missing.

The wallpaper is JPEG q92 (which ImageMagick keeps at 4:4:4 chroma). Lossless
PNG with a Lanczos upscale and dithered gradients was tried and rolled back:
technically cleaner, but the encoder's slight softening reads better on the
upscaled artwork.

## Tests

The generator will happily produce an unreadable theme if the maths is wrong on
one of 905 inputs, and you would not find out until that day came around. So
each property is checked across the whole set rather than spot-checked:

```bash
tests/run                            # all of them; --quick skips the slow sprite check

python3 tests/validate_contrast.py   # all 905 palettes vs WCAG, and hue drift
python3 tests/validate_schedule.py   # stability, spread, no near repeats
python3 tests/validate_sprites.py    # every name resolves to a sprite
python3 tests/validate_pins.py       # pin precedence and expiry
python3 tests/validate_shiny.py      # odds, determinism, config
python3 tests/validate_render.py     # wallpaper format, no stray temp files
                                     # (render half needs ImageMagick 7)
python3 tests/validate_menu.py       # menu splice, idempotency, removal
```

`validate_contrast.py` runs two passes: the 905 type-based palettes, and a
sweep of every hue at four extremes of lightness and chroma. The second pass is
the one that matters now; the accent comes from an arbitrary sprite pixel, so
the claim worth testing is that the clamps hold for *any* input colour, not
just for eighteen type colours. Worst case across both is 4.93:1.

`validate_shiny.py` checks the odds are the odds (400k draws at 1-in-14,
1-in-64 and 1-in-4096), that a day's roll is deterministic, and that the config
key reaches the roll. That last one caught a real bug: `set_key` quoted
everything it wrote, so `shiny-odds = "4096"` came back a string and was
silently ignored.

`validate_menu.py` earns its keep for a different reason: `omarchy-menu.jsonc`
is shared with every other tool that adds rows, so one bad character does not
break four rows, it breaks the file, and with it every other tool's entries. It
also checks that no `when` or `checked` condition contains a double quote,
which is the specific mistake that caused exactly that.

## Layout

| Path | Contents |
| --- | --- |
| `bin/pokemon-theme-gen` | The generator, and the only entry point |
| `lib/oklch.py` | sRGB and OKLCh, with gamut mapping by chroma reduction |
| `lib/palette.py` | The ladder, the ANSI anchors, and `colors.toml` output |
| `lib/schedule.py` | Date to Pokémon, deterministic and stateless |
| `lib/pins.py` | Precedence between the roll and the two kinds of pin |
| `lib/config.py` | The user config file, read and edited in place |
| `lib/lockscreen.py` | The `shell.lock.toml` that pins the lock screen |
| `lib/ambient.py` | The `shell.background.toml` that drives the motion |
| `lib/wallpaper.py` | ImageMagick composition |
| `lib/artwork.py` | The creature's dominant colour, quantized and cached |
| `lib/atomic.py` | Replace-by-rename, and the two temp-name traps |
| `lib/shiny.py` | The odds, and the roll against them |
| `lib/state.py` | What is written out now: day, Pokémon, and why |
| `lib/xdg.py` | The config, state and cache directories |
| `lib/tomlout.py` | Shared rendering for the generated TOML sections |
| `data/dex.json` | National dex order, so a name gives an artwork id offline |
| `data/types.json` | Name to types, from PokéAPI via omarchy-lock-pokemon |
| `data/type-colors.json` | The eighteen community type colours |
| `data/type-effects.json` | Type to ambient effect name and traits |
| `plugins/background/` | The ambient background plugin |
| `systemd/` | The daily timer and its service |
| `hooks/theme-set` | Regenerates when you switch to this theme |
| `bin/pokemon-theme-pick` | The native menu picker over all 905 |
| `bin/pokemon-theme-menu-install` | Splices the menu rows in and out |
| `tests/run` | Runs every validator, reporting all failures |

`colors.toml`, `icons.theme`, `shell.lock.toml` and the single wallpaper under
`backgrounds/` are generated. The wallpaper and the lock file are gitignored; a
missing lock file only means the lock screen rolls its own Pokémon.
`colors.toml` and `icons.theme` are committed, since a theme without
`colors.toml` generates no configs at all, and a fresh clone should apply
cleanly before the first run.

The artwork is composited as its own layer rather than baked into the ground,
which is what made the ambient plugin possible: the sprite stays addressable.
Only `colors.toml` is actually required of an Omarchy 4 theme; the
`neovim.lua`, `vscode.json` and `preview.png` files that stock themes carry are
legacy, since the templates generate their equivalents now.
