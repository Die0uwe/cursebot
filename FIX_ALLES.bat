@echo off
chcp 65001 >nul
echo ========================================
echo  CurseBot — FIX ALLES
echo  Slayer Alliance Edition
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [FOUT] Python niet gevonden!
    echo Installeer Python 3.11+ van python.org
    pause & exit /b 1
)

echo [1/3] Vereiste packages installeren...
pip install customtkinter Pillow requests aiohttp httpx pydantic pydantic-settings pystray discord.py --quiet --upgrade
if errorlevel 1 (
    echo [FOUT] pip install mislukt. Probeer: pip install customtkinter
    pause & exit /b 1
)
echo     OK

echo [2/3] requirements.txt installeren...
pip install -r requirements.txt --quiet
echo     OK

echo [3/3] Klaar!
echo.
echo ========================================
echo  Start nu: python launch.py
echo  of dubbelklik op: start_cursebot.bat
echo ========================================
echo.
pause
