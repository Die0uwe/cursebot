@echo off
:: ============================================================================
:: CurseBot -- FIX_UPDATER.bat -- Noodreparatie bij kapotte updater
:: Download updater.py direct via curl, omzeilt syntax error
:: ============================================================================
setlocal enabledelayedexpansion
title CurseBot - Updater Noodreparatie
chcp 437 >nul
cls

echo.
echo  ============================================================
echo   CurseBot -- Updater Noodreparatie
echo   Download updater.py en bot-bestanden direct van GitHub
echo  ============================================================
echo.

cd /d "%~dp0"
set REPO=https://raw.githubusercontent.com/Die0uwe/cursebot/main

echo  [1/5] Internetverbinding testen...
curl -sf --max-time 10 "%REPO%/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FOUT] GitHub niet bereikbaar!
    pause >nul & exit /b 1
)
echo  [OK]   Verbinding OK

echo  [2/5] updater.py downloaden ^(vaste versie^)...
curl -sf --max-time 30 -o "updater.py" "%REPO%/updater.py" 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] Download mislukt!
    pause >nul & exit /b 1
)
echo  [OK]   updater.py vervangen

echo  [3/5] ui\app.py downloaden...
if not exist "ui" mkdir "ui" >nul 2>&1
curl -sf --max-time 30 -o "ui\app.py" "%REPO%/ui/app.py" 2>nul
echo  [OK]   ui\app.py vervangen

echo  [4/5] Kritieke bot-bestanden downloaden...
if not exist "bot\services" mkdir "bot\services" >nul 2>&1
if not exist "bot\utils"    mkdir "bot\utils"    >nul 2>&1
if not exist "bot\cogs"     mkdir "bot\cogs"     >nul 2>&1
if not exist "bot\models"   mkdir "bot\models"   >nul 2>&1
if not exist "bot\i18n"     mkdir "bot\i18n"     >nul 2>&1

for %%F in (
    "bot\__init__.py"
    "bot\main.py"
    "bot\config.py"
    "bot\services\__init__.py"
    "bot\services\stats.py"
    "bot\services\cache.py"
    "bot\services\curseforge_api.py"
    "bot\services\claude_api.py"
    "bot\services\key_manager.py"
    "bot\utils\__init__.py"
    "bot\utils\logger.py"
    "bot\utils\embeds.py"
    "bot\utils\retry.py"
    "bot\cogs\__init__.py"
    "bot\cogs\curseforge.py"
    "bot\cogs\admin.py"
    "bot\cogs\watchlist.py"
    "bot\cogs\onboarding.py"
    "bot\cogs\help.py"
    "bot\models\__init__.py"
    "bot\models\release.py"
    "bot\i18n\__init__.py"
    "bot\i18n\strings.json"
    "bot\i18n\translator.py"
    "ui\__init__.py"
    "ui\setup_wizard.py"
    "dashboard.py"
    "launch.py"
) do (
    set FSLASH=%%~F
    set FSLASH=!FSLASH:\=/!
    curl -sf --max-time 20 -o %%F "%REPO%/!FSLASH!" 2>nul
    echo  [OK]   %%F
)

echo  [5/5] .last_commit wissen voor volledige sync...
if exist ".last_commit" del ".last_commit" >nul 2>&1
echo  [OK]   .last_commit gewist

echo.
echo  ============================================================
echo   REPARATIE KLAAR
echo   Start nu: start_cursebot.bat
echo  ============================================================
echo.
pause >nul
