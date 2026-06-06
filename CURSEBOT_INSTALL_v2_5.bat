@echo off
:: ============================================================================
:: CurseBot -- Slayer Alliance Edition
:: CURSEBOT_INSTALL_v2.5.bat -- Universele Installer
:: Fixes: ASCII-only (geen UTF-8 box chars), status_line zonder printf syntax
:: ============================================================================
title CurseBot -- Installatie v2.5
color 0A
chcp 437 >nul
cls

echo.
echo  ============================================================
echo   CurseBot -- Slayer Alliance Edition
echo   Universele Installer v2.5
echo  ------------------------------------------------------------
echo   Modes: Nieuwe install / Update / Reparatie
echo  ============================================================
echo.

cd /d "%~dp0"

if not exist "requirements.txt" (
    echo  [FOUT] requirements.txt ontbreekt in deze map.
    echo         Zorg dat de installer in de CurseBot map staat.
    echo.
    pause >nul & exit /b 1
)

set TOTAL_ERRORS=0

:: ============================================================
:: STAP 0 -- Modus detecteren
:: ============================================================
set MODE=nieuw
if exist ".venv\Scripts\python.exe" (
    if exist ".env" (set MODE=update) else (set MODE=reparatie)
)
echo  [INFO] Modus: %MODE%
echo.

:: ============================================================
:: STAP 1 -- Python
:: ============================================================
echo  -- [1/9] Python controleren --
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Python niet gevonden -- downloaden...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile '%TEMP%\python_setup.exe' -UseBasicParsing } catch { exit 1 }}"
    if %errorlevel% neq 0 (
        echo  [FOUT] Python download mislukt.
        echo         Installeer handmatig: https://www.python.org/downloads/
        echo         Vink 'Add Python to PATH' aan!
        set /a TOTAL_ERRORS+=1
        goto stap2
    )
    "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    timeout /t 12 /nobreak >nul
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set PATH=%%i;%PATH%
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [FOUT] Python installatie mislukt. Open nieuwe CMD en probeer opnieuw.
        set /a TOTAL_ERRORS+=1
        goto stap2
    )
    echo  [OK]   Python geinstalleerd
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK]   %%v
)

:stap2
echo.
echo  -- [2/9] pip upgraden --
python -m pip install --upgrade pip --quiet 2>nul
if %errorlevel% equ 0 (echo  [OK]   pip up-to-date) else (echo  [WARN] pip upgrade overgeslagen)

echo.
echo  -- [3/9] Virtuele omgeving --
if not exist ".venv\Scripts\python.exe" (
    echo  [INFO] .venv aanmaken -- even geduld...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  [FOUT] .venv aanmaken mislukt.
        echo         Probeer als Administrator te draaien.
        echo.
        pause >nul & exit /b 1
    )
    echo  [OK]   .venv aangemaakt
) else (
    echo  [OK]   .venv aanwezig -- hergebruikt
)

call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] .venv activeren mislukt -- beschadigd?
    echo         Verwijder de .venv map en start opnieuw.
    pause >nul & exit /b 1
)
echo  [OK]   Virtuele omgeving actief

echo.
echo  -- [4/9] Basis packages --
pip install -r requirements.txt --quiet --upgrade
if %errorlevel% neq 0 (
    echo  [WARN] requirements.txt deels mislukt -- individueel proberen...
    pip install "discord.py>=2.4.0" --quiet
    pip install "httpx>=0.27.0" --quiet
    pip install "pydantic>=2.7.0" --quiet
    pip install "customtkinter>=5.2.0" --quiet
    pip install "flask>=3.0.0" --quiet
    pip install "pystray>=0.19.0" --quiet
) else (
    echo  [OK]   Basis packages geinstalleerd
)

echo.
echo  -- [5/9] Extra packages --
pip install "flask-cors>=4.0.0" --quiet
if %errorlevel% equ 0 (echo  [OK]   flask-cors) else (echo  [WARN] flask-cors overgeslagen)

pip install "Pillow>=10.0.0" --quiet
if %errorlevel% equ 0 (echo  [OK]   Pillow) else (echo  [WARN] Pillow overgeslagen)

pip install "keyring>=24.0.0" --quiet
if %errorlevel% equ 0 (echo  [OK]   keyring) else (echo  [WARN] keyring overgeslagen)

pip install "python-dotenv>=1.0.0" --quiet
if %errorlevel% equ 0 (echo  [OK]   python-dotenv) else (echo  [WARN] python-dotenv overgeslagen)

echo.
echo  -- [6/9] Ontbrekende bestanden ophalen van GitHub --
call :fetch_missing_files

echo.
echo  -- [7/9] Configuratie (.env) --
if not exist ".env" (
    if exist "env.example" (
        copy "env.example" ".env" >nul
        echo  [OK]   .env aangemaakt vanuit env.example
    ) else (
        echo  [WARN] env.example niet gevonden
    )
    echo.
    echo  ============================================================
    echo   TOKENS INVULLEN -- browservenster wordt geopend
    echo  ============================================================
    echo.
    if exist "cursebot_setup.html" start "" "%~dp0cursebot_setup.html"
    echo  Vul je tokens in en klik Opslaan.
    echo  Druk hier op een toets als je klaar bent...
    pause >nul
) else (
    echo  [OK]   .env aanwezig
    findstr /C:"DISCORD_TOKEN=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [FOUT] DISCORD_TOKEN nog niet ingevuld in .env!
        set /a TOTAL_ERRORS+=1
    ) else (
        echo  [OK]   DISCORD_TOKEN ingevuld
    )
    findstr /C:"CURSEFORGE_API_KEY=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [FOUT] CURSEFORGE_API_KEY nog niet ingevuld in .env!
        set /a TOTAL_ERRORS+=1
    ) else (
        echo  [OK]   CURSEFORGE_API_KEY ingevuld
    )
)

echo.
echo  -- [8/9] Cache opschonen --
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
if exist ".last_commit" del ".last_commit" >nul 2>&1
echo  [OK]   Cache gewist

echo.
echo  -- [9/9] Verificatie imports --
python -c "import discord; print('  [OK]   discord.py', discord.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] discord.py & set /a TOTAL_ERRORS+=1)

python -c "import customtkinter; print('  [OK]   customtkinter', customtkinter.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] customtkinter & set /a TOTAL_ERRORS+=1)

python -c "import httpx; print('  [OK]   httpx', httpx.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] httpx & set /a TOTAL_ERRORS+=1)

python -c "import flask; print('  [OK]   flask', flask.__version__)" 2>nul
if %errorlevel% neq 0 (echo  [FOUT] flask & set /a TOTAL_ERRORS+=1)

:: ============================================================
:: SAMENVATTING
:: ============================================================
echo.
echo  ============================================================
echo   INSTALLATIE SAMENVATTING
echo  ============================================================

if %TOTAL_ERRORS% equ 0 (
    color 0A
    echo.
    echo  [OK] CURSEBOT IS KLAAR!
    echo.
    echo   Start bot:    start_cursebot.bat
    echo   Diagnose:     HEALTH_CHECK.bat
    echo   Reparatie:    FIX_ALLES.bat
    echo   Dashboard:    http://localhost:5000
) else (
    color 0E
    echo.
    echo  [WARN] Installatie klaar met %TOTAL_ERRORS% fout(en).
    echo         Zie meldingen hierboven.
    echo         Draai HEALTH_CHECK.bat voor diagnose.
)

echo.
set HANDLEIDING=
if exist "%~dp0CurseBot_Handleiding_v2_4.html" set HANDLEIDING=%~dp0CurseBot_Handleiding_v2_4.html
if not "%HANDLEIDING%"=="" (
    start "" "%HANDLEIDING%"
    echo  [OK]   Handleiding geopend
)

echo.
choice /C JN /M "  Eerst HEALTH_CHECK uitvoeren? [J/N]"
if %errorlevel% equ 1 call "%~dp0HEALTH_CHECK.bat"

echo.
choice /C JN /M "  Bot nu starten? [J/N]"
if %errorlevel% equ 1 start "" "%~dp0start_cursebot.bat"

echo.
echo  Druk op een toets om te sluiten...
pause >nul
exit /b %TOTAL_ERRORS%

:: ============================================================
:: SUBROUTINES
:: ============================================================

:fetch_missing_files
set FETCH_ERRORS=0
set REPO_RAW=https://raw.githubusercontent.com/Die0uwe/cursebot/main

curl -sf --max-time 8 "%REPO_RAW%/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [WARN] GitHub niet bereikbaar -- bestandsdownload overgeslagen
    goto :eof
)

call :fetch_if_missing "bot\__init__.py"
call :fetch_if_missing "bot\main.py"
call :fetch_if_missing "bot\config.py"
call :fetch_if_missing "bot\cogs\__init__.py"
call :fetch_if_missing "bot\cogs\curseforge.py"
call :fetch_if_missing "bot\cogs\admin.py"
call :fetch_if_missing "bot\cogs\watchlist.py"
call :fetch_if_missing "bot\cogs\onboarding.py"
call :fetch_if_missing "bot\models\__init__.py"
call :fetch_if_missing "bot\models\release.py"
call :fetch_if_missing "bot\services\__init__.py"
call :fetch_if_missing "bot\services\cache.py"
call :fetch_if_missing "bot\services\claude_api.py"
call :fetch_if_missing "bot\services\curseforge_api.py"
call :fetch_if_missing "bot\services\stats.py"
call :fetch_if_missing "bot\services\key_manager.py"
call :fetch_if_missing "bot\utils\__init__.py"
call :fetch_if_missing "bot\utils\embeds.py"
call :fetch_if_missing "bot\utils\logger.py"
call :fetch_if_missing "bot\utils\retry.py"
call :fetch_if_missing "ui\__init__.py"
call :fetch_if_missing "ui\app.py"
call :fetch_if_missing "ui\setup_wizard.py"
call :fetch_if_missing "dashboard.py"
call :fetch_if_missing "launch.py"
call :fetch_if_missing "updater.py"

if %FETCH_ERRORS% equ 0 (
    echo  [OK]   Alle bestanden aanwezig
) else (
    echo  [WARN] %FETCH_ERRORS% bestand(en) niet opgehaald
)
goto :eof

:fetch_if_missing
set _LOCAL=%~1
set _REMOTE=%REPO_RAW%/%~1
set _REMOTE=%_REMOTE:\=/%

set _NEEDS_FETCH=0
if not exist "%_LOCAL%" set _NEEDS_FETCH=1
if exist "%_LOCAL%" (
    for %%A in ("%_LOCAL%") do if %%~zA equ 0 set _NEEDS_FETCH=1
)
if %_NEEDS_FETCH% equ 0 goto :eof

for %%F in ("%_LOCAL%") do (
    if not exist "%%~dpF" mkdir "%%~dpF" >nul 2>&1
)

curl -sf --max-time 20 -o "%_LOCAL%" "%_REMOTE%" 2>nul
if %errorlevel% neq 0 (
    echo  [FOUT] Ophalen mislukt: %_LOCAL%
    set /a FETCH_ERRORS+=1
    goto :eof
)
for %%A in ("%_LOCAL%") do (
    if %%~zA equ 0 (
        del "%_LOCAL%" >nul 2>&1
        echo  [FOUT] Leeg bestand: %_LOCAL%
        set /a FETCH_ERRORS+=1
        goto :eof
    )
)
echo  [OK]   Opgehaald: %_LOCAL%
goto :eof

:: ============================================================================
:: File: CURSEBOT_INSTALL_v2.5.bat  |  v2.5.1  |  2026-06-06
:: Fix v2.5.1: ASCII-only output (geen UTF-8 box-chars) -- CMD-compatibel
:: Fix v2.5.1: status_line subroutine verwijderd (printf werkt niet in CMD)
:: Fix v2.5.1: chcp 437 aan begin voor correcte codepage
:: Fix v2.5.1: alle echo inline ipv via subroutine
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
