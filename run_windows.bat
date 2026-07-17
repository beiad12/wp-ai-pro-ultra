@echo off
echo Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found. Install Python 3.9+ from https://www.python.org/downloads/
    echo IMPORTANT: during install, check "Add python.exe to PATH".
    pause
    exit /b 1
)

echo.
echo Installing/updating dependencies (this can take a minute)...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See the message above for details.
    pause
    exit /b 1
)

echo.
echo Launching WP Pro Ultra locally at http://localhost:8501 ...
python -m streamlit run app.py
pause
