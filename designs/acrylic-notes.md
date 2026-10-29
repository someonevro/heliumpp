# Acrylic glass: paused (2026-10-29)

The owner turned the acrylic glass effect off everywhere until we design it again together.
Last build WITH acrylic: `build/saved/0.20.2.2-redesign-0133/` (run line in its README.txt).

## How it is switched off (patch 0134-acrylic-off)
- `features::HeliumNativeFrameAvailable()` (chrome/browser/ui/ui_features.cc) returns false on every platform.
  That makes `helium::ShouldUseNativeFrameMaterials()` false, so the frame paints opaque, no compositor blur is
  requested, and Settings > Appearance hides the "acrylic" switch (loadTimeData showNativeFrameMaterialsOption).
- Setup page "Choose your tab layout": the "Acrylic window" switch is removed.
- Web sidebar: the grain and sheen layers (`:host::before/::after` in heliumpp_sidebar/app.css) are removed.
- To bring it back: drop the early `return false` in HeliumNativeFrameAvailable, restore the onboarding Toggle and
  the sidebar CSS from patch 0133 (they are in patches/0133-frosted-acrylic.patch and 0116/0122/0127/0131).

## What we tried and what the owner said
| Patch | Tint (light / dark) | Extra | Owner's verdict |
|---|---|---|---|
| 0116 + 0122 | 74% / 55% | compositor blur (KWin, ext-background-effect-v1) | "basically just translucent, showing what's behind it" |
| 0127 | 74% / 55-80% adaptive to wallpaper luma | contrast fix over light wallpapers | (part of the above) |
| 0131 | 88% / 84-92% | Zephium-style evened-out glass | "feels like I'm using the normal mode" (looked opaque) |
| 0133 | 80% / 70-86% | sidebar sheen + 5-7% fractal-noise grain | effect paused before feedback |

## What we learned
- The blur radius is the compositor's (KDE: Desktop Effects > Blur, a desktop-wide setting); the browser can only
  ask for blur behind a region, not choose its strength. GNOME has no blur protocol at all.
- Tint alone can only trade "see-through" against "solid". The frosted feel comes from a heavy blur plus grain,
  a light gradient and a bright rim (the mock uses 28px blur + saturate(1.4), 74% / 58% tint).
- Zephium (MPL-2.0, build/ref/zephium, frame/src/styles/axes/material.css, tokens/sky.css): native material
  supplies depth; a theme wash keeps colour neutral (28% over Windows acrylic, 20% over mica, 72-76% "evened-out"
  glass beside its new tab), lit from the side by the new tab's picture. Rows use 4-7.5% ink overlays + 1px rim.
- The web sidebar cannot blend with the native frame (mix-blend-mode only sees its own page), so grain and
  light must be plain alpha layers.
- Contrast floor stays: tab text >= 4.5:1 on the matrix wallpapers (scripts/shot_matrix.sh), measured each time.

## Ideas for next time
- Ask KWin for stronger blur only for our window (no protocol for that today; check KWin's blur effect options).
- Fake the frost ourselves: draw the decoded wallpaper (we already keep a thumbnail, helium.theme.wallpaper_thumb)
  heavily blurred behind the sidebar, aligned to the window's screen position; then the look no longer depends on
  the desktop's blur setting, and it works on GNOME too. Needs the window position and per-monitor wallpaper.
- Glass only on the sidebar and the new tab surroundings, opaque elsewhere.
