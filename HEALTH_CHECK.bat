@echo off
:: ╔══════════════════════════════════════════════════════════════════════════════╗
:: ║  CurseBot — Slayer Alliance Edition                                        ║
:: ║  HEALTH_CHECK.bat  v1.1 — Volledig stress-test en pentestrapport          ║
:: ║  Schrijft GEEN bestanden — 100% veilig diagnostisch gereedschap           ║
:: ╚══════════════════════════════════════════════════════════════════════════════╝
title CurseBot - Health Check & Pentest
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  CurseBot — Health Check ^& Security Scan  v1.1             ║
echo  ║  Schrijft GEEN bestanden — puur diagnostisch                ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
cd /d "%~dp0"

set ERRORS=0
set WARNINGS=0
set SECURITY_ISSUES=0

:: ════════════════════════════════════════════════════════
:: CHECK 1 — Python
:: ════════════════════════════════════════════════════════
echo  ── [1/9] Python ─────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FOUT] Python NIET in PATH
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK]   %%v
)
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 2 — Virtuele omgeving
:: ════════════════════════════════════════════════════════
echo  ── [2/9] Virtuele omgeving (.venv) ──────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo  [FOUT] .venv niet gevonden → CURSEBOT_INSTALL_v2_5.bat
    set /a ERRORS+=1
) else (
    .venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [FOUT] .venv Python niet uitvoerbaar — beschadigd
        set /a ERRORS+=1
    ) else (
        for /f "tokens=*" %%v in ('.venv\Scripts\python.exe --version 2^>^&1') do echo  [OK]   venv %%v
    )
)
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat 2>nul
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 3 — Packages
:: ════════════════════════════════════════════════════════
echo  ── [3/9] Python packages ────────────────────────────────────
call :pkg_check "discord"       "discord.py"       FOUT
call :pkg_check "customtkinter" "customtkinter"    FOUT
call :pkg_check "httpx"         "httpx"            FOUT
call :pkg_check "pydantic"      "pydantic"         FOUT
call :pkg_check "flask"         "flask"            FOUT
call :pkg_check "PIL"           "Pillow"           WARN
call :pkg_check "dotenv"        "python-dotenv"    WARN
call :pkg_check "keyring"       "keyring"          WARN
call :pkg_check "pystray"       "pystray"          WARN
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 4 — Kritieke bestanden aanwezig en niet leeg
:: ════════════════════════════════════════════════════════
echo  ── [4/9] Kritieke bestanden ─────────────────────────────────
call :file_check "launch.py"
call :file_check "updater.py"
call :file_check "dashboard.py"
call :file_check "requirements.txt"
call :file_check "bot\main.py"
call :file_check "bot\config.py"
call :file_check "bot\cogs\curseforge.py"
call :file_check "bot\services\curseforge_api.py"
call :file_check "bot\services\stats.py"
call :file_check "bot\services\cache.py"
call :file_check "bot\utils\logger.py"
call :file_check "ui\app.py"
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 5 — .env configuratie
:: ════════════════════════════════════════════════════════
echo  ── [5/9] Configuratie (.env) ────────────────────────────────
if not exist ".env" (
    echo  [FOUT] .env niet gevonden → CURSEBOT_INSTALL_v2_5.bat
    set /a ERRORS+=1
) else (
    echo  [OK]   .env aanwezig
    findstr /C:"DISCORD_TOKEN=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (echo  [FOUT] DISCORD_TOKEN leeg & set /a ERRORS+=1) else (echo  [OK]   DISCORD_TOKEN ingevuld)
    findstr /C:"CURSEFORGE_API_KEY=jouw" ".env" >nul 2>&1
    if %errorlevel% equ 0 (echo  [FOUT] CURSEFORGE_API_KEY leeg & set /a ERRORS+=1) else (echo  [OK]   CURSEFORGE_API_KEY ingevuld)
)
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 6 — Internet
:: ════════════════════════════════════════════════════════
echo  ── [6/9] Internet en API-bereikbaarheid ─────────────────────
curl -sf --max-time 8 "https://raw.githubusercontent.com/Die0uwe/cursebot/main/requirements.txt" >nul 2>&1
if %errorlevel% neq 0 (echo  [WARN] GitHub niet bereikbaar & set /a WARNINGS+=1) else (echo  [OK]   GitHub bereikbaar)
curl -sf --max-time 8 "https://api.curseforge.com" >nul 2>&1
if %errorlevel% neq 0 (echo  [WARN] CurseForge API niet bereikbaar & set /a WARNINGS+=1) else (echo  [OK]   CurseForge bereikbaar)
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 7 — Python syntax
:: ════════════════════════════════════════════════════════
echo  ── [7/9] Python syntax controle ────────────────────────────
call :syntax_check "launch.py"
call :syntax_check "updater.py"
call :syntax_check "dashboard.py"
call :syntax_check "bot\main.py"
call :syntax_check "bot\config.py"
call :syntax_check "bot\cogs\curseforge.py"
call :syntax_check "bot\services\stats.py"
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 8 — Import test
:: ════════════════════════════════════════════════════════
echo  ── [8/9] Module import test ─────────────────────────────────
python -c "import bot.config; print('  [OK]   bot.config')" 2>nul || (echo  [FOUT] bot.config importeert niet & set /a ERRORS+=1)
python -c "import bot.services.stats; print('  [OK]   bot.services.stats')" 2>nul || (echo  [FOUT] bot.services.stats importeert niet & set /a ERRORS+=1)
python -c "import launch; print('  [OK]   launch.py')" 2>nul || (echo  [FOUT] launch.py importeert niet & set /a ERRORS+=1)
echo.

:: ════════════════════════════════════════════════════════
:: CHECK 9 — SECURITY / PENTEST
:: ════════════════════════════════════════════════════════
echo  ── [9/9] Security scan (pentest) ────────────────────────────

:: 9a — .env in git? (mag NOOIT ge-commit worden)
if exist ".git\index" (
    git ls-files ".env" 2>nul | findstr ".env" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  [SEC!] .env staat getrackt in git — VERWIJDER DIRECT
        echo         Voer uit: git rm --cached .env
        set /a SECURITY_ISSUES+=1
    ) else (
        echo  [OK]   .env niet getrackt in git
    )
) else (
    echo  [INFO] Geen .git map — git-check overgeslagen
)

:: 9b — Hardcoded tokens in Python-bestanden?
echo  [..] Controleren op hardcoded tokens in Python-bestanden...
findstr /R /S /I "discord_token\s*=\s*['\"][A-Za-z0-9._-]\{20,\}['\"]" bot\*.py >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SEC!] Mogelijk hardcoded Discord token gevonden in bot\*.py!
    set /a SECURITY_ISSUES+=1
) else (
    echo  [OK]   Geen hardcoded Discord tokens gevonden
)

findstr /R /S /I "api_key\s*=\s*['\"][A-Za-z0-9-]\{30,\}['\"]" bot\*.py >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SEC!] Mogelijk hardcoded API key gevonden in bot\*.py!
    set /a SECURITY_ISSUES+=1
) else (
    echo  [OK]   Geen hardcoded API keys gevonden
)

:: 9c — Dashboard open op 0.0.0.0?
findstr /I "host.*0\.0\.0\.0" dashboard.py >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SEC!] Dashboard gebonden aan 0.0.0.0 — extern bereikbaar!
    set /a SECURITY_ISSUES+=1
) else (
    echo  [OK]   Dashboard gebonden aan 127.0.0.1 ^(lokaal only^)
)

:: 9d — debug=True in Flask?
findstr /I "debug.*=.*True" dashboard.py >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SEC!] Flask debug=True gevonden — NOOIT in productie!
    set /a SECURITY_ISSUES+=1
) else (
    echo  [OK]   Flask debug=False
)

:: 9e — .env beschermde velden in ALLOWED_SETTINGS?
findstr /I "DISCORD_TOKEN\|CURSEFORGE_API_KEY\|ANTHROPIC_API_KEY" dashboard.py | findstr /I "ALLOWED_SETTINGS" >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SEC!] Token-keys in ALLOWED_SETTINGS van dashboard — lek risico!
    set /a SECURITY_ISSUES+=1
) else (
    echo  [OK]   Token-keys niet schrijfbaar via dashboard API
)

echo.

:: ════════════════════════════════════════════════════════
:: EINDRAPPORT
:: ════════════════════════════════════════════════════════
echo  ════════════════════════════════════════════════════════════
echo  HEALTH CHECK RAPPORT
echo  ════════════════════════════════════════════════════════════
echo.
echo  Fouten:             %ERRORS%
echo  Waarschuwingen:     %WARNINGS%
echo  Security issues:    %SECURITY_ISSUES%
echo.

if %ERRORS% equ 0 (
    if %SECURITY_ISSUES% equ 0 (
        if %WARNINGS% equ 0 (
            color 0A
            echo  ✅ PERFECT — Alles gezond, geen security issues.
        ) else (
            color 0E
            echo  ⚠️  OK met waarschuwingen — bot kan starten.
        )
    ) else (
        color 0C
        echo  🔒 SECURITY ISSUES GEVONDEN — %SECURITY_ISSUES% probleem^(en^)
        echo     Verhelp de SEC! meldingen hierboven voor je verder gaat.
    )
) else (
    color 0C
    echo  ❌ %ERRORS% FOUT^(EN^) + %SECURITY_ISSUES% security issues
    echo     Draai: CURSEBOT_INSTALL_v2_5.bat voor volledig herstel.
)

echo.
echo  Druk op een toets om te sluiten...
pause >nul
exit /b %ERRORS%

:: ── Subroutines ───────────────────────────────────────────────────────────────
:pkg_check
python -c "import %~1; v=getattr(%~1,'__version__','?'); print('  [OK]  ','%~2',v)" 2>nul
if %errorlevel% neq 0 (
    if "%~3"=="FOUT" (echo  [FOUT] %~2 niet geinstalleerd & set /a ERRORS+=1)
    if "%~3"=="WARN" (echo  [WARN] %~2 niet geinstalleerd & set /a WARNINGS+=1)
)
goto :eof

:file_check
if not exist "%~1" (echo  [FOUT] ONTBREEKT: %~1 & set /a ERRORS+=1 & goto :eof)
for %%A in ("%~1") do (
    if %%~zA equ 0 (echo  [FOUT] LEEG: %~1 & set /a ERRORS+=1) else (echo  [OK]   %~1)
)
goto :eof

:syntax_check
if not exist "%~1" (echo  [SKIP] %~1 ontbreekt & goto :eof)
python -m py_compile "%~1" >nul 2>&1
if %errorlevel% neq 0 (echo  [FOUT] SYNTAX FOUT in %~1 & set /a ERRORS+=1) else (echo  [OK]   %~1 syntax OK)
goto :eof

:: ╔══════════════════════════════════════════════════════════════════════╗
:: ║  File: HEALTH_CHECK.bat  │  v1.1  │  2026-06-06                   ║
:: ║  Checks 1-8: Python, venv, packages, bestanden, .env, net, syntax  ║
:: ║  Check 9: security/pentest — git-tracking, hardcoded tokens,       ║
:: ║           dashboard host/debug, ALLOWED_SETTINGS token-keys        ║
:: ║  Schrijft GEEN bestanden — 100% veilig diagnostisch               ║
:: ║  Created by DieOuwe · www.dieouwe.nl · discord.gg/y8Pu5qsEbQ      ║
:: ╚══════════════════════════════════════════════════════════════════════╝
