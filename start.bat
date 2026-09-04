@echo off
title Nyxeris Storefront - Pipeline Theme
cd /d "%~dp0"

echo ======================================================================
echo           NYXERIS PIPELINE THEME STOREFRONT & DROPSHIPPING
echo ======================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not detected in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Initializing database and verifying assets...
python -c "import database; database.init_db()"
if errorlevel 1 (
    echo [ERROR] Database initialization failed.
    pause
    exit /b 1
)

echo [*] Starting Local Server at http://localhost:8000 ...
echo [*] Nyxeris Pipeline Storefront: http://localhost:8000
echo [*] Dropshipping Cockpit (Admin): http://localhost:8000/admin
echo [*] Onsus Themes: http://localhost:8000/home-05 ^| http://localhost:8000/home-01
echo.

:: Automatically launch default browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Start Uvicorn Server
python -m uvicorn main:app --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo [ERROR] Server terminated with an error.
    pause
)

