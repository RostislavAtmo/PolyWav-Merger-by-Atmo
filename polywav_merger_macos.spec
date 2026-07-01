# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PolyWav Merger — macOS .app bundle

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH).resolve()

datas = []
binaries = []
hiddenimports = [
    'sounddevice', '_sounddevice', '_cffi_backend', '_soundfile',
]

for fn in ("icon.png", "icon.ico"):
    p = ROOT / fn
    if p.exists():
        datas.append((str(p), "."))

datas += collect_data_files('_sounddevice_data')

# Bundled ffmpeg binary (expected at ffmpeg_bin/ffmpeg, placed by CI)
ffmpeg_bin = ROOT / "ffmpeg_bin"
if ffmpeg_bin.exists():
    for f in ffmpeg_bin.iterdir():
        datas.append((str(f), "ffmpeg_bin"))

for _pkg in ('PySide6', 'soundfile', 'numpy', 'cffi'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    [str(ROOT / "polywav_merger.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "customtkinter", "PIL"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts,
    exclude_binaries=True,
    name="PolyWav Merger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="PolyWav Merger",
)

app = BUNDLE(
    coll,
    name="PolyWav Merger.app",
    icon=str(ROOT / "icon.icns") if (ROOT / "icon.icns").exists() else None,
    bundle_identifier="com.deity.polywav.merger",
    version="4.0.1",
    info_plist={
        "CFBundleName": "PolyWav Merger",
        "CFBundleDisplayName": "PolyWav Merger",
        "CFBundleShortVersionString": "4.0.1",
        "CFBundleVersion": "4.0.1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "© DEITY",
    },
)
