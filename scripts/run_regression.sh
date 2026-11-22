#!/usr/bin/env bash
# Runs every scripts/test_*.py and test_*.sh against the current build, one after another, and writes
# "<exit> <script> <seconds>" lines to build/audit/regression-<label>.txt plus each test's output to
# build/audit/regression-<label>/<test>.log. A failed test is run once more; both results are kept, so a flaky
# pass is visible ("1->0"), never hidden. Exit code: number of tests that failed twice.
#   scripts/run_regression.sh [label]        ONLY='ntp web_sidebar' runs a subset (names without test_ and suffix)
# Needs a finished build (build/src/out/Default/helium). Takes ~25 min (test_update.sh alone ~8 min).
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$root"
label="${1:-$(date +%Y%m%d-%H%M)}"
out="build/audit/regression-$label.txt"; logs="build/audit/regression-$label"
mkdir -p "$logs"; : > "$out"
[ -x build/src/out/Default/helium ] || { echo "no build at build/src/out/Default/helium" >&2; exit 99; }

run() {  # script -> exit code, output to $logs/<name>.log (appended on retry)
  case "$1" in *.py) python3 -I "$1" ;; *) bash "$1" ;; esac >>"$logs/$(basename "$1").log" 2>&1
}

failed=0
for t in scripts/test_*.py scripts/test_*.sh; do
  name="$(basename "$t")"; short="${name#test_}"; short="${short%.*}"
  if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $short "* ]]; then continue; fi
  start=$SECONDS; run "$t"; rc=$?
  if [ $rc -ne 0 ]; then
    echo "--- retry ---" >>"$logs/$name.log"; run "$t"; rc2=$?
    result="$rc->$rc2"; [ $rc2 -ne 0 ] && failed=$((failed + 1))
  else
    result=0
  fi
  line="$result $t $((SECONDS - start))s"; echo "$line" | tee -a "$out"
done
echo "failed twice: $failed  (summary $out, logs $logs/)" | tee -a "$out"
exit $failed
