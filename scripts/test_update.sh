#!/usr/bin/env bash
# Update flow test (headless + DevTools reads the About page text, local server). Uses fake AppImages; never touches the real one.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; t="$root/build/updtest"; port=8099
rm -rf "$t"; mkdir -p "$t/www" "$t/profile/Default"
# onboarding already done, otherwise a fresh profile redirects to the new tab page
echo '{"helium":{"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}}}' > "$t/profile/Default/Preferences"
python3 -I -m http.server $port --bind 127.0.0.1 --directory "$t/www" >/dev/null 2>&1 & srv=$!
trap 'kill $srv 2>/dev/null' EXIT; sleep 1
fail=0
run() { # name, expect "replaced"|"unchanged"
  head -c 3000000 /dev/urandom > "$t/www/$IMG"
  echo old > "$t/target"; before="$(sha256sum "$t/target" | cut -d' ' -f1)"
  "$root/scripts/release_sign.sh" sign "$t/www/$IMG" "http://127.0.0.1:$port" >/dev/null
  [ -z "${MUTATE:-}" ] || eval "$MUTATE"
  XDG_CONFIG_HOME="$root/build/xdg/config" XDG_CACHE_HOME="$root/build/xdg/cache" "$root/build/src/out/Default/helium" \
    --user-data-dir="$t/profile" --headless=new --no-first-run --no-sandbox --disable-gpu --remote-debugging-port=9333 \
    --helium-update-url="http://127.0.0.1:$port/latest.json" --helium-update-target="$t/target" about:blank >/dev/null 2>&1 & bpid=$!
  sleep 4
  python3 -I "$root/scripts/cdp_about.py" 9333 10 | tee "$t/$1.txt" | tail -1
  kill $bpid 2>/dev/null; wait $bpid 2>/dev/null; sleep 1
  after="$(sha256sum "$t/target" | cut -d' ' -f1)"; want="$(sha256sum "$t/www/$IMG" | cut -d' ' -f1)"
  if [ "$2" = replaced ]; then [ "$after" = "$want" ] && [ -x "$t/target" ] && r=PASS || r=FAIL
  else [ "$after" = "$before" ] && [ ! -e "$t/target.new" ] && r=PASS || r=FAIL; fi
  [ $r = PASS ] || fail=1; echo "$r $1 (expected $2)"
}
IMG=heliumpp-9.0.0.0-x86_64.AppImage MUTATE= run newer replaced
IMG=heliumpp-9.0.0.0-x86_64.AppImage MUTATE="sed -i 's/\"signature\":\"../\"signature\":\"00/' $t/www/latest.json" run badsig unchanged
IMG=heliumpp-9.0.0.0-x86_64.AppImage MUTATE="echo x >> $t/www/$IMG" run tampered-file unchanged
IMG=heliumpp-9.0.0.0-x86_64.AppImage MUTATE="printf X | dd of=$t/www/$IMG bs=1 count=1 conv=notrunc 2>/dev/null" run tampered-same-size unchanged
IMG=heliumpp-0.0.0.1-x86_64.AppImage MUTATE= run older unchanged
exit $fail
