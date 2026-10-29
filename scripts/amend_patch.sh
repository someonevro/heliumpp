#!/usr/bin/env bash
# Re-records an existing patch after more hand edits in build/src to the files it already touches.
#   scripts/amend_patch.sh <NNNN-name> [new files...]
# Only for the LAST patch in patches/series (it is reverse-applied to build/pristine and rewritten from build/src).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
name="$1"; shift; pf="$root/patches/$name.patch"
[ "$(tail -n1 "$root/patches/series")" = "$name.patch" ] || { echo "$name is not the last patch in series" >&2; exit 1; }
mapfile -t files < <(grep '^+++ b/' "$pf" | sed 's|^+++ b/||; s|\t.*||')
files+=("$@")
# A file named twice would be diffed twice and the patch would no longer apply.
mapfile -t files < <(printf '%s\n' "${files[@]}" | awk '!seen[$0]++')
patch -d "$b/pristine/src" -p1 -R -s < "$pf"
out=$(mktemp -p "$b"); trap 'rm -f "$out"' EXIT
for f in "${files[@]}"; do
  if [ -e "$b/pristine/src/$f" ]; then
    diff -u --label "a/$f" --label "b/$f" "$b/pristine/src/$f" "$b/src/$f" >> "$out" || true
  else
    diff -u --label /dev/null --label "b/$f" /dev/null "$b/src/$f" >> "$out" || true
  fi
done
[ -s "$out" ] || { echo "no changes found; pristine left without $name" >&2; exit 1; }
patch -d "$b/pristine/src" -p1 -s < "$out"
mv "$out" "$pf"; trap - EXIT
for f in "${files[@]}"; do cmp -s "$b/pristine/src/$f" "$b/src/$f" || echo "differs after amend: $f" >&2; done
echo "amended patches/$name.patch ($(wc -l < "$pf") lines, ${#files[@]} files)"
