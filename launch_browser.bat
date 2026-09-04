@echo off
title Nyxeris Persistent Automation Browser
cd /d "%~dp0"

echo ======================================================================
echo           NYXERIS REAL HUMAN BROWSER (ANTI-BOT PROTECTED)
echo ======================================================================
echo.
echo [*] Initializing persistent user profile at C:\Nyxeris\browser_profile ...
if not exist "C:\Nyxeris\browser_profile" mkdir "C:\Nyxeris\browser_profile"

:: Detect Chrome path
set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist %CHROME_PATH% (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
if not exist %CHROME_PATH% (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)
if not exist %CHROME_PATH% (
    echo [!] Chrome not found in standard path, falling back to Microsoft Edge...
    set CHROME_PATH="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

echo [*] Launching genuine browser with Remote Debugging on Port 9222...
echo [*] Login to Whop, CJ Dropshipping, or Gmail inside this browser.
echo [*] Your logins and cookies will be saved permanently in C:\Nyxeris\browser_profile
echo.

start "" %CHROME_PATH% ^
  --remote-debugging-port=9222 ^
  --user-data-dir="C:\Nyxeris\browser_profile" ^
  --disable-blink-features=AutomationControlled ^
  --no-first-run ^
  --no-default-browser-check ^
  "https://whop.com" "https://cjdropshipping.com" "http://localhost:8000"

echo [SUCCESS] Real browser launched! You can now log into your accounts.
timeout /t 5
