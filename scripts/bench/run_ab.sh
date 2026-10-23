#!/usr/bin/env bash
# A/B JS+startup benchmark, headless, software GL. Usage: run_ab.sh <label>=<binary> [<label>=<binary>...]; env N = rounds (default 5)
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; page="file://$root/scripts/bench/jsbench.html"; N="${N:-5}"
for r in $(seq "$N"); do for spec in "$@"; do
  lab="${spec%%=*}"; bin="${spec#*=}"; prof="$root/build/bench-profile-$lab"; rm -rf "$prof"
  s=$(date +%s.%N)
  out=$("$bin" --user-data-dir="$prof" --headless=new --no-sandbox --disable-gpu --no-first-run --dump-dom "$page" 2>/dev/null)
  e=$(date +%s.%N)
  echo "$lab $(awk "BEGIN{printf \"%.2f\", $e - $s}") $(grep -o 'RESULT {[^}]*}' <<<"$out")"
done; done
