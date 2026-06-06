@echo off
:: ============================================================================
:: CurseBot -- FIX_ASSETS.bat v1.0 -- Asset bestanden naar correcte locatie
:: ============================================================================
title CurseBot - Asset Fix
chcp 437 >nul
cd /d "%~dp0"

echo.
echo  ============================================================
echo   CurseBot -- Asset Fix v1.0
echo   Kopieert LOGOSMALL.png, gaming_tools.webp naar ui\assets\
echo  ============================================================
echo.

:: Maak ui\assets map aan
if not exist "ui" mkdir "ui" >nul 2>&1
if not exist "ui\assets" mkdir "ui\assets" >nul 2>&1
echo  [OK]   ui\assets\ map aangemaakt

:: Kopieer van root map
set COPIED=0
for %%F in (LOGOSMALL.png gaming_tools.webp gt2-1.webp icon.ico CURSEBOT.png HEADER.png) do (
    if exist "%%F" (
        copy "%%F" "ui\assets\%%F" >nul 2>&1
        echo  [OK]   Gekopieerd: %%F
        set /a COPIED+=1
    )
)

:: Kopieer van images\ map
if exist "images" (
    for %%F in (LOGOSMALL.png gaming_tools.webp gt2-1.webp icon.ico CURSEBOT.png HEADER.png) do (
        if exist "images\%%F" (
            copy "images\%%F" "ui\assets\%%F" >nul 2>&1
            echo  [OK]   Gekopieerd van images\: %%F
            set /a COPIED+=1
        )
    )
    :: Kopieer alle PNG/webp/ico uit images\
    for %%F in (images\*.png images\*.webp images\*.ico) do (
        if exist "%%F" (
            copy "%%F" "ui\assets\" >nul 2>&1
        )
    )
    echo  [OK]   Alles uit images\ gekopieerd
)

:: Alias: gt2-1.webp als gaming_tools.webp
if exist "ui\assets\gt2-1.webp" (
    copy "ui\assets\gt2-1.webp" "ui\assets\gaming_tools.webp" >nul 2>&1
    echo  [OK]   gt2-1.webp -> gaming_tools.webp alias aangemaakt
)

:: Resultaat tonen
echo.
echo  ui\assets\ inhoud:
dir "ui\assets\" /b 2>nul || echo  (leeg)
echo.

if %COPIED% gtr 0 (
    color 0A
    echo  [OK] %COPIED% bestand(en) gekopieerd -- herstart CurseBot
) else (
    color 0E
    echo  [WARN] Geen bestanden gevonden in root of images\ map
    echo         Zet LOGOSMALL.png en gaming_tools.webp in de CurseBot map
)

echo.
echo  Druk op een toets om te sluiten...
pause >nul

:: ============================================================================
:: File: FIX_ASSETS.bat  |  v1.0  |  2026-06-07
:: Kopieert assets van root/images naar ui\assets\
:: Ondersteunt alias gt2-1.webp -> gaming_tools.webp
:: Created by DieOuwe . www.dieouwe.nl . discord.gg/y8Pu5qsEbQ
:: ============================================================================
