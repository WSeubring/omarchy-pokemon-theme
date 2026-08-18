# Pokémon Theme

An [Omarchy](https://omarchy.org/) 4 theme that picks a different Pokémon every
day. Its **own artwork** sets the palette, the whole desktop retints to match,
and that artwork becomes the wallpaper. Every couple of weeks, it shows up
shiny.

![The Gen 1 starters, their evolutions, and a few iconic Pokémon](docs/gallery.jpg)

Companion to [omarchy-lock-pokemon](https://github.com/WSeubring/omarchy-lock-pokemon),
which does the same thing to the lock screen: with both installed, unlocking
shows the Pokémon already on the desktop.

## What changes

Omarchy generates seventeen config files from a theme's `colors.toml`, so one
palette carries all the way out to the edges:

| | |
| --- | --- |
| Terminals | alacritty, foot, kitty, ghostty |
| Editors | neovim, helix, vscode, obsidian |
| Shell & tools | the Omarchy bar, btop, gum, chromium |
| Agents | claude, pi |
| System | hyprland borders, keyboard backlight, icon theme |

The colours come from the creature's own artwork: Charizard's orange belly,
Lapras's specific blue, Umbreon's yellow rings. Dual types show up too, as a
two-stop border gradient and a second layer of ambient motion.

![The whole desktop on a Golbat day](preview.png)

The same desktop on a Venusaur, Charizard and Blastoise day:

![A Venusaur day](docs/desktop-venusaur.jpg)
![A Charizard day](docs/desktop-charizard.jpg)
![A Blastoise day](docs/desktop-blastoise.jpg)

## Install

```bash
omarchy theme install https://github.com/WSeubring/omarchy-pokemon-theme
~/.config/omarchy/themes/pokemon/install.sh
```

The installer asks about the two extras (both default to yes):

- **Ambient motion**: the day's types drive subtle motion behind the wallpaper.
  Embers for a fire type, drifting flakes for an ice type, wisps for a ghost.
- **Menu rows**: a Pokémon section in the omarchy menu, shown only while this
  theme is active.

Flags (`--no-animation`, `--no-menu`, `--defaults`) or a non-interactive run
skip the questions. Everything is reversible with `./uninstall.sh`.

The theme rolls itself at midnight, catches up after sleep, and regenerates
whenever you switch to it, so you never land on a stale day.

## Picking a Pokémon

From the omarchy menu, under **Pokémon**:

```
Pokémon…
   Pick for today     search all 905; reverts at midnight
   Random for today   surprise me; reverts at midnight
   Pin permanently    keep one until you unpin it
   Back to daily ✓    drop any pin and use the day's own Pokémon
```

Or from the command line:

```bash
bin/pokemon-theme-gen --pokemon gengar   # just for today
bin/pokemon-theme-gen --random           # a random one, just for today
bin/pokemon-theme-gen --pin lapras       # permanently
bin/pokemon-theme-gen --unpin            # back to the daily roll
```

The generator always prints what it chose and why:

```
$ bin/pokemon-theme-gen
2026-08-18  #131 lapras (water/ice)  accent #6390f0  [pinned in config]
```

## Shiny

Every day rolls for shiny at **1 in 14**, about once a fortnight. A shiny day
is obvious from across the room: the shiny artwork's colours theme the whole
desktop (shiny Charizard means black-and-red, not orange), sparkles ring the
creature on the wallpaper, gold twinkles join the ambient motion, and the lock
screen fires its own sparkle animation.

Rerolling is how you hunt one: `--random`, or "Random for today" in the menu.
A shiny that turns up sticks for the rest of the day. `--shiny` forces one,
`--no-shiny` forces it back.

## Configuration

Yours to edit, in `~/.config/omarchy-pokemon-theme/config.toml`:

```toml
pokemon = "lapras"   # pin one permanently; remove the line (or --unpin) to stop
shiny-odds = 14      # 1 in N per day; 4096 for canonical full odds
```

Per-key overrides in `~/.config/omarchy/shell.toml` win over anything the
theme writes:

```toml
[background]
effects            = "hide"    # ambient motion off, plugin still installed
effect-intensity   = 1.0      # default is 0.55
pause-on-battery   = "never"  # default pauses when discharging below 30%
pause-when-covered = "false"  # default pauses when windows cover the desktop

[lock]
pokemon-name = ""             # lock screen rolls its own Pokémon again
```

Ambient motion pauses on its own when nobody can see it: whenever windows
cover the desktop, and on low battery. See
[plugins/background/README.md](plugins/background/README.md) for every token.

## More

How the palette is built, why all 905 days stay readable, the test suite, and
the repository layout: [docs/internals.md](docs/internals.md).

## Credits

Artwork and type data from [PokéAPI](https://pokeapi.co/). Type colours are the
long-standing community palette. Theming machinery from
[Omarchy](https://omarchy.org/). MIT licensed.
