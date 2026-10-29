#!/usr/bin/env bash
# Turns hand edits in build/src into a new patches/ entry.
#   scripts/make_patch.sh start <NNNN-name> <src-relative file>...   snapshot the files before editing
#   (edit the files in build/src)
#   scripts/make_patch.sh finish <NNNN-name>   write patches/<NNNN-name>.patch, apply it to build/pristine,
#                                              add it to patches/series and both .ours.applied lists
# New files: list them at start too (they are recorded as new). Run finish before compiling is fine.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
cmd="${1:-}"; name="${2:-}"
[[ "$name" =~ ^[0-9]{4}-[a-z0-9.-]+$ ]] || { echo "usage: $0 start|finish <NNNN-name> [files...]" >&2; exit 1; }
snap="$b/patch-snap/$name"; pf="$root/patches/$name.patch"
case "$cmd" in
start)
  shift 2; [ $# -gt 0 ] || { echo "list the files you will edit" >&2; exit 1; }
  [ ! -e "$snap" ] || { echo "$snap exists: finish it or delete it" >&2; exit 1; }
  [ ! -e "$pf" ] || { echo "$pf exists" >&2; exit 1; }
  for f in "$@"; do
    mkdir -p "$snap/$(dirname "$f")"
    if [ -e "$b/src/$f" ]; then cp -p "$b/src/$f" "$snap/$f"; else touch "$snap/$f.isnew"; fi
  done
  echo "snapshot of $# file(s) in $snap; edit build/src, then: $0 finish $name" ;;
finish)
  [ -d "$snap" ] || { echo "no snapshot for $name (run start first)" >&2; exit 1; }
  out=$(mktemp -p "$b"); trap 'rm -f "$out"' EXIT
  while IFS= read -r s; do
    f="${s#"$snap/"}"
    if [[ "$f" == *.isnew ]]; then
      f="${f%.isnew}"; diff -u --label /dev/null --label "b/$f" /dev/null "$b/src/$f" >> "$out" || true
    else
      diff -u --label "a/$f" --label "b/$f" "$s" "$b/src/$f" >> "$out" || true
    fi
  done < <(find "$snap" -type f | sort)
  [ -s "$out" ] || { echo "no changes found" >&2; exit 1; }
  patch -d "$b/pristine/src" -p1 --forward --dry-run -s < "$out" >/dev/null || { echo "does not apply to build/pristine" >&2; exit 1; }
  patch -d "$b/pristine/src" -p1 --forward -s < "$out"
  mv "$out" "$pf"; trap - EXIT
  for t in "$b/pristine/src" "$b/src"; do echo "$name.patch" >> "$t/.ours.applied"; done
  echo "$name.patch" >> "$root/patches/series"
  rm -r "$snap"
  echo "wrote patches/$name.patch ($(wc -l < "$pf") lines), applied to build/pristine, added to series" ;;
*) echo "usage: $0 start|finish <NNNN-name> [files...]" >&2; exit 1 ;;
esac
