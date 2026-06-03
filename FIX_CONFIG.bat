@echo off
cd /d "%~dp0"
echo [FIX] __pycache__ wissen...
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo [FIX] config.py vervangen...
curl -sf -o bot\config.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/config.py"
echo [FIX] Klaar! Start nu start_cursebot.bat
pause
