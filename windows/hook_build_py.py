# Inserts the Helium++ step (apply_ours.py) into helium-windows' build.py.
# Usage: python hook_build_py.py <helium-windows>/build.py   (helium-windows 0.20.2.1, 40061d5)
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding='utf-8')
anchor = '        _configure_remoteexec(source_tree)\n'
hook = ("        # Helium++: our patches and files, after Helium's (see heliumpp/windows/apply_ours.py)\n"
        "        sys.path.insert(0, str(_ROOT_DIR / 'heliumpp' / 'windows'))\n"
        "        import apply_ours\n"
        "        apply_ours.apply(source_tree, source_tree / _PATCH_BIN_RELPATH)\n")
if hook in text:
    sys.exit(0)
if text.count(anchor) != 1:
    sys.exit(f'{path}: anchor found {text.count(anchor)} times, expected 1 (helium-windows changed?)')
path.write_text(text.replace(anchor, hook + anchor), encoding='utf-8')
