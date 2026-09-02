@echo off
title ARIA — AI Personal Assistant
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] ARIA failed to start. Run setup.bat first.
    pause
)
