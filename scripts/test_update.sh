#!/usr/bin/env bash
# Update flow test (headless + DevTools reads the About page text, local server). Uses fake AppImages; never touches the real one.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; t="$root/build/updtest"; port=8099
rm -rf "$t"; mkdir -p "$t/www" "$t/profile/Default"
# onboarding already done, otherwise a fresh profile redirects to the new tab page
echo '{"helium":{"completed_onboarding":true,"privacy_mode":"medium","services":{"schema_version":1,"user_consented":true}}}' > "$t/profile/Default/Preferences"
# Serves at ~4 MB/s so a 40 MB file is still downloading when the closed-tab case closes About.
python3 -I -c '
import functools, http.server, sys, time
class H(http.server.SimpleHTTPRequestHandler):
    def copyfile(self, src, dst):
        while chunk := src.read(65536):
            dst.write(chunk); time.sleep(0.016)
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), functools.partial(H, directory=sys.argv[2])).serve_forever()
' $port "$t/www" >/dev/null 2>"$t/server.log" & srv=$!
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
  sleep "${WAIT:-4}"
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
# Closing About mid-download must free the updater: reopening About downloads again (it used to
# say "already downloading" until restart).
head -c 40000000 /dev/urandom > "$t/www/heliumpp-9.0.0.2-x86_64.AppImage"
"$root/scripts/release_sign.sh" sign "$t/www/heliumpp-9.0.0.2-x86_64.AppImage" "http://127.0.0.1:$port" >/dev/null
echo old > "$t/target"
XDG_CONFIG_HOME="$root/build/xdg/config" XDG_CACHE_HOME="$root/build/xdg/cache" "$root/build/src/out/Default/helium" \
  --user-data-dir="$t/profile" --headless=new --no-first-run --no-sandbox --disable-gpu --remote-debugging-port=9333 \
  --helium-update-url="http://127.0.0.1:$port/latest.json" --helium-update-target="$t/target" about:blank >/dev/null 2>&1 & bpid=$!
sleep 4
python3 -I "$root/scripts/cdp_about.py" 9333 3 close > "$t/closed1.txt"
python3 -I "$root/scripts/cdp_about.py" 9333 20 > "$t/closed2.txt"
kill $bpid 2>/dev/null; wait $bpid 2>/dev/null; sleep 1
n=$(grep -c "GET /heliumpp-9.0.0.2" "$t/server.log")
grep -q "Updating" "$t/closed1.txt" && grep -q "Nearly up to date" "$t/closed2.txt" && [ "$n" = 2 ] \
  && echo "PASS closed-tab (About downloads again after the first About tab closed mid-download)" \
  || { fail=1; echo "FAIL closed-tab: downloads=$n, first: $(tail -1 "$t/closed1.txt") second: $(tail -1 "$t/closed2.txt")"; }
# Background check (5 min after start) installs it without the About page; About then offers
# Relaunch instead of downloading the same file a second time.
IMG=heliumpp-9.0.0.1-x86_64.AppImage MUTATE= WAIT=320 run background replaced
n=$(grep -c "GET /heliumpp-9.0.0.1" "$t/server.log"); grep -q "Nearly up to date" "$t/background.txt" && [ "$n" = 1 ] \
  && echo "PASS background: About shows Relaunch, AppImage downloaded once" \
  || { fail=1; echo "FAIL background: downloads=$n, About: $(tail -1 "$t/background.txt")"; }
exit $fail
