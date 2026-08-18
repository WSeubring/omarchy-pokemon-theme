#!/bin/bash
# Remove the timer, hook and theme link. Leaves the checkout and the artwork
# cache alone.

set -uo pipefail

THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"
PLUGIN_ID="${USER:-$(id -un)}.background"
PLUGIN_DIR="$HOME/.config/omarchy/plugins/$PLUGIN_ID"

systemctl --user disable --now omarchy-pokemon-theme.timer 2>/dev/null
rm -f "$UNIT_DIR/omarchy-pokemon-theme.timer" "$UNIT_DIR/omarchy-pokemon-theme.service"
systemctl --user daemon-reload
rm -f "$HOME/.config/omarchy/hooks/theme-set.d/theme-set"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$REPO/bin/pokemon-theme-menu-install" --remove 2>/dev/null || true

# Hand the background layer back to omarchy before removing the clone, or the
# desktop is left with no renderer at all.
if [[ -L $PLUGIN_DIR ]]; then
  omarchy plugin enable omarchy.background >/dev/null 2>&1 || true
  omarchy plugin disable "$PLUGIN_ID" >/dev/null 2>&1 || true
  rm -f "$PLUGIN_DIR"
  omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
  echo "Restored omarchy.background and removed $PLUGIN_ID"
fi
[[ -L $THEME_DIR ]] && rm -f "$THEME_DIR"

echo "Removed. If Pokemon is still the active theme, pick another:"
echo "  omarchy theme set tokyo-night"
