@echo off
:: ╔══════════════════════════════════════════════════════════════════════════════╗
:: ║  CurseBot — FIX_PYTHON.bat                                                 ║
:: ║  Fixt: "Ontbrekende packages" loop na Python versiewijziging               ║
:: ║  Wat dit doet: verwijdert oude .venv, maakt nieuwe met juiste Python       ║
:: ╚══════════════════════════════════════════════════════════════════════════════╝
title CurseBot — Python Fix
color 0E
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  CurseBot — Python Versie Fix                   ║
echo  ║  Fixt de "Pillow loop" na Python wijziging      ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Stap 1: Welke Python draait er nu? ─────────────────────────────────────
echo  [1/5] Python versie controleren...
python --version 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  [FOUT] Python niet gevonden in PATH!
    echo  Installeer Python 3.10+ en vink "Add to PATH" aan.
    echo  https://www.python.org/downloads/
    echo.
    pause & exit /b 1
)

:: Controleer of het Python 3.10+ is
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Gevonden: Python %PYVER%

:: Extracteer major.minor
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if %PY_MAJOR% LSS 3 (
    echo  [FOUT] Python 3.10+ vereist, gevonden: %PYVER%
    pause & exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo.
    echo  ╔══════════════════════════════════════════════════╗
    echo  ║  WAARSCHUWING: Python %PYVER% is te oud!         ║
    echo  ║  CurseBot vereist Python 3.10 of hoger.         ║
    echo  ║  Download: https://www.python.org/downloads/    ║
    echo  ╚══════════════════════════════════════════════════╝
    pause & exit /b 1
)
echo  [OK] Python %PYVER% — geschikt

:: ── Stap 2: Oude .venv verwijderen ─────────────────────────────────────────
echo.
echo  [2/5] Oude .venv verwijderen...
if exist ".venv" (
    rmdir /s /q ".venv"
    echo  [OK] Oude .venv verwijderd
) else (
    echo  [INFO] Geen .venv gevonden — overgeslagen
)

:: ── Stap 3: Nieuwe .venv aanmaken met HUIDIGE Python ───────────────────────
echo.
echo  [3/5] Nieuwe .venv aanmaken met Python %PYVER%...
python -m venv .venv
if %errorlevel% neq 0 (
    echo  [FOUT] .venv aanmaken mislukt!
    pause & exit /b 1
)
echo  [OK] Nieuwe .venv aangemaakt

:: ── Stap 4: pip upgraden + alle packages installeren ───────────────────────
echo.
echo  [4/5] Packages installeren...
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo  [WARN] pip upgrade mislukt — doorgaan...
)

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [WARN] requirements.txt install had fouten.
    echo  Individueel proberen...
    pip install discord.py>=2.4.0
    pip install httpx>=0.27.0
    pip install pydantic>=2.7.0
    pip install pydantic-settings>=2.3.0
    pip install flask>=3.0.0
    pip install flask-cors>=4.0.0
    pip install customtkinter>=5.2.0
    pip install pystray>=0.19.0
    pip install python-dotenv>=1.0.0
    pip install keyring>=24.0.0
    pip install Pillow>=10.0.0
)

:: ── Verificeer Pillow expliciet ─────────────────────────────────────────────
python -c "from PIL import Image; print('[OK] Pillow werkt')" 2>nul
if %errorlevel% neq 0 (
    echo  [WARN] Pillow nog niet gevonden — extra install poging...
    pip install Pillow --force-reinstall
    python -c "from PIL import Image; print('[OK] Pillow nu werkend')" 2>nul
    if %errorlevel% neq 0 (
        echo  [FOUT] Pillow kan niet geïnstalleerd worden.
        echo  Probeer: pip install Pillow --pre
    )
)

:: ── Stap 5: __pycache__ opruimen ────────────────────────────────────────────
echo.
echo  [5/5] Cache opruimen...
for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo  [OK] __pycache__ gewist

:: ── Klaar ───────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  Fix voltooid!                                   ║
echo  ║  Start nu: start_cursebot.bat                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
