@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title PolyWAV Builder — Complete Installer Builder

echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║     PolyWAV Builder v7.0  —  Complete Build System        ║
echo  ║     Автоматическая сборка установщика для Windows         ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.

:: ── Check current directory ─────────────────────────────────────────
if not exist "%~dp0polywav_builder.py" (
    echo [ERROR] Скрипт должен быть запущен из папки с polywav_builder.py
    pause & exit /b 1
)

:: ── Check Python ────────────────────────────────────────────────────
echo [1/6] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден. Установите Python 3.11+ с https://python.org
    echo         При установке поставьте галочку "Add Python to PATH"
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% найден

:: ── Install Python dependencies ─────────────────────────────────────
echo.
echo [2/6] Установка зависимостей Python...
pip install --quiet --upgrade pip >nul 2>&1
pip install --quiet customtkinter pillow pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Не удалось установить Python пакеты
    pause & exit /b 1
)
echo [OK] customtkinter, pillow, pyinstaller установлены

:: ── Download ffmpeg ─────────────────────────────────────────────────
echo.
echo [3/6] Подготовка ffmpeg...

set FFMPEG_DIR=%~dp0ffmpeg_tmp
set FFMPEG_ZIP=%~dp0ffmpeg.zip
set FFMPEG_EXE=%~dp0ffmpeg.exe

if exist "%FFMPEG_EXE%" (
    echo [OK] ffmpeg.exe уже присутствует, пропускаем загрузку
    goto :ffmpeg_done
)

echo Загрузка ffmpeg (~80MB из GitHub)...
powershell -NoProfile -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; $url = 'https://github.com/BtbN/ffmpeg-builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'; Invoke-WebRequest -Uri $url -OutFile '%FFMPEG_ZIP%' -UseBasicParsing -ErrorAction Stop" 2>nul

if errorlevel 1 (
    echo [WARN] Не удалось загрузить ffmpeg. Продолжаем без него.
    goto :ffmpeg_done
)

echo Распаковка ffmpeg...
powershell -NoProfile -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force" 2>nul

for /r "%FFMPEG_DIR%" %%f in (ffmpeg.exe) do (
    copy "%%f" "%FFMPEG_EXE%" >nul 2>&1
    echo [OK] ffmpeg.exe извлечён
    goto :ffmpeg_found
)

echo [WARN] ffmpeg.exe не найден в архиве
goto :ffmpeg_cleanup

:ffmpeg_found
:ffmpeg_cleanup
rmdir /s /q "%FFMPEG_DIR%" >nul 2>&1
del "%FFMPEG_ZIP%" >nul 2>&1

:ffmpeg_done

:: ── Check icon and logo files ────────────────────────────────────────
echo.
echo [4/6] Проверка файлов иконки и логотипа...

if not exist "%~dp0polywav_icon.ico" (
    echo [ERROR] polywav_icon.ico не найден!
    echo         Поместите эти файлы в одну папку со скриптом:
    echo           - polywav_icon.ico
    echo           - logo_48.png
    pause & exit /b 1
)

if not exist "%~dp0logo_48.png" (
    echo [ERROR] logo_48.png не найден!
    echo         Поместите эти файлы в одну папку со скриптом:
    echo           - polywav_icon.ico
    echo           - logo_48.png
    pause & exit /b 1
)

echo [OK] Найдены polywav_icon.ico и logo_48.png

:: ── Build .exe with PyInstaller ─────────────────────────────────────
echo.
echo [5/6] Сборка .exe через PyInstaller...

:: Удаляем старые артефакты
if exist "dist\" rmdir /s /q "dist\" >nul 2>&1
if exist "build_tmp\" rmdir /s /q "build_tmp\" >nul 2>&1

set FFMPEG_ARGS=
if exist "ffmpeg.exe" set FFMPEG_ARGS=--add-data "ffmpeg.exe;."

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "polywav_builder" ^
    --icon=polywav_icon.ico ^
    --add-data "polywav_icon.ico;." ^
    --add-data "logo_48.png;." ^
    %FFMPEG_ARGS% ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    --collect-all customtkinter ^
    --collect-all PIL ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build_tmp" ^
    --specpath "%~dp0build_tmp" ^
    --clean ^
    "%~dp0polywav_builder.py" >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Сборка .exe завершилась с ошибкой
    pause & exit /b 1
)

if not exist "dist\polywav_builder.exe" (
    echo [ERROR] polywav_builder.exe не был создан
    pause & exit /b 1
)

echo [OK] polywav_builder.exe создан (dist\)

:: ── Check NSIS ──────────────────────────────────────────────────────
echo.
echo [6/6] Сборка установщика...

:: Пытаемся найти NSIS
set NSIS_PATH=
if exist "C:\Program Files (x86)\NSIS\makensis.exe" set NSIS_PATH=C:\Program Files (x86)\NSIS\makensis.exe
if exist "C:\Program Files\NSIS\makensis.exe" set NSIS_PATH=C:\Program Files\NSIS\makensis.exe

if "%NSIS_PATH%"=="" (
    echo [WARN] NSIS не установлен на компьютер
    echo         Загрузите NSIS отсюда: https://nsis.sourceforge.io/
    echo         После установки запустите этот скрипт снова
    echo.
    echo         А пока у вас есть готовый .exe файл:
    echo         %CD%\dist\polywav_builder.exe
    echo.
    echo         Вы можете распространять его пользователям (размер ~100-150 MB)
    echo         или создать установщик вручную используя NSIS
    echo.
    goto :build_done_no_nsis
)

echo Запуск NSIS компилятора...
"%NSIS_PATH%" "build_nsis_installer.nsi"

if errorlevel 1 (
    echo [ERROR] Ошибка при сборке NSIS инсталлятора
    pause & exit /b 1
)

if not exist "dist\PolyWAV_Builder_Setup.exe" (
    echo [ERROR] PolyWAV_Builder_Setup.exe не был создан
    pause & exit /b 1
)

echo [OK] PolyWAV_Builder_Setup.exe создан

:build_done_no_nsis

:: ── Cleanup ─────────────────────────────────────────────────────────
echo.
echo Очистка временных файлов...
if exist "build_tmp\" rmdir /s /q "build_tmp\" >nul 2>&1
if exist "build\" rmdir /s /q "build\" >nul 2>&1

:: ── Final message ───────────────────────────────────────────────────
echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║                     ГОТОВО!                               ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.
echo  📁 Результаты в папке: %CD%\dist\
echo.

if exist "dist\PolyWAV_Builder_Setup.exe" (
    echo  ✓ PolyWAV_Builder_Setup.exe  (Установщик с мастером)
    echo    — Распространяйте ЭТОТ файл пользователям
    echo    — Он включает мастер установки, ярлыки в меню Пуск и на рабочем столе
    echo.
)

if exist "dist\polywav_builder.exe" (
    echo  ✓ polywav_builder.exe  (Портативный .exe)
    echo    — Можно запустить без установки
    echo    — Размер: ~100-150 MB
    echo.
)

echo  Содержимое .exe:
echo    • Python runtime
echo    • customtkinter + PIL
if exist "ffmpeg.exe" echo    • ffmpeg.exe (встроен)
echo    • polywav_icon.ico + logo_48.png (встроены)
echo    • polywav_builder.py (скомпилирован)
echo.

echo  Откройте папку dist:
explorer "%~dp0dist"
pause
