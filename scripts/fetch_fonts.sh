#!/usr/bin/env bash
# Downloads the official Satoshi files from Fontshare into build/fonts/satoshi (UI font, ITF Free Font License).
# The license forbids redistributing the files through a repository, so they are never committed; the build
# ships them unmodified inside the app (embedding is allowed). Checksums pin the exact official files.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; d="$root/build/fonts/satoshi"
sums="02ad131926aa46d282b6af73ad2bcaecb0ec6ef3b830a2f08dcabef44f1140ff  Satoshi-Variable.ttf
cfe8f600aa33dc80075b319a16ae663df30c7901b6cb332e70ea7dfb9c08b6ad  Satoshi-VariableItalic.ttf
145e7fe2429a3336ba215c070ef722000e01348a3e1baaa127e871bb5012f554  FFL.txt"
mkdir -p "$d"
if ! (cd "$d" && sha256sum -c --quiet <<<"$sums" >/dev/null 2>&1); then
  dl="$root/build/fonts/dl"; rm -rf "$dl"; mkdir -p "$dl"
  curl -fsSL -o "$dl/satoshi.zip" "https://api.fontshare.com/v2/fonts/download/satoshi"
  unzip -q -j -o "$dl/satoshi.zip" "Satoshi_Complete/Fonts/TTF/Satoshi-Variable.ttf" \
    "Satoshi_Complete/Fonts/TTF/Satoshi-VariableItalic.ttf" "Satoshi_Complete/License/FFL.txt" -d "$d"
  (cd "$d" && sha256sum -c --quiet <<<"$sums") || { echo "Satoshi files changed upstream; check the license and update the sums" >&2; exit 1; }
fi
