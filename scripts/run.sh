#!/usr/bin/env bash
# Launch the built browser with a profile kept inside build/. Usage: scripts/run.sh <profile-name> [extra args]
# A name that does not exist yet starts a brand-new profile (first-run setup shows).
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <profile-name> [args...]" >&2; exit 1; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
name="$1"; shift
export XDG_CONFIG_HOME="$b/xdg/config" XDG_CACHE_HOME="$b/xdg/cache"
exec "$b/src/out/Default/helium" --user-data-dir="$b/profile-$name" "$@"
