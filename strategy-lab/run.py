#!/usr/bin/env python
"""启动策略实验室"""
import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import run_app

if __name__ == '__main__':
    run_app(host='0.0.0.0', port=8888, debug=True)
