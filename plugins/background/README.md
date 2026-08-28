# Ambient Background

A clone of Omarchy's `omarchy.background` service plugin with one addition: an
ambient motion layer over the wallpaper, configured through a `[background]`
section in `shell.toml`.

`Background.qml` is upstream Omarchy code — the wallpaper images, the theme
transition and the reveal mask are carried verbatim. The additions are the token
readers, the pause gate, and two `Loader`s holding `Ambient` items. With no
`[background]` tokens set it behaves exactly like the plugin it was cloned from.

`Ambient.qml` and `Effects.js` come from
[omarchy-lock-pokemon](https://github.com/WSeubring/omarchy-lock-pokemon) —
`Effects.js` unchanged, `Ambient.qml` with one addition: a `sizeScale` property,
which defaults to the lock screen's own sizing. The lock screen is not touched
by anything here. They know nothing about Pokémon: `Ambient` takes a `kind` naming one
of the eighteen behaviours in `Effects.js`, plus a variant, a tint and an
intensity. The theme resolves types to effect names and passes them as tokens,
so this plugin stays a generic ambient-background renderer.

## Tokens

All under `[background]`, in a theme's `shell.background.toml` or in
`~/.config/omarchy/shell.toml` (the latter wins per key).

| Key | Default | Meaning |
| --- | --- | --- |
| `effects` | `hide` | Master switch. Nothing animates until this is on |
| `effect-primary` | `none` | Effect name, e.g. `embers`, `leaves`, `wisps` |
| `effect-secondary` | `none` | Layered behind the primary |
| `effect-secondary-strength` | `0.55` | Density of that second layer |
| `effect-intensity` | `1.0` | Scales shape counts; `0` disables |
| `effect-variant` | `1` | `1` calm, `2` busy, `3` bold |
| `effect-count-scale` | `1.8` | Desktop bump: shapes per screen |
| `effect-size-scale` | `1.4` | Desktop bump: shape size and wander |
| `effect-tint` · `effect-secondary-tint` | theme accent | Shape colour |
| `pause-when-covered` | `true` | Stop on a monitor whose active workspace has windows |
| `pause-on-battery` | `low` | `never`, `low`, or `always` |
| `pause-on-battery-below` | `30` | The percentage `low` means |
| `debug` | `false` | Log resolved tokens and gate transitions |

## Why the desktop scales the numbers

`Effects.js` was tuned against a lock-screen card. A monitor is one to two
orders of magnitude more pixels, so the same twelve 3px embers read as two
specks of dust on a 1920x1200 desktop rather than as a fire. `effect-count-scale`
and `effect-size-scale` are the whole adjustment: a few more shapes, each a
little bigger. They are kept modest on purpose — a card is glanced at for a
second, a desktop is looked past all day, so the motion should be noticeable on
an empty workspace and never something you have to look around. Set both to
`1.0` for exactly the lock screen's numbers.

When paused the `Loader`s are deactivated, so the shapes leave the scene graph
entirely rather than animating unseen behind a zero opacity.

Coverage is asked per monitor, not once for the desktop: an empty second screen
keeps moving while the screen being worked on is full of windows. Each panel
resolves its own Hyprland monitor out of `Hyprland.monitors`, reads that
monitor's active workspace, and gates its own two `Loader`s. Only the master
switch, the intensity and the battery policy are still decided once for
everything. A monitor Hyprland has not answered for yet counts as uncovered.

A monitor showing only a special workspace reads as uncovered, because
`activeWorkspace` does not include special workspaces -- shapes will animate
behind those windows.

A background layer is awkward to introspect -- it sits under every window and has
no chrome of its own -- so `debug = "true"` logs the resolved tokens and every
gate transition:

```bash
journalctl --user -f | grep ambient-bg
# [ambient-bg] gate-changed enabled=true primary=leaves ... covered=true RUNNING=false
```

Plugin code changes need `omarchy restart shell`; saving alone does not reliably
reload them.

## Reverting

```bash
omarchy plugin disable pokemon.background  # back to the stock static renderer
```

Enabling this plugin is what disables `omarchy.background`: the shell reads
`clonedFrom` from the manifest, switches the source off, and records the
handover so that disabling or removing this one gives the desktop back. Do not
disable `omarchy.background` by hand first -- the shell only arms that restore
while the source is still enabled, and without it the desktop is left with no
background renderer at all. `omarchy plugin enable omarchy.background` is the
way back from that state.

To keep the plugin but stop the motion, set `effects = "hide"` under
`[background]` in `~/.config/omarchy/shell.toml`.
