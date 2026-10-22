#!/usr/bin/env bash
# Ad-blocking check: ad/tracker hostnames are mapped to a local server; blocked requests never reach it.
# Needs a built helium + chromedriver. Fails unless every ad host is blocked and the control host loads.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
export XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache"
: > "$b/adtest.log"; [ -n "${KEEP:-}" ] || rm -rf "$b/ab-def"
python3 -I "$root/scripts/adblock_test/server.py" 8765 "$b/adtest.log" & srv=$!
"$b/src/out/Default/chromedriver" --port=9515 > "$b/chromedriver.log" 2>&1 & drv=$!
trap 'kill $srv $drv 2>/dev/null' EXIT
sleep 2
res=$(python3 -I "$root/scripts/adblock_test/run.py" "$b/ab-def" "${WARMUP:-25}")
echo "$res"
python3 -I - "$res" "$b/adtest.log" <<'PY'
import json, sys
r = json.loads(sys.argv[1]); log = open(sys.argv[2]).read()
assert r.pop("control") == "loaded", "control host did not load: test setup broken"
bad = [h for h, v in r.items() if v != "blocked"]
reached = [h for h in r if f"{h}:" in log]
assert not bad and not reached, f"not blocked: {bad}; reached server: {reached}"
print(f"ok: {len(r)} ad/tracker hosts blocked, none reached the server")
PY
