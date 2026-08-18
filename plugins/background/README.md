# Ambient Background

A clone of Omarchy's `omarchy.background` service plugin with one addition: an
ambient motion layer over the wallpaper, configured through a `[background]`
section in `shell.toml`.

`Background.qml` is upstream Omarchy code — the wallpaper images, the theme
transition and the reveal mask are carried verbatim. The additions are the token
readers, the pause gate, and two `Loader`s holding `Ambient` items. With no
`[background]` tokens set it behaves exactly like the plugin it was cloned from.

`Ambient.qml` and `Effects.js` come from
[omarchy-lock-pokemon](https://github.com/WSeubring/omarchy-lock-pokemon)
unchanged. They know nothing about Pokémon: `Ambient` takes a `kind` naming one
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
| `effect-tint` · `effect-secondary-tint` | theme accent | Shape colour |
| `pause-when-covered` | `true` | Stop when the focused workspace has windows |
| `pause-on-battery` | `low` | `never`, `low`, or `always` |
| `pause-on-battery-below` | `30` | The percentage `low` means |
| `debug` | `false` | Log resolved tokens and gate transitions |

When paused the `Loader`s are deactivated, so the shapes leave the scene graph
entirely rather than animating unseen behind a zero opacity.

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
omarchy plugin enable omarchy.background   # back to the stock static renderer
```

To keep the plugin but stop the motion, set `effects = "hide"` under
`[background]` in `~/.config/omarchy/shell.toml`.
