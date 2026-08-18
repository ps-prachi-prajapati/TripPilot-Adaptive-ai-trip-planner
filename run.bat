@echo off
setlocal enabledelayedexpansion

:: Set window title
title Adaptive AI Trip Planner

:: Change working directory to the folder containing this batch script
cd /d "%~dp0"

echo ===================================================
echo     Adaptive AI Trip Planner - Starting App...
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in system PATH.
    echo Please install Python 3.10 or higher and make sure it is added to PATH.
    echo.
    pause
    exit /b 1
)

:: Check if streamlit is installed
python -m streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Streamlit package not found. Installing requirements...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies from requirements.txt.
        echo.
        pause
        exit /b 1
    )
)

echo [SUCCESS] Environment check passed.
echo [INFO] Launching Streamlit App (app.py)...
echo [INFO] Browser window will open automatically.
echo.

:: Run the application
python -m streamlit run app.py

:: Keep window open if app stops
echo.
echo ===================================================
echo Application has finished or was stopped.
echo ===================================================
pause
