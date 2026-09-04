@echo off
title Necyron - Local Offline Website
cd /d "%~dp0"

echo ======================================================================
echo           NECYRON - LOCAL OFFLINE CYBERSECURITY TEMPLATE
echo ======================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not detected in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Starting Necyron Local Server at http://localhost:8080 ...
echo [*] Website Root: %~dp0necyron
echo.

:: Automatically launch default browser after 1.5 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8080"

:: Start Necyron Local Server
python necyron\server.py 8080

if errorlevel 1 (
    echo [ERROR] Necyron server terminated with an error.
    pause
)
