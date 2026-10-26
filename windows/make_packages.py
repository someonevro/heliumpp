# Unsigned Helium++ Windows packages: portable zip + Chromium's mini_installer.
# Helium's NSIS installer is skipped on purpose: it hard-codes imput\Helium install paths.
# Usage: python make_packages.py <helium-windows dir> <output dir>
import shutil
import sys
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
package.filescfg.create_archive(package.portable_files(outputs), tuple(), outputs,
                                dest / f'heliumpp_{version}_{cpu}-windows.zip', None)
print(*sorted(p.name for p in dest.iterdir()), sep='\n')
