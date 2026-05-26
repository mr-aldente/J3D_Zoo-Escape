@echo off
title Desinstallation de Zoo Escape
cd /d "%~dp0"

if exist "%~dp0unins000.exe" (
    echo Lancement du desinstalleur Windows...
    start "" "%~dp0unins000.exe"
    exit /b 0
)

echo Desinstalleur introuvable dans ce dossier.
echo Utilisez : Parametres Windows ^> Applications ^> Zoo Escape ^> Desinstaller
pause
