# Pokémon Theme

An [Omarchy](https://omarchy.org/) 4 theme that picks a different Pokémon every
day. Its types set the palette, the whole desktop retints to match, and the
official artwork becomes the wallpaper.

![Six days of the theme](docs/gallery.jpg)

Companion to [omarchy-lock-pokemon](https://github.com/WSeubring/omarchy-lock-pokemon),
which does the same thing to the lock screen. The type colours and the
name-to-type table come from there.

## What changes

Omarchy generates seventeen config files from a theme's `colors.toml`, so a
single generated palette carries all the way out to the edges:

| | |
| --- | --- |
| Terminals | alacritty, foot, kitty, ghostty |
| Editors | neovim, helix, vscode, obsidian |
| Shell & tools | the Omarchy bar, btop, gum, chromium |
| Agents | claude, pi |
| System | hyprland borders, keyboard backlight, icon theme |

The wallpaper and `colors.toml` are the only files this theme writes. Everything
above follows from them.

## Install

```bash
omarchy theme install https://github.com/WSeubring/omarchy-pokemon-theme
~/.config/omarchy/themes/pokemon/install.sh
```

The first command clones the theme into place and applies it. The second
schedules the daily roll and installs the hook. Requires `magick` (ImageMagick)
and `python3`, both already present on a stock Omarchy system.

To develop against a working copy instead, clone anywhere and run `install.sh`
from it — it links the checkout to `~/.config/omarchy/themes/pokemon`, so edits
take effect with no reinstall.

## Usage

```bash
bin/pokemon-theme-gen                      # generate today (no-op if current)
bin/pokemon-theme-gen --force              # roll it again now
bin/pokemon-theme-gen --pokemon mew        # preview a specific one
bin/pokemon-theme-gen --date 2026-12-25    # what will Christmas look like
bin/pokemon-theme-gen --no-apply           # write the files, don't retint
```

The daily roll is a systemd user timer at 00:05 with `Persistent=true`, so a
laptop that was asleep across midnight catches up when it wakes. Switching to
the theme by hand (`omarchy theme set pokemon`, or the theme switcher) also
regenerates, so you never land on a stale day.

To stop it: `./uninstall.sh`.

## How the palette is built

The day's Pokémon supplies **hue and nothing else**. Lightness and chroma come
from a fixed ladder measured off the stock Catppuccin and Tokyo Night themes,
whose neutral tokens all sit within about ten degrees of a single hue — that
unity is what reads as "a theme" rather than "some colours".

This split is the whole trick. Naively recolouring a theme from artwork gives
you a usable desktop on a Charizard day and an unreadable one on a Magnemite
day. Pinning the ladder and substituting only the hue means all 905 days are
structurally identical and differ only in colour.

Three places deliberately bend that rule:

- **The accent keeps its own lightness**, clamped to `[0.66, 0.865]`. Pinning it
  outright turned every yellow into mustard: hue 95 does not read as "electric"
  below L 0.85, while a violet up there is washed out. Inside the band the
  canonical type colour usually passes through untouched — electric really is
  `#f7d02c`.
- **ANSI colours rotate 15% toward the day's hue**, so the palette feels
  cohesive, but no further. Red has to still look red in a diff.
- **A second type tints the mid-greys** and pulls whichever ANSI anchors are
  closer to it, so a dual type shows up in the UI chrome without fighting the
  primary accent.

Everything happens in [OKLCh](https://bottosson.github.io/posts/oklab/), where
lightness is perceptually uniform, so "pin L" actually means "keep the same
apparent brightness" instead of "keep the same number".

## Tests

The generator will happily produce an unreadable theme if the maths is wrong on
one of 905 inputs, and you would not find out until that day came around. So
both properties are checked exhaustively rather than spot-checked:

```bash
python3 tests/validate_contrast.py   # all 905 palettes vs WCAG, and hue drift
python3 tests/validate_schedule.py   # stability, spread, no near repeats
```

`validate_contrast.py` builds every palette and asserts each text token clears
4.5:1 against its own background. Current worst case is 4.95:1, on Arbok.

## Layout

| Path | Contents |
| --- | --- |
| `bin/pokemon-theme-gen` | The generator, and the only entry point |
| `lib/oklch.py` | sRGB ↔ OKLCh, with gamut mapping by chroma reduction |
| `lib/palette.py` | The ladder, the ANSI anchors, and `colors.toml` output |
| `lib/schedule.py` | Date → Pokémon, deterministic and stateless |
| `lib/wallpaper.py` | ImageMagick composition |
| `data/dex.json` | National dex order, so a name gives an artwork id offline |
| `data/types.json` | Name → types, from PokéAPI via omarchy-lock-pokemon |
| `data/type-colors.json` | The eighteen community type colours |
| `systemd/` | The daily timer and its service |
| `hooks/theme-set` | Regenerates when you switch to this theme |

`colors.toml`, `icons.theme` and `backgrounds/today.jpg` are generated. The
wallpaper is gitignored; the other two are committed so a fresh clone applies
cleanly before the first run.

## Notes

Artwork is fetched once per Pokémon from the
[PokeAPI sprites](https://github.com/PokeAPI/sprites) repo and cached under
`~/.cache/omarchy-pokemon-theme/`, outside the theme directory — `theme set`
copies the whole theme into a staging dir on every apply, and a growing cache
would be copied along with it. With no network the palette and the ground still
render; only the creature is missing.

The artwork is composited as its own layer rather than baked into the ground.
That is deliberate: animating the wallpaper means cloning `omarchy.background`
(its `Background.qml` uses a static `Image`, so a GIF would only show frame one)
and lifting the per-type ambient effects out of `omarchy-lock-pokemon`. Keeping
the sprite addressable leaves that door open.

Only `colors.toml` is actually required of an Omarchy 4 theme. The `neovim.lua`,
`vscode.json` and `preview.png` files that stock themes carry are legacy — the
templates generate their equivalents now.

## Credits

Artwork and type data from [PokéAPI](https://pokeapi.co/). Type colours are the
long-standing community palette. Theming machinery from
[Omarchy](https://omarchy.org/). MIT licensed.
