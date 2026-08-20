#!/bin/bash
# Remove the timer, hook and theme link. Leaves the checkout and the artwork
# cache alone.

set -uo pipefail

THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"
PLUGIN_ID="pokemon.background"
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

# The generator writes a Discord theme into any Vesktop/Vencord it finds and
# enables it in the client's settings; without the generator those files would
# just go stale, so take both along. Same running-client caveat as enabling:
# an open client rewrites its settings on quit, but with the theme file gone
# a stale entry is harmless -- Vencord skips themes it cannot find.
for base in "$HOME/.config/vesktop" \
  "$HOME/.var/app/dev.vencord.Vesktop/config/vesktop" \
  "$HOME/.config/Vencord"; do
  rm -f "$base/themes/pokemon.css"
  [[ -f "$base/settings/settings.json" ]] && python3 - "$base/settings/settings.json" <<'EOF'
import json, sys
path = sys.argv[1]
try:
    with open(path) as fh:
        settings = json.load(fh)
except ValueError:
    sys.exit(0)
themes = settings.get("enabledThemes")
if isinstance(themes, list) and "pokemon.css" in themes:
    themes.remove("pokemon.css")
    with open(path, "w") as fh:
        json.dump(settings, fh, indent=4)
        fh.write("\n")
EOF
done

echo "Removed. If Pokemon is still the active theme, pick another:"
echo "  omarchy theme set tokyo-night"
