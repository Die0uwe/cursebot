@echo off
title CurseBot - Slayer Alliance Edition
color 0A
cd /d "%~dp0"

:: Activeer de Python omgeving
call .venv\Scripts\activate

:loop
echo.
echo  ========================================
echo   CurseBot - Slayer Alliance Edition
echo   Gestart op %date% om %time%
echo  ========================================
echo.

:: Auto-update check via GitHub API
echo [UPDATER] Update check...
python updater.py
if %errorlevel% == 42 (
    echo [UPDATER] Bestanden bijgewerkt - herstart bot...
    echo.
    goto loop
)

:: Start de bot
python -m bot.main

echo.
echo [CurseBot] Bot gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak >nul
goto loop
