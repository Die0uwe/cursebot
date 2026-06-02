@echo off
title CurseBot - Alles Fixen
color 0C
cls
echo.
echo  ============================================
echo   CurseBot - Volledige Reset en Update
echo  ============================================
echo.

cd /d "%~dp0"

echo [1/5] __pycache__ wissen...
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo       Klaar.

echo [2/5] Bestanden downloaden van GitHub...
curl -sf -o bot\config.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/config.py"
echo       config.py
curl -sf -o bot\services\curseforge_api.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/services/curseforge_api.py"
echo       curseforge_api.py
curl -sf -o bot\services\stats.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/services/stats.py"
echo       stats.py
curl -sf -o bot\cogs\curseforge.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/cogs/curseforge.py"
echo       curseforge.py
curl -sf -o bot\main.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/main.py"
echo       main.py
curl -sf -o bot\utils\logger.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/bot/utils/logger.py"
echo       logger.py
curl -sf -o dashboard.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/dashboard.py"
echo       dashboard.py
curl -sf -o updater.py "https://raw.githubusercontent.com/Die0uwe/cursebot/main/updater.py"
echo       updater.py

echo [3/5] Last commit resetten zodat updater werkt...
if exist .last_commit del .last_commit

echo [4/5] Dependencies updaten...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [5/5] Bot starten...
echo.
echo  ============================================
echo   Klaar! Bot start nu op...
echo  ============================================
echo.

:loop
echo.
echo [CurseBot] Gestart op %date% om %time%

python updater.py
if %errorlevel% == 42 (
    for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    goto loop
)

python -m bot.main
echo [CurseBot] Bot gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak >nul
goto loop
