#!/bin/bash
# Install the Pokemon desktop, end to end. This repo is the lead: it links the
# theme, schedules the daily roll and the light/dark flips, and pulls in the
# two companions -- the lock screen plugin and the terminal Pokedex greeting --
# so one run covers the whole experience.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="$HOME/.config/omarchy/themes/pokemon"
UNIT_DIR="$HOME/.config/systemd/user"
# A fixed id, matching pokemon.lock from the companion repo. The directory name
# has to match the id in the manifest.
PLUGIN_ID="pokemon.background"
PLUGIN_DIR="$HOME/.config/omarchy/plugins/$PLUGIN_ID"

LOCK_ID="pokemon.lock"
LOCK_URL="https://github.com/WSeubring/omarchy-lock-pokemon"
GREETING_URL="https://github.com/WSeubring/pokedex-greeting"
GREETING_DIR="$HOME/.local/share/pokedex-greeting"

WITH_ANIMATION=1
WITH_MENU=1
WITH_LOCK=1
WITH_GREETING=0
MODE=""
INTENSITY=""
POKEMON=""
PIN=0
for arg in "$@"; do
  case "$arg" in
  --with-animation) WITH_ANIMATION=1 ;;
  --no-animation) WITH_ANIMATION=0 ;;
  --no-menu) WITH_MENU=0 ;;
  --no-lock) WITH_LOCK=0 ;;
  --no-greeting) WITH_GREETING=0 ;;
  --mode=*) MODE="${arg#*=}" ;;
  --intensity=*) INTENSITY="${arg#*=}" ;;
  --pokemon=*) POKEMON="${arg#*=}" ;;
  --pin) PIN=1 ;;
  --defaults) ;;
  -h | --help)
    cat <<USAGE
Usage: install.sh [options]

Links the theme, schedules the daily roll and the light/dark flip timer,
applies today's Pokemon, and offers the companions: the ambient background
motion, the omarchy menu rows, the Pokemon lock screen ($LOCK_ID), and the
terminal Pokedex greeting.

Run from a terminal with no options, it walks through the choices and shows
a live palette preview of what each one does. Any option (or a
non-interactive run) skips the questions.

  --mode=MODE        colour scheme: dark, light, auto (clock) or pokemon
                     (bright creatures get the light theme). Default dark.
  --intensity=N      colour intensity 0.4-1.6 (chroma multiplier). Default 1.
  --pokemon=NAME     start with this Pokemon today.
  --pin              with --pokemon: pin it permanently; without this flag
                     the pick lasts today only and the daily roll resumes.
  --no-animation     skip the ambient background plugin and keep the stock
                     static background renderer.
  --no-menu          skip the omarchy menu rows. They are only visible while
                     this theme is active, so installing them is harmless.
  --no-lock          skip the Pokemon lock screen plugin.
  --no-greeting      skip the terminal Pokedex greeting.
  --defaults         take every default without asking.
USAGE
    exit 0
    ;;
  *)
    echo "unknown option: $arg" >&2
    exit 1
    ;;
  esac
done

case "$MODE" in ""|dark|light|auto|pokemon) ;; *)
  echo "invalid --mode: $MODE (want dark, light, auto or pokemon)" >&2
  exit 1 ;;
esac

say() { printf '\033[32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# "Yes" is 0 so the answer reads like an exit code. Defaults to yes on a bare
# enter, and to yes wholesale when there is no terminal to ask.
ask() {
  if command -v gum >/dev/null; then
    gum confirm --default=yes "$1"
  else
    local reply
    read -r -p "$1 [Y/n] " reply
    [[ ! $reply =~ ^[Nn] ]]
  fi
}

# Pick one of $2.. under prompt $1; prints the choice. Bare enter takes the
# first option, which is therefore always the default.
choose() {
  local prompt="$1"
  shift
  if command -v gum >/dev/null; then
    gum choose --header "$prompt" "$@"
  else
    local i=1 reply
    echo "$prompt" >&2
    for opt in "$@"; do
      echo "  $i) $opt" >&2
      i=$((i + 1))
    done
    read -r -p "> " reply
    if [[ $reply =~ ^[0-9]+$ ]] && (( reply >= 1 && reply <= $# )); then
      eval "echo \"\${$reply}\""
    else
      echo "$1"
    fi
  fi
}

set_config() { # set_config key value
  python3 - "$1" "$2" <<PY
import sys
sys.path.insert(0, "$REPO/lib")
import config
key, raw = sys.argv[1], sys.argv[2]
try:
    value = float(raw) if "." in raw else int(raw)
except ValueError:
    value = raw
config.set_key(key, value)
PY
}

# Interactive only on a bare run from a terminal: any option means the caller
# already decided, and a curl-pipe or scripted run has no one to ask.
#
# Three tiers of the same questions, best available first: the browser widget
# (real rendered wallpapers, live palettes), the full-screen terminal wizard,
# and plain prompts. Each exits 2 to hand over to the next.
if (( $# == 0 )) && [[ -t 0 && -t 2 ]]; then
  wizard_status=0
  answers=$("$REPO/bin/pokemon-theme-setup-gui") || wizard_status=$?
  if (( wizard_status == 2 )); then
    wizard_status=0
    answers=$("$REPO/bin/pokemon-theme-setup") || wizard_status=$?
  fi
  if (( wizard_status == 0 )); then
    eval "$answers"
  elif (( wizard_status == 1 )); then
    die "setup aborted"
  else
    say "colour scheme -- what dark and light look like:"
    "$REPO/bin/pokemon-theme-preview" --choice mode
    MODE=$(choose "Colour scheme?" \
      "dark" "light" "auto - light 08:00-20:00, dark at night" \
      "pokemon - bright creatures get the light theme")
    MODE=${MODE%% *}

    say "colour intensity -- the same palettes, muted to vivid:"
    "$REPO/bin/pokemon-theme-preview" --choice intensity
    INTENSITY=$(choose "Colour intensity?" \
      "1.0 - as designed" "0.7 - muted" "1.3 - vivid")
    INTENSITY=${INTENSITY%% *}

    if ask "Choose your starter? (otherwise the wild daily encounter decides)"; then
      while true; do
        read -r -p "Pokemon: " POKEMON
        POKEMON=$(echo "$POKEMON" | tr '[:upper:]' '[:lower:]' | xargs)
        [[ -z $POKEMON ]] && break
        if "$REPO/bin/pokemon-theme-preview" --pokemon "$POKEMON" \
            --intensity "$INTENSITY" 2>/dev/null; then
          pick=$(choose "Keep $POKEMON?" \
            "pin it - your partner pokemon, every day" \
            "actually, a different one" \
            "keep wild encounters - a new pokemon at midnight")
          case "$pick" in
          pin*) PIN=1; break ;;
          keep*) POKEMON=""; break ;;
          esac
        else
          echo "unknown pokemon: $POKEMON (names as in the national dex, lowercase)"
        fi
      done
    fi

    ask "Animated particles on the wallpaper? (replaces the static background renderer, reversible)" \
      && WITH_ANIMATION=1 || WITH_ANIMATION=0
    ask "Pokemon picker in the omarchy menu? (pick / random / pin; hidden unless this theme is active)" \
      && WITH_MENU=1 || WITH_MENU=0
    ask "Pokemon theme lock screen? ($LOCK_URL)" \
      && WITH_LOCK=1 || WITH_LOCK=0
    ask "Pokemon greeting in the terminal? (sprite + dex entry, via pokedex-greeting)" \
      && WITH_GREETING=1 || WITH_GREETING=0
  fi
fi

for tool in magick python3 jq; do
  command -v "$tool" >/dev/null || die "$tool is required but not on PATH"
done
command -v omarchy-theme-set >/dev/null || die "this is not an Omarchy system"

# One ✓/- line per component, from the artefacts actually on the machine.
# Used before the questions (so the wizard opens on the truth) and after the
# work (so "done" means something concrete).
status_report() {
  python3 - "$REPO" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/lib")
import config
import installed
import state
have = installed.detect()
labels = (
    ("theme", "theme linked and scheduled"),
    ("animation", "animated particles on the wallpaper"),
    ("menu", "pokemon picker in the omarchy menu"),
    ("lock", "pokemon theme lock screen"),
    ("greeting", "pokemon greeting in the terminal"),
)
for key, label in labels:
    print("  %s %s" % ("\033[32m✓\033[0m" if have[key] else "-", label))
day, name, shiny, mode, _ = state.read()
if name:
    print("  today: %s%s, %s mode, intensity %.2g"
          % (name, " (shiny!)" if shiny else "", mode or "dark",
             config.intensity()))
print("  config: mode = %s  (%s)" % (config.mode(), config.PATH))
PY
}

if [[ -e $THEME_DIR ]]; then
  say "already on this machine -- current state:"
  status_report
  echo
fi

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

say "installing the daily and light/dark flip timers"
mkdir -p "$UNIT_DIR"
for unit in omarchy-pokemon-theme.service omarchy-pokemon-theme.timer \
            omarchy-pokemon-theme-flip.timer; do
  ln -sfn "$REPO/systemd/$unit" "$UNIT_DIR/$unit"
done
systemctl --user daemon-reload
systemctl --user enable --now omarchy-pokemon-theme.timer \
  omarchy-pokemon-theme-flip.timer
systemctl --user list-timers 'omarchy-pokemon-theme*' --no-pager | sed -n '2,3p'

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

if [[ -n $MODE ]]; then
  say "setting mode = $MODE"
  set_config mode "$MODE"
fi
if [[ -n $INTENSITY && $INTENSITY != 1.0 ]]; then
  say "setting intensity = $INTENSITY"
  set_config intensity "$INTENSITY"
fi

if (( WITH_LOCK )); then
  if [[ -e "$HOME/.config/omarchy/plugins/$LOCK_ID" ]]; then
    say "lock screen plugin already installed ($LOCK_ID)"
  else
    say "installing the lock screen plugin from $LOCK_URL"
    omarchy plugin add "$LOCK_URL" --enable \
      || echo "lock screen install failed; retry later with:" \
              "omarchy plugin add $LOCK_URL --enable" >&2
  fi
fi

if (( WITH_GREETING )); then
  if command -v pokedex-greeting >/dev/null; then
    say "pokedex-greeting already installed"
  elif ! command -v pokemon-colorscripts >/dev/null; then
    echo "skipping the greeting: pokemon-colorscripts is not installed" >&2
    echo "  get it first (AUR: yay -S pokemon-colorscripts-git), then run:" >&2
    echo "  git clone $GREETING_URL && bash pokedex-greeting/install.sh" >&2
  else
    say "installing pokedex-greeting from $GREETING_URL"
    if [[ -d $GREETING_DIR/.git ]]; then
      git -C "$GREETING_DIR" pull --ff-only >/dev/null || true
    else
      git clone --depth 1 "$GREETING_URL" "$GREETING_DIR"
    fi
    # Its installer is interactive itself: shiny odds, shell config lines.
    bash "$GREETING_DIR/install.sh" \
      || echo "greeting install failed; retry: bash $GREETING_DIR/install.sh" >&2
  fi
fi

say "generating today's theme"
if [[ -n $POKEMON ]] && (( PIN )); then
  "$REPO/bin/pokemon-theme-gen" --pin "$POKEMON"
elif [[ -n $POKEMON ]]; then
  "$REPO/bin/pokemon-theme-gen" --pokemon "$POKEMON" --force
else
  "$REPO/bin/pokemon-theme-gen" --force
fi

# The generation above already wrote pokemon.css into any Vesktop/Vencord it
# found and enabled it in the client's settings. A client that is open right
# now rewrites its settings on quit, so the enable lands on its next launch.
for dir in "$HOME/.config/vesktop" \
  "$HOME/.var/app/dev.vencord.Vesktop/config/vesktop" \
  "$HOME/.config/Vencord"; do
  if [[ -d $dir ]]; then
    say "Discord client found: themed. If it is open now, restart it once."
    break
  fi
done

echo
say "installed -- the desktop you are looking at is today's Pokemon:"
status_report
cat <<'DONE'

  omarchy theme set pokemon              switch to it (regenerates for today)
  bin/pokemon-theme-gen --force          roll it again now
  bin/pokemon-theme-gen --pokemon mew    preview a specific one
  bin/pokemon-theme-gen --mode light     flip the scheme for this run
  omarchy plugin enable omarchy.background   hand the desktop back to the
                                             stock renderer (motion off)
  ./uninstall.sh                         remove what this repo installed
                                         (lock and greeting are their own
                                         repos, removable separately)

Mode, flip times, intensity and the pin live in
~/.config/omarchy-pokemon-theme/config.toml.

Or from the omarchy menu, under Pokemon (shown while this theme is active):
  Pick for today / Random for today / Pin permanently / Back to daily
DONE
