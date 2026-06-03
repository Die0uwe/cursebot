@echo off
title CurseBot — GitHub Push
color 0A
cd /d "%~dp0"

echo.
echo  ========================================
echo   CurseBot — GitHub Push Tool
echo   Repo: github.com/Die0uwe/cursebot
echo  ========================================
echo.
echo  Haal je PAT token op via:
echo  github.com ^> Settings ^> Developer settings
echo  ^> Personal access tokens ^> Tokens (classic)
echo  ^> Generate new token ^> repo scope
echo.

set /p TOKEN=Plak je GitHub token hier: 

if "%TOKEN%"=="" (
    echo [FOUT] Geen token ingevoerd.
    pause & exit /b 1
)

echo.
echo [1/3] Token instellen...
git remote set-url origin https://%TOKEN%@github.com/Die0uwe/cursebot.git

echo [2/3] Pushen naar GitHub...
git push origin main
if errorlevel 1 (
    echo [FOUT] Push mislukt. Controleer je token en internetverbinding.
    git remote set-url origin https://github.com/Die0uwe/cursebot.git
    set TOKEN=
    pause & exit /b 1
)

echo [3/3] Token verwijderen...
git remote set-url origin https://github.com/Die0uwe/cursebot.git
set TOKEN=

echo.
echo  ========================================
echo   Push geslaagd! Token verwijderd.
echo   Vergeet je token te revoken op GitHub!
echo  ========================================
echo.
pause
