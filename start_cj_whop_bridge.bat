@echo off
title CJdropshipping: Sourcing, Dropshipping & Fulfillment - Developed by Taki
cd /d "%~dp0whop_cj_app"

echo ======================================================================
echo    CJDROPSHIPPING: SOURCING, DROPSHIPPING & FULFILLMENT FOR WHOP
echo    Multi-Tenant Sourcing & Automated Carrier Fulfillment Engine
echo    Developed by Taki • Whop Vibe Architecture
echo ======================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not detected in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Initializing CJ-Whop Bridge Server on http://127.0.0.1:8090 ...
echo.

:: Launch browser in background after 1.5 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8090"

:: Start Uvicorn Server
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] CJ Dropshipping Bridge terminated with an error code.
    pause
)
