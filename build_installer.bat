cd F:\DEITY_PYTHON\V3\build

@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title polywav_builder — Windows Installer Builder

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   polywav_builder  —  Build Installer       ║
echo  ║   Автоматическая сборка .exe для Windows    ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Check Python ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден. Установите Python 3.11+ с python.org
    echo         При установке поставьте галочку "Add to PATH"
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ── Install Python deps ───────────────────────────────────────────
echo.
echo [1/4] Установка зависимостей Python...
pip install --quiet --upgrade pip
pip install --quiet customtkinter pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости
    pause & exit /b 1)
echo [OK] customtkinter, pillow, pyinstaller установлены

:: ── Download ffmpeg ───────────────────────────────────────────────
echo.
echo [2/4] Загрузка ffmpeg...

set FFMPEG_DIR=%~dp0ffmpeg_tmp
set FFMPEG_ZIP=%~dp0ffmpeg.zip
set FFMPEG_EXE=%~dp0ffmpeg.exe

if exist "%FFMPEG_EXE%" (
    echo [OK] ffmpeg.exe уже есть, пропускаем загрузку
    goto :ffmpeg_done
)

:: Use PowerShell to download ffmpeg (essentials build from github)
powershell -Command "& { $url = 'https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'; Write-Host 'Скачиваем ffmpeg (~80MB)...'; Invoke-WebRequest -Uri $url -OutFile '%FFMPEG_ZIP%' -UseBasicParsing }"
if errorlevel 1 (
    echo [ERROR] Не удалось скачать ffmpeg. Проверьте интернет-соединение.
    pause & exit /b 1
)

echo Распаковка ffmpeg...
powershell -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"

:: Find ffmpeg.exe inside the zip (it's in a subfolder)
for /r "%FFMPEG_DIR%" %%f in (ffmpeg.exe) do (
    copy "%%f" "%FFMPEG_EXE%" >nul
    echo [OK] ffmpeg.exe извлечён
    goto :ffmpeg_found
)
echo [ERROR] ffmpeg.exe не найден в архиве
pause & exit /b 1

:ffmpeg_found
:: Cleanup
rmdir /s /q "%FFMPEG_DIR%" >nul 2>&1
del "%FFMPEG_ZIP%" >nul 2>&1

:ffmpeg_done

:: ── Check icon files ────────────────────────────────────────────
echo.
echo [3/4] Проверка файлов иконки и логотипа...

if not exist "%~dp0polywav_icon.ico" (
    echo [ERROR] polywav_icon.ico не найден в %~dp0
    echo         Убедитесь что рядом со скриптом лежат:
    echo           polywav_icon.ico  ^(иконка для .exe и ярлыка^)
    echo           logo_48.png       ^(логотип в заголовке UI^)
    pause ^& exit /b 1
)
if not exist "%~dp0logo_48.png" (
    echo [WARN] logo_48.png не найден — UI будет использовать запасной логотип
)
echo [OK] Иконки найдены

:: ── PyInstaller build ─────────────────────────────────────────────
echo.
echo [4/4] Сборка .exe через PyInstaller...

set ICON_ARG=
if exist "polywav_icon.ico" set ICON_ARG=--icon=polywav_icon.ico

:: Check if polywav_builder.py exists here
if not exist "%~dp0polywav_builder.py" (
    echo [ERROR] polywav_builder.py не найден в %~dp0
    echo         Положите build_installer.bat рядом с polywav_builder.py
    pause & exit /b 1
)

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "polywav_builder" ^
    %ICON_ARG% ^
    --add-data "ffmpeg.exe;." ^
    --add-data "polywav_icon.ico;." ^
    --add-data "logo_48.png;." ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    --collect-all customtkinter ^
    --collect-all PIL ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build_tmp" ^
    --specpath "%~dp0build_tmp" ^
    --clean ^
    "%~dp0polywav_builder.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Сборка завершилась с ошибкой. Проверьте вывод выше.
    pause & exit /b 1
)

:: ── Cleanup build artifacts ───────────────────────────────────────
echo.
echo Очистка временных файлов...
rmdir /s /q "%~dp0build_tmp" >nul 2>&1

:: ── Done ─────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   ГОТОВО!                                   ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Файл: %~dp0dist\PolyWAV_Builder.exe
echo.
echo  Этот .exe содержит:
echo    • Python runtime
echo    • customtkinter + PIL
echo    • ffmpeg.exe (встроен)
echo    • polywav_icon.ico + logo_48.png (встроены)
echo    • polywav_builder.py (скомпилирован)
echo.
echo  Передайте коллеге ТОЛЬКО файл PolyWAV_Builder.exe
echo  Никаких дополнительных установок не требуется.
echo.

:: Open dist folder
explorer "%~dp0dist"
pause
