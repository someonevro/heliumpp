#!/usr/bin/env bash
# Builds a fresh source tree the same way build/src was made, then applies our patch series.
# Usage: scripts/prepare_source.sh <dest-dir>   (e.g. build/pristine; needs ~35 GB, no compile)
# Steps = upstream helium-linux scripts/shared.sh (unpack, prune, Helium patches, domain + name
# substitution, translations, version, resources) with paths pointed into this workspace, then
# patches/series with `patch -p1`. Uses the pinned helium-chromium worktree and the tarballs already
# in build/ (hard-linked into the download cache, hashes checked by upstream's downloads.py).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"
dest="$(realpath -m "${1:?usage: prepare_source.sh <dest-dir>}")"
case "$dest" in "$root"/*) ;; *) echo "dest must be inside $root" >&2; exit 1;; esac
[ "$dest" != "$b/src" ] || { echo "refusing to touch build/src" >&2; exit 1; }
pinned="$root/research/helium-chromium-pinned"
[ "$(git -C "$pinned" rev-parse --short=7 HEAD)" = 832faa7 ] || { echo "helium-chromium-pinned is not at 832faa7" >&2; exit 1; }

. "$root/research/helium-linux/scripts/shared.sh"
setup_environment
_main_repo="$pinned"; _build_dir="$dest"; _src_dir="$dest/src"; _out_dir="$_src_dir/out/Default"
_dl_cache="$b/download_cache"; _namesubs_cache="$dest/namesubs.tar"; _subs_cache="$dest/subs.tar.gz"
mkdir -p "$dest"
for f in "$b"/chromium-*.tar.zst "$b"/chromium-*.tar.zst.hashes; do
  [ -e "$_dl_cache/$(basename "$f")" ] || ln "$f" "$_dl_cache/"
done

export PATH="$b/venv/bin:$PATH"   # upstream's resource step needs PIL
fetch_sources false false
apply_patches
apply_domsub
# These have no upstream stamps and must not run twice (name substitution refuses to).
step() { [ -f "$_src_dir/.$1.stamp" ] || { "$1"; touch "$_src_dir/.$1.stamp"; }; }
step helium_substitution
step helium_apply_translations
step helium_version
step helium_resources

if [ ! -f "$_src_dir/.ours.stamp" ]; then
  while read -r p; do
    [ -z "$p" ] && continue
    patch -d "$_src_dir" -p1 --forward --no-backup-if-mismatch -s < "$root/patches/$p" \
      || { echo "FAILED: $p" >&2; exit 1; }
    echo "applied $p"
  done < "$root/patches/series"
  touch "$_src_dir/.ours.stamp"
fi
# Bundled Bonjourr (0073): release files are fetched, not patched in.
"$root/scripts/fetch_bonjourr.sh" "$_src_dir/third_party/bonjourr"
echo "OK: $_src_dir ($(grep -c . "$root/patches/series") patches). args.gn is not written: copy build/src/out/Default/args.gn (chrome_pgo_phase=2)."
