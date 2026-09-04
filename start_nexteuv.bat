@echo off
title Next EUV - Electric Vehicles Showcase (Local Server)
cd /d "%~dp0"

echo ======================================================================
echo           NEXT EUV - ELECTRIC VEHICLES SHOWCASE ^(LOCAL^)
echo ======================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not detected in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Starting Next EUV Local Server at http://localhost:8000 ...
echo [*] Local Mirror Directory: %~dp0nexteuv
echo.

:: Automatically launch default browser after 1.5 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Start Server
python serve_nexteuv.py 8000

if errorlevel 1 (
    echo [ERROR] Server terminated with an error.
    pause
)
