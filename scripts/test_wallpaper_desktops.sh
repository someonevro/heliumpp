#!/usr/bin/env bash
# Wallpaper sync on desktops other than KDE/GNOME/Omarchy, in fake homes (HOME too, so the real
# ~/.fehbg or ~/.config is never read): XFCE, MATE + Pantheon (gsettings stubbed on PATH),
# and window managers via hyprpaper, sway, feh and nitrogen configs.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"; t="$b/test-desktops"
rm -rf "$t"; mkdir -p "$t/bin"
"$b/venv/bin/python" - "$t" <<'PY'
import sys; from PIL import Image
t = sys.argv[1]
Image.new("RGB", (400, 300), (200, 40, 90)).save(f"{t}/vivid.png")
Image.new("RGB", (400, 300), (40, 90, 200)).save(f"{t}/blue.png")
PY
# gsettings stub: answers from $GS_<schema>_<key> (dots and dashes as underscores).
cat > "$t/bin/gsettings" <<'SH'
#!/bin/sh
var="GS_$(printf '%s_%s' "$2" "$3" | tr '.-' '__')"
eval "printf '%s\n' \"\${$var:-''}\""
SH
chmod +x "$t/bin/gsettings"
fails=0
case_run() {  # name desktop expected [VAR=value ...] -> browser in fake home $t/<name>
  local name="$1" h="$t/$1" desktop="$2" want="$3"; shift 3
  mkdir -p "$h/config"
  env "$@" HOME="$h" PATH="$t/bin:$PATH" XDG_CURRENT_DESKTOP="$desktop" XDG_CONFIG_HOME="$h/config" \
    XDG_DATA_HOME="$h/data" XDG_DATA_DIRS="$h/sys" XDG_STATE_HOME="$h/state" XDG_CACHE_HOME="$h/cache" \
    "$b/src/out/Default/helium" --headless=new --no-sandbox --disable-gpu --no-first-run \
    --user-data-dir="$h/profile" about:blank >/dev/null 2>&1 & local pid=$!
  sleep 7; kill -TERM $pid; wait $pid || true
  got=$(python3 -I -c 'import json,sys; c=json.load(open(sys.argv[1])).get("browser",{}).get("theme",{}).get("user_color2"); print("none" if c is None else "#%06x" % (c & 0xFFFFFF))' "$h/profile/Default/Preferences")
  if [ "$got" = "$want" ]; then echo "ok $name $got"; else echo "FAIL $name: got $got, want $want"; fails=$((fails+1)); fi
}
V="#c8285a"; B="#285ac8"

mkdir -p "$t/xfce/config/xfce4/xfconf/xfce-perchannel-xml"
printf '<channel name="xfce4-desktop"><property name="backdrop"><property name="screen0"><property name="monitorDP-1"><property name="workspace0"><property name="last-image" type="string" value="%s"/></property></property></property></property></channel>\n' \
  "$t/vivid.png" > "$t/xfce/config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
case_run xfce XFCE "$V"

case_run mate MATE "$B" GS_org_mate_background_picture_filename="'$t/blue.png'"
case_run pantheon Pantheon "$V" GS_org_gnome_desktop_background_picture_uri="'file://$t/vivid.png'"

mkdir -p "$t/hyprpaper/config/hypr"
printf 'preload = %s\nwallpaper = ,%s\n' "$t/vivid.png" "$t/vivid.png" > "$t/hyprpaper/config/hypr/hyprpaper.conf"
case_run hyprpaper Hyprland "$V"

mkdir -p "$t/sway/config/sway"
printf 'output * bg %s fill\n' "$t/blue.png" > "$t/sway/config/sway/config"
case_run sway sway "$B"

mkdir -p "$t/feh"
printf "#!/bin/sh\nfeh --no-fehbg --bg-fill '%s'\n" "$t/vivid.png" > "$t/feh/.fehbg"
case_run feh i3 "$V"

# A config naming a missing file is skipped; the next tool's wallpaper is used.
mkdir -p "$t/fallthrough/config/sway" "$t/fallthrough/config/nitrogen"
printf 'output * bg %s fill\n' "$t/gone.png" > "$t/fallthrough/config/sway/config"
printf '[xin_-1]\nfile=%s\nmode=5\n' "$t/blue.png" > "$t/fallthrough/config/nitrogen/bg-saved.cfg"
case_run fallthrough openbox "$B"

case_run nothing openbox "none"

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
