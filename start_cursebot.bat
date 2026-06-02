@echo off
title CurseBot - Slayer Alliance Edition
color 0A
cd /d "%~dp0"
call .venv\Scripts\activate.bat 2>nul

:loop
echo.
echo  ========================================
echo   CurseBot - Slayer Alliance Edition
echo   Gestart op %date% om %time%
echo  ========================================

python updater.py
if %errorlevel% == 42 (
    for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    goto loop
)

:: Start de native UI in een apart venster
start "CurseBot UI" python -m ui.app

:: Start de bot (met Flask dashboard op achtergrond)
python -m bot.main

echo [CurseBot] Bot gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak >nul
goto loop
