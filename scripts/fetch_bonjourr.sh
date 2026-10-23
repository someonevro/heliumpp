#!/usr/bin/env bash
# Puts Bonjourr (GPL-3.0 new tab page, https://github.com/victrme/Bonjourr) into <dest> with Helium++'s
# privacy defaults. Usage: scripts/fetch_bonjourr.sh <dest-dir>   (e.g. build/src/third_party/bonjourr/ext)
# The release zip is pinned by sha256. Changes to upstream (all checked, the script fails if one misses):
#   - default background: plain colour instead of photos from Bonjourr's servers
#   - weather hidden by default, and its 20-minute refresh timer only runs while weather is shown
#     (upstream polls weather.bonjourr.fr even when it is hidden)
#   - supporter banner and update announcements off
#   - quotes only downloaded while quotes are on (upstream fetches them while off)
#   - no welcome tab on install, no goodbye page on bonjourr.fr when removed
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ver=22.3.0; sha=233ced61032996b5c82438994729dda187ad2dcbc5f376e60850cc7a2fccedc8
dest="$(realpath -m "${1:?usage: fetch_bonjourr.sh <dest-dir>}")"
case "$dest" in "$root"/*) ;; *) echo "dest must be inside $root" >&2; exit 1;; esac
dl="$root/build/deps/bonjourr-$ver"; zip="$dl/bonjourr-chrome-$ver.zip"
mkdir -p "$dl"
[ -f "$zip" ] || gh release download "$ver" -R victrme/Bonjourr -p "bonjourr-chrome-$ver.zip" -D "$dl"
echo "$sha  $zip" | sha256sum -c --quiet
[ -f "$dl/LICENSE" ] || gh api "repos/victrme/Bonjourr/contents/LICENSE.md?ref=$ver" --jq .content | base64 -d > "$dl/LICENSE"
grep -q "GNU GENERAL PUBLIC LICENSE" "$dl/LICENSE"

# Keep our build files when dest is the Chromium third_party/bonjourr folder.
mkdir -p "$dest"
find "$dest" -mindepth 1 -maxdepth 1 ! -name BUILD.gn ! -name generate_file_list.py ! -name README.chromium -exec rm -rf {} +
unzip -q "$zip" -d "$dest"
cp "$dl/LICENSE" "$dest/LICENSE"
# Chrome only reads _locales/xx_YY; the identical xx-YY copies (for other browsers) give duplicate grit IDs.
for d in "$dest"/_locales/*-*; do
  cmp -s "$d/messages.json" "${d//-/_}/messages.json" || { echo "locale ${d##*/} differs from its _ twin" >&2; exit 1; }
  rm -rf "$d"
done
python3 -I - "$dest/src/scripts/main.js" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
reps = [
    ('    backgrounds: {\n      type: "images",', '    backgrounds: {\n      type: "color",'),
    ('    hide: {},\n    linkstyle:', '    hide: { weatherdesc: true, weathericon: true },\n    linkstyle:'),
    ('    announcements: "major",', '    announcements: "off",'),
    ('    supporters: {\n      enabled: true', '    supporters: {\n      enabled: false'),
    ('''    queueMicrotask(() => {
      clearInterval(pollingInterval);
      pollingInterval = setInterval(async () => {''',
     '''    queueMicrotask(() => {
      clearInterval(pollingInterval);
      // Helium++: no background weather requests while weather is hidden.
      if (!canShowWeather) return;
      pollingInterval = setInterval(async () => {'''),
    ('''      if (noCache) {
        list = await tryFetchQuotes(lang, quotes2.type, quotes2.url);''',
     '''      // Helium++: upstream downloads quotes even while quotes are off.
      if (noCache && quotes2.on) {
        list = await tryFetchQuotes(lang, quotes2.type, quotes2.url);'''),
    # ...and again when a new quote is due (controlCacheList refetches an empty cache).
    ('''    if (needsNewQuote) {
      quotes2.last = userDate().getTime();''',
     '''    if (needsNewQuote && quotes2.on) {
      quotes2.last = userDate().getTime();'''),
]
for a, b in reps:
    assert s.count(a) == 1, "Bonjourr changed upstream, update fetch_bonjourr.sh: " + a[:50]
    s = s.replace(a, b)
open(p, 'w').write(s)
PY
# Helium++ turns Bonjourr on from its own setup: no welcome tab, no goodbye page on bonjourr.fr.
python3 -I - "$dest/src/scripts/service-worker.js" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
for a in ("        chrome.runtime.onInstalled.addListener(handleInstalled)\n",
          "        chrome.runtime.setUninstallURL('https://bonjourr.fr/goodbye')\n"):
    assert s.count(a) == 1, "Bonjourr changed upstream, update fetch_bonjourr.sh: " + a[:50]
    s = s.replace(a, "")
open(p, 'w').write(s)
PY
# Fixed public key: a component extension without one gets an ID from its folder path, which changes
# with every AppImage mount (settings lost). The private key was never kept; nothing is signed with it.
python3 -I - "$dest/manifest.json" "$root/scripts/bonjourr_manifest_key.txt" <<'PY'
import base64, hashlib, json, sys
m = json.load(open(sys.argv[1])); key, want = open(sys.argv[2]).read().split()
got = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32].translate(str.maketrans("0123456789abcdef", "abcdefghijklmnop"))
assert got == want, (got, want)
m["key"] = key
json.dump(m, open(sys.argv[1], "w"), indent=2)
PY
echo "Bonjourr $ver -> $dest (privacy defaults applied, id $(tail -1 "$root/scripts/bonjourr_manifest_key.txt"))"
