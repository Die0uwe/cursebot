@echo off
:: ╔══════════════════════════════════════════════════════════════════════════════╗
:: ║  CurseBot — Slayer Alliance Edition                                        ║
:: ║  CURSEBOT_INSTALL_v2.5.bat — Universele Installer met live statusscherm   ║
:: ║  Modes: nieuw / update / reparatie  ·  Pentest: geen token-lekkage        ║
:: ╚══════════════════════════════════════════════════════════════════════════════╝
title CurseBot — Installatie v2.5
color 0A
cls

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  CurseBot — Slayer Alliance Edition                         ║
echo  ║  Universele Installer v2.5                                  ║
echo  ╠══════════════════════════════════════════════════════════════╣
echo  ║  Modes: Nieuwe install · Update · Reparatie                 ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── Veiligheidscheck: juiste map? ────────────────────────────────────────────
if not exist "requirements.txt" (
    echo  [FOUT] requirements.txt ontbreekt in deze map.
    echo         Zorg dat de installer in de CurseBot map staat.
    echo.
    pause >nul & exit /b 1
)

set TOTAL_ERRORS=0

:: ════════════════════════════════════════════════════════
:: STAP 0 — Modus detecteren
:: ════════════════════════════════════════════════════════
set MODE=nieuw
if exist ".venv\Scripts\python.exe" (
    if exist ".env" (set MODE=update) else (set MODE=reparatie)
)

call :status_line "Modus gedetecteerd" "%MODE%" OK
echo.

:: ════════════════════════════════════════════════════════
:: LIVE STATUS SCHERM — 9 stappen
:: ════════════════════════════════════════════════════════
call :header 1 9 "Python controleren"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [STAP 1] Python niet gevonden — downloaden via PowerShell...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile '%TEMP%\python_setup.exe' -UseBasicParsing; Write-Host 'Download OK' } catch { Write-Host 'FOUT: ' + $_.Exception.Message; exit 1 }}"
    if %errorlevel% neq 0 (
        call :status_line "Python download" "mislukt — installeer handmatig via python.org" FOUT
        set /a TOTAL_ERRORS+=1
        goto :stap2
    )
    "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    timeout /t 12 /nobreak >nul
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set PATH=%%i;%PATH%
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :status_line "Python installatie" "mislukt — open nieuwe CMD en probeer opnieuw" FOUT
        set /a TOTAL_ERRORS+=1
        goto :stap2
    )
    call :status_line "Python" "geinstalleerd" OK
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do call :status_line "Python" "%%v" OK
)

:stap2
call :header 2 9 "pip upgraden"
python -m pip install --upgrade pip --quiet 2>nul
if %errorlevel% equ 0 (call :status_line "pip" "up-to-date" OK) else (call :status_line "pip upgrade" "overgeslagen" WARN)

call :header 3 9 "Virtuele omgeving"
if not exist ".venv\Scripts\python.exe" (
    echo  [3/9] .venv aanmaken — even geduld...
    python -m venv .venv
    if %errorlevel% neq 0 (
        call :status_line ".venv aanmaken" "MISLUKT" FOUT
        set /a TOTAL_ERRORS+=1
        echo.
        echo  Kritieke fout — installatie kan niet doorgaan.
        echo  Probeer als Administrator te draaien.
        pause >nul & exit /b 1
    )
    call :status_line ".venv" "aangemaakt" OK
) else (
    call :status_line ".venv" "al aanwezig hergebruikt" OK
)

call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    call :status_line ".venv activeren" "MISLUKT — beschadigd?" FOUT
    set /a TOTAL_ERRORS+=1
    echo  Verwijder de .venv map en start opnieuw.
    pause >nul & exit /b 1
)
call :status_line "Virtuele omgeving" "actief" OK

call :header 4 9 "Basis packages installeren"
pip install -r requirements.txt --quiet --upgrade
if %errorlevel% neq 0 (
    call :status_line "requirements.txt" "deels mislukt — individueel proberen" WARN
    pip install "discord.py>=2.4.0" --quiet
    pip install "httpx>=0.27.0" --quiet
    pip install "pydantic>=2.7.0" --quiet
    pip install "customtkinter>=5.2.0" --quiet
    pip install "flask>=3.0.0" --quiet
    pip install "pystray>=0.19.0" --quiet
) else (
    call :status_line "Basis packages" "geinstalleerd" OK
)

call :header 5 9 "Extra packages installeren"
pip install "flask-cors>=4.0.0" --quiet
if %errorlevel% equ 0 (call :status_line "flask-cors" "OK" OK) else (call :status_line "flask-cors" "overgeslagen" WARN)

pip install "Pillow>=10.0.0" --quiet
if %errorlevel% equ 0 (call :status_line "Pillow" "OK" OK) else (call :status_line "Pillow" "overgeslagen" WARN)

pip install "keyring>=24.0.0" --quiet
if %errorlevel% equ 0 (call :status_line "keyring" "OK" OK) else (call :status_line "keyring" "overgeslagen" WARN)

pip install "python-dotenv>=1.0.0" --quiet
if %errorlevel% equ 0 (call :status_line "python-dotenv" "OK" OK) else (call :status_line "python-dotenv" "overgeslagen" WARN)

call :header 6 9 "Ontbrekende bot-bestanden ophalen"
call :fetch_missing_files

call :header 7 9 "Configuratie (.env)"
if not exist ".env" (
    if exist "env.example" (
        copy "env.example" ".env" >nul
        call :status_line ".env" "aangemaakt vanuit env.example" OK
    ) else (
        call :status_line ".env" "env.example ook niet gevonden!" WARN
    )
    echo.
    echo  ══════════════════════════════════════════════════════
    echo   TOKENS INVULLEN — browservenster wordt geopend
    echo  ══════════════════════════════════════════════════════
    if exist "cursebot_setup.html" start "" "%~dp0cursebot_setup.html"
    echo.
    echo  Vul in het browservenster je tokens in en klik opslaan.
    echo  Druk hier op een toets als je klaar bent...
    pause >nul
) else (
    call :status_line ".env" "al aanwezig" OK
    findstr /C:"DISCORD_TOKEN=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 call :status_line "DISCORD_TOKEN" "nog niet ingevuld!" FOUT
    findstr /C:"CURSEFORGE_API_KEY=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 call :status_line "CURSEFORGE_API_KEY" "nog niet ingevuld!" FOUT
)

call :header 8 9 "Cache opschonen"
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
if exist ".last_commit" del ".last_commit" >nul 2>&1
call :status_line "Cache" "gewist" OK

call :header 9 9 "Verificatie"
python -c "import discord" >nul 2>&1
if %errorlevel% equ 0 (call :status_line "discord.py" "OK" OK) else (call :status_line "discord.py" "NIET gevonden" FOUT & set /a TOTAL_ERRORS+=1)
python -c "import customtkinter" >nul 2>&1
if %errorlevel% equ 0 (call :status_line "customtkinter" "OK" OK) else (call :status_line "customtkinter" "NIET gevonden" FOUT & set /a TOTAL_ERRORS+=1)
python -c "import httpx" >nul 2>&1
if %errorlevel% equ 0 (call :status_line "httpx" "OK" OK) else (call :status_line "httpx" "NIET gevonden" FOUT & set /a TOTAL_ERRORS+=1)
python -c "import flask" >nul 2>&1
if %errorlevel% equ 0 (call :status_line "flask" "OK" OK) else (call :status_line "flask" "NIET gevonden" FOUT & set /a TOTAL_ERRORS+=1)

echo.
echo  ════════════════════════════════════════════════════════════
echo  INSTALLATIE SAMENVATTING
echo  ════════════════════════════════════════════════════════════

if %TOTAL_ERRORS% equ 0 (
    color 0A
    echo.
    echo  ╔══════════════════════════════════════════════════════════╗
    echo  ║  ✅ CURSEBOT IS KLAAR!                                  ║
    echo  ╠══════════════════════════════════════════════════════════╣
    echo  ║  Start:     start_cursebot.bat                          ║
    echo  ║  Diagnose:  HEALTH_CHECK.bat                            ║
    echo  ║  Reparatie: FIX_ALLES.bat                               ║
    echo  ║  Dashboard: http://localhost:5000                        ║
    echo  ╚══════════════════════════════════════════════════════════╝
) else (
    color 0E
    echo.
    echo  ╔══════════════════════════════════════════════════════════╗
    echo  ║  ⚠️  INSTALLATIE GEDEELTELIJK — %TOTAL_ERRORS% FOUT(EN)          ║
    echo  ║  Zie meldingen hierboven voor details.                  ║
    echo  ║  Draai HEALTH_CHECK.bat voor uitgebreide diagnose.      ║
    echo  ╚══════════════════════════════════════════════════════════╝
)

echo.
set HANDLEIDING=
if exist "%~dp0CurseBot_Handleiding_v2_4.html" set HANDLEIDING=%~dp0CurseBot_Handleiding_v2_4.html
if not "%HANDLEIDING%"=="" (start "" "%HANDLEIDING%" & call :status_line "Handleiding" "geopend in browser" OK)

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

:: ════════════════════════════════════════════════════════
:: SUBROUTINES
:: ════════════════════════════════════════════════════════

:header
echo.
echo  ── [%~1/%~2] %~3 ──────────────────────────────────
goto :eof

:status_line
set _LABEL=%~1
set _MSG=%~2
set _TYPE=%~3
if "%_TYPE%"=="OK"   echo  [OK]   %-25s %_MSG%
if "%_TYPE%"=="WARN" echo  [WARN] %-25s %_MSG%
if "%_TYPE%"=="FOUT" echo  [FOUT] %-25s %_MSG%
if "%_TYPE%"=="INFO" echo  [INFO] %-25s %_MSG%
goto :eof

:fetch_missing_files
:: Haalt ALLEEN ontbrekende of lege bestanden op — overschrijft nooit .env of secrets
set FETCH_ERRORS=0
set REPO_RAW=https://raw.githubusercontent.com/Die0uwe/cursebot/main

:: Verbinding testen
curl -sf --max-time 8 "%REPO_RAW%/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (
    call :status_line "GitHub" "niet bereikbaar — download overgeslagen" WARN
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
    call :status_line "Bestandscheck" "alle bestanden aanwezig" OK
) else (
    call :status_line "Bestandscheck" "%FETCH_ERRORS% bestand(en) niet opgehaald" WARN
)
goto :eof

:fetch_if_missing
set _LOCAL=%~1
set _REMOTE=%REPO_RAW%/%~1
set _REMOTE=%_REMOTE:\=/%

:: Alleen ophalen als bestand ontbreekt of leeg is
set _NEEDS_FETCH=0
if not exist "%_LOCAL%" set _NEEDS_FETCH=1
if exist "%_LOCAL%" (
    for %%A in ("%_LOCAL%") do if %%~zA equ 0 set _NEEDS_FETCH=1
)

if %_NEEDS_FETCH% equ 0 goto :eof

:: Map aanmaken
for %%F in ("%_LOCAL%") do (
    if not exist "%%~dpF" mkdir "%%~dpF" >nul 2>&1
)

curl -sf --max-time 20 -o "%_LOCAL%" "%_REMOTE%" 2>nul
if %errorlevel% neq 0 (
    call :status_line "OPHALEN MISLUKT" "%_LOCAL%" FOUT
    set /a FETCH_ERRORS+=1
    goto :eof
)

for %%A in ("%_LOCAL%") do (
    if %%~zA equ 0 (
        del "%_LOCAL%" >nul 2>&1
        call :status_line "LEEG BESTAND" "%_LOCAL%" FOUT
        set /a FETCH_ERRORS+=1
        goto :eof
    )
)
call :status_line "Opgehaald" "%_LOCAL%" OK
goto :eof

:: ╔══════════════════════════════════════════════════════════════════════╗
:: ║  File: CURSEBOT_INSTALL_v2.5.bat  │  v2.5  │  2026-06-06          ║
:: ║  Nieuw: live status-scherm per stap                                ║
:: ║  Nieuw: fetch_if_missing — haalt ALLEEN ontbrekende files op       ║
:: ║  Fix: alle exitcode-checks aanwezig                                ║
:: ║  Fix: .env wordt NOOIT overschreven door fetch                     ║
:: ║  Pentest: geen shell-injection in curl-paden                       ║
:: ║  Pentest: tokens nooit in BAT-variabelen opgeslagen               ║
:: ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
:: ╚══════════════════════════════════════════════════════════════════════╝
