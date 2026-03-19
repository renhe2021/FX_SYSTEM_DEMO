#!/usr/bin/env python
"""
Create Bloomberg Data Toolbox Distribution Package
"""
import os
import shutil

def create_distribution():
    # Paths
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(src_dir, "BBG_Toolbox_Distribution")
    
    # Clean and create dist folder
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    os.makedirs(os.path.join(dist_dir, "output"))
    
    # Files to copy
    files_to_copy = [
        ("quant_system/tools/bbg_wrapper.py", "bbg_wrapper.py"),
        ("quant_system/tools/web_app.py", "web_app.py"),
        ("quant_system/tools/data_explorer.py", "data_explorer.py"),
    ]
    
    for src, dst in files_to_copy:
        src_path = os.path.join(src_dir, src)
        dst_path = os.path.join(dist_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"Copied: {src} -> {dst}")
        else:
            print(f"Warning: {src} not found")
    
    # Fix imports in web_app.py
    web_app_path = os.path.join(dist_dir, "web_app.py")
    if os.path.exists(web_app_path):
        with open(web_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace relative imports with local imports
        content = content.replace("from .data_explorer import", "from data_explorer import")
        content = content.replace("from .bbg_wrapper import", "from bbg_wrapper import")
        
        with open(web_app_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed imports in web_app.py")
    
    # Fix imports in data_explorer.py
    data_explorer_path = os.path.join(dist_dir, "data_explorer.py")
    if os.path.exists(data_explorer_path):
        with open(data_explorer_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace("from .bbg_wrapper import", "from bbg_wrapper import")
        
        with open(data_explorer_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed imports in data_explorer.py")
    
    # Create START.bat
    start_bat = '''@echo off
chcp 65001 >nul
cd /d "%~dp0"
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

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

start http://127.0.0.1:5001
python start_server.py
pause
'''
    with open(os.path.join(dist_dir, "START.bat"), 'w', encoding='utf-8') as f:
        f.write(start_bat)
    print("Created: START.bat")
    
    # Create install.bat
    install_bat = '''@echo off
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

echo [1/2] Installing required packages...
pip install flask pandas openpyxl blpapi --quiet

if errorlevel 1 (
    echo.
    echo [WARNING] blpapi installation may require:
    echo   1. Bloomberg Terminal installed and running
    echo   2. C++ Build Tools (Visual Studio Build Tools)
    echo   See: https://www.bloomberg.com/professional/support/api-library/
    echo.
)

echo [2/2] Creating output folder...
if not exist "output" mkdir output

echo.
echo ========================================
echo   Installation complete!
echo   To start, double-click: START.bat
echo ========================================
pause
'''
    with open(os.path.join(dist_dir, "INSTALL.bat"), 'w', encoding='utf-8') as f:
        f.write(install_bat)
    print("Created: INSTALL.bat")
    
    # Create start_server.py
    server_py = '''#!/usr/bin/env python
"""Bloomberg Data Toolbox - Server Launcher"""
import sys
import os

# Setup path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
os.chdir(script_dir)

# Create output folder
os.makedirs("output", exist_ok=True)

try:
    from web_app import run_server
    run_server(host="127.0.0.1", port=5001)
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Please run INSTALL.bat first, or manually run:")
    print("  pip install flask pandas openpyxl blpapi")
    input("Press Enter to exit...")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
'''
    with open(os.path.join(dist_dir, "start_server.py"), 'w', encoding='utf-8') as f:
        f.write(server_py)
    print("Created: start_server.py")
    
    # Create requirements.txt
    requirements = '''flask>=2.0.0
pandas>=1.3.0
openpyxl>=3.0.0
blpapi>=3.0.0
'''
    with open(os.path.join(dist_dir, "requirements.txt"), 'w', encoding='utf-8') as f:
        f.write(requirements)
    print("Created: requirements.txt")
    
    # Create README.txt
    readme = '''========================================
  Bloomberg Data Toolbox
========================================

A web-based tool for downloading market data from Bloomberg Terminal.

REQUIREMENTS:
-------------
1. Python 3.8 or higher
2. Bloomberg Terminal (running)
3. Bloomberg API access

INSTALLATION:
-------------
1. Double-click INSTALL.bat
   - This will install required Python packages
   - If blpapi fails, you may need Visual Studio Build Tools

2. If INSTALL.bat doesn't work, run manually:
   pip install flask pandas openpyxl blpapi

USAGE:
------
1. Make sure Bloomberg Terminal is running
2. Double-click START.bat
3. Browser will open automatically at http://127.0.0.1:5001
4. Select data type, enter symbol, and download!

SUPPORTED DATA TYPES:
---------------------
- Bar Data (OHLCV): 1m/5m/15m/30m/1h intervals
- Tick Data: Trade ticks
- Bid/Ask Data: Quote data with resample options (1s to 1h)
- Reference Data: Static fields (PX_LAST, NAME, etc.)
- Historical Data: Daily/Weekly/Monthly OHLCV

COMMON SYMBOLS:
---------------
- USDCNH Curncy  (USD/CNH)
- EURUSD Curncy  (EUR/USD)
- USDJPY Curncy  (USD/JPY)
- SPX Index      (S&P 500)
- AAPL US Equity (Apple)

OUTPUT:
-------
Downloaded files are saved to the "output" folder in Excel format.

TROUBLESHOOTING:
----------------
1. "Cannot connect to Bloomberg"
   - Make sure Bloomberg Terminal is running
   - Check if you have API access enabled

2. "blpapi not installed"
   - Install Visual Studio Build Tools first
   - Then run: pip install blpapi

3. "No data returned"
   - Check if the symbol is correct
   - Verify the date range has trading data

========================================
'''
    with open(os.path.join(dist_dir, "README.txt"), 'w', encoding='utf-8') as f:
        f.write(readme)
    print("Created: README.txt")
    
    print(f"\n{'='*50}")
    print(f"Distribution package created at:")
    print(f"  {dist_dir}")
    print(f"\nTo share: Zip the entire folder and send to others.")
    print(f"{'='*50}")
    
    return dist_dir

if __name__ == "__main__":
    create_distribution()
