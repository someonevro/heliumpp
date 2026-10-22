#!/usr/bin/env bash
# Update-signing tool. Keys live in build/keys (private key never leaves this machine; do not copy or publish it).
#   release_sign.sh keygen                       make the key pair once; prints the public key (hex, 32 bytes)
#   release_sign.sh sign <appimage> <base-url>   write latest.json next to the AppImage
# The signature covers "heliumpp-update-v1\n<version>\n<sha256>\n<size>\n". The URL is not signed on purpose:
# the browser checks the downloaded file against the signed sha256, so a mirror cannot swap the file.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; keys="$root/build/keys"
case "${1:-}" in
keygen)
    [ ! -e "$keys/update.key" ] || { echo "key exists, refusing to overwrite: $keys/update.key" >&2; exit 1; }
    mkdir -p "$keys"; chmod 700 "$keys"
    openssl genpkey -algorithm ed25519 -out "$keys/update.key"; chmod 600 "$keys/update.key"
    openssl pkey -in "$keys/update.key" -pubout -outform DER | tail -c 32 | od -An -v -tx1 | tr -d " \n" > "$keys/update.pub.hex"
    cat "$keys/update.pub.hex"; echo ;;
sign)
    f="$2"; base="${3%/}"; [ -f "$f" ] && [ -f "$keys/update.key" ] || { echo "missing AppImage or key" >&2; exit 1; }
    ver="$(basename "$f" | grep -oE '[0-9]+(\.[0-9]+){3}')"
    sha="$(sha256sum "$f" | cut -d' ' -f1)"; size="$(stat -c %s "$f")"
    msg="$(mktemp -p "$root/build")"; trap 'rm -f "$msg"' EXIT
    printf 'heliumpp-update-v1\n%s\n%s\n%s\n' "$ver" "$sha" "$size" > "$msg"
    sig="$(openssl pkeyutl -sign -rawin -inkey "$keys/update.key" -in "$msg" | od -An -v -tx1 | tr -d " \n")"
    printf '{"version":"%s","url":"%s/%s","sha256":"%s","size":%s,"signature":"%s"}\n' \
        "$ver" "$base" "$(basename "$f")" "$sha" "$size" "$sig" > "$(dirname "$f")/latest.json"
    cat "$(dirname "$f")/latest.json" ;;
*) sed -n 2,6p "$0"; exit 1 ;;
esac
