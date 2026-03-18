#!/usr/bin/env python
"""启动 Bloomberg 数据工具箱 Web UI"""
import sys
import os
import traceback

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)

print(f"Project root: {project_root}")
print(f"Python: {sys.executable}")

try:
    print("Importing web_app...")
    from quant_system.tools.web_app import run_server
    print("Import successful, starting server...")
    run_server(host="127.0.0.1", port=5001)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
