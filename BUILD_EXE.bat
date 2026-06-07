@echo off
:: ============================================================================
:: CurseBot -- BUILD_EXE.bat v2.0 -- EXE bouwen met status overzicht
:: Inclusief alle nieuwe modules: i18n, pystray, help cog, gaming_tools
:: ============================================================================
title CurseBot - EXE Builder v2.0
color 0A
chcp 437 >nul
cls

echo.
echo  ============================================================
echo   CurseBot -- EXE Builder v2.0
echo   Bouwt een standalone Windows .exe via PyInstaller
echo  ============================================================
echo.

cd /d "%~dp0"

:: ── Vereisten controleren ─────────────────────────────────────────────────────
echo  [1/6] Vereisten controleren...

if not exist ".venv\Scripts\activate.bat" (
    echo  [FOUT] .venv niet gevonden!
    echo         Draai eerst: CURSEBOT_INSTALL_v2_5.bat
    pause >nul & exit /b 1
)
echo  [OK]   .venv aanwezig

if not exist "launch.py" (
    echo  [FOUT] launch.py niet gevonden!
    echo         Zorg dat je in de CurseBot map staat.
    pause >nul & exit /b 1
)
echo  [OK]   launch.py aanwezig

if not exist "cursebot.spec" (
    echo  [FOUT] cursebot.spec niet gevonden!
    pause >nul & exit /b 1
)
echo  [OK]   cursebot.spec aanwezig

:: Assets waarschuwen als ze ontbreken
if not exist "ui\assets\icon.ico" (
    echo  [WARN] ui\assets\icon.ico ontbreekt -- EXE krijgt geen icoon
    echo         Draai FIX_ASSETS.bat om assets te kopieren
)
if not exist "ui\assets\LOGOSMALL.png" (
    echo  [WARN] ui\assets\LOGOSMALL.png ontbreekt -- logo werkt niet in EXE
)

echo.
echo  -- [2/6] Virtuele omgeving activeren --
call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] .venv activeren mislukt
    pause >nul & exit /b 1
)
echo  [OK]   Actief

echo.
echo  -- [3/6] PyInstaller installeren/updaten --
pip install pyinstaller --quiet --upgrade --no-cache-dir
if %errorlevel% neq 0 (
    echo  [FOUT] PyInstaller installatie mislukt
    pause >nul & exit /b 1
)
for /f "tokens=*" %%v in ('pyinstaller --version 2^>^&1') do echo  [OK]   PyInstaller %%v

echo.
echo  -- [4/6] Oude build opschonen --
if exist "dist\CurseBot" (
    rd /s /q "dist\CurseBot" >nul 2>&1
    echo  [OK]   dist\CurseBot gewist
)
if exist "build\CurseBot" (
    rd /s /q "build\CurseBot" >nul 2>&1
    echo  [OK]   build\CurseBot gewist
)

echo.
echo  -- [5/6] EXE bouwen -- ^(dit duurt 2-5 minuten^)
echo.
pyinstaller cursebot.spec --clean --noconfirm
set BUILD_EXIT=%errorlevel%

echo.
if %BUILD_EXIT% neq 0 (
    color 0C
    echo  -- [6/6] BUILD MISLUKT ^(exitcode %BUILD_EXIT%^) --
    echo.
    echo  Mogelijke oorzaken:
    echo    - Ontbrekende module: check console output hierboven
    echo    - icon.ico ontbreekt: draai FIX_ASSETS.bat
    echo    - .venv kapot: draai CURSEBOT_INSTALL_v2_5.bat
    echo.
    pause >nul & exit /b %BUILD_EXIT%
)

echo  -- [6/6] Build geslaagd! --
echo.
echo  ============================================================
echo   OUTPUT: dist\CurseBot\CurseBot.exe
echo  ============================================================
echo.
echo  VOLGENDE STAPPEN:
echo    1. Kopieer je .env naar dist\CurseBot\
echo    2. Kopieer ui\assets\ naar dist\CurseBot\ui\assets\
echo    3. Optioneel: kopieer images\ naar dist\CurseBot\images\
echo    4. Dubbelklik dist\CurseBot\CurseBot.exe
echo.

:: Controleer of .env gekopieerd moet worden
if not exist "dist\CurseBot\.env" (
    echo  [WARN] .env ontbreekt in dist\CurseBot\ -- bot kan niet starten!
    choice /C JN /M "  .env nu kopieren naar dist\CurseBot\? [J/N]"
    if %errorlevel% equ 1 (
        copy ".env" "dist\CurseBot\.env" >nul 2>&1
        echo  [OK]   .env gekopieerd
    )
)

:: Assets kopieren naar dist
if exist "ui\assets" (
    xcopy /E /I /Q /Y "ui\assets" "dist\CurseBot\ui\assets\" >nul 2>&1
    echo  [OK]   ui\assets gekopieerd naar dist
)
if exist "images" (
    xcopy /E /I /Q /Y "images" "dist\CurseBot\images\" >nul 2>&1
    echo  [OK]   images\ gekopieerd naar dist
)

echo.
echo  Druk op een toets om te sluiten...
pause >nul

:: ============================================================================
:: File: BUILD_EXE.bat  |  v2.0  |  2026-06-07
:: Fix: status per stap, exitcode check, assets auto-kopieren naar dist
:: Fix: .env waarschuwing en kopieer-optie
:: Fix: chcp 437 (ASCII CMD compatibel)
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
