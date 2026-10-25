#!/usr/bin/env bash
# Package build/src/out/Default into build/release/heliumpp-<version>-x86_64.AppImage.
# Everything stays under build/. Needs docker (squashfs-tools image) and network once (appimagetool).
# Layout and AppRun are reused from research/helium-linux/package. No zsync update info yet
# (upstream's points at Helium's GitHub; ours needs a host first).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/build/src/out/Default"; rel="$root/build/release"; tools="$root/build/tools"
pkg="$root/research/helium-linux/package"
ver="$("$out/helium" --version | grep -oE '[0-9]+(\.[0-9]+){3}' | head -1)"
app="$rel/Helium++.AppDir"; name="heliumpp-$ver-x86_64.AppImage"

mkdir -p "$tools" "$rel"
tool="$tools/appimagetool"
if [ ! -x "$tool" ]; then
    curl -fL -o "$tool" https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-x86_64.AppImage
    echo "46fdd785094c7f6e545b61afcfb0f3d98d8eab243f644b4b17698c01d06083d1  $tool" | sha256sum -c - || { rm -f "$tool"; exit 1; }
    chmod +x "$tool"
fi
docker image inspect helium-packager >/dev/null 2>&1 || docker build -t helium-packager -f "$root/scripts/docker/packager.Dockerfile" "$root/scripts/docker"

rm -rf "$app"; mkdir -p "$app/opt/helium/locales" "$app/usr/share/icons/hicolor/256x256/apps"
for f in helium chrome_100_percent.pak chrome_200_percent.pak helium_crashpad_handler chromedriver icudtl.dat \
         libEGL.so libGLESv2.so libqt5_shim.so libqt6_shim.so libvk_swiftshader.so libvulkan.so.1 \
         product_logo_256.png resources.pak v8_context_snapshot.bin vk_swiftshader_icd.json; do
    cp "$out/$f" "$app/opt/helium/"
done
cp "$out"/locales/*.pak "$app/opt/helium/locales/"
mkdir -p "$app/opt/helium/fonts"; cp "$out"/fonts/* "$app/opt/helium/fonts/"
find "$app/opt/helium" -type f -exec file {} + | awk -F: '/ELF/ {print $1}' | xargs strip --strip-unneeded
# Own desktop id/icon (heliumpp, matches GetDesktopName in 0066) so desktops never mix us up with real Helium.
sed 's/^Name=Helium$/Name=Helium++/; s/^Icon=helium$/Icon=heliumpp/; /^\[Desktop Entry\]$/a StartupWMClass=heliumpp' \
    "$pkg/helium.desktop" > "$app/heliumpp.desktop"
[ "$(grep -c '^StartupWMClass=heliumpp$' "$app/heliumpp.desktop")" = 1 ] && ! grep -q '^Icon=helium$' "$app/heliumpp.desktop" \
    || { echo "desktop entry rename failed" >&2; exit 1; }
# Own AppArmor profile name: the upstream one (helium-appimage) is shared with real Helium's AppImage.
sed 's|/etc/apparmor.d/helium-appimage|/etc/apparmor.d/heliumpp-appimage|; s|profile helium-appimage |profile heliumpp-appimage |; s|<local/helium-appimage>|<local/heliumpp-appimage>|' \
    "$pkg/helium-wrapper-appimage.sh" > "$app/AppRun"; chmod +x "$app/AppRun"
grep -q "heliumpp-appimage" "$app/AppRun" && ! grep -q "helium-appimage" "$app/AppRun" || { echo "AppArmor rename failed" >&2; exit 1; }
# Upstream's AppArmor re-exec drops the arguments: a link opened on the first launch was lost.
sed -i 's|^\( *APPARMOR_BOOTSTRAPPED=1 exec "\$APPIMAGE"\)$|\1 "$@"|' "$app/AppRun"
grep -q 'APPARMOR_BOOTSTRAPPED=1 exec "$APPIMAGE" "$@"$' "$app/AppRun" || { echo "AppArmor re-exec fix failed" >&2; exit 1; }
# Menu entry and desktop icon: splice ours in before the last line, which starts the browser.
launch='"${HERE}"/opt/helium/helium "$@"'
[ "$(tail -n 1 "$app/AppRun")" = "$launch" ] || { echo "AppRun last line changed" >&2; exit 1; }
{ head -n -1 "$app/AppRun"; cat "$root/scripts/appimage_desktop_entry.sh"; echo; echo "$launch"; } > "$app/AppRun.new"
mv "$app/AppRun.new" "$app/AppRun"; chmod +x "$app/AppRun"
cp "$out/product_logo_256.png" "$app/heliumpp.png"
cp "$out/product_logo_256.png" "$app/usr/share/icons/hicolor/256x256/apps/heliumpp.png"

rm -f "$rel/$name"
docker run --rm -u "$(id -u):$(id -g)" -e APPIMAGE_EXTRACT_AND_RUN=1 -e ARCH=x86_64 \
    -e APPIMAGETOOL_APP_NAME="Helium++" -e VERSION="$ver" -v "$root/build:$root/build" -w "$rel" \
    helium-packager "$tool" "$app" "$rel/$name"
ls -l "$rel/$name"
