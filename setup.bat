@echo off
title ARIA Setup
color 0A
echo.
echo  =========================================
echo    ARIA - AI Personal Voice Assistant
echo    Setup Script
echo  =========================================
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found!
    echo  Please install Python 3.9+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo  [OK] Python found:
python --version
echo.

:: Upgrade pip silently
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.

:: Install all dependencies
echo  Installing ARIA dependencies (this may take a minute)...
echo.
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Installation failed.
    echo  Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo  =========================================
echo    Setup Complete!
echo  =========================================
echo.
echo  To start ARIA:
echo    - Double-click start_aria.bat
echo    - Or run: python main.py
echo.
echo  First-time setup:
echo    1. Click the Settings (gear) button in ARIA
echo    2. Paste your free Gemini API key
echo    3. Click Save Settings
echo    4. Press F2 and start talking!
echo.
echo  Get your free API key at:
echo    https://aistudio.google.com/apikey
echo.
pause
