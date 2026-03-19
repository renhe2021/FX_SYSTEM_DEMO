# -*- coding: utf-8 -*-
"""
app.py - 损益分析工具
======================
上传 Excel/CSV → 自动分析 → 预览 → 下载生成的 Excel 报表
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd

from data_loader import load_csv, calc_derived_fields, extract_period_label, extract_date_str, load_all_data
from analysis_engine import run_all_analysis, monthly_comparison
from excel_export import export_analysis_to_excel, export_multi_period_excel

app = Flask(__name__, static_folder='.', static_url_path='/static')
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# ---------- 目录 ----------
BASE = Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
OUTPUT_DIR = BASE / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- 全局状态 ----------
# 支持多批次数据: { session_id: { periods: [...], analysis: {...}, files: [...] } }
_sessions = {}
_current_session = None


def _new_session_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_session(sid=None):
    if sid and sid in _sessions:
        return _sessions[sid]
    if _current_session and _current_session in _sessions:
        return _sessions[_current_session]
    return None


def _process_files(file_paths: list[Path]) -> str:
    """处理上传的文件，返回 session_id"""
    global _current_session

    sid = _new_session_id()
    periods = []
    analysis_cache = {}

    for fp in sorted(file_paths):
        label = extract_period_label(fp.name)
        date_str = extract_date_str(fp.name)

        if fp.suffix.lower() == '.csv':
            df = load_csv(fp)
        else:
            # 尝试读 Excel
            df = pd.read_excel(fp, dtype={"商户号": str})
            df.dropna(how="all", inplace=True)

        df = calc_derived_fields(df)
        periods.append((label, date_str, df))
        analysis_cache[label] = run_all_analysis(df)

    _sessions[sid] = {
        "periods": periods,
        "analysis": analysis_cache,
        "files": [fp.name for fp in file_paths],
        "created": datetime.now().isoformat(),
    }
    _current_session = sid
    return sid


import numpy as np


def _sanitize(obj):
    """递归转换 numpy 类型为 Python 原生类型，确保 JSON 可序列化。"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def _df_to_records(df):
    result = df.copy()
    for col in result.select_dtypes(include=["float64", "float32"]).columns:
        result[col] = result[col].round(2)
    return json.loads(result.to_json(orient="records", force_ascii=False))


# ═══════════════ 也支持从本地 data/ 预加载 ═══════════════

def _try_preload():
    """启动时如果 data/ 或 ddd/ 有数据，自动加载"""
    _local = BASE / "data"
    _source = BASE.parent / "ddd" / "20260310151934" / "data"

    data_dir = None
    if _local.exists() and any(_local.glob("*.csv")):
        data_dir = _local
    elif _source.exists() and any(_source.glob("*.csv")):
        data_dir = _source

    if data_dir:
        csv_files = sorted(data_dir.glob("PROFIT_LOSS_DETAIL_*.csv"))
        if csv_files:
            _process_files(csv_files)
            return True
    return False


# ═══════════════════ API ═══════════════════

@app.route("/")
def index():
    html_path = BASE / "dashboard.html"
    if html_path.exists():
        return send_file(str(html_path))
    return "<h1>PnL Analysis</h1><p>dashboard.html not found</p>"


# ── 上传 ──

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """上传一个或多个 CSV/Excel 文件"""
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({"error": "没有选择文件"}), 400

    files = request.files.getlist('files') or request.files.getlist('file')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "没有选择文件"}), 400

    saved = []
    for f in files:
        if f.filename and (f.filename.endswith('.csv') or f.filename.endswith('.xlsx') or f.filename.endswith('.xls')):
            safe_name = f.filename.replace(' ', '_')
            save_path = UPLOAD_DIR / safe_name
            f.save(str(save_path))
            saved.append(save_path)

    if not saved:
        return jsonify({"error": "没有有效的 CSV/Excel 文件"}), 400

    try:
        sid = _process_files(saved)
        sess = _sessions[sid]
        return jsonify({
            "status": "ok",
            "session_id": sid,
            "files": [p.name for p in saved],
            "periods": [
                {"label": label, "date_str": ds, "records": len(df)}
                for label, ds, df in sess["periods"]
            ],
        })
    except Exception as e:
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


# ── 已上传文件管理 ──

@app.route("/api/sessions")
def api_sessions():
    """列出所有已加载的会话"""
    result = []
    for sid, sess in _sessions.items():
        result.append({
            "session_id": sid,
            "files": sess["files"],
            "periods": [
                {"label": label, "date_str": ds, "records": len(df)}
                for label, ds, df in sess["periods"]
            ],
            "created": sess["created"],
            "current": sid == _current_session,
        })
    return jsonify({"sessions": result})


@app.route("/api/switch/<session_id>", methods=["POST"])
def api_switch(session_id):
    global _current_session
    if session_id in _sessions:
        _current_session = session_id
        return jsonify({"status": "ok", "session_id": session_id})
    return jsonify({"error": "session not found"}), 404


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """清除上传的文件和所有会话"""
    global _sessions, _current_session
    _sessions = {}
    _current_session = None
    # 清理上传目录
    if UPLOAD_DIR.exists():
        shutil.rmtree(str(UPLOAD_DIR))
        UPLOAD_DIR.mkdir(exist_ok=True)
    return jsonify({"status": "ok"})


# ── 数据查询 ──

@app.route("/api/periods")
def api_periods():
    sess = _get_session()
    if not sess:
        return jsonify({"periods": []})
    periods = [{"label": label, "date_str": ds, "records": len(df)}
               for label, ds, df in sess["periods"]]
    return jsonify({"periods": periods})


@app.route("/api/overview")
def api_overview():
    sess = _get_session()
    if not sess:
        return jsonify({"error": "没有数据，请先上传文件"}), 404

    period = request.args.get("period", "all")

    if period == "all":
        all_dfs = [df for _, _, df in sess["periods"]]
        combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else None
        if combined is None:
            return jsonify({"error": "no data"}), 404
        results = run_all_analysis(combined)
    elif period in sess["analysis"]:
        results = sess["analysis"][period]
    else:
        return jsonify({"error": f"period '{period}' not found"}), 404

    return jsonify({"overview": _sanitize(results["overview"])})


@app.route("/api/summary/<dimension>")
def api_summary(dimension):
    sess = _get_session()
    if not sess:
        return jsonify({"error": "没有数据，请先上传文件"}), 404

    period = request.args.get("period", "all")

    if period == "all":
        all_dfs = [df for _, _, df in sess["periods"]]
        combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else None
        if combined is None:
            return jsonify({"error": "no data"}), 404
        results = run_all_analysis(combined)
    elif period in sess["analysis"]:
        results = sess["analysis"][period]
    else:
        return jsonify({"error": f"period '{period}' not found"}), 404

    key = f"by_{dimension}" if dimension != "detail" else "detail"
    if key not in results:
        return jsonify({"error": f"dimension '{dimension}' not found"}), 404

    return jsonify({
        "dimension": dimension,
        "period": period,
        "columns": list(results[key].columns),
        "data": _df_to_records(results[key]),
    })


@app.route("/api/comparison")
def api_comparison():
    sess = _get_session()
    if not sess:
        return jsonify({"error": "没有数据"}), 404
    if len(sess["periods"]) < 2:
        return jsonify({"error": "至少需要 2 个月份数据才能对比"}), 400

    dim = request.args.get("dimension", "损益实际归属主体")
    period_dfs = [(label, df) for label, _, df in sess["periods"]]
    comp_df = monthly_comparison(period_dfs, dim)

    return jsonify({
        "dimension": dim,
        "columns": list(comp_df.columns),
        "data": _df_to_records(comp_df),
    })


@app.route("/api/waterfall")
def api_waterfall():
    sess = _get_session()
    if not sess:
        return jsonify({"error": "没有数据"}), 404

    period = request.args.get("period", "all")
    dim = request.args.get("dimension", "entity")

    if period == "all":
        all_dfs = [df for _, _, df in sess["periods"]]
        combined = pd.concat(all_dfs, ignore_index=True)
        results = run_all_analysis(combined)
    elif period in sess["analysis"]:
        results = sess["analysis"][period]
    else:
        return jsonify({"error": "period not found"}), 404

    key = f"by_{dim}"
    if key not in results:
        return jsonify({"error": f"dimension '{dim}' not found"}), 404

    df = results[key]
    df_clean = df[~df.iloc[:, 0].str.contains("合计|小计|汇总", na=False)]

    return jsonify({
        "labels": df_clean.iloc[:, 0].tolist(),
        "pnl": df_clean["损益金额"].round(2).tolist(),
        "wx": df_clean["其中WX"].round(2).tolist(),
        "fit": df_clean["FIT"].round(2).tolist(),
    })


# ── 导出 Excel ──

@app.route("/api/export")
def api_export():
    """生成并下载 Excel 报表"""
    sess = _get_session()
    if not sess:
        return jsonify({"error": "没有数据，请先上传文件"}), 404

    period = request.args.get("period", "all")

    if period != "all" and period in sess["analysis"]:
        results = sess["analysis"][period]
        filename = f"损益报表_{period}.xlsx"
        output_path = OUTPUT_DIR / filename
        export_analysis_to_excel(results, period, output_path)
    else:
        period_results = [(label, sess["analysis"][label])
                          for label in sess["analysis"]]

        all_dfs = [df for _, _, df in sess["periods"]]
        combined_results = run_all_analysis(pd.concat(all_dfs, ignore_index=True)) if all_dfs else None

        comparison_dfs = None
        if len(sess["periods"]) >= 2:
            period_dfs = [(label, df) for label, _, df in sess["periods"]]
            comparison_dfs = {
                "按渠道": monthly_comparison(period_dfs, "损益实际归属主体"),
                "按业务": monthly_comparison(period_dfs, "所属业务"),
                "按币种": monthly_comparison(period_dfs, "原币种"),
            }

        date_strs = [ds for _, ds, _ in sess["periods"]]
        if len(date_strs) > 1:
            filename = f"损益汇总报表_{date_strs[0]}_{date_strs[-1]}.xlsx"
        else:
            filename = f"损益汇总报表_{date_strs[0]}.xlsx"
        output_path = OUTPUT_DIR / filename

        export_multi_period_excel(period_results, combined_results, comparison_dfs, output_path)

    return send_file(
        str(output_path),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ═══════════════════ 启动 ═══════════════════

def create_app():
    return app


if __name__ == "__main__":
    print("=" * 60)
    print("  📊 PnL Analysis — 损益分析工具")
    print("  http://localhost:5003")
    print("=" * 60)

    preloaded = _try_preload()
    if preloaded:
        sess = _get_session()
        print(f"\n📂 预加载 {len(sess['periods'])} 个月份:")
        for label, ds, df in sess["periods"]:
            print(f"   {label}: {len(df)} 条记录")
    else:
        print("\n📂 暂无数据，请通过网页上传 CSV/Excel 文件")

    print("=" * 60)
    app.run(host="0.0.0.0", port=5005, debug=True)
