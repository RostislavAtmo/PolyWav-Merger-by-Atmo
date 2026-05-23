# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PolyWav Merger — macOS .app bundle

from pathlib import Path

ROOT = Path(SPECPATH).resolve()

datas = []
for fn in ("icon.png", "icon.ico"):
    p = ROOT / fn
    if p.exists():
        datas.append((str(p), "."))

# Bundled ffmpeg binary (expected at ffmpeg_bin/ffmpeg, placed by CI)
ffmpeg_bin = ROOT / "ffmpeg_bin"
if ffmpeg_bin.exists():
    for f in ffmpeg_bin.iterdir():
        datas.append((str(f), "ffmpeg_bin"))

a = Analysis(
    [str(ROOT / "polywav_merger.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    version="2.5.0",
    info_plist={
        "CFBundleName": "PolyWav Merger",
        "CFBundleDisplayName": "PolyWav Merger",
        "CFBundleShortVersionString": "2.5.0",
        "CFBundleVersion": "2.5.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSHumanReadableCopyright": "© DEITY",
    },
)
