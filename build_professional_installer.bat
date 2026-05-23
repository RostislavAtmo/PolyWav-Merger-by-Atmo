@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title PolyWav Merger - Professional Installer

set ROOT=%~dp0
set NSIS=
if exist "C:\Program Files (x86)\NSIS\makensis.exe" set NSIS=C:\Program Files (x86)\NSIS\makensis.exe
if exist "C:\Program Files\NSIS\makensis.exe" set NSIS=C:\Program Files\NSIS\makensis.exe

echo.
echo PolyWav Merger - professional Windows installer
echo.

if not exist "%ROOT%polywav_merger.py" (
    echo [ERROR] polywav_merger.py not found.
    pause & exit /b 1
)
if not exist "%ROOT%icon.png" (
    echo [ERROR] icon.png not found.
    pause & exit /b 1
)
if "%NSIS%"=="" (
    echo [ERROR] NSIS not found. Install NSIS from https://nsis.sourceforge.io/
    pause & exit /b 1
)

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or is not in PATH.
    pause & exit /b 1
)

echo [2/4] Installing build dependencies...
pip install --quiet --upgrade pip PySide6 pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install Python build dependencies.
    pause & exit /b 1
)

echo Generating high-resolution Windows icon...
python -c "from PIL import Image; sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]; Image.open(r'%ROOT%icon.png').convert('RGBA').save(r'%ROOT%icon.ico', format='ICO', sizes=sizes)"
if errorlevel 1 (
    echo [ERROR] Failed to generate icon.ico from icon.png.
    pause & exit /b 1
)

echo [3/4] Building portable executable...
if exist "%ROOT%dist_merged\" rmdir /s /q "%ROOT%dist_merged\" >nul 2>&1
if exist "%ROOT%build_tmp_merged\" rmdir /s /q "%ROOT%build_tmp_merged\" >nul 2>&1

set DATA_ARGS=
if exist "%ROOT%ffmpeg.exe" set DATA_ARGS=!DATA_ARGS! --add-data "%ROOT%ffmpeg.exe;."
set DATA_ARGS=!DATA_ARGS! --add-data "%ROOT%icon.png;."
set DATA_ARGS=!DATA_ARGS! --add-data "%ROOT%icon.ico;."

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "polywav_merger" ^
    --icon "%ROOT%icon.ico" ^
    !DATA_ARGS! ^
    --distpath "%ROOT%dist_merged" ^
    --workpath "%ROOT%build_tmp_merged" ^
    --specpath "%ROOT%build_tmp_merged" ^
    --clean ^
    "%ROOT%polywav_merger.py"

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause & exit /b 1
)
if not exist "%ROOT%dist_merged\polywav_merger.exe" (
    echo [ERROR] polywav_merger.exe was not created.
    pause & exit /b 1
)

echo [4/4] Building installer with NSIS...
pushd "%ROOT%"
"%NSIS%" "polywav_merger_installer.nsi"
set NSIS_RESULT=%ERRORLEVEL%
popd

if not "%NSIS_RESULT%"=="0" (
    echo [ERROR] NSIS build failed.
    pause & exit /b 1
)
if not exist "%ROOT%dist_merged\PolyWav_Merger_Setup.exe" (
    echo [ERROR] Setup file was not created.
    pause & exit /b 1
)

rmdir /s /q "%ROOT%build_tmp_merged\" >nul 2>&1

echo.
echo [OK] Installer ready:
echo %ROOT%dist_merged\PolyWav_Merger_Setup.exe
echo.
explorer "%ROOT%dist_merged"
pause
