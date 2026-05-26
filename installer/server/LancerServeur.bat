@echo off
title Zoo Escape - Serveur multijoueur
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 zoo_escape_server.py
    goto :fin
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python zoo_escape_server.py
    goto :fin
)

echo Python 3 est requis. Installez-le depuis https://www.python.org/downloads/
pause
exit /b 1

:fin
if errorlevel 1 pause
