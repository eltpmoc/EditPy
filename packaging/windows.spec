# -*- mode: python ; coding: utf-8 -*-
import shutil
import sys
import sysconfig
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
ruff = shutil.which('ruff.exe', path=sysconfig.get_path('scripts')) or shutil.which('ruff.exe')
if not ruff:
    raise SystemExit('Ruff não encontrado no ambiente de build.')
datas = [(str(root / 'editpy' / 'assets'), 'editpy/assets'), (str(root / 'docs'), 'docs'),
         (str(root / 'README.md'), '.'), (str(root / 'build' / 'third-party-licenses'), 'third-party-licenses')]
binaries = [(ruff, '.')]
hiddenimports = []
for package in ('jedi', 'parso', 'winpty'):
    data, native, imports = collect_all(package)
    datas += data
    binaries += native
    hiddenimports += imports
for package in ('pywinpty', 'Pygments', 'pyte', 'wcwidth'):
    datas += copy_metadata(package)
analysis = Analysis([str(root / 'scripts' / 'launch.py')], pathex=[str(root)],
                    binaries=binaries, datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='EditPy',
          console=False, strip=False, upx=False, icon=str(root / 'assets' / 'EditPy.ico'),
          version=str(root / 'build' / 'windows-version.txt'))
collection = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name='EditPy')
