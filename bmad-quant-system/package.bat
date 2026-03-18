@echo off
echo ========================================
echo Bloomberg Data Toolbox - Packaging
echo ========================================

set PACKAGE_NAME=bbg_toolbox
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%

:: Create package directory
if exist %PACKAGE_NAME% rmdir /s /q %PACKAGE_NAME%
mkdir %PACKAGE_NAME%

:: Copy necessary files
echo Copying files...
xcopy /E /I /Y quant_system %PACKAGE_NAME%\quant_system
copy start_bbg_web.py %PACKAGE_NAME%\
copy requirements.txt %PACKAGE_NAME%\
copy INSTALL.txt %PACKAGE_NAME%\

:: Remove __pycache__
echo Cleaning cache...
for /d /r %PACKAGE_NAME% %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r %PACKAGE_NAME% %%f in (*.pyc) do @if exist "%%f" del "%%f"

:: Create zip
echo Creating zip...
powershell Compress-Archive -Path %PACKAGE_NAME% -DestinationPath %PACKAGE_NAME%_%TIMESTAMP%.zip -Force

:: Cleanup
rmdir /s /q %PACKAGE_NAME%

echo ========================================
echo Done! Package: %PACKAGE_NAME%_%TIMESTAMP%.zip
echo ========================================
pause
