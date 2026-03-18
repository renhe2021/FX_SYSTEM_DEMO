#!/usr/bin/env python
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
    from bbg_web import run_server
    run_server(host="127.0.0.1", port=5001)
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Please run: pip install flask pandas openpyxl blpapi")
    input("Press Enter to exit...")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
