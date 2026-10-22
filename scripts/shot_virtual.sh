#!/usr/bin/env bash
# Runs the browser in a private virtual display (Xvfb) and saves a screenshot of that display only.
# Usage: scripts/shot_virtual.sh <out.png> [browser args...]   (never touches the real desktop)
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
out="$1"; shift
disp=":97"
Xvfb $disp -screen 0 1100x800x24 >/dev/null 2>&1 & xpid=$!
sleep 1
prof="$b/profile-virtual"; rm -rf "$prof"; mkdir -p "$prof/Default"
# Same layout your window uses: vertical tabs, onboarding already done.
cat > "$prof/Default/Preferences" <<'J'
{"helium":{"browser":{"layout":2,"zen_mode":false},"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}},"vertical_tabs":{"collapsed_state":false,"uncollapsed_width":200}}
J
DISPLAY=$disp XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache" "$b/src/out/Default/helium" \
  --ozone-platform=x11 --user-data-dir="$prof" --no-sandbox --disable-gpu --no-first-run --window-size=1100,800 --window-position=0,0 "$@" >/dev/null 2>&1 & bpid=$!
sleep "${SHOT_WAIT:-14}"
DISPLAY=$disp import -window root "$out"
kill $bpid 2>/dev/null || true; sleep 1; kill $xpid 2>/dev/null || true
