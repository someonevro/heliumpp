# PLATFORM_SUPPORT.md
Everything below is "untested" unless stated. Table updated 2026-10-29 (session 8).

| Item | Linux | Windows | macOS | Android | iOS |
|---|---|---|---|---|---|
| Engine | Helium / Chromium 156.0.8078.73 (0.20.2.2, local; released 0.19.4.7 = Chromium 155) | same patches + helium-windows 0.20.2.1 | Chromium (planned) | Chromium (own build, later) | WebKit (WKWebView); Blink only EU/Japan prototypes |
| Build status | builds locally (Docker), 156 OK 2026-10-29 | 155 built on GitHub Actions (free runners, staged); 156 not built yet | none | none | none |
| UI | planned WebUI vertical tabs | same | same | touch UI, separate | native SwiftUI/UIKit |
| Presets | planned shared schema | same | same | same schema, platform enforcement | same schema, limited enforcement |
| Ad blocking | uBO MV2 or Lite (undecided) | same | same | native engine (no extensions) | WKContentRuleList |
| Extensions | planned | planned | planned | unsupported in stock Chromium | unsupported (Safari-ext model only) |
| DRM | user-side Widevine, L3 likely | same | same | differs; untested | FairPlay via WebKit; untested |
| Security updates | own rebase every Chromium major | same | same | same | via Apple/WebKit OS updates |
| Packaging | AppImage on GitHub releases, signed self-updater | per-user installer + portable zip, not code-signed, no auto-update (Helium updater not compiled; 0120 also turns its feed off) | dmg, signing/notarization | APK/Play | App Store rules |
| Tests | 27 scripts in scripts/ (headless, virtual display, nested KWin) | none run on Windows; installer not tried on a real PC | none | none | none |
| Limits | 15 GB RAM dev box | each CI run 3-4 chained 6 h stages (~15-20 h) | build on macOS needed | | App Store/engine entitlement |

## Linux desktop status note (2026-10-20)
Engine: Helium / Chromium 155.0.8059.84, built in Docker (`scripts/compile.sh`) and run from `build/src/out/Default/helium`. Verified by user on Arch + Hyprland (Wayland): launches, onboarding (privacy mode + tab layout), vertical-tab sidebar UI, theme accent. Verified headless: privacy-mode prefs/flags, uBO blocking, codecs. Unverified: Widevine/DRM playback, GPU/VAAPI, packaging, other desktops (GNOME/KDE/X11), tiling-WM window controls beyond close. Windows, macOS, Android, iOS: not started.


## Desktop colour sync (2026-10-20)
Linux/Omarchy: implemented, headless-verified (accent read from colors.toml). Windows: implemented (DWM accent registry + wallpaper path), not compiled or run. macOS: implemented (controlAccentColor + desktop image URL), not compiled or run. Other Linux desktops: no source yet.

## Session 8 notes (2026-10-29)
- Windows: 0.19.4.7 installer released (built by CI). Acrylic glass is Linux/macOS only. Wallpaper colour on Windows reads Windows' own copy of the shown image and follows changes (0115), compiled only for Linux so far.
- Linux: acrylic window now asks the compositor for blur (ext-background-effect-v1 on Wayland, _KDE_NET_WM_BLUR_BEHIND_REGION on X11); verified in a nested KWin 6.8, not on GNOME (no blur protocol there: plain see-through).
- Wallpaper colour: KDE live desktop/activity, slideshow, XFCE connected monitor, GNOME 47 accent, undecodable files (0115); parser tests pass.
