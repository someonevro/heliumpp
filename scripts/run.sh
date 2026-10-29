#!/usr/bin/env bash
# Launch the built browser with a profile kept inside build/. Usage: scripts/run.sh <profile-name> [extra args]
# A name that does not exist yet starts a brand-new profile (first-run setup shows).
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <profile-name> [args...]" >&2; exit 1; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
name="$1"; shift
export XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache"
# The browser reads the desktop's wallpaper/accent from $XDG_CONFIG_HOME, so link those in.
mkdir -p "$XDG_CONFIG_HOME"
for f in kdeglobals plasma-org.kde.plasma.desktop-appletsrc dconf hypr sway nitrogen xfce4; do
  if [ -e "$HOME/.config/$f" ] && [ ! -e "$XDG_CONFIG_HOME/$f" ]; then ln -s "$HOME/.config/$f" "$XDG_CONFIG_HOME/$f"; fi
done
# HELIUM_BIN: run a saved build instead (build/saved/*/bin/helium).
exec "${HELIUM_BIN:-$b/src/out/Default/helium}" --user-data-dir="$b/profile-$name" "$@"
