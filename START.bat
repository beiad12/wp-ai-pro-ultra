@echo off
title WP AI Pro Ultra
color 0A

echo.
echo  ============================================
echo   WP AI Pro Ultra — Starting...
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Run install.bat first.
    pause
    exit /b 1
)

:: Check if streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependencies missing. Run install.bat first.
    pause
    exit /b 1
)

echo  [OK] Starting WP AI Pro on http://localhost:8501
echo.
echo  The app will open in your browser automatically.
echo  To stop the app, close this window.
echo.

:: Open browser after 3 seconds
start /b cmd /c "timeout /t 3 >nul && start http://localhost:8501"

:: Launch Streamlit
streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
