@echo off
:: ============================================================================
:: CurseBot -- Slayer Alliance Edition
:: start_cursebot.bat  v2.2 -- Veilige start met crash-detectie
:: Fix v2.2: ASCII-only, chcp 437, geen UTF-8 box chars
:: ============================================================================
title CurseBot - Slayer Alliance Edition
color 0A
chcp 437 >nul
cd /d "%~dp0"

if not exist "requirements.txt" (
    echo  [FOUT] Verkeerde map -- zorg dat dit bat-bestand in de CurseBot map staat.
    pause >nul & exit /b 1
)

set CRASH_COUNT=0
set MAX_CRASHES=3

:loop
cls
echo.
echo  ============================================================
echo   CurseBot -- Slayer Alliance Edition
echo   Start: %date%  %time%
echo   Crashes: %CRASH_COUNT%/%MAX_CRASHES%
echo  ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  [FOUT] .venv niet gevonden of beschadigd!
    echo         Oplossing: Draai CURSEBOT_INSTALL_v2_5.bat
    echo.
    pause >nul & exit /b 1
)

call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] .venv activeren mislukt.
    echo         Oplossing: Draai CURSEBOT_INSTALL_v2_5.bat
    pause >nul & exit /b 1
)

echo  [..] Update check...
python updater.py
set UPDATER_EXIT=%errorlevel%

if %UPDATER_EXIT% equ 42 (
    echo  [OK]   Update toegepast -- herstarten...
    for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
    set CRASH_COUNT=0
    goto loop
)

echo  [START] CurseBot starten...
echo.
python launch.py
set LAUNCH_EXIT=%errorlevel%

echo.
echo  [INFO] launch.py gestopt (exitcode: %LAUNCH_EXIT%)

if %LAUNCH_EXIT% equ 0 (
    echo  [OK]   Bot netjes afgesloten.
    timeout /t 2 /nobreak >nul
    exit /b 0
)

set /a CRASH_COUNT+=1
echo  [WARN] Crash #%CRASH_COUNT% gedetecteerd

if %CRASH_COUNT% geq %MAX_CRASHES% (
    echo.
    echo  ============================================================
    echo   [!!] CurseBot is %MAX_CRASHES%x gecrasht -- autostart gestopt
    echo  ------------------------------------------------------------
    echo   Mogelijke oorzaken:
    echo     1. DISCORD_TOKEN ongeldig of verlopen
    echo     2. CURSEFORGE_API_KEY ongeldig
    echo     3. Kapotte .venv  --^> CURSEBOT_INSTALL_v2_5.bat
    echo     4. Missende bestanden --^> FIX_ALLES.bat
    echo     5. Zie logs\cursebot.log voor details
    echo  ============================================================
    echo.
    pause >nul & exit /b %LAUNCH_EXIT%
)

echo  [..] Herstart over 5 seconden... (druk Ctrl+C om te annuleren)
timeout /t 5
if %errorlevel% neq 0 (
    echo  [INFO] Herstart geannuleerd.
    pause >nul & exit /b 0
)
goto loop

:: ============================================================================
:: File: start_cursebot.bat  |  v2.2  |  2026-06-06
:: Fix v2.2: ASCII-only, chcp 437
:: Fix v2.1: crash-teller, exitcode 0 = stop, Ctrl+C werkt, .venv check
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
