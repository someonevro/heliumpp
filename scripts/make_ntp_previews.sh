#!/usr/bin/env bash
# Regenerates the onboarding "Choose your new tab page" previews from the real browser in a private
# virtual display: our page with three wallpaper colours, and the bundled Bonjourr (Ctrl+T with it on).
# Usage: scripts/make_ntp_previews.sh   (needs a finished build; writes .webp into the onboarding source)
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; b="$root/build"; w="$b/previews"
out="$root/shared/ntp-previews"   # compile.sh copies these into the onboarding source
mkdir -p "$w" "$out"
"$b/venv/bin/python" - "$w" <<'PY'
import sys; from PIL import Image
for name, rgb in [("crimson", (200, 40, 90)), ("blue", (40, 90, 200)), ("green", (40, 160, 90))]:
    Image.new("RGB", (400, 300), rgb).save(f"{sys.argv[1]}/wp-{name}.png")
PY
crop() { magick "$1" -crop 888x780+200+8 +repage -resize "$3" -quality 82 "$2"; }  # page area of the 1100x800 tour window
for c in crimson blue green; do
  TOUR_ARGS="--match-wallpaper=$w/wp-$c.png" python3 -I "$root/scripts/ui_tour.py" "$w/ours-$c" shot >/dev/null
  crop "$w/ours-$c/01.png" "$out/ours-$c.webp" 300x
done
# Bonjourr through the bundled component: turn the pref on in a seeded profile, then open a new tab.
TOUR_BONJOURR=1 python3 -I "$root/scripts/ui_tour.py" "$w/bonjourr" newtab >/dev/null
crop "$w/bonjourr/01-ctrl-t.png" "$out/bonjourr.webp" 600x
ls -l "$out"
