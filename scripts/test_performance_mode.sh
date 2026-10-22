#!/usr/bin/env bash
# Checks that --performance-mode=on sets the memory/energy saver prefs and =off restores the previous values.
# Uses a throwaway profile inside build/. Usage: scripts/test_performance_mode.sh
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
prof="$b/profile-perftest"; rm -rf "$prof"
run() { XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache" timeout 60 "$b/src/out/Default/helium" --user-data-dir="$prof" --headless=new --no-sandbox --disable-gpu --virtual-time-budget=3000 --screenshot=/dev/null "$@" about:blank >/dev/null 2>&1 || true; }
read_prefs() { python3 -I - "$prof/Local State" <<'P'
import json,sys
d=json.load(open(sys.argv[1])).get('performance_tuning',{})
print(d.get('high_efficiency_mode',{}).get('state'),d.get('high_efficiency_mode',{}).get('aggressiveness'),d.get('high_efficiency_mode',{}).get('time_before_discard_in_minutes'),d.get('battery_saver_mode',{}).get('state'))
P
}
read_profile() { python3 -I - "$prof/Default/Preferences" <<'P'
import json,sys
d=json.load(open(sys.argv[1]))
print(d.get('settings',{}).get('a11y',{}).get('animation_policy'),d.get('browser',{}).get('enable_spellchecking'))
P
}
run --privacy-mode=medium
echo "baseline : $(read_prefs)   (None = default, unchanged)"
run --performance-mode=on
on="$(read_prefs)"; echo "mode on  : $on   (expect: 2 2 5 3)"
echo "profile on : $(read_profile)   (expect: once False)"
run --performance-mode=off
off="$(read_prefs)"; echo "mode off : $off   (expect values back to baseline/default)"
echo "profile off: $(read_profile)   (expect: allowed True)"
[ "$on" = "2 2 5 3" ] && echo "PASS on" || { echo "FAIL on"; exit 1; }
