@echo off
title WP AI Pro — Installer
color 0A

echo.
echo  ============================================
echo   WP AI Pro Ultra — One-Click Installer
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Please install Python 3.9+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo  [OK] Python found.
echo.
echo  Installing dependencies... (this takes ~1 minute)
echo.

pip install --upgrade streamlit google-generativeai anthropic openai requests beautifulsoup4 apscheduler pandas python-dotenv >nul 2>&1

if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    echo  Try running this file as Administrator.
    pause
    exit /b 1
)

echo  [OK] All dependencies installed!
echo.
echo  ============================================
echo   Installation complete!
echo   Run START.bat to launch the app.
echo  ============================================
echo.
pause
