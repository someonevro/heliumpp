#!/usr/bin/env bash
# Theme checks: fallback color on a new profile, wallpaper accent from a vivid test image, and no accent from a gray image.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
export XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache"
real_state="${XDG_STATE_HOME:-$HOME/.local/state}"
export XDG_STATE_HOME="$b/xdg/state"   # isolate from the real desktop wallpaper; restored for the informational check
# No desktop type either: on KDE the browser also reads system-wide defaults (/etc/xdg/kdeglobals,
# /usr/share wallpapers), which would give a "new" profile the distro's color.
export XDG_CURRENT_DESKTOP=
"$b/venv/bin/python" - "$b" <<'PY'
import sys; from PIL import Image
b=sys.argv[1]
Image.new("RGB",(400,300),(200,40,90)).save(f"{b}/wp-vivid.png")   # crimson
Image.new("RGB",(400,300),(110,110,110)).save(f"{b}/wp-gray.png")
Image.new("RGB",(400,300),(40,90,200)).save(f"{b}/wp-blue.png")
PY
"$b/src/out/Default/chromedriver" --port=9515 > "$b/chromedriver.log" 2>&1 & drv=$!
trap 'kill $drv 2>/dev/null' EXIT
sleep 2
session() {  # profile [chrome args...]  -> start, wait, quit cleanly so prefs are flushed
  python3 -I - "$b" "$@" <<'PY'
import json, sys, time, urllib.request
b, profile, extra = sys.argv[1], sys.argv[2], sys.argv[3:]
def call(m, p, body=None):
    r = urllib.request.Request("http://127.0.0.1:9515" + p, method=m, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=120))["value"]
sid = call("POST", "/session", {"capabilities": {"alwaysMatch": {"goog:chromeOptions": {"binary": f"{b}/src/out/Default/helium", "excludeSwitches": ["disable-extensions"],
    "args": ["--headless=new", f"--user-data-dir={b}/{profile}", "--no-first-run", *extra]}}}})["sessionId"]
time.sleep(6)
call("DELETE", f"/session/{sid}")
PY
}
color() {  # profile -> user_color as #rrggbb or none
  python3 -I - "$b/$1/Default/Preferences" <<'PY'
import json, sys
c = json.load(open(sys.argv[1])).get("browser", {}).get("theme", {}).get("user_color2")
print("none" if c is None else "#%06x" % (c & 0xFFFFFF))
PY
}
rm -rf "$b"/th-new "$b"/th-vivid "$b"/th-gray "$b"/th-default "$b"/th-user "$b/xdg/state"
session th-new;                                          got=$(color th-new);   [ "$got" = "none" ] || { echo "FAIL fallback: $got"; exit 1; }; echo "ok fallback $got"
session th-vivid --match-wallpaper="$b/wp-vivid.png";    got=$(color th-vivid); echo "vivid image -> $got"; [ "$got" = "#c8285a" ] || { echo "FAIL vivid accent"; exit 1; }; echo "ok wallpaper accent"
session th-gray --match-wallpaper="$b/wp-gray.png";      got=$(color th-gray);  [ "$got" = "none" ] || { echo "FAIL gray should stay grayscale: $got"; exit 1; }; echo "ok gray image stays grayscale"
# default-on: a fake Omarchy wallpaper link, no switch at all
mkdir -p "$b/xdg/state/omarchy/current"; ln -sf "$b/wp-vivid.png" "$b/xdg/state/omarchy/current/background"
session th-default;                                      got=$(color th-default); [ "$got" = "#c8285a" ] || { echo "FAIL default-on wallpaper: $got"; exit 1; }; echo "ok default-on picks wallpaper $got"
# unchanged wallpaper is skipped at startup (0062); a swapped one must still apply, and a relaunch must keep it
rm -rf "$b/th-swap"; session th-swap;                     got=$(color th-swap);  [ "$got" = "#c8285a" ] || { echo "FAIL swap start: $got"; exit 1; }
ln -sf "$b/wp-blue.png" "$b/xdg/state/omarchy/current/background"
session th-swap;                                          got=$(color th-swap);  [ "$got" = "#285ac8" ] || { echo "FAIL swapped wallpaper not applied: $got"; exit 1; }
session th-swap;                                          got=$(color th-swap);  [ "$got" = "#285ac8" ] || { echo "FAIL relaunch lost color: $got"; exit 1; }; echo "ok swapped wallpaper applied and kept $got"
ln -sf "$b/wp-vivid.png" "$b/xdg/state/omarchy/current/background"
# performance mode pauses the sync (0068): the swap back to crimson must not apply until it is off again
session th-swap --performance-mode=on;                     got=$(color th-swap);  [ "$got" = "#285ac8" ] || { echo "FAIL performance mode still synced: $got"; exit 1; }
session th-swap --performance-mode=off;                    got=$(color th-swap);  [ "$got" = "#c8285a" ] || { echo "FAIL sync did not resume: $got"; exit 1; }; echo "ok performance mode pauses and resumes sync"
# a color the user chose must survive a restart even though a wallpaper accent exists
python3 -I - "$b/th-default/Default/Preferences" <<'PY'
import json, sys
f = sys.argv[1]; p = json.load(open(f)); p["browser"]["theme"]["user_color2"] = -16711936  # 0xFF00FF00, not ours
json.dump(p, open(f, "w"))
PY
session th-default;                                      got=$(color th-default); [ "$got" = "#00ff00" ] || { echo "FAIL user theme overridden: $got"; exit 1; }; echo "ok user-chosen color kept $got"
# informational: the real desktop wallpaper (Omarchy symlink), result depends on the image.
# The path is passed explicitly because the browser inherits the isolated XDG_STATE_HOME above.
if [ -e "$real_state/omarchy/current/background" ]; then
  rm -rf "$b/th-real"; session th-real --match-wallpaper="$real_state/omarchy/current/background"
  echo "real wallpaper -> $(color th-real) (#20222e means the image has no usable color)"
fi
