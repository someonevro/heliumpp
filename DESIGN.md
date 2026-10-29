---
name: Helium++
description: A privacy browser whose window is frosted glass cut from your own wallpaper; the page is a card lying on it.
colors:
  # Every colour is derived at runtime from the wallpaper-seeded browser theme (chrome://theme/colors.css).
  # Values are the CSS expressions in shared/design/tokens.css, the normative source. Fallback seed when the
  # wallpaper has no usable colour: neutral grayscale theme (patch 0027).
  ink: "var(--color-sys-on-surface)"
  ink-2: "color-mix(in oklab, var(--color-sys-on-surface) 86%, var(--color-sys-surface))"
  ink-3: "color-mix(in oklab, var(--color-sys-on-surface) 66%, var(--color-sys-surface))"
  accent: "var(--color-sys-primary)"
  on-accent: "var(--color-sys-on-primary)"
  card: "var(--color-sys-base)"
  raised: "var(--color-sys-base-container-elevated)"
  danger: "var(--color-sys-error)"
typography:
  display:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "88px"
    fontWeight: 300
    lineHeight: 1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 450
    lineHeight: 1.4
  label:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
  meta:
    fontFamily: "Figtree, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
    fontFeature: "tnum"
rounded:
  sm: "6px"
  tab: "8px"
  control: "10px"
  card: "12px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
components:
  tab-row:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.tab}"
    height: "32px"
    padding: "0 8px"
  tab-row-selected:
    textColor: "{colors.ink}"
    rounded: "{rounded.tab}"
    height: "32px"
  workspace-segment-active:
    textColor: "{colors.ink}"
    rounded: "{rounded.tab}"
    height: "28px"
  address-field:
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "34px"
    padding: "0 12px"
  icon-button:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.tab}"
    size: "28px"
  chip:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    height: "30px"
    padding: "0 12px"
  page-card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
---

# Design System: Helium++

Status: Stage 0 seed (2026-10-29). Written from the approved direction contract
(`.impeccable/surfaces/designs-redesign-mock-html.md`) and mock (`designs/redesign/mock.html`) before the build;
re-run `/impeccable document` at Stage 7 against the shipped UI and add the `.impeccable/design.json` sidecar then.
Normative tokens: `shared/design/tokens.css` (checked by `shared/tests/test_tokens.py`).

## Overview

**North star: the glass sheet.** The window is one sheet of frosted glass cut from the user's own wallpaper; the
page is a card lying on it. The browser's own surfaces recede and carry the wallpaper's colour quietly; the page is
the only thing with weight.

Lineage: Zen Browser for the structure (vertical tabs, named workspaces, essentials, folders, a calm floating page),
Zephium for the restraint (one accent, hairline edges, no ornament). Helium++'s own marks: colour that follows the
desktop wallpaper, workspaces as named segments, and the shield as the one place for privacy, showing its effect as
a live blocked count.

Mode: Operate. Scanability and keyboard speed outrank expression; the brand lives in the material, the type and the
precision of spacing. Anti-references: a grey toolbar strip over a tab bar; settings scattered across pages;
dashboard cards on the new tab page; any control that does nothing.

## Colors

All colour comes from the browser theme, which is seeded from the wallpaper (dominant hue if it is saturated
enough, else the desktop accent, else grayscale). No surface has a fixed colour.

- **Glass** (sidebar, window ground): not a token. The native window paints the compositor blur of the desktop
  behind it, tinted 74% (light) / 55% (dark) with the theme frame colour (patches 0116, 0122). WebUI on glass has a
  transparent background.
- **Ink** (`--hp-ink`): theme foreground. **Ink-2** and **ink-3** are ink mixed toward the surface (86% / 66%; 80% measured 4.0:1 on dark glass over a light wallpaper), so
  secondary text keeps the wallpaper's tint instead of going grey. Ink-3 is for section labels and hints only.
- **Accent** (`--hp-accent`): the theme primary. Used for exactly four things: the selected workspace segment's
  marker, focus rings, the primary action on a page, and toggled-on states. Never for decoration or large fills;
  `--hp-accent-soft` (16%) is the only tinted fill.
- **Selected / hover / pressed**: white overlays on glass (82% light, 11% dark) and ink at 7% / 11%.
- **Card** (`--hp-card`): the page plane; **raised** for menus and popovers.
- Contrast floor: ink and ink-2 >= 4.5:1, ink-3 >= 3:1 on glass with the measured tint, in light and dark, on the
  three matrix wallpapers (grey-blue, saturated, light). The lock icon and URL always meet 4.5:1.

## Typography

One family: **Figtree** (variable 300-900, SIL OFL 1.1, `shared/fonts/figtree/`). Satoshi was the mock's face; its
ITF Free Font License forbids making the file available through a repository or public server and forbids format
conversion, which a public open-source browser cannot avoid, so it is not shipped.

- 13px / 450 for UI text; 600 for labels and the active item. Sentence case everywhere, no letter-spaced capitals.
- 11px with tabular numbers only for counts, shortcut hints and meta.
- 15px / 600 for panel titles; 20px for page headings in settings and onboarding.
- Display (new tab clock): 88px / 300, tight tracking. The only large type in the product.
- Native Views (omnibox, menus, tooltips) keep the platform UI font; matching Figtree there is a later decision.

## Layout

- 4px grid. Rows 32px, controls 34px, segments and icon buttons 28px (pointer targets never below 24px).
- Window: sidebar 232px full or 48px rail, page card inset 8px from every window edge, sidebar content padding 8px.
- Sidebar order, top to bottom: window controls + sidebar toggle + back/forward/reload; workspace segments; address
  field; essentials grid (up to 4 square tiles per row); tab sections ("Pinned", "Today") with folders; "+ New tab";
  footer pinned to the bottom (shield with blocked count, downloads, extensions, settings).
- Collapsed rail (48px): favicons, workspace markers, shield; hovering the rail edge reveals the full sidebar over the
  page without reflowing it. Ctrl+B toggles.
- New tab page: wallpaper softened behind the card, clock + date centred slightly above the middle, search field
  (max 620px) below, shortcut row, chip row at the foot. Nothing else. The wallpaper is a 192px JPEG the browser
  saves at each wallpaper decode (pref `helium.theme.wallpaper_thumb`), blurred 18px; text is white with a dark
  theme-tinted wash, or dark when the wallpaper's mean luma is above 150. Chips appear only with real data.
- Wide windows add space to the page, never to the sidebar.

## Elevation & Depth

Flat glass with one lifted plane. Only the page card casts a shadow (`--hp-shadow-card`); menus and popovers use
`--hp-shadow-pop`. Everything on the glass separates by tone and a 1px hairline (`--hp-edge`), never by shadow.

## Shapes

Radii: card 12, controls 10, tabs and segments 8, small 6. Nested shapes step down (card 12 > field 10 > tab 8).
Icons: one line set, 16px (20px in the rail), 1.7 stroke, round caps and joins, currentColor.

## Components

- **Tab row**: 32px, favicon 16 + title (ink-2), close button on hover/selected only. Selected: white overlay pill,
  ink, weight 600 not used (the pill carries selection). Audio/isolated badges sit right of the title.
- **Workspace segments**: named segments in a 28px track; active one gets the selected overlay and an accent dot.
  Switching slides the tab list sideways (150ms ease-out) under the moving highlight.
- **Address field**: 34px, field fill, domain only when unfocused, full URL when focused; lock/page-info icon at
  the start keeps full contrast. It is the native omnibox (security UI and popup stay native).
- **Folder**: chevron + colour dot + name (label weight) + count (meta); children indented 12px with a hairline guide.
- **Essentials tile**: square, max 4 per row, favicon centred, selected = overlay + accent dot below.
- **Shield panel**: anchored popover from the footer shield; privacy level, performance mode, blocked counts.
  The footer shield itself shows uBlock Origin's count for the active tab ("3 blocked", from its badge), or the
  level name when uBlock Origin is not running.
- **Chip** (new tab page): 30px, field fill, icon + figure (600) + label (ink-2).
- **Focus**: 2px accent ring, 2px offset, on every interactive element; keyboard order follows visual order.

### Native mapping (Views C++)

Native surfaces take the same values through the colour pipeline and Views constants, never through hard-coded
RGB:

| Token | Native source |
|---|---|
| ink / ink-2 | `kColorSysOnSurface`, mixed in `material_chrome_color_mixer.cc` |
| accent, focus | `kColorSysPrimary`, `kColorSysStateFocusRing` |
| selected / hover | `kColorTabBackgroundActiveFrameActive`, `kColorSysStateHoverOnSubtle` (tab strip mixer) |
| raised (menus, bubbles, omnibox popup) | `kColorSysBaseContainerElevated` |
| radii | `ChromeLayoutProvider` / `views::LayoutProvider` emphasis radii; tab and footer views in `tabs/vertical/` |

## Do's and Don'ts

- Do take every colour from the theme; a fixed hue is a bug (test: `shared/tests/test_tokens.py`).
- Do keep the page the only lifted, opaque plane.
- Do show privacy as an outcome (blocked count) in one place, the shield.
- Don't put privacy or performance controls on the new tab page.
- Don't add a button that does nothing, or a greeting with a placeholder name.
- Don't use shadows on the glass, gradients as decoration, or accent fills larger than a dot or a ring.
- Don't change behaviour while restyling: privacy, isolation, profiles and security UI stay as they are.
