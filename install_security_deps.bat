@echo off
title CurseBot — Security dependencies installeren
color 0A
cd /d "%~dp0"

echo.
echo  ============================================
echo   CurseBot — pip install security packages
echo  ============================================
echo.

:: Activeer de venv
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [WARN] Geen .venv gevonden — installeer globaal
)

echo [1/3] keyring installeren ^(Windows Credential Manager^)...
pip install "keyring>=24.0.0" --quiet
if errorlevel 1 (
    echo [FOUT] keyring installatie mislukt
    pause & exit /b 1
)
echo       OK

echo [2/3] python-dotenv installeren ^(.env lezen^)...
pip install "python-dotenv>=1.0.0" --quiet
if errorlevel 1 (
    echo [FOUT] python-dotenv installatie mislukt
    pause & exit /b 1
)
echo       OK

echo [3/3] Verificatie...
python -c "import keyring; print('  keyring versie:', keyring.__version__)"
python -c "import dotenv; print('  python-dotenv OK')"

echo.
echo  ============================================
echo   Klaar! Security packages geinstalleerd.
echo   Start nu: start_cursebot.bat
echo  ============================================
echo.
pause
