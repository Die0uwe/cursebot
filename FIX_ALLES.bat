@echo off
:: ============================================================================
:: CurseBot -- Slayer Alliance Edition
:: FIX_ALLES.bat  v2.2 -- Reset + download + verificatie
:: Fix v2.2: ASCII-only, chcp 437
:: ============================================================================
title CurseBot - FIX ALLES v2.2
color 0C
chcp 437 >nul
cls

echo.
echo  ============================================================
echo   CurseBot -- Volledige Reset en Update  v2.2
echo  ============================================================
echo.
cd /d "%~dp0"

set DOWNLOAD_ERRORS=0
set REPO=https://raw.githubusercontent.com/Die0uwe/cursebot/main

echo  [1/6] Cache wissen...
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo  [OK]   Cache gewist

echo.
echo  [2/6] GitHub verbinding testen...
curl -sf --max-time 10 "%REPO%/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FOUT] GitHub NIET bereikbaar!
    echo         Controleer je internet en probeer later opnieuw.
    pause >nul & exit /b 1
)
echo  [OK]   GitHub bereikbaar

echo.
echo  [3/6] Bot-bestanden downloaden...

call :dl "bot\config.py"                  "bot/config.py"
call :dl "bot\main.py"                    "bot/main.py"
call :dl "bot\cogs\curseforge.py"         "bot/cogs/curseforge.py"
call :dl "bot\cogs\admin.py"              "bot/cogs/admin.py"
call :dl "bot\cogs\watchlist.py"          "bot/cogs/watchlist.py"
call :dl "bot\cogs\onboarding.py"         "bot/cogs/onboarding.py"
call :dl "bot\services\curseforge_api.py" "bot/services/curseforge_api.py"
call :dl "bot\services\stats.py"          "bot/services/stats.py"
call :dl "bot\services\cache.py"          "bot/services/cache.py"
call :dl "bot\services\claude_api.py"     "bot/services/claude_api.py"
call :dl "bot\services\key_manager.py"    "bot/services/key_manager.py"
call :dl "bot\utils\embeds.py"            "bot/utils/embeds.py"
call :dl "bot\utils\logger.py"            "bot/utils/logger.py"
call :dl "bot\utils\retry.py"             "bot/utils/retry.py"
call :dl "bot\models\release.py"          "bot/models/release.py"
call :dl "ui\app.py"                      "ui/app.py"
call :dl "dashboard.py"                   "dashboard.py"
call :dl "updater.py"                     "updater.py"
call :dl "launch.py"                      "launch.py"
call :dl "requirements.txt"               "requirements.txt"

if %DOWNLOAD_ERRORS% gtr 0 (
    echo.
    echo  [WARN] %DOWNLOAD_ERRORS% bestand(en) mislukt -- bot kan instabiel zijn.
) else (
    echo  [OK]   Alle bestanden gedownload
)

echo.
echo  [4/6] Update-state resetten...
if exist .last_commit del .last_commit >nul 2>&1
echo  [OK]   .last_commit gewist

echo.
echo  [5/6] Dependencies updaten...
if not exist ".venv\Scripts\activate.bat" (
    echo  [WARN] .venv niet gevonden -- aanmaken...
    python -m venv .venv
)
call .venv\Scripts\activate.bat 2>nul
pip install -r requirements.txt --quiet --upgrade
if %errorlevel% equ 0 (echo  [OK]   Packages up-to-date) else (echo  [WARN] Sommige packages niet geupdate)

echo.
echo  [6/6] Klaar!
echo.
echo  ============================================================
echo   FIX_ALLES KLAAR
echo   Bot start NIET automatisch -- kies hieronder
echo  ============================================================
echo.

choice /C JN /M "  Bot starten via start_cursebot.bat? [J/N]"
if %errorlevel% equ 1 start "" "%~dp0start_cursebot.bat"

echo.
pause >nul
exit /b 0

:dl
set _L=%~1
set _R=%~2
for %%F in ("%_L%") do (
    if not exist "%%~dpF" mkdir "%%~dpF" >nul 2>&1
)
curl -sf --max-time 25 -o "%_L%" "%REPO%/%_R%" 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] %_R% -- download mislukt
    set /a DOWNLOAD_ERRORS+=1
    goto :eof
)
for %%A in ("%_L%") do (
    if %%~zA equ 0 (
        del "%_L%" >nul 2>&1
        echo  [FOUT] %_R% -- leeg bestand (404?)
        set /a DOWNLOAD_ERRORS+=1
        goto :eof
    )
)
echo  [OK]   %_R%
goto :eof

:: ============================================================================
:: File: FIX_ALLES.bat  |  v2.2  |  2026-06-06
:: Fix v2.2: ASCII-only, chcp 437
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
