# Design snapshot: glass-v1 (2026-10-20)

The state of the browser UI after: Wallpaper-Lit Glass direction, floating page card,
vertical tabs, back/forward/reload inside the address bar, workspaces (dots, Ctrl+Alt+Left/Right),
folders (tab groups, small-caps labels), tab selection wipe, desktop colour sync
(wallpaper two-colour fade, neutral grayscale theme for grey wallpapers).

## Contents
- `patches/`: the full patch series 0001-0027 and its `series` file. Apply in order with
  `patch -p1` against the Helium Chromium 155.0.8059.84 source tree (`build/src`).
- `PRODUCT.md`: the product record at the time of the snapshot.
- `decision-sketches/`: the HTML sketches of the five design directions that were compared.

## Restore this design
1. Make sure `build/src` has none of the later experiment patches applied (reverse them with
   `patch -R -p1`, newest first), or re-extract a pristine tree.
2. Replace `patches/` with `designs/glass-v1/patches/`.
3. Apply any patch from `series` that is not applied yet, then run `scripts/compile.sh`
   (3-5 minutes, incremental).

## Known
- The series has not been replayed on a pristine tree yet (see PROJECT_STATUS.md).
- The Windows and macOS colour-sync code in patch 0024 was never compiled.
