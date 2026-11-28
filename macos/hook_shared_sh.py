# Makes helium-macos' devutils/shared.sh apply Helium++ (macos/apply_ours.py) at the end of
# prepare_sources. Usage: hook_shared_sh.py <helium-macos root>
import sys
from pathlib import Path

shared = Path(sys.argv[1]) / 'devutils' / 'shared.sh'
text = shared.read_text()
end = '\n  helium_resources\n}\n'
if text.count(end) != 1:
    sys.exit(f'{shared}: end of prepare_sources not found')
shared.write_text(text.replace(
    end, '\n  helium_resources\n  python3 "$_root_dir/heliumpp/macos/apply_ours.py" "$_root_dir" || return\n}\n'))
