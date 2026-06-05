@echo off
title CurseBot - Slayer Alliance Edition
color 0A
cd /d "%~dp0"

:: ── Controleer of .venv bestaat ──────────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  ╔══════════════════════════════════════════════════╗
    echo  ║  [FOUT] .venv niet gevonden of beschadigd!      ║
    echo  ║  Draai eerst: FIX_PYTHON.bat                    ║
    echo  ╚══════════════════════════════════════════════════╝
    echo.
    pause & exit /b 1
)

:: ── Activeer de venv ─────────────────────────────────────────────────────────
call .venv\Scripts\activate.bat

:: ── Verificeer dat de venv Python overeenkomt met systeem Python ─────────────
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set VENV_VER=%%v
for /f "tokens=2" %%v in ('".venv\Scripts\python.exe" --version 2^>^&1') do set VENV_INTERNAL=%%v

:: ── Pillow check BINNEN de venv ──────────────────────────────────────────────
python -c "from PIL import Image" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [WARN] Pillow mist in .venv — wordt geïnstalleerd...
    python -m pip install Pillow --quiet
    python -c "from PIL import Image" >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [FOUT] Pillow installatie mislukt.
        echo  Draai FIX_PYTHON.bat om de venv te herstellen.
        pause & exit /b 1
    )
    echo  [OK] Pillow geïnstalleerd in .venv
)

:loop
echo.
echo  ========================================
echo   CurseBot - Slayer Alliance Edition
echo   Gestart op %date% om %time%
echo   Python: %VENV_INTERNAL%
echo  ========================================

python updater.py
if %errorlevel% == 42 (
    for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    goto loop
)

python launch.py

echo [CurseBot] Gestopt. Herstart over 5 seconden...
timeout /t 5 /nobreak >nul
goto loop
