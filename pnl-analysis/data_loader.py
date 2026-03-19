# -*- coding: utf-8 -*-
"""
data_loader.py - 损益明细数据加载与清洗
========================================
读取 data/ 下所有 PROFIT_LOSS_DETAIL_*.csv 文件，
清洗、计算衍生字段，返回可分析的 DataFrame。
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

# ---------- 常量 ----------
RATE_PRECISION = 1e8
AMT_PRECISION = 100  # 分 -> 元

# 需要转为数值的列
NUMERIC_COLS = [
    "期初余额", "期末余额", "期初垫资余额", "期末垫资余额",
    "当期非白名单流水汇总余额", "历史非白名单流水汇总余额",
    "折算CNY期初汇率", "折算CNY期末汇率", "折算CNY损益金额",
]


def load_csv(csv_path: str | Path) -> pd.DataFrame:
    """读取单个 CSV 并做基础清洗。"""
    df = pd.read_csv(csv_path, dtype={"商户号": str})
    df.dropna(how="all", inplace=True)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def calc_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """计算衍生字段：损益金额(元)、其中WX、FIT。"""
    df = df.copy()
    df["损益金额"] = df["折算CNY损益金额"] / AMT_PRECISION

    rate_diff = (df["折算CNY期末汇率"] - df["折算CNY期初汇率"]) / RATE_PRECISION
    non_whitelist_bal = df["当期非白名单流水汇总余额"] + df["历史非白名单流水汇总余额"]
    df["其中WX"] = (non_whitelist_bal * rate_diff) / AMT_PRECISION
    df["FIT"] = df["损益金额"] - df["其中WX"]

    # 期初/期末余额转元
    df["期初余额_元"] = df["期初余额"] / AMT_PRECISION
    df["期末余额_元"] = df["期末余额"] / AMT_PRECISION
    df["期初垫资余额_元"] = df["期初垫资余额"] / AMT_PRECISION
    df["期末垫资余额_元"] = df["期末垫资余额"] / AMT_PRECISION

    return df


def extract_period_label(filename: str) -> str:
    """从文件名提取日期，转换为易读月份标签。如 20260131 -> '2026年1月'"""
    m = re.search(r"(\d{4})(\d{2})\d{2}", filename)
    if m:
        year, month = m.group(1), int(m.group(2))
        return f"{year}年{month}月"
    return filename


def extract_date_str(filename: str) -> str:
    """从文件名提取日期字符串如 20260131。"""
    m = re.search(r"(\d{8})", filename)
    return m.group(1) if m else filename


def load_all_data(data_dir: str | Path) -> list[tuple[str, str, pd.DataFrame]]:
    """
    加载 data/ 目录下所有 PROFIT_LOSS_DETAIL_*.csv。
    
    Returns:
        [(period_label, date_str, df), ...]  按日期排序
    """
    data_dir = Path(data_dir)
    csv_files = sorted(data_dir.glob("PROFIT_LOSS_DETAIL_*.csv"))

    if not csv_files:
        return []

    results = []
    for csv_path in csv_files:
        label = extract_period_label(csv_path.name)
        date_str = extract_date_str(csv_path.name)
        df = load_csv(csv_path)
        df = calc_derived_fields(df)
        results.append((label, date_str, df))

    return results
