@echo off
title CurseBot EXE Builder
color 0A
cd /d "%~dp0"

echo.
echo  ========================================
echo   CurseBot EXE Builder
echo  ========================================
echo.

call .venv\Scripts\activate.bat

echo [1/3] PyInstaller installeren...
pip install pyinstaller --quiet

echo [2/3] EXE bouwen...
pyinstaller cursebot.spec --clean --noconfirm

echo [3/3] Klaar!
echo.
echo  Output: dist\CurseBot\CurseBot.exe
echo  Kopieer je .env naar dist\CurseBot\ voor je start!
echo.
pause
