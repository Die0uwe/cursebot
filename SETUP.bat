# ==============================================================================
# Copyright (C) 2026  DieOuwe (https://www.dieouwe.nl / https://www.slayeralliance.com)
#
# This work is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# ==============================================================================
@echo off
title CurseBot Setup — Slayer Alliance Edition
color 0A
cls

echo.
echo  ========================================
echo   CurseBot - Slayer Alliance Edition
echo   Automatische installatie
echo  ========================================
echo.

:: Check of Python al geinstalleerd is
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Python gevonden.
    goto :install_deps
)

echo  [!] Python niet gevonden. Downloaden...
echo.

:: Download Python installer via PowerShell
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'}"

echo  [!] Python installer gedownload. Nu installeren...
echo      Wacht even - dit duurt 1-2 minuten.
echo.

:: Installeer Python stil met PATH toegevoegd
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

:: Ververs de PATH omgevingsvariabele
call RefreshEnv.cmd >nul 2>&1

:: Wacht even
timeout /t 5 /nobreak >nul

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FOUT] Python installatie mislukt.
    echo  Installeer Python handmatig via: https://www.python.org/downloads/
    echo  Vink "Add Python to PATH" aan!
    pause
    exit /b 1
)

echo  [OK] Python succesvol geinstalleerd.

:install_deps
echo.
echo  [..] Python omgeving aanmaken...
cd /d "%~dp0"
python -m venv .venv >nul 2>&1
echo  [OK] Virtuele omgeving aangemaakt.

echo  [..] Pakketten installeren (discord.py etc.)...
call .venv\Scripts\activate
pip install -r requirements.txt --quiet
echo  [OK] Alle pakketten geinstalleerd.

echo.
echo  [..] Configuratie openen...
start "" "%~dp0cursebot_setup.html"

echo.
echo  ========================================
echo   Setup klaar!
echo.  
echo   1. Vul je tokens in het browservenster in
echo   2. Klik "Opslaan als .env"
echo   3. Sla het bestand op als .env in deze map
echo   4. Dubbelklik daarna op: start_cursebot.bat
echo  ========================================
echo.
pause

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         FILE CARD                                    ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  File         : SETUP.bat                                           ║
# ║  Role         : Docs                                                ║
# ║  Version      : 1.0.0                                               ║
# ║  Created      : 2026-06-02                                          ║
# ║  Last Updated : 2026-06-02  13:45                                     ║
# ║  Status       : Updated                                             ║
# ║  Notes        : Windows setup script                                ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║  Created by Dieouwe                                                  ║
# ║  🌐 www.dieouwe.nl          ⚔️  www.slayeralliance.com              ║
# ║  📦 curseforge.com/members/dieouwe/projects                         ║
# ║  💬 discord.gg/y8Pu5qsEbQ                                           ║
# ╚══════════════════════════════════════════════════════════════════════╝
