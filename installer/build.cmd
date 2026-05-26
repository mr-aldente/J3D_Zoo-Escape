@echo off
REM Lance le build sans modifier la strategie d'execution PowerShell du systeme.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
if errorlevel 1 (
    echo.
    echo Echec du build. Verifiez Python 3.10-3.12 et Inno Setup 6.
    pause
    exit /b 1
)
pause
