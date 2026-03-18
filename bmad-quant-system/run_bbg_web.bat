@echo off
cd /d %~dp0
echo Starting Bloomberg Data Toolbox...
python -c "import sys; sys.path.insert(0, r'%~dp0'); from quant_system.tools.web_app import run_server; run_server()"
pause
