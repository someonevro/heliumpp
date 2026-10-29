# Helium++ on top of helium-windows: called from helium-windows' build.py (inserted by
# hook_build_py.py) right after Helium's own patches, substitutions, version and resources,
# the same point where scripts/prepare_source.sh applies our series on Linux.
import shutil
from pathlib import Path

import patches

_HPP = Path(__file__).resolve().parent.parent


def apply(source_tree, patch_bin_path):
    # Our patches were made on the Linux tree; give them the Linux context they expect.
    patches.apply_patches([_HPP / 'windows' / 'linux-context.patch'], source_tree,
                          patch_bin_path=patch_bin_path)
    for series_dir in (_HPP / 'patches', _HPP / 'windows' / 'patches'):
        patches.apply_patches(
            patches.generate_patches_from_series(series_dir, resolve=True),
            source_tree, patch_bin_path=patch_bin_path)
    shutil.copytree(_HPP / 'branding', source_tree, dirs_exist_ok=True)
    onboarding = source_tree / 'components/helium_onboarding/src'
    shutil.copy2(_HPP / 'shared/presets.json', onboarding / 'lib/presets.json')
    shutil.copy2(_HPP / 'shared/design/tokens.css',
                 source_tree / 'ui/webui/resources/css/heliumpp_tokens.css')
    previews = onboarding / 'assets/ntp-previews'
    previews.mkdir(parents=True, exist_ok=True)
    for f in (_HPP / 'shared/ntp-previews').glob('*.webp'):
        shutil.copy2(f, previews)
    # Made by scripts/fetch_bonjourr.sh in the workflow's Linux job.
    bonjourr = _HPP / 'build/bonjourr'
    if not (bonjourr / 'manifest.json').exists():
        raise FileNotFoundError(f'{bonjourr} is missing: run scripts/fetch_bonjourr.sh first')
    shutil.copytree(bonjourr, source_tree / 'third_party/bonjourr', dirs_exist_ok=True)
