# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = [('icon.png', '.'), ('icon.ico', '.')]
binaries = []
hiddenimports = [
    'sounddevice', '_sounddevice', '_cffi_backend', '_soundfile',
]

# PortAudio DLLs — sounddevice is a single .py module, not a package.
datas += collect_data_files('_sounddevice_data')

# Bundled ffmpeg for merge/trim (local ffmpeg.exe, gitignored).
_ffmpeg = os.path.join(SPECPATH, 'ffmpeg.exe')
if os.path.isfile(_ffmpeg):
    datas.append((_ffmpeg, 'ffmpeg_bin'))

for _pkg in ('PySide6', 'soundfile', 'numpy', 'cffi'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h


a = Analysis(
    ['polywav_merger.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='polywav_merger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['icon.ico'],
)
