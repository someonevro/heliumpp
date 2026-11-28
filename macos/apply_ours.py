# Helium++ on top of helium-macos: run by its devutils/shared.sh prepare_sources (inserted by
# macos/hook_shared_sh.py) right after Helium's patches, substitutions, version and resources,
# the same point as on Linux and Windows. Usage: apply_ours.py <helium-macos root>
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'helium-chromium' / 'utils'))  # Helium's patches.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'windows'))
import apply_ours  # noqa: E402  (windows/apply_ours.py, shared by both platforms)

apply_ours.apply(root / 'build' / 'src', None, 'macos')
