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

:: Start de native UI + bot samen via launch.py
:: launch.py start bot als daemon thread, UI in main thread
:: Zo is er maar EEN venster (de UI), bot draait op de achtergrond
python launch.py

echo [CurseBot] Gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak >nul
goto loop
