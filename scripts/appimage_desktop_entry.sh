# Spliced into AppRun by package_appimage.sh, just before the browser starts.
# AppImages have no installer, so add our own menu entry (refreshed every launch, so a moved
# AppImage keeps working) and, the first time only, a desktop icon. Only heliumpp names are used.
# shortcut: a "%" in the AppImage path gets no entry: GLib checks Exec unexpanded (so "%%"
# hides it) and expands "%" at launch; upgrade to a launcher script if anyone hits this.
case "$APPIMAGE" in *%*) echo "Helium++: no menu entry, the AppImage path contains %" >&2 ;; esac
if [ -n "$APPIMAGE" ] && [ -n "$HOME" ] && case "$APPIMAGE" in *%*) false ;; esac; then
    data="${XDG_DATA_HOME:-$HOME/.local/share}"
    entry="$data/applications/heliumpp.desktop"
    # Desktop Exec quoting: escape \ " ` $ inside double quotes, double every backslash (the
    # key-file layer unescapes once first), then escape for the sed replacement.
    exec_path=$(printf '%s' "$APPIMAGE" | sed 's/[\\"`$]/\\&/g; s/\\/\\\\/g; s/[\\&|]/\\&/g')
    new=$(sed "s|^Exec=helium|Exec=\"$exec_path\"|" "$HERE/heliumpp.desktop")
    icon="$data/icons/hicolor/256x256/apps/heliumpp.png"
    first=0; [ -f "$entry" ] || first=1
    # An update keeps the path, so the entry text may match while the icon changed.
    if [ "$first" = 1 ] || [ "$new" != "$(cat "$entry")" ] || ! cmp -s "$HERE/heliumpp.png" "$icon"; then
        mkdir -p "$data/applications" "${icon%/*}" \
            && cp "$HERE/heliumpp.png" "$icon" \
            && printf '%s\n' "$new" > "$entry" \
            && { has_command update-desktop-database && update-desktop-database -q "$data/applications" || true; }
    fi
    if [ "$first" = 1 ] && [ -f "$entry" ]; then
        desk=$(xdg-user-dir DESKTOP 2>/dev/null) || desk="$HOME/Desktop"
        if [ -d "$desk" ] && [ "$desk" != "$HOME" ] && ! [ -e "$desk/heliumpp.desktop" ]; then
            cp "$entry" "$desk/heliumpp.desktop" && chmod +x "$desk/heliumpp.desktop"
            # GNOME's desktop icons only launch entries marked trusted.
            has_command gio && gio set "$desk/heliumpp.desktop" metadata::trusted true 2>/dev/null
        fi
    fi
fi
