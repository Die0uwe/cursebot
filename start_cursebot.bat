@echo off
title CurseBot - Slayer Alliance Edition

:: Ga naar de map waar dit .bat bestand staat
cd /d "%~dp0"

:: Activeer de Python omgeving
call .venv\Scripts\activate

:loop
echo [CurseBot] Gestart op %date% om %time%
python -m bot.main

echo [CurseBot] Bot gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak
goto loop
