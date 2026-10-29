#!/usr/bin/env bash
# Redesign screenshot matrix: light/dark x three wallpapers (grey-blue, saturated, light), plus a wide window and a
# collapsed sidebar, each in a private nested KWin (scripts/shot_kwin.sh). Writes <outdir>/*.png and a contact sheet
# <outdir>/sheet.png. Usage: scripts/shot_matrix.sh <outdir> [browser args...]  ONLY=<name> runs one shot.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$(realpath -m "$1")"; shift; mkdir -p "$out"
wp=/usr/share/wallpapers/cachyos-wallpapers
declare -A walls=([grey]="$wp/north.png" [vivid]="$wp/OrangeFeathers.png" [paper]="$wp/paper.png")

shot() {  # name, then env assignments
  local name="$1"; shift
  [ -n "${ONLY:-}" ] && [ "$ONLY" != "$name" ] && return 0
  env "$@" MATCH=1 "$root/scripts/shot_kwin.sh" "$out/$name.raw.png" "${args[@]}" >/dev/null
  # Drop the picture viewer's toolbar strip at the top; the rest is wallpaper + browser window.
  magick "$out/$name.raw.png" -crop +0+88 +repage "$out/$name.png" && rm -f "$out/$name.raw.png"
  echo "$out/$name.png"
}
args=("$@")
for scheme in light dark; do
  for w in grey vivid paper; do shot "$scheme-$w" SCHEME=$scheme BACKDROP="${walls[$w]}"; done
done
shot dark-grey-wide SCHEME=dark BACKDROP="${walls[grey]}" WIN=1600,860 OUT=1700x1000
shot dark-grey-collapsed SCHEME=dark BACKDROP="${walls[grey]}" COLLAPSED=true
[ -n "${ONLY:-}" ] && exit 0
magick montage -label '%t' "$out"/{light,dark}-{grey,vivid,paper}.png "$out"/dark-grey-{wide,collapsed}.png \
  -tile 2x -geometry 700x+6+6 -background '#111' -fill '#ddd' "$out/sheet.png"
echo "$out/sheet.png"
