#!/usr/bin/env bash
# Compile and run the wallpaper parser tests on the host (no Chromium build needed).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; out="$root/build/test-wallpaper-parsers"
g++ -std=c++20 -Wall -Wextra -I"$root/build/src" -o "$out" "$root/scripts/test_wallpaper_parsers.cc" \
    "$root/build/src/chrome/browser/helium_theme/wallpaper_config_parsers.cc"
"$out"
