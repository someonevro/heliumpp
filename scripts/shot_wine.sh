#!/usr/bin/env bash
# Screenshot of the Windows build running under Wine in a private Xvfb display (build/winrun is the only place used).
# Usage: scripts/shot_wine.sh <out.png> [URL] [-- extra browser args]   env: PKG=<dir with chrome.exe> LAYOUT=2|0 (2 = vertical)
# Wine is not Windows: no DWM (rounded corners, Mica, snap layouts) and a different frame; use it for layout, fonts,
# colours, WebUI pages. Needs an unpacked portable zip (gh release download <tag> -p '*-windows.zip').
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; w="$root/build/winrun"
out="$(realpath -m "$1")"; url="${2:-chrome://new-tab-page}"; [ "${3:-}" = "--" ] && shift 3 || shift $(( $# > 1 ? 2 : $# ))
pkg="${PKG:-$(echo "$w"/zip/*/)}"; [ -f "$pkg/chrome.exe" ] || { echo "no chrome.exe in $pkg" >&2; exit 1; }
export WINEPREFIX="$w/prefix" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml=" WINEARCH=win64 DISPLAY=:97
wineserver -k 2>/dev/null || true; pkill -f "Xvfb :97" 2>/dev/null || true
Xvfb :97 -screen 0 1400x860x24 >/dev/null 2>&1 & xv=$!; sleep 2
trap 'wineserver -k 2>/dev/null || true; kill $xv 2>/dev/null || true' EXIT
rm -rf "$w/profile"; mkdir -p "$w/profile/Default"
cat > "$w/profile/Default/Preferences" <<J
{"helium":{"browser":{"layout":${LAYOUT:-2},"native_frame_materials":false,"zen_mode":false},"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}},"vertical_tabs":{"collapsed_state":false,"uncollapsed_width":200}}
J
(cd "$pkg" && wine chrome.exe --no-sandbox --test-type --disable-gpu --no-first-run \
  --user-data-dir="Z:${w//\//\\}\\profile" "$@" "$url" >"$w/wine.log" 2>&1 &)
sleep "${WAIT:-45}"; import -display :97 -window root "$out"; echo "$out"
