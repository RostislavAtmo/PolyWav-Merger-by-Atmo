@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title PolyWAV Builder — Quick .exe Build

echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║     PolyWAV Builder  —  Quick .exe Builder                ║
echo  ║     (без установщика — прямое создание .exe)              ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.

if not exist "%~dp0polywav_builder.py" (
    echo [ERROR] Скрипт должен быть в папке с polywav_builder.py
    pause & exit /b 1
)

echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не установлен или не в PATH
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v

echo.
echo [2/4] Установка зависимостей...
pip install --quiet --upgrade pip customtkinter pillow pyinstaller 2>nul
if errorlevel 1 echo [WARN] Возможна ошибка при установке пакетов

echo.
echo [3/4] Проверка иконок...
if not exist "polywav_icon.ico" (
    echo [ERROR] polywav_icon.ico не найден!
    pause & exit /b 1
)
if not exist "logo_48.png" (
    echo [ERROR] logo_48.png не найден!
    pause & exit /b 1
)
echo [OK] Найдены иконка и логотип

echo.
echo [4/4] Сборка .exe (это может занять 2-5 минут)...

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
    --collect-all customtkinter ^
    --collect-all PIL ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build_tmp" ^
    --specpath "%~dp0build_tmp" ^
    --clean ^
    "%~dp0polywav_builder.py" >nul 2>&1

if not exist "dist\polywav_builder.exe" (
    echo [ERROR] Сборка не удалась
    pause & exit /b 1
)

rmdir /s /q "build_tmp\" >nul 2>&1

echo.
echo  ✓ ГОТОВО!
echo.
echo  📁 Файл: %CD%\dist\polywav_builder.exe
echo.
echo  Откройте папку dist:
explorer "%~dp0dist"
pause
