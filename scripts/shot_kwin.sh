#!/usr/bin/env bash
# Screenshot of the browser in a private nested KWin (virtual output, its own D-Bus session), so
# KWin effects such as blur behind the acrylic window can be checked without touching the desktop.
# Usage: scripts/shot_kwin.sh <out.png> [browser args...]   ACRYLIC_PREF=false turns acrylic off.
# A picture viewer shows a wallpaper image behind the window (BACKDROP=<image>). PREFS=<file> replaces the
# seeded Preferences. SCHEME=light|dark|system (default system), COLLAPSED=true, WIN=<w,h> (window, default
# 1100,750) inside a 1400x900 output (OUT=<w>x<h>), MATCH=1 colours the browser from BACKDROP (--match-wallpaper).
# SEED=1 adds three workspaces (scripts/shot_seed_workspaces.json); PROBE=<script.py> runs it with the remote
# debugging port as argument once the browser is up (e.g. scripts/shot_probe_workspace.py switches to "Work").
# EXTRA_PREFS='"key":value,...' adds top-level entries to the seeded Preferences (e.g. new tab shortcuts).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
out="$(realpath -m "$1")"; shift
backdrop="${BACKDROP:-/usr/share/wallpapers/cachyos-wallpapers/north.png}"
case "${SCHEME:-system}" in light) scheme=1;; dark) scheme=2;; *) scheme=0;; esac
match=""; [ "${MATCH:-0}" = 1 ] && match="--match-wallpaper=$backdrop"
out_size="${OUT:-1400x900}"
seed=""; [ "${SEED:-0}" = 1 ] && seed="\"workspaces\":$(tr -d '\n' < "$root/scripts/shot_seed_workspaces.json"),\"workspaces_active\":\"home\","
debug=""; probe=""
if [ -n "${PROBE:-}" ]; then debug="--remote-debugging-port=9339"; probe="python3 -I $(realpath "$PROBE") 9339"; fi
prof="$b/profile-kwin"; rm -rf "$prof"; mkdir -p "$prof/Default"
# PREFS=<file>: use that Preferences file instead (e.g. with workspaces set up).
if [ -n "${PREFS:-}" ]; then cp "$PREFS" "$prof/Default/Preferences"; else
cat > "$prof/Default/Preferences" <<J
{${EXTRA_PREFS:+$EXTRA_PREFS,}"helium":{$seed"browser":{"layout":${LAYOUT:-2},"native_frame_materials":${ACRYLIC_PREF:-true},"zen_mode":false},"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}},"browser":{"theme":{"color_scheme2":$scheme}},"vertical_tabs":{"collapsed_state":${COLLAPSED:-false},"uncollapsed_width":${SIDEBAR_W:-232}}}
J
fi
session="$b/kwin-session.sh"
cat > "$session" <<S
#!/usr/bin/env bash
QT_QPA_PLATFORM=wayland gwenview --fullscreen "$backdrop" >/dev/null 2>&1 &
sleep 4
XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache" "$b/src/out/Default/helium" \\
  --ozone-platform=wayland --user-data-dir="$prof" --no-first-run --window-size=${WIN:-1100,750} $match $debug $* >/dev/null 2>&1 &
sleep ${SHOT_WAIT:-14}
$probe
QT_QPA_PLATFORM=wayland spectacle -b -n -f -o "$out" >/dev/null 2>&1
sleep 2
S
chmod +x "$session"
# Nested KWin only lets Spectacle capture without a portal prompt with this test switch.
KWIN_SCREENSHOT_NO_PERMISSION_CHECKS=1 WAYLAND_DISPLAY= DISPLAY= dbus-run-session -- \
  kwin_wayland --virtual --no-lockscreen --no-global-shortcuts --no-kactivities \
  --width "${out_size%x*}" --height "${out_size#*x}" --socket heliumpp-kwin --exit-with-session "$session" >/dev/null 2>&1 || true
rm -f "$session"
[ -s "$out" ] && echo "saved $out"
