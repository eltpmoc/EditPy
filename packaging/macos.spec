# -*- mode: python ; coding: utf-8 -*-
"""macOS bundle metadata is defined before signing, never patched afterward."""
import platform
import shutil
import sys
import tomllib
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
ruff = shutil.which('ruff', path=str(Path(sys.executable).parent))
if not ruff:
    raise SystemExit('Ruff não encontrado no ambiente de build.')

datas = [(str(root / 'editpy' / 'assets'), 'editpy/assets'), (str(root / 'docs'), 'docs')]
binaries = [(ruff, '.')]
hiddenimports = []
for package in ('jedi', 'parso'):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports

analysis = Analysis(
    [str(root / 'scripts' / 'launch.py')], pathex=[str(root)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True, name='EditPy',
    debug=False, strip=False, upx=False, console=False,
    target_arch=platform.machine(),
)
collection = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name='EditPy')
app = BUNDLE(
    collection, name='EditPy.app', icon=str(root / 'assets' / 'EditPy.icns'),
    bundle_identifier='dev.editpy.ide', version=version,
    info_plist={
        'CFBundleVersion': version,
        'CFBundleSupportedPlatforms': ['MacOSX'],
        'LSMinimumSystemVersion': '14.0',
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
)
