#!/usr/bin/env bash
# Compile Helium/Chromium inside the chromium-builder image. Only ninja/siso, none of Helium's
# non-idempotent prep steps. build/ is mounted at its host path because gn bakes in absolute paths. Usage: scripts/compile.sh [-j N] [extra autoninja args]
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
jobs=8   # 15 GB RAM: ThinLTO links are memory-heavy, stay below 12 threads
if [ "${1:-}" = "-j" ]; then jobs="$2"; shift 2; fi
# Single source of truth for the onboarding page; touch the dir vite watches only when it changed.
dest="$root/build/src/components/helium_onboarding/src/lib/presets.json"
if ! cmp -s "$root/shared/presets.json" "$dest"; then
    cp "$root/shared/presets.json" "$dest"
    touch "$root/build/src/components/helium_onboarding/src"
fi
# vite never cleans its output dir; stale hashed files overflow the grd's fixed resource ID range
# (IdRangeOverflow). Wiping it forces a vite run on every compile (costs ~a minute) but is always correct.
rm -rf "$root/build/src/out/Default/gen/components/helium_onboarding/dist"
docker run --rm -i --memory 8g --memory-swap 20g -u "$(id -u):$(id -g)" \
    -e HOME="$root/build/home" -e SISO_PATH="$root/build/src/third_party/siso/cipd/siso" \
    -v "$root/build:$root/build" -w "$root/build/src" chromium-builder:trixie-slim \
    python3 third_party/depot_tools/autoninja.py -C out/Default -j "$jobs" chrome chromedriver "$@"
