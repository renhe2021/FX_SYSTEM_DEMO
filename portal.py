# -*- coding: utf-8 -*-
"""
FX_SYSTEM Portal — 统一入口
============================
汇集所有子模块，一个页面看全局、一键启动各工具。
"""

import sys
import os
import json
import socket
import subprocess
import signal
from pathlib import Path
from flask import Flask, jsonify, send_file
from flask_cors import CORS

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent

app = Flask(__name__, static_folder='.', static_url_path='/static')
CORS(app)

# ═══════════════════════════════════════════════
# 模块注册表
# ═══════════════════════════════════════════════

MODULES = [
    {
        "id": "markup-pricing",
        "name": "加价定价模拟器",
        "name_en": "Markup Pricing Simulator",
        "icon": "💰",
        "port": 8891,
        "category": "pricing",
        "category_label": "定价与收入",
        "description": "交易量 Excel → 交互式加价模拟，支持统一/波动率加权/反算等6种加价策略",
        "data_format": "月度交易量 Excel (.xlsx)",
        "entry": "markup_app.py",
        "dir": "markup-pricing",
        "features": [
            "按币种/业务设加价 BPS",
            "统一加价扫描",
            "波动率加权建议 (BBG)",
            "目标收入反推加价方案",
            "隐蔽式加价优化",
            "MSO / SVF 主体切换",
        ],
    },
    {
        "id": "pnl-analysis",
        "name": "损益分析工具",
        "name_en": "P&L Analysis Tool",
        "icon": "📊",
        "port": 5004,
        "category": "reporting",
        "category_label": "报表与可视化",
        "description": "上传损益明细 CSV/Excel → 自动多维度分析 → 生成格式化 Excel 报表下载",
        "data_format": "PROFIT_LOSS_DETAIL_*.csv / .xlsx",
        "entry": "app.py",
        "dir": "pnl-analysis",
        "launch_script": "run_pnl.py",  # 根目录启动脚本
        "features": [
            "拖拽上传 CSV/Excel",
            "9维度自动分析",
            "WX vs FIT 损益拆解",
            "多月份对比",
            "一键导出 Excel 报表",
        ],
    },
    {
        "id": "strategy-lab",
        "name": "策略回测实验室",
        "name_en": "Strategy Lab",
        "icon": "🧪",
        "port": 8888,
        "category": "quant",
        "category_label": "量化与策略",
        "description": "上传交易数据 CSV → 选择策略 → 配置参数 → 运行回测 → 查看结果",
        "data_format": "交易数据 CSV (分钟线/日线)",
        "entry": "app.py",
        "dir": "strategy-lab",
        "features": [
            "周五晚锁价策略",
            "MA 交叉策略",
            "可上传数据文件",
            "参数可调回测",
            "收益曲线 + 统计",
        ],
    },
    {
        "id": "fx-report",
        "name": "FX 研报制作平台",
        "name_en": "FX Research Report Hub",
        "icon": "📝",
        "port": 8080,
        "category": "reporting",
        "category_label": "报表与可视化",
        "description": "客户门户 + 市场数据 → 投行级 FX 研究报告 (HTML/PDF)",
        "data_format": "Bloomberg 市场数据 JSON",
        "entry": "app.py",
        "dir": "fx-report",
        "features": [
            "客户画像管理",
            "报告章节编辑",
            "Corridor 分析",
            "图表自动生成",
            "PDF 报告导出",
        ],
    },
    {
        "id": "fx-report-generator",
        "name": "FX 研报 CLI",
        "name_en": "FX Report Generator (CLI)",
        "icon": "📄",
        "port": None,
        "category": "reporting",
        "category_label": "报表与可视化",
        "description": "命令行一键生成 FX 研究报告 PDF，支持指定日期和币种",
        "data_format": "自动拉取市场数据",
        "entry": "generate_report.py",
        "dir": "fx-report-generator",
        "features": [
            "一键生成 PDF",
            "指定日期/币种",
            "自动拉取数据",
        ],
    },
    {
        "id": "bmad-quant",
        "name": "BMAD 量化系统",
        "name_en": "BMAD Quant System",
        "icon": "📈",
        "port": 5002,
        "category": "quant",
        "category_label": "量化与策略",
        "description": "全功能量化交易平台：策略管理、信号查看、回测、BBG 数据工具箱",
        "data_format": "USDCNH 信号文件 / BBG 数据",
        "entry": "main.py",
        "dir": "bmad-quant-system",
        "features": [
            "Quant Web UI (策略管理)",
            "BBG 数据工具箱 (Port 5001)",
            "周末锁价回测仪表盘",
            "信号生成 & 监控",
            "多策略回测引擎",
        ],
    },
    {
        "id": "wedata-analysis",
        "name": "WeData 数据分析",
        "name_en": "WeData Analysis Notebooks",
        "icon": "🔬",
        "port": None,
        "category": "data",
        "category_label": "数据分析",
        "description": "WeData 平台 Hive 大数据分析 Notebook 集 (加价/损益/流量/流动性等)",
        "data_format": "WeData Hive SQL",
        "entry": None,
        "dir": "wedata_analysis",
        "features": [
            "加价 BPS 分析 (markup_analysis)",
            "平台损益分析 (fx_platform_pnl)",
            "客户资金流 (fx_client_flow)",
            "日交易量 (fx_daily_volume)",
            "流动性监控 (liquidity_monitor)",
            "头寸暴露 (exposure_report)",
            "收入优化 (revenue_optimization)",
        ],
    },
    {
        "id": "soros-agent",
        "name": "索罗斯 FX Agent",
        "name_en": "George Soros FX Agent",
        "icon": "🦅",
        "port": 8901,
        "category": "agent",
        "category_label": "AI Agent",
        "description": "与传奇外汇交易大师索罗斯对话，探讨反射性理论、央行博弈、非对称押注等核心策略",
        "data_format": "对话交互",
        "entry": "app.py",
        "dir": "agents/soros",
        "features": [
            "反射性理论分析",
            "央行博弈策略",
            "非对称风险/回报",
            "1992 英镑狙击复盘",
            "实时市场观点",
        ],
    },
    {
        "id": "linhuiyin-agent",
        "name": "林徽因",
        "name_en": "Lin Huiyin — Architect & Poet",
        "icon": "🏛️",
        "port": 8902,
        "category": "agent",
        "category_label": "AI Agent",
        "description": "与中国第一位女建筑师、诗人林徽因对话，聊建筑哲学、诗歌创作、民国风华",
        "data_format": "对话交互",
        "entry": "app.py",
        "dir": "agents/linhuiyin",
        "features": [
            "建筑美学探讨",
            "古建筑考察故事",
            "诗歌创作与赏析",
            "宾大求学往事",
            "民国文化沙龙",
        ],
    },
    {
        "id": "financial-calendar",
        "name": "金融日历系统",
        "name_en": "Financial Calendar Dashboard",
        "icon": "📅",
        "port": 5173,
        "category": "quant",
        "category_label": "量化与策略",
        "description": "金融日历驱动的 PAMAS 点差拉宽 + ROMS 敞口平仓模拟，交互式可视化 Dashboard",
        "data_format": "经济日历事件 Excel / JSON",
        "entry": "run.py",
        "dir": "financial-calendar",
        "features": [
            "经济事件日历",
            "PAMAS Spread Widening",
            "ROMS 敞口平仓信号",
            "Pipeline 可视化",
            "时间线播放器",
            "手动覆盖模拟",
        ],
    },
]

# 子进程管理
_processes = {}


def _is_port_open(port):
    """检测端口是否在监听"""
    if port is None:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return False


# ═══ Pages ═══

@app.route('/')
def index():
    return send_file(str(BASE_DIR / 'portal.html'))


# ═══ API ═══

@app.route('/api/modules')
def api_modules():
    """返回所有模块信息 + 运行状态"""
    result = []
    for m in MODULES:
        info = {**m}
        info['running'] = _is_port_open(m['port'])
        info['url'] = f"http://localhost:{m['port']}" if m['port'] else None
        result.append(info)
    return jsonify({"modules": result})


@app.route('/api/launch/<module_id>', methods=['POST'])
def api_launch(module_id):
    """启动某个模块"""
    mod = next((m for m in MODULES if m['id'] == module_id), None)
    if not mod:
        return jsonify({"error": f"模块 '{module_id}' 不存在"}), 404

    if not mod.get('port'):
        return jsonify({"error": "该模块没有 Web 服务，无法启动"}), 400

    if _is_port_open(mod['port']):
        return jsonify({"status": "already_running", "url": f"http://localhost:{mod['port']}"})

    # 启动
    try:
        if mod.get('launch_script'):
            # 有根目录启动脚本
            cmd = [sys.executable, str(BASE_DIR / mod['launch_script'])]
        else:
            cmd = [sys.executable, str(BASE_DIR / mod['dir'] / mod['entry'])]

        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR / mod['dir']) if not mod.get('launch_script') else str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
        )
        _processes[module_id] = proc

        # 等几秒看看是否启动成功
        import time
        for _ in range(10):
            time.sleep(0.5)
            if _is_port_open(mod['port']):
                return jsonify({
                    "status": "started",
                    "url": f"http://localhost:{mod['port']}",
                    "pid": proc.pid,
                })
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode('utf-8', errors='replace')
                return jsonify({"error": f"启动失败: {stderr}"}), 500

        return jsonify({"status": "starting", "pid": proc.pid, "message": "正在启动中..."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stop/<module_id>', methods=['POST'])
def api_stop(module_id):
    """停止某个模块"""
    mod = next((m for m in MODULES if m['id'] == module_id), None)
    if not mod:
        return jsonify({"error": f"模块 '{module_id}' 不存在"}), 404

    # 1. 尝试停止由 Portal 管理的进程
    proc = _processes.get(module_id)
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=5)
        del _processes[module_id]
        return jsonify({"status": "stopped"})

    # 2. 如果进程不在管理列表中，通过端口强制停止
    if mod.get('port') and _is_port_open(mod['port']):
        import subprocess as sp
        try:
            # 用 netstat 找到监听该端口的进程 PID
            result = sp.run(
                f'netstat -ano | findstr ":{mod["port"]}.*LISTENING"',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5 and 'LISTENING' in line:
                    pid = parts[-1]
                    # 强制杀掉进程
                    sp.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    return jsonify({"status": "force_stopped", "pid": int(pid)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"status": "not_running"})


@app.route('/api/shutdown', methods=['POST'])
def api_shutdown():
    """关闭 Portal 服务"""
    # 先停掉所有由 Portal 管理的子进程
    for mid, proc in list(_processes.items()):
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except:
                proc.kill()
    _processes.clear()

    def _shutdown():
        import time
        time.sleep(0.5)
        os._exit(0)

    import threading
    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({"status": "shutting_down", "message": "Portal 正在关闭..."})


# ═══ 启动 ═══

if __name__ == '__main__':
    port = 8899
    print("=" * 60)
    print("  🏠 FX_SYSTEM Portal — 统一入口")
    print(f"  http://localhost:{port}")
    print("=" * 60)

    # 检测各模块状态
    for m in MODULES:
        status = "✅ 运行中" if _is_port_open(m['port']) else "⬚ 未启动" if m['port'] else "📓 Notebook"
        print(f"  {m['icon']} {m['name']:20s} {status}")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=False)
