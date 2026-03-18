#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
周末报价方案对比分析 - USDCNH + USDJPY
===============================================================

分析两种报价方案的PnL差异：
- 原方案: 北京时间 周六 02:00-06:00 取 max(ASK)
- 新方案: 北京时间 周六 00:00-06:00 取 max(ASK)

货币对:
- USDCNH: 每周交易量 6000万美元
- USDJPY: 每周交易量 40亿日元

最终PnL用人民币表示
"""

import sys
import os
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np

# ============================================================
# 配置参数
# ============================================================
USDCNH_TRADE_SIZE = 60_000_000  # 6000万美元
USDJPY_TRADE_SIZE = 4_000_000_000  # 40亿日元
JPYCNH_RATE = 0.048  # 1日元 ≈ 0.048人民币

DATA_DIR = ROOT / "output"

# 数据文件
USDCNH_FILE = "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx"
USDJPY_FILE = "USDJPY_Curncy_bidask_1min_20260130_094644.xlsx"  # 新下载的数据


def analyze_weekend_pricing(data, symbol):
    """分析每个周末的报价差异"""
    if data is None or data.empty:
        return None
    
    ask_col = 'ask_high' if 'ask_high' in data.columns else 'ask'
    if ask_col not in data.columns:
        return None
    
    saturday_data = data[data.index.dayofweek == 5]
    if saturday_data.empty:
        return None
    
    unique_saturdays = sorted(set(saturday_data.index.date))
    
    results = []
    for sat_date in unique_saturdays:
        day_data = saturday_data[saturday_data.index.date == sat_date]
        original_window = day_data.between_time("02:00", "05:59")
        new_window = day_data.between_time("00:00", "05:59")
        
        if original_window.empty or new_window.empty:
            continue
        
        original_max = original_window[ask_col].max()
        new_max = new_window[ask_col].max()
        
        original_max_idx = original_window[original_window[ask_col] == original_max].index
        new_max_idx = new_window[new_window[ask_col] == new_max].index
        
        if len(original_max_idx) == 0 or len(new_max_idx) == 0:
            continue
        
        results.append({
            'date': sat_date,
            'original_quote': original_max,
            'original_max_time': original_max_idx[0].strftime('%H:%M:%S'),
            'new_quote': new_max,
            'new_max_time': new_max_idx[0].strftime('%H:%M:%S'),
            'quote_diff': new_max - original_max
        })
    
    return pd.DataFrame(results) if results else None


def main():
    print("=" * 70)
    print("周末报价方案对比分析 - USDCNH + USDJPY")
    print("=" * 70)
    
    print(f"\n交易参数:")
    print(f"  USDCNH 每周交易量: {USDCNH_TRADE_SIZE/1e6:.0f}M USD")
    print(f"  USDJPY 每周交易量: {USDJPY_TRADE_SIZE/1e9:.0f}B JPY")
    print(f"  JPYCNH 汇率: {JPYCNH_RATE}")
    
    print(f"\n报价方案:")
    print(f"  原方案: 北京时间 周六 02:00-06:00 取 max(ASK)")
    print(f"  新方案: 北京时间 周六 00:00-06:00 取 max(ASK)")
    
    # ============================================================
    # 1. USDCNH
    # ============================================================
    print(f"\n" + "-" * 70)
    print("1. USDCNH 分析")
    print("-" * 70)
    
    usdcnh_file = DATA_DIR / USDCNH_FILE
    usdcnh_results = None
    
    if usdcnh_file.exists():
        print(f"  加载: {USDCNH_FILE}")
        usdcnh_data = pd.read_excel(usdcnh_file, parse_dates=['timestamp'])
        usdcnh_data.set_index('timestamp', inplace=True)
        
        usdcnh_results = analyze_weekend_pricing(usdcnh_data, "USDCNH")
        
        if usdcnh_results is not None:
            # PnL (CNY) = quote_diff * USD_notional
            usdcnh_results['pnl_cny'] = usdcnh_results['quote_diff'] * USDCNH_TRADE_SIZE
            usdcnh_results['quote_diff_pips'] = usdcnh_results['quote_diff'] * 10000
            
            print(f"\n  结果:")
            print(f"    周末数: {len(usdcnh_results)}")
            print(f"    新方案更优: {(usdcnh_results['quote_diff'] > 0).sum()} 次")
            print(f"    平均差异: {usdcnh_results['quote_diff_pips'].mean():.2f} pips")
            print(f"    最大差异: {usdcnh_results['quote_diff_pips'].max():.2f} pips")
            print(f"    累计PnL增量: ¥{usdcnh_results['pnl_cny'].sum():,.0f}")
    else:
        print(f"  文件不存在: {USDCNH_FILE}")
    
    # ============================================================
    # 2. USDJPY (需要数据)
    # ============================================================
    print(f"\n" + "-" * 70)
    print("2. USDJPY 分析")
    print("-" * 70)
    
    usdjpy_results = None
    
    if USDJPY_FILE:
        usdjpy_file = DATA_DIR / USDJPY_FILE
        if usdjpy_file.exists():
            print(f"  加载: {USDJPY_FILE}")
            usdjpy_data = pd.read_excel(usdjpy_file, parse_dates=['timestamp'])
            usdjpy_data.set_index('timestamp', inplace=True)
            
            usdjpy_results = analyze_weekend_pricing(usdjpy_data, "USDJPY")
            
            if usdjpy_results is not None:
                avg_quote = usdjpy_results['original_quote'].mean()
                usdjpy_results['pnl_jpy'] = usdjpy_results['quote_diff'] * (USDJPY_TRADE_SIZE / avg_quote)
                usdjpy_results['pnl_cny'] = usdjpy_results['pnl_jpy'] * JPYCNH_RATE
                usdjpy_results['quote_diff_pips'] = usdjpy_results['quote_diff'] * 100
                
                print(f"\n  结果:")
                print(f"    周末数: {len(usdjpy_results)}")
                print(f"    新方案更优: {(usdjpy_results['quote_diff'] > 0).sum()} 次")
                print(f"    累计PnL增量: ¥{usdjpy_results['pnl_cny'].sum():,.0f}")
    else:
        print("  暂无 USDJPY 数据文件")
        print("  请提供 USDJPY 的 bid/ask 数据文件")
    
    # ============================================================
    # 3. 汇总
    # ============================================================
    print(f"\n" + "=" * 70)
    print("汇总结果 (PnL 单位: 人民币)")
    print("=" * 70)
    
    total_pnl = 0
    total_weeks = 0
    
    if usdcnh_results is not None:
        pnl = usdcnh_results['pnl_cny'].sum()
        total_pnl += pnl
        total_weeks = len(usdcnh_results)
        print(f"\n  USDCNH: ¥{pnl:,.0f} (周末数: {len(usdcnh_results)})")
    
    if usdjpy_results is not None:
        pnl = usdjpy_results['pnl_cny'].sum()
        total_pnl += pnl
        print(f"  USDJPY: ¥{pnl:,.0f} (周末数: {len(usdjpy_results)})")
    
    print(f"\n  " + "-" * 40)
    print(f"  累计PnL增量: ¥{total_pnl:,.0f}")
    
    if total_weeks > 0:
        avg_weekly = total_pnl / total_weeks
        annual = avg_weekly * 52
        print(f"  平均每周:    ¥{avg_weekly:,.0f}")
        print(f"  年化估算:    ¥{annual:,.0f}")
    
    # 导出
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = DATA_DIR / f"weekend_pricing_combined_{ts}.xlsx"
    
    with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
        if usdcnh_results is not None:
            usdcnh_results.to_excel(writer, sheet_name='USDCNH', index=False)
        if usdjpy_results is not None:
            usdjpy_results.to_excel(writer, sheet_name='USDJPY', index=False)
    
    print(f"\n结果已导出: {out_file.name}")


if __name__ == "__main__":
    main()
