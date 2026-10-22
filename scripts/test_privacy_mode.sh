#!/usr/bin/env bash
# Headless check of privacy-mode enforcement. Needs a built helium. Profiles live in build/pm-*.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
export XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache"
run() {  # profile [extra args]
  local d="$b/pm-$1"; shift
  timeout 90 "$b/src/out/Default/helium" --headless=new --user-data-dir="$d" --no-first-run "$@" --dump-dom about:blank >/dev/null 2>&1
}
check() {  # profile expected-json (subset of values)
  python3 -I - "$b/pm-$1/Default/Preferences" "$1" "$2" <<'PY'
import json, sys
f, name, want = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
p = json.load(open(f))
def get(path):
    for k in path.split("/"):
        p_ = get.cur
        get.cur = p_.get(k) if isinstance(p_, dict) else None
    r = get.cur; get.cur = p; return r
get.cur = p
got = {k: get(k) for k in want}
assert got == want, f"{name}: got {got}, want {want}"
print("ok", name)
PY
}
rm -rf "$b"/pm-usability "$b"/pm-medium "$b"/pm-maximum "$b"/pm-persist
run usability --privacy-mode=usability
check usability '{"helium/privacy_mode":"usability","profile/cookie_controls_mode":2,"webrtc/ip_handling_policy":"default","https_first_balanced_mode_enabled":true,"https_only_mode_enabled":false,"profile/default_content_setting_values/geolocation":null}'
run medium --privacy-mode=medium
check medium '{"helium/privacy_mode":"medium","profile/cookie_controls_mode":1,"webrtc/ip_handling_policy":"default_public_interface_only","https_first_balanced_mode_enabled":true,"profile/default_content_setting_values/geolocation":null,"net/network_prediction_options":2}'
run maximum --privacy-mode=maximum
check maximum '{"helium/privacy_mode":"maximum","profile/cookie_controls_mode":1,"profile/default_content_setting_values/cookies":4,"webrtc/ip_handling_policy":"disable_non_proxied_udp","https_only_mode_enabled":true,"profile/default_content_setting_values/geolocation":2,"profile/default_content_setting_values/notifications":2,"profile/default_content_setting_values/media_stream_mic":2,"profile/default_content_setting_values/media_stream_camera":2}'
# persistence: choose maximum once, restart WITHOUT the switch, then switch to usability and make sure it resets
run persist --privacy-mode=maximum
run persist
check persist '{"helium/privacy_mode":"maximum","profile/default_content_setting_values/cookies":4}'
run persist --privacy-mode=usability
check persist '{"helium/privacy_mode":"usability","profile/cookie_controls_mode":2,"profile/default_content_setting_values/cookies":null,"profile/default_content_setting_values/geolocation":null,"webrtc/ip_handling_policy":"default"}'

# fingerprinting/referrer flags live in Local State (browser-wide); other flags must survive
flags() {  # profile
  python3 -I -c "import json,sys;print(json.dumps(sorted(json.load(open(sys.argv[1])).get('browser',{}).get('enabled_labs_experiments',[]))))" "$b/pm-$1/Local State"
}
expect() { [ "$(flags "$1")" = "$2" ] || { echo "FAIL flags $1: got $(flags "$1"), want $2"; exit 1; }; echo "ok flags $1"; }
rm -rf "$b"/pm-flags "$b"/pm-flagsmed; mkdir -p "$b/pm-flags"
echo '{"browser":{"enabled_labs_experiments":["enable-incognito-themes"]}}' > "$b/pm-flags/Local State"
run flags --privacy-mode=maximum
expect flags '["enable-incognito-themes", "fingerprinting-canvas-measuretext-noise", "fingerprinting-client-rects-noise", "reduced-system-info@1", "remove-client-hints@1", "remove-cross-origin-referrers@1"]'
run flags --privacy-mode=medium
expect flags '["enable-incognito-themes"]'
run flagsmed --privacy-mode=medium
expect flagsmed '[]'
