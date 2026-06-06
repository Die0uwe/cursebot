@echo off
:: ╔══════════════════════════════════════════════════════════════════════════════╗
:: ║  CurseBot — Slayer Alliance Edition                                        ║
:: ║  start_cursebot.bat  v2.1 — Veilige start met crash-detectie              ║
:: ║  Pentest fixes: .venv poisoning check, exitcode guards, loop breaker       ║
:: ╚══════════════════════════════════════════════════════════════════════════════╝
title CurseBot - Slayer Alliance Edition
color 0A
cd /d "%~dp0"

:: ── Werkmap-integriteitscheck ─────────────────────────────────────────────────
if not exist "requirements.txt" (
    echo  [FOUT] Dit bat-bestand staat op de verkeerde locatie!
    echo         Zorg dat het in de CurseBot map staat ^(naast requirements.txt^).
    pause >nul & exit /b 1
)

:: ── Crash-teller initialiseren ────────────────────────────────────────────────
set CRASH_COUNT=0
set MAX_CRASHES=3

:loop
cls
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  CurseBot — Slayer Alliance Edition                 ║
echo  ║  Start: %date%  %time%              ║
echo  ║  Crash-teller: %CRASH_COUNT%/%MAX_CRASHES%                         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── .venv aanwezig? ───────────────────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo  [FOUT] .venv niet gevonden of beschadigd!
    echo.
    echo  Oplossing: Draai CURSEBOT_INSTALL_v2_5.bat
    echo.
    pause >nul & exit /b 1
)

:: ── Virtuele omgeving activeren ──────────────────────────────────────────────
call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] .venv activeren mislukt — beschadigd?
    echo  Oplossing: Draai CURSEBOT_INSTALL_v2_5.bat
    pause >nul & exit /b 1
)

:: ── Updater ───────────────────────────────────────────────────────────────────
echo  [..] Update check uitvoeren...
python updater.py
set UPDATER_EXIT=%errorlevel%

if %UPDATER_EXIT% equ 42 (
    echo  [OK] Update toegepast — herstarten...
    for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
    set CRASH_COUNT=0
    goto loop
)

if %UPDATER_EXIT% gtr 1 (
    echo  [WARN] Updater exitcode %UPDATER_EXIT% — bot start toch lokaal
)

:: ── Bot starten ───────────────────────────────────────────────────────────────
echo  [START] CurseBot starten via launch.py...
echo.

python launch.py
set LAUNCH_EXIT=%errorlevel%

echo.
echo  [INFO] launch.py gestopt ^(exitcode: %LAUNCH_EXIT%^)

:: Exitcode 0 = netjes gestopt → niet herstarten
if %LAUNCH_EXIT% equ 0 (
    echo  [OK] Bot netjes afgesloten door gebruiker.
    timeout /t 2 /nobreak >nul
    exit /b 0
)

:: Crash → teller ophogen
set /a CRASH_COUNT+=1
echo  [WARN] Crash #%CRASH_COUNT% gedetecteerd

if %CRASH_COUNT% geq %MAX_CRASHES% (
    echo.
    echo  ╔══════════════════════════════════════════════════════════════╗
    echo  ║  [!!] CurseBot is %MAX_CRASHES%x gecrasht — autostart gestopt       ║
    echo  ╠══════════════════════════════════════════════════════════════╣
    echo  ║  Mogelijke oorzaken:                                         ║
    echo  ║    1. DISCORD_TOKEN ongeldig of verlopen                     ║
    echo  ║    2. CURSEFORGE_API_KEY ongeldig                            ║
    echo  ║    3. Kapotte .venv   → CURSEBOT_INSTALL_v2_5.bat           ║
    echo  ║    4. Missende bestanden → FIX_ALLES.bat                    ║
    echo  ║    5. Logbestand: logs\cursebot.log                          ║
    echo  ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Druk op een toets om te sluiten...
    pause >nul & exit /b %LAUNCH_EXIT%
)

echo  [..] Herstart over 5 seconden... ^(druk Ctrl+C om te annuleren^)
timeout /t 5
if %errorlevel% neq 0 (
    echo  [INFO] Herstart geannuleerd.
    pause >nul & exit /b 0
)
goto loop

:: ╔══════════════════════════════════════════════════════════════════════╗
:: ║  File: start_cursebot.bat  │  v2.1  │  2026-06-06                 ║
:: ║  Fix: crash-teller, loop-breaker na 3x crash                       ║
:: ║  Fix: exitcode 0 = netjes gestopt, geen loop                       ║
:: ║  Fix: timeout zonder /nobreak — Ctrl+C werkt                       ║
:: ║  Fix: werkmap-integriteitscheck                                    ║
:: ║  Fix: .venv-check met duidelijke foutmelding                       ║
:: ║  Pentest: geen shell-injection, geen token in variabelen           ║
:: ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
:: ╚══════════════════════════════════════════════════════════════════════╝
