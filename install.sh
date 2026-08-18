#!/bin/bash
# Install the Pokemon-of-the-day theme: put it where omarchy looks for themes,
# schedule the daily roll, and apply it once.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"
# Omarchy namespaces user plugins as <username>.<id>, and the directory name has
# to match the id in the manifest.
PLUGIN_ID="${USER:-$(id -un)}.background"
PLUGIN_DIR="$HOME/.config/omarchy/plugins/$PLUGIN_ID"

WITH_ANIMATION=0
WITH_MENU=1
for arg in "$@"; do
  case "$arg" in
  --with-animation) WITH_ANIMATION=1 ;;
  --no-menu) WITH_MENU=0 ;;
  -h | --help)
    cat <<USAGE
Usage: install.sh [--with-animation]

Links the theme, schedules the daily roll, and applies it.

  --with-animation   also install the ambient background plugin, which adds
                     subtle per-type motion behind the wallpaper. Replaces
                     omarchy's static background renderer; reversible with
                     'omarchy plugin enable omarchy.background'.
  --no-menu          skip the omarchy menu rows. They are only visible while
                     this theme is active, so installing them is harmless.
USAGE
    exit 0
    ;;
  *)
    echo "unknown option: $arg" >&2
    exit 1
    ;;
  esac
done

say() { printf '\033[32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

for tool in magick python3 jq; do
  command -v "$tool" >/dev/null || die "$tool is required but not on PATH"
done
command -v omarchy-theme-set >/dev/null || die "this is not an Omarchy system"

# The theme has to be reachable at the slug omarchy will look up. A checkout
# already in place (via `omarchy theme install`) is left alone; anywhere else is
# linked, so edits in the working copy take effect with no reinstall.
if [[ "$REPO" == "$(readlink -f "$THEME_DIR" 2>/dev/null || echo)" ]]; then
  say "theme already linked at $THEME_DIR"
elif [[ -e $THEME_DIR && ! -L $THEME_DIR ]]; then
  die "$THEME_DIR exists and is not a symlink; move it aside first"
else
  mkdir -p "$(dirname "$THEME_DIR")"
  ln -sfn "$REPO" "$THEME_DIR"
  say "linked $THEME_DIR -> $REPO"
fi

say "installing the theme-set hook"
omarchy hook install theme-set "$REPO/hooks/theme-set" >/dev/null
say "installed ~/.config/omarchy/hooks/theme-set.d/theme-set"

say "installing the daily timer"
mkdir -p "$UNIT_DIR"
for unit in omarchy-pokemon-theme.service omarchy-pokemon-theme.timer; do
  ln -sfn "$REPO/systemd/$unit" "$UNIT_DIR/$unit"
done
systemctl --user daemon-reload
systemctl --user enable --now omarchy-pokemon-theme.timer
systemctl --user list-timers omarchy-pokemon-theme.timer --no-pager | sed -n 2p

if (( WITH_ANIMATION )); then
  say "installing the ambient background plugin as $PLUGIN_ID"
  if [[ -e $PLUGIN_DIR && ! -L $PLUGIN_DIR ]]; then
    die "$PLUGIN_DIR exists and is not a symlink; move it aside first"
  fi
  mkdir -p "$(dirname "$PLUGIN_DIR")"
  ln -sfn "$REPO/plugins/background" "$PLUGIN_DIR"
  # The manifest id has to match the directory name. It is generated rather
  # than committed so the repo does not carry one user's username.
  jq --arg id "$PLUGIN_ID" '.id = $id' "$REPO/plugins/background/manifest.json.in" \
    >"$REPO/plugins/background/manifest.json"

  # Two plugins claiming the background layer would both draw. The clone carries
  # clonedFrom, so IPC calls (including theme transitions) still route here.
  omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
  omarchy plugin disable omarchy.background >/dev/null 2>&1 || true
  omarchy plugin enable "$PLUGIN_ID" >/dev/null 2>&1 || true
  say "disabled omarchy.background in favour of the clone"
fi

if (( WITH_MENU )); then
  # The rows carry a `when` condition, so they stay hidden unless this theme is
  # the active one; installing them for everyone costs nothing.
  "$REPO/bin/pokemon-theme-menu-install"
fi

say "generating today's theme"
"$REPO/bin/pokemon-theme-gen" --force

cat <<'DONE'

Done. Today's Pokemon is live.

  omarchy theme set pokemon              switch to it (regenerates for today)
  bin/pokemon-theme-gen --force          roll it again now
  bin/pokemon-theme-gen --pokemon mew    preview a specific one
  ./install.sh --with-animation          add ambient motion behind the wallpaper
  ./uninstall.sh                         remove everything this installed

Or from the omarchy menu, under Pokemon (shown while this theme is active):
  Pick for today / Pin permanently / Unpin / Roll again
DONE
