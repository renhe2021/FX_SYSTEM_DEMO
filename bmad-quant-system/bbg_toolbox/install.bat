@echo off
chcp 65001 >nul
echo ========================================
echo   Bloomberg Data Toolbox - Installation
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing required packages...
pip install flask pandas openpyxl blpapi --quiet

if errorlevel 1 (
    echo.
    echo [WARNING] blpapi installation may require:
    echo   1. Bloomberg Terminal installed and running
    echo   2. C++ Build Tools (Visual Studio Build Tools)
    echo   See: https://www.bloomberg.com/professional/support/api-library/
    echo.
)

echo [2/3] Creating output folder...
if not exist "output" mkdir output

echo [3/3] Installation complete!
echo.
echo ========================================
echo   To start the toolbox, run: START.bat
echo ========================================
pause
