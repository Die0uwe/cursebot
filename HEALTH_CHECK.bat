@echo off
:: ============================================================================
:: CurseBot -- Slayer Alliance Edition
:: HEALTH_CHECK.bat  v1.2 -- Stress-test en pentest
:: Fix v1.2: ASCII-only, geen subroutine-printf, chcp 437
:: ============================================================================
title CurseBot - Health Check
color 0B
chcp 437 >nul
cls

echo.
echo  ============================================================
echo   CurseBot -- Health Check en Security Scan  v1.2
echo   Schrijft GEEN bestanden -- puur diagnostisch
echo  ============================================================
echo.
cd /d "%~dp0"

set ERRORS=0
set WARNINGS=0
set SECURITY_ISSUES=0

if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat 2>nul

echo  -- [1/9] Python --
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FOUT] Python NIET in PATH
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK]   %%v
)
echo.

echo  -- [2/9] Virtuele omgeving (.venv) --
if not exist ".venv\Scripts\python.exe" (
    echo  [FOUT] .venv niet gevonden
    echo         Oplossing: CURSEBOT_INSTALL_v2_5.bat
    set /a ERRORS+=1
) else (
    .venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [FOUT] .venv Python niet uitvoerbaar -- beschadigd?
        set /a ERRORS+=1
    ) else (
        for /f "tokens=*" %%v in ('.venv\Scripts\python.exe --version 2^>^&1') do echo  [OK]   venv: %%v
    )
)
echo.

echo  -- [3/9] Python packages --
python -c "import discord; print('  [OK]   discord.py', discord.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] discord.py niet geinstalleerd & set /a ERRORS+=1)

python -c "import customtkinter; print('  [OK]   customtkinter', customtkinter.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] customtkinter niet geinstalleerd & set /a ERRORS+=1)

python -c "import httpx; print('  [OK]   httpx', httpx.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] httpx niet geinstalleerd & set /a ERRORS+=1)

python -c "import pydantic; print('  [OK]   pydantic', pydantic.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] pydantic niet geinstalleerd & set /a ERRORS+=1)

python -c "import flask; print('  [OK]   flask', flask.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] flask niet geinstalleerd & set /a ERRORS+=1)

python -c "import PIL; print('  [OK]   Pillow', PIL.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [WARN] Pillow niet geinstalleerd & set /a WARNINGS+=1)

python -c "import dotenv; print('  [OK]   python-dotenv')" 2>nul
if %errorlevel% neq 0 (echo  [WARN] python-dotenv niet geinstalleerd & set /a WARNINGS+=1)

python -c "import keyring; print('  [OK]   keyring')" 2>nul
if %errorlevel% neq 0 (echo  [WARN] keyring niet geinstalleerd & set /a WARNINGS+=1)
echo.

echo  -- [4/9] Kritieke bestanden --
call :fc "launch.py"
call :fc "updater.py"
call :fc "dashboard.py"
call :fc "requirements.txt"
call :fc "bot\main.py"
call :fc "bot\config.py"
call :fc "bot\cogs\curseforge.py"
call :fc "bot\services\curseforge_api.py"
call :fc "bot\services\stats.py"
call :fc "bot\services\cache.py"
call :fc "bot\utils\logger.py"
call :fc "ui\app.py"
echo.

echo  -- [5/9] Configuratie (.env) --
if not exist ".env" (
    echo  [FOUT] .env niet gevonden
    set /a ERRORS+=1
) else (
    echo  [OK]   .env aanwezig
    findstr /C:"DISCORD_TOKEN=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (echo  [FOUT] DISCORD_TOKEN leeg & set /a ERRORS+=1) else (echo  [OK]   DISCORD_TOKEN ingevuld)
    findstr /C:"CURSEFORGE_API_KEY=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (echo  [FOUT] CURSEFORGE_API_KEY leeg & set /a ERRORS+=1) else (echo  [OK]   CURSEFORGE_API_KEY ingevuld)
)
echo.

echo  -- [6/9] Internet --
curl -sf --max-time 8 "https://raw.githubusercontent.com/Die0uwe/cursebot/main/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (echo  [WARN] GitHub niet bereikbaar & set /a WARNINGS+=1) else (echo  [OK]   GitHub bereikbaar)
curl -sf --max-time 8 "https://api.curseforge.com" >nul 2>&1
if %errorlevel% neq 0 (echo  [WARN] CurseForge niet bereikbaar & set /a WARNINGS+=1) else (echo  [OK]   CurseForge bereikbaar)
echo.

echo  -- [7/9] Python syntax --
call :sc "launch.py"
call :sc "updater.py"
call :sc "dashboard.py"
call :sc "bot\main.py"
call :sc "bot\config.py"
call :sc "bot\cogs\curseforge.py"
call :sc "bot\services\stats.py"
echo.

echo  -- [8/9] Import test --
python -c "import bot.config; print('  [OK]   bot.config')" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] bot.config importeert niet & set /a ERRORS+=1)
python -c "import bot.services.stats; print('  [OK]   bot.services.stats')" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] bot.services.stats importeert niet & set /a ERRORS+=1)
python -c "import launch; print('  [OK]   launch.py')" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] launch.py importeert niet & set /a ERRORS+=1)
echo.

echo  -- [9/9] Security scan --

if exist ".git\index" (
    git ls-files ".env" 2>nul | findstr ".env" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [SEC!] .env staat getrackt in git -- voer uit: git rm --cached .env
        set /a SECURITY_ISSUES+=1
    ) else (
        echo  [OK]   .env niet getrackt in git
    )
) else (
    echo  [INFO] Geen .git map -- git-check overgeslagen
)

findstr /I "host.*0\.0\.0\.0" dashboard.py >nul 2>&1
if %errorlevel% equ 0 (echo  [SEC!] Dashboard gebonden aan 0.0.0.0 -- extern bereikbaar! & set /a SECURITY_ISSUES+=1) else (echo  [OK]   Dashboard alleen lokaal ^(127.0.0.1^))

findstr /I "debug.*=.*True" dashboard.py >nul 2>&1
if %errorlevel% equ 0 (echo  [SEC!] Flask debug=True -- NOOIT in productie! & set /a SECURITY_ISSUES+=1) else (echo  [OK]   Flask debug=False)

echo.
echo  ============================================================
echo   HEALTH CHECK RAPPORT
echo  ============================================================
echo.
echo   Fouten:          %ERRORS%
echo   Waarschuwingen:  %WARNINGS%
echo   Security issues: %SECURITY_ISSUES%
echo.

if %ERRORS% equ 0 (
    if %SECURITY_ISSUES% equ 0 (
        color 0A
        echo  [OK] ALLES GEZOND -- CurseBot klaar voor gebruik.
    ) else (
        color 0C
        echo  [SEC] SECURITY ISSUES GEVONDEN: %SECURITY_ISSUES%
    )
) else (
    color 0C
    echo  [FOUT] %ERRORS% fout(en) gevonden.
    echo         Draai: CURSEBOT_INSTALL_v2_5.bat
)
echo.
echo  Druk op een toets om te sluiten...
pause >nul
exit /b %ERRORS%

:fc
if not exist "%~1" (echo  [FOUT] ONTBREEKT: %~1 & set /a ERRORS+=1 & goto :eof)
for %%A in ("%~1") do (
    if %%~zA equ 0 (echo  [FOUT] LEEG: %~1 & set /a ERRORS+=1) else (echo  [OK]   %~1)
)
goto :eof

:sc
if not exist "%~1" (echo  [SKIP] %~1 ontbreekt & goto :eof)
python -m py_compile "%~1" >nul 2>&1
if %errorlevel% neq 0 (echo  [FOUT] SYNTAX FOUT in %~1 & set /a ERRORS+=1) else (echo  [OK]   %~1)
goto :eof

:: ============================================================================
:: File: HEALTH_CHECK.bat  |  v1.2  |  2026-06-06
:: Fix v1.2: ASCII-only output, chcp 437, geen printf-subroutines
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
