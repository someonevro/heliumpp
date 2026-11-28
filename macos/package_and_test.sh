#!/bin/bash
# Packages a finished helium-macos build tree as an unsigned (ad-hoc signed) .dmg and smoke-tests it on
# the CI Mac. Usage, from the helium-macos root: package_and_test.sh <arch> <out-dir>
# No Apple Developer ID: Gatekeeper blocks the app on first open (right-click > Open, or
# xattr -dr com.apple.quarantine "/Applications/Helium++.app").
# shortcut: the Figtree UI font (0125, <exe dir>/fonts) is not put in the bundle (codesign rejects data
# files in Contents/MacOS), so WebUI pages fall back to the system font; move it to Resources when it matters.
set -euxo pipefail
arch="$1"; out="$(mkdir -p "$2" && cd "$2" && pwd)"
cd build/src
app="out/Default/Helium++.app"
bin="$app/Contents/MacOS/Helium++"
xattr -cs "$app"
codesign --force --deep --sign - "$app"
ver="$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$app/Contents/Info.plist")"
id="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$app/Contents/Info.plist")"
# Never Helium's bundle id: it would share real Helium's settings, keychain item and policies.
[ "$id" = io.github.someonevro.heliumpp ] || { echo "unexpected bundle id $id" >&2; exit 1; }

dmg="$out/heliumpp_${ver}_${arch}-macos.dmg"
chrome/installer/mac/pkg-dmg --sourcefile --source "$app" --target "$dmg" --volname "Helium++" \
    --format ULMO --icon "$app/Contents/Resources/app.icns" --symlink /Applications:/Applications --verbosity 2
(cd "$out" && shasum -a 256 "$(basename "$dmg")" | tee "$(basename "$dmg").sha256")

# Smoke tests, only possible when the runner can execute this arch.
[ "$(uname -m)" = "$arch" ] || { echo "runner is $(uname -m), skipping smoke tests for $arch"; exit 0; }
"$bin" --version | tee "$out/version.txt"
grep -q '^Helium++ ' "$out/version.txt"
tmp="$(mktemp -d)"
dom="$(timeout 120 "$bin" --headless=new --no-first-run --user-data-dir="$tmp/headless" --dump-dom \
    'data:text/html,<p id=ok>heliumpp-ok</p>')"
grep -q heliumpp-ok <<<"$dom"
# A real window with the default profile, so the data folder check below sees where it really writes.
support="$HOME/Library/Application Support"
"$bin" --no-first-run 'https://example.com' & pid=$!
sleep 45
screencapture -x "$out/window-$arch.png" || true
kill "$pid"; wait "$pid" || true
ls "$support" | tee "$out/app-support.txt"
[ -d "$support/heliumpp" ] || { echo "no $support/heliumpp" >&2; exit 1; }
[ ! -e "$support/net.imput.helium" ] || { echo "wrote into Helium's data folder" >&2; exit 1; }
echo "smoke tests passed"
