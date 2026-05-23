@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title PolyWav Merger - Quick .exe Build

echo.
echo  PolyWav Merger - merged design + working logic
echo.

if not exist "%~dp0polywav_merger.py" (
    echo [ERROR] polywav_merger.py not found next to this script.
    pause & exit /b 1
)

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or is not in PATH.
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v

echo.
echo [2/4] Installing dependencies...
pip install --quiet --upgrade pip PySide6 pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause & exit /b 1
)

echo.
echo [3/4] Checking assets...
if not exist "%~dp0icon.png" echo [WARN] icon.png not found, UI will use fallback logo.
if exist "%~dp0icon.png" (
    echo Generating high-resolution Windows icon...
    python -c "from PIL import Image; sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]; Image.open(r'%~dp0icon.png').convert('RGBA').save(r'%~dp0icon.ico', format='ICO', sizes=sizes)"
)
if not exist "%~dp0icon.ico" echo [WARN] icon.ico not found, executable icon will be default.

echo.
echo [4/4] Building .exe...
if exist "%~dp0dist_merged\" rmdir /s /q "%~dp0dist_merged\" >nul 2>&1
if exist "%~dp0build_tmp_merged\" rmdir /s /q "%~dp0build_tmp_merged\" >nul 2>&1

set ICON_ARG=
if exist "%~dp0icon.ico" set ICON_ARG=--icon "%~dp0icon.ico"

set DATA_ARGS=
if exist "%~dp0ffmpeg.exe" set DATA_ARGS=!DATA_ARGS! --add-data "%~dp0ffmpeg.exe;."
if exist "%~dp0icon.png" set DATA_ARGS=!DATA_ARGS! --add-data "%~dp0icon.png;."
if exist "%~dp0icon.ico" set DATA_ARGS=!DATA_ARGS! --add-data "%~dp0icon.ico;."

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "polywav_merger" ^
    !ICON_ARG! ^
    !DATA_ARGS! ^
    --distpath "%~dp0dist_merged" ^
    --workpath "%~dp0build_tmp_merged" ^
    --specpath "%~dp0build_tmp_merged" ^
    --clean ^
    "%~dp0polywav_merger.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See PyInstaller output above.
    pause & exit /b 1
)

if not exist "%~dp0dist_merged\polywav_merger.exe" (
    echo [ERROR] polywav_merger.exe was not created.
    pause & exit /b 1
)

rmdir /s /q "%~dp0build_tmp_merged\" >nul 2>&1

echo.
echo [OK] Done: %~dp0dist_merged\polywav_merger.exe
explorer "%~dp0dist_merged"
pause
