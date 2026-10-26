# PLATFORM_SUPPORT.md
Everything below is "untested" unless stated. Updated 2026-10-19 (research only).

| Item | Linux | Windows | macOS | Android | iOS |
|---|---|---|---|---|---|
| Engine (planned) | Chromium (ungoogled) | Chromium | Chromium | Chromium (own build, later) | WebKit (WKWebView); Blink only EU/Japan prototypes |
| Build status | none | none | none | none | none |
| UI | planned WebUI vertical tabs | same | same | touch UI, separate | native SwiftUI/UIKit |
| Presets | planned shared schema | same | same | same schema, platform enforcement | same schema, limited enforcement |
| Ad blocking | uBO MV2 or Lite (undecided) | same | same | native engine (no extensions) | WKContentRuleList |
| Extensions | planned | planned | planned | unsupported in stock Chromium | unsupported (Safari-ext model only) |
| DRM | user-side Widevine, L3 likely | same | same | differs; untested | FairPlay via WebKit; untested |
| Security updates | own rebase every Chromium major | same | same | same | via Apple/WebKit OS updates |
| Packaging | tar/AppImage/deb (Helium model) | installer | dmg, signing/notarization | APK/Play | App Store rules |
| Tests | none | none | none | none | none |
| Limits | 15 GB RAM dev box | GitHub Actions workflow written, never run | build on macOS needed | | App Store/engine entitlement |

## Linux desktop status note (2026-10-20)
Engine: Helium / Chromium 155.0.8059.84, built in Docker (`scripts/compile.sh`) and run from `build/src/out/Default/helium`. Verified by user on Arch + Hyprland (Wayland): launches, onboarding (privacy mode + tab layout), vertical-tab sidebar UI, theme accent. Verified headless: privacy-mode prefs/flags, uBO blocking, codecs. Unverified: Widevine/DRM playback, GPU/VAAPI, packaging, other desktops (GNOME/KDE/X11), tiling-WM window controls beyond close. Windows, macOS, Android, iOS: not started.


## Desktop colour sync (2026-10-20)
Linux/Omarchy: implemented, headless-verified (accent read from colors.toml). Windows: implemented (DWM accent registry + wallpaper path), not compiled or run. macOS: implemented (controlAccentColor + desktop image URL), not compiled or run. Other Linux desktops: no source yet.
