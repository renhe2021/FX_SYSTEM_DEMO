@echo off
chcp 65001 >nul
cd /d %~dp0
title Bloomberg Data Toolbox

echo ========================================
echo   Bloomberg Data Toolbox
echo ========================================
echo.
echo Starting server at http://127.0.0.1:5001
echo.
echo [!] Make sure Bloomberg Terminal is running
echo [!] Press Ctrl+C to stop the server
echo.
start http://127.0.0.1:5001
python start_server.py
pause
