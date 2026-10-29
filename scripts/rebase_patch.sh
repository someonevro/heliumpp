#!/usr/bin/env bash
# Refreshes one patch of patches/series for a new Chromium tree (used for the 155 -> 156 upgrade).
#   scripts/rebase_patch.sh <tree> <patch> start    snapshot the files it touches, apply with rejects
#   (fix the .rej hunks by hand in <tree>/src, delete the .rej files)
#   scripts/rebase_patch.sh <tree> <patch> finish   rewrite patches/<patch> from the snapshot, mark applied
# <tree> is a prepare_source.sh tree (e.g. build/pristine156); then rerun prepare_source.sh to go on.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(realpath "$1")/src"; p="$2"; pf="$root/patches/$p"; snap="$(realpath "$1")/rebase-snap/$p"
files() { sed -n 's|^+++ b/\([^\t]*\).*|\1|p' "$pf" | awk '!seen[$0]++'; }
case "$3" in
start)
  [ ! -e "$snap" ] || { echo "$snap exists: finish or delete it first" >&2; exit 1; }
  for f in $(files); do
    mkdir -p "$snap/$(dirname "$f")"
    if [ -e "$src/$f" ]; then cp -p "$src/$f" "$snap/$f"; else touch "$snap/$f.isnew"; fi
  done
  patch -d "$src" -p1 --forward --no-backup-if-mismatch < "$pf" || echo ">> fix the .rej files above"
  ;;
finish)
  ! find "$src" -name '*.rej' -newer "$snap" | grep . || { echo "rejects left" >&2; exit 1; }
  out=$(mktemp -p "$root/build")
  for f in $(files); do
    if [ -e "$snap/$f.isnew" ]; then
      diff -u --label /dev/null --label "b/$f" /dev/null "$src/$f" >> "$out" || true
    else
      diff -u --label "a/$f" --label "b/$f" "$snap/$f" "$src/$f" >> "$out" || true
    fi
  done
  mv "$out" "$pf"; echo "$p" >> "$src/.ours.applied"; rm -r "$snap"; echo "rewrote patches/$p"
  ;;
*) echo "usage: $0 <tree> <patch> start|finish" >&2; exit 1;;
esac
