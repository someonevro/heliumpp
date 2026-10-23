#!/usr/bin/env bash
# KDE wallpaper/accent integration test in a fake home (never reads the real desktop or /usr/share):
# picked wallpaper, global-theme default wallpaper, "Next" + AccentColor fallback, selection-colour fallback.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"; t="$b/test-kde"
rm -rf "$t"; mkdir -p "$t"
"$b/venv/bin/python" - "$t" <<'PY'
import sys; from PIL import Image
t = sys.argv[1]
Image.new("RGB", (400, 300), (200, 40, 90)).save(f"{t}/vivid.png")
Image.new("RGB", (400, 300), (40, 90, 200)).save(f"{t}/blue.png")
Image.new("RGB", (400, 300), (110, 110, 110)).save(f"{t}/gray.png")
PY
fails=0
case_run() {  # name expected -> runs the browser in fake home $t/<name>, reads the applied colour
  local h="$t/$1"
  XDG_CURRENT_DESKTOP=KDE XDG_CONFIG_HOME="$h/config" XDG_DATA_HOME="$h/data" XDG_DATA_DIRS="$h/sys" \
  XDG_STATE_HOME="$h/state" XDG_CACHE_HOME="$h/cache" \
    "$b/src/out/Default/helium" --headless=new --no-sandbox --disable-gpu --no-first-run \
    --user-data-dir="$h/profile" about:blank >/dev/null 2>&1 & local pid=$!
  sleep 7; kill -TERM $pid; wait $pid || true
  got=$(python3 -I -c 'import json,sys; c=json.load(open(sys.argv[1])).get("browser",{}).get("theme",{}).get("user_color2"); print("none" if c is None else "#%06x" % (c & 0xFFFFFF))' "$h/profile/Default/Preferences")
  if [ "$got" = "$2" ]; then echo "ok $1 $got"; else echo "FAIL $1: got $got, want $2"; fails=$((fails+1)); fi
}
pkg() {  # home wallpaper-dir-name image
  mkdir -p "$t/$1/sys/wallpapers/$2/contents/images"; cp "$t/$3" "$t/$1/sys/wallpapers/$2/contents/images/1920x1080.png"
}
mkdir -p "$t"/{picked,laf,next-accent,next-selection}/config

printf '[Containments][1][Wallpaper][org.kde.image][General]\nImage=file://%s\n' "$t/vivid.png" \
  > "$t/picked/config/plasma-org.kde.plasma.desktop-appletsrc"
case_run picked "#c8285a"

# never picked: appletsrc has no Image=, global theme names the wallpaper package
printf '[Containments][1]\nplugin=org.kde.plasma.folder\n' > "$t/laf/config/plasma-org.kde.plasma.desktop-appletsrc"
printf '[KDE]\nLookAndFeelPackage=test.laf\n' > "$t/laf/config/kdeglobals"
mkdir -p "$t/laf/sys/plasma/look-and-feel/test.laf/contents"
printf '[Wallpaper]\nImage=TestWall\n' > "$t/laf/sys/plasma/look-and-feel/test.laf/contents/defaults"
pkg laf TestWall blue.png; pkg laf Next vivid.png
case_run laf "#285ac8"

# no config at all: Plasma's "Next" (gray here, no usable colour) -> KDE AccentColor
printf '[General]\nAccentColor=200,40,90\n' > "$t/next-accent/config/kdeglobals"
pkg next-accent Next gray.png
case_run next-accent "#c8285a"

# no AccentColor: the colour scheme's selection colour is Plasma's accent
printf '[Colors:Selection]\nBackgroundNormal=40,90,200\n' > "$t/next-selection/config/kdeglobals"
pkg next-selection Next gray.png
case_run next-selection "#285ac8"

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
