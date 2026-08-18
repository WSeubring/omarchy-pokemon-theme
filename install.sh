#!/bin/bash
# Install the Pokemon-of-the-day theme: put it where omarchy looks for themes,
# schedule the daily roll, and apply it once.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"

say() { printf '\033[32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

for tool in magick python3; do
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

say "generating today's theme"
"$REPO/bin/pokemon-theme-gen" --force

cat <<'DONE'

Done. Today's Pokemon is live.

  omarchy theme set pokemon              switch to it (regenerates for today)
  bin/pokemon-theme-gen --force          roll it again now
  bin/pokemon-theme-gen --pokemon mew    preview a specific one
  ./uninstall.sh                         remove the timer and hook
DONE
