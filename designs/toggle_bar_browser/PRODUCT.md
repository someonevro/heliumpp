# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

(Recorded as `web` because the schema has no desktop-native value. The shipped window chrome is native Chromium Views code (C++ patches); the new tab page, onboarding and settings are WebUI. Design mocks are HTML; see Capabilities and Constraints.)

## Users
Primary user today: the project owner, using the browser all day on Linux (Arch, Hyprland, Omarchy). Keyboard-heavy, many tabs, wants workspaces and folders, cares about privacy and ad blocking. A public release later is intended, so the design must not depend on one person's wallpaper, setup or technical skill.

## Product Purpose
A privacy-first desktop browser built on a Helium / ungoogled-chromium base, with built-in uBlock Origin, three privacy modes (usability, medium [recommended], maximum) chosen at first run, a vertical-tab sidebar, tab groups (folders) and workspaces. Success: a real browser that is pleasant to look at and use for hours, without giving up privacy or compatibility.

## Positioning
Zen-inspired in feel (vertical tabs, workspaces, calm floating page card) but Chromium-based, with real privacy presets and a window whose colours follow the user's desktop wallpaper. It is not a Zen or Helium reskin: the look is meant to stop reading as "just Helium".

## Operating Context
Window chrome is native Chromium Views (C++). Each chrome change needs a patch in `patches/` and an incremental rebuild of 3 to 7 minutes (`scripts/compile.sh`), so designs are reviewed as static HTML mocks before being built. Colours must come from theme tokens derived from the desktop wallpaper (Omarchy: `~/.local/state/omarchy/current/background`), with a fallback accent when the wallpaper has none. Default sidebar width is about 190 px. Current chrome: sidebar with address bar (back/forward/reload inside the pill) at the top, tab list with pinned tabs and tab groups, workspace dots, a footer row of 6 icons (new folder, settings, extensions, downloads, history, bookmarks), floating rounded page card, dark theme.

## Capabilities and Constraints
- Native chrome can paint rounded shapes, theme-token colours, simple animations and vector icons. Blur / translucency behind the sidebar is unverified on this compositor.
- Workspaces switch by closing and reopening tabs (state is lost); dots in a row, Ctrl+Alt+Left/Right to cycle.
- Folders are Chromium tab groups.
- Platform is Linux first; Windows, macOS, Android and iOS come later and must not be blocked by Linux-only design.
- Browser name and logo are undecided and deliberately deferred.

## Brand Commitments
- No copying of Zen or Helium branding, logos or assets.
- All chrome colours derive from the wallpaper-driven theme; no hard-coded surface colours except the fallback.
- Keep security UI trustworthy: the lock/page-info icon and URL must stay legible.

## Evidence on Hand
No user research, no brand assets. Working browser binary at `build/src/out/Default/helium`; `shared/presets.json` for privacy modes; screenshots must not be taken of the whole desktop (privacy).

## Product Principles
- Looks and daily comfort come first now; privacy features are already in place and must keep working.
- The page is the hero: chrome recedes and carries the wallpaper's colour quietly.
- Every control is real; no decorative buttons.
- One design language across sidebar, tabs, address bar, popups and internal pages.
- Prefer keyboard and low-clutter patterns over more visible buttons.

## Accessibility & Inclusion
Text and icons must stay readable on any wallpaper-derived palette, light or dark. Pointer targets in the sidebar at least 24 px. Keyboard access for workspace switching.
