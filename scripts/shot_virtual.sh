#!/usr/bin/env bash
# Runs the browser in a private virtual display (Xvfb) and saves a screenshot of that display only.
# Usage: scripts/shot_virtual.sh <out.png> [browser args...]   (never touches the real desktop)
# ACRYLIC=1: acrylic window on, a compositor (build/tools xcompmgr) and a striped desktop behind the window.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
out="$1"; shift
disp=":97"
Xvfb $disp -screen 0 1100x800x24 >/dev/null 2>&1 & xpid=$!
trap 'kill ${bpid:-} ${cpid:-} ${spid:-} 2>/dev/null || true; sleep 1; kill $xpid 2>/dev/null || true' EXIT
sleep 1
if [ "${ACRYLIC:-}" = 1 ]; then
  ACRYLIC_PREF=${ACRYLIC_PREF:-true}
  # Stripes on the root window, so see-through areas show them.
  DISPLAY=$disp python3 -I -c '
import ctypes, time
x = ctypes.CDLL("libX11.so.6"); V, U = ctypes.c_void_p, ctypes.c_ulong
x.XOpenDisplay.restype = V
for f in ("XDefaultRootWindow", "XDefaultGC", "XCreatePixmap", "XInternAtom"): getattr(x, f).restype = U
d = V(x.XOpenDisplay(None)); r = U(x.XDefaultRootWindow(d)); gc = U(x.XDefaultGC(d, 0))
pm = U(x.XCreatePixmap(d, r, 1100, 800, 24))
for i in range(0, 1100, 40):
    x.XSetForeground(d, gc, U(0xE04080 if i // 40 % 2 else 0x30C0A0)); x.XFillRectangle(d, pm, gc, i, 0, 40, 800)
x.XSetWindowBackgroundPixmap(d, r, pm); x.XClearWindow(d, r)
x.XChangeProperty(d, r, U(x.XInternAtom(d, b"_XROOTPMAP_ID", 0)), U(20), 32, 0, ctypes.byref(pm), 1)
x.XFlush(d); time.sleep(90)' & spid=$!
  sleep 1
  "$b/tools/xcompmgr/usr/bin/xcompmgr" -d $disp >/dev/null 2>&1 & cpid=$!
  sleep 1
fi
prof="$b/profile-virtual"; rm -rf "$prof"; mkdir -p "$prof/Default"
# Same layout your window uses: vertical tabs (LAYOUT=0: horizontal), onboarding already done.
cat > "$prof/Default/Preferences" <<J
{"helium":{"browser":{"layout":${LAYOUT:-2},"native_frame_materials":${ACRYLIC_PREF:-false},"zen_mode":false},"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}},"vertical_tabs":{"collapsed_state":false,"uncollapsed_width":200}}
J
DISPLAY=$disp XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache" "$b/src/out/Default/helium" \
  --ozone-platform=x11 --user-data-dir="$prof" --no-sandbox --disable-gpu --no-first-run --window-size=1100,800 --window-position=0,0 "$@" >/dev/null 2>&1 & bpid=$!
sleep "${SHOT_WAIT:-14}"
[ -z "${PROBE:-}" ] || DISPLAY=$disp python3 -I "$PROBE"
DISPLAY=$disp import -window root "$out"
