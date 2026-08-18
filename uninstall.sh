#!/bin/bash
# Remove the timer, hook and theme link. Leaves the checkout and the artwork
# cache alone.

set -uo pipefail

THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"

systemctl --user disable --now omarchy-pokemon-theme.timer 2>/dev/null
rm -f "$UNIT_DIR/omarchy-pokemon-theme.timer" "$UNIT_DIR/omarchy-pokemon-theme.service"
systemctl --user daemon-reload
rm -f "$HOME/.config/omarchy/hooks/theme-set.d/theme-set"
[[ -L $THEME_DIR ]] && rm -f "$THEME_DIR"

echo "Removed. If Pokemon is still the active theme, pick another:"
echo "  omarchy theme set tokyo-night"
