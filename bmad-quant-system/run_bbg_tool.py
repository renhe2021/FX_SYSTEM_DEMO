#!/usr/bin/env python
"""
启动 Bloomberg 数据工具箱 Web UI
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_system.tools.web_app import run_server

if __name__ == "__main__":
    run_server(host="127.0.0.1", port=5001)
