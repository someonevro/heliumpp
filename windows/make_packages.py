# Unsigned Helium++ Windows packages: portable zip + Chromium's mini_installer.
# Helium's NSIS installer is skipped on purpose: it hard-codes imput\Helium install paths.
# Usage: python make_packages.py <helium-windows dir> <output dir>
import shutil
import sys
import zipfile
from pathlib import Path

root = Path(sys.argv[1]).resolve()
dest = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root))
import package  # helium-windows/package.py

outputs = package._BUILD_SRC / 'out/Default'
v = dict(l.split('=', 1) for l in (package._BUILD_SRC / 'chrome/VERSION').read_text().split())
version = '.'.join(v['HELIUM_' + k] for k in ('MAJOR', 'MINOR', 'PATCH', 'PLATFORM'))
cpu = package.get_target_cpu(outputs)
dest.mkdir(parents=True, exist_ok=True)
shutil.copy2(outputs / 'mini_installer.exe', dest / f'heliumpp_{version}_{cpu}-installer.exe')
portable = dest / f'heliumpp_{version}_{cpu}-windows.zip'
package.filescfg.create_archive(package.portable_files(outputs), tuple(), outputs, portable, None)
# The UI font (patch 0125) is not in FILES.cfg: add <top dir>/fonts/* next to chrome.exe.
fonts = sorted((outputs / 'fonts').glob('*'))
if not fonts:
    sys.exit(f'{outputs / "fonts"} is empty: apply_ours.py did not copy the UI font')
with zipfile.ZipFile(portable, 'a', zipfile.ZIP_DEFLATED) as z:
    top = next(n.split('/')[0] for n in z.namelist() if n.endswith('chrome.exe'))
    for f in fonts:
        z.write(f, f'{top}/fonts/{f.name}')
print(*sorted(p.name for p in dest.iterdir()), sep='\n')
