#!/usr/bin/env bash
# Render the Helium++ logo (designs/logo/kit/*.svg) into branding/, laid out like the Chromium tree.
# prepare_source.sh copies branding/ over the source after the patches (patch -p1 can't carry PNGs).
# Needs rsvg-convert and ImageMagick; rerun only when the logo changes, the PNGs are committed.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kit="$root/designs/logo/kit"; out="$root/branding/chrome/app/theme"
rose="#D9435F"; ink="#221C2B"
tmp="$root/build/branding-tmp"; rm -rf "$tmp" "$root/branding"; mkdir -p "$tmp"
mkdir -p "$out/chromium/linux" "$out/default_100_percent/chromium/linux" "$out/default_200_percent/chromium"

# colour <svg> <fill> <out.svg>: same artwork, one fill on the root.
colour() { sed "s|<svg |<svg fill=\"$2\" |" "$1" > "$3"; }
colour "$kit/heliumpp-symbol.svg" "$rose" "$tmp/big.svg"
colour "$kit/heliumpp-symbol-small.svg" "$rose" "$tmp/small.svg"
colour "$kit/heliumpp-symbol-small.svg" "#3C3C3C" "$tmp/mono.svg"
# Lockups for the name images: symbol in rose, wordmark (the <g>) in ink or white.
sed "s|<svg |<svg fill=\"$rose\" |; s|<g transform|<g fill=\"$ink\" transform|" "$kit/heliumpp-horizontal.svg" > "$tmp/name.svg"
sed "s|<svg |<svg fill=\"$rose\" |; s|<g transform|<g fill=\"#FFFFFF\" transform|" "$kit/heliumpp-horizontal.svg" > "$tmp/name_white.svg"

# png <svg> <size> <out>: square icon; the small cut is used at 24 px and below.
png() { rsvg-convert -w "$2" -h "$2" "$1" -o "$3"; }
icon() { if [ "$1" -le 24 ]; then png "$tmp/small.svg" "$1" "$2"; else png "$tmp/big.svg" "$1" "$2"; fi; }
for s in 16 24 48 64 128 256; do icon $s "$out/chromium/product_logo_$s.png"; done
for s in 24 48 64 128 256; do icon $s "$out/chromium/linux/product_logo_$s.png"; done
for d in default_100_percent/chromium default_100_percent/chromium/linux; do
    icon 16 "$out/$d/product_logo_16.png"; icon 32 "$out/$d/product_logo_32.png"
done
icon 32 "$out/default_200_percent/chromium/product_logo_16.png"; icon 64 "$out/default_200_percent/chromium/product_logo_32.png"
png "$tmp/mono.svg" 22 "$out/chromium/product_logo_22_mono.png"
icon 32 "$tmp/32.png"; magick "$tmp/32.png" "$out/chromium/linux/product_logo_32.xpm"
# lockup <svg> <w> <h> <out>: logo + name, padded on the right to the size Chromium's art had.
lockup() { rsvg-convert -h "$3" "$1" -o "$tmp/l.png"; magick "$tmp/l.png" -background none -gravity west -extent "$2x$3" "$4"; }
comp="$root/branding/components/resources"; mkdir -p "$comp/default_100_percent/chromium" "$comp/default_200_percent/chromium"
for n in name name_white; do
    f="product_logo_${n/name/name_22}.png"
    lockup "$tmp/$n.svg" 97 22 "$out/default_100_percent/chromium/$f"
    lockup "$tmp/$n.svg" 194 44 "$out/default_200_percent/chromium/$f"
    f="product_logo${n#name}.png"
    lockup "$tmp/$n.svg" 140 32 "$comp/default_100_percent/chromium/$f"
    lockup "$tmp/$n.svg" 280 64 "$comp/default_200_percent/chromium/$f"
done
# Tab icon of the new tab page and of helium://setup (onboarding's own favicon).
mkdir -p "$out/default_100_percent/common" "$out/default_200_percent/common" "$root/branding/components/helium_onboarding/public"
icon 16 "$out/default_100_percent/common/favicon_ntp.png"; icon 32 "$out/default_200_percent/common/favicon_ntp.png"
icon 128 "$root/branding/components/helium_onboarding/public/favicon.png"
# Vector icon (address bar, menus, notifications): every path where Helium put its logo.
for f in chrome/app/vector_icons/{browser_logo,browser_logo_old,chrome_product}.icon \
         components/omnibox/browser/vector_icons/{chrome_product,product_chrome_refresh,product_chrome_refresh_old,product_old}.icon \
         components/vector_icons/chromium/product.icon ui/message_center/vector_icons/{chrome_product,product_old}.icon; do
    mkdir -p "$root/branding/${f%/*}"; cp "$kit/heliumpp-symbol-small.icon" "$root/branding/$f"
done
cp "$tmp/big.svg" "$out/chromium/product_logo.svg"
cp "$tmp/big.svg" "$out/chromium/product_logo_animation.svg"
rm -rf "$tmp"
find "$root/branding" -type f | sort
