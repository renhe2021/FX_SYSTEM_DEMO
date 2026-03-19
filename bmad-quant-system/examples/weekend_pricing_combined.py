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
from datetime import datetime, timedelta

# 设置控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


# ============================================================
# 配置参数
# ============================================================

# 交易量
USDCNH_TRADE_SIZE = 60_000_000  # 6000万美元
USDJPY_TRADE_SIZE = 4_000_000_000  # 40亿日元

# 汇率 (用于换算成人民币)
# USDJPY PnL 以日元计价，需要转换为人民币
# 假设 JPYCNH ≈ 0.048 (1日元 ≈ 0.048人民币)
JPYCNH_RATE = 0.048

# 数据文件路径
DATA_DIR = ROOT / "output"


def load_data(symbol: str, filename: str = None):
    """
    加载数据文件
    
    Args:
        symbol: 货币对代码
        filename: 指定文件名（可选）
    """
    if filename:
        filepath = DATA_DIR / filename
        if filepath.exists():
            print(f"  加载文件: {filename}")
            df = pd.read_excel(filepath, parse_dates=['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
        else:
            print(f"  文件不存在: {filename}")
            return None
    
    # 查找匹配的文件 - 优先选择包含完整数据的 1s 文件
    pattern_1s = f"{symbol.replace(' ', '_')}*1s*.xlsx"
    files_1s = list(DATA_DIR.glob(pattern_1s))
    
    if files_1s:
        # 选择最新的 1s 文件
        latest_file = max(files_1s, key=lambda x: x.stat().st_mtime)
    else:
        # 否则选择任意匹配文件
        pattern = f"{symbol.replace(' ', '_')}*.xlsx"
        files = list(DATA_DIR.glob(pattern))
        if not files:
            print(f"  未找到 {symbol} 的数据文件")
            return None
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
    
    print(f"  加载文件: {latest_file.name}")
    
    try:
        df = pd.read_excel(latest_file, parse_dates=['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"  加载失败: {e}")
        # 尝试其他文件
        for f in sorted(files_1s if files_1s else [], key=lambda x: x.stat().st_mtime, reverse=True)[1:3]:
            try:
                print(f"  尝试加载: {f.name}")
                df = pd.read_excel(f, parse_dates=['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
            except:
                continue
        return None


def analyze_weekend_pricing(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    分析每个周末的报价差异
    
    原方案: 北京时间 周六 02:00-06:00 取 max(ASK)
    新方案: 北京时间 周六 00:00-06:00 取 max(ASK)
    """
    if data is None or data.empty:
        return None
    
    # 确保 ask 列存在
    if 'ask' not in data.columns and 'ask_high' not in data.columns:
        print(f"  Warning: no 'ask' column in {symbol} data")
        return None
    
    # 使用 ask_high 如果存在（更准确）
    ask_col = 'ask_high' if 'ask_high' in data.columns else 'ask'
    
    # 筛选周六数据 (weekday=5)
    saturday_data = data[data.index.dayofweek == 5]
    
    if saturday_data.empty:
        print(f"  Warning: no Saturday data for {symbol}")
        return None
    
    # 获取所有周六日期
    saturday_dates = saturday_data.index.date
    unique_saturdays = sorted(set(saturday_dates))
    
    print(f"  找到 {len(unique_saturdays)} 个周六")
    
    results = []
    for sat_date in unique_saturdays:
        # 筛选该周六的数据
        day_data = saturday_data[saturday_data.index.date == sat_date]
        
        # 原方案: 02:00-05:59 (06:00之前)
        original_window = day_data.between_time("02:00", "05:59")
        
        # 新方案: 00:00-05:59
        new_window = day_data.between_time("00:00", "05:59")
        
        if original_window.empty or new_window.empty:
            continue
        
        # 取最大值
        original_max = original_window[ask_col].max()
        new_max = new_window[ask_col].max()
        
        # 找到最大值发生的时间
        original_max_idx = original_window[original_window[ask_col] == original_max].index
        new_max_idx = new_window[new_window[ask_col] == new_max].index
        
        if len(original_max_idx) == 0 or len(new_max_idx) == 0:
            continue
            
        original_max_time = original_max_idx[0].strftime('%H:%M:%S')
        new_max_time = new_max_idx[0].strftime('%H:%M:%S')
        
        results.append({
            'date': sat_date,
            'original_quote': original_max,
            'original_max_time': original_max_time,
            'new_quote': new_max,
            'new_max_time': new_max_time,
            'quote_diff': new_max - original_max
        })
    
    if not results:
        return None
    
    return pd.DataFrame(results)


def download_usdjpy_data():
    """
    使用 Bloomberg API 下载 USDJPY 数据
    """
    from quant_system.tools.bbg_wrapper import BloombergWrapper
    
    print("\n尝试从 Bloomberg 下载 USDJPY 数据...")
    
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("  Bloomberg 连接失败")
        return None
    
    symbol = "USDJPY Curncy"
    
    # 下载最近 140 天的 1 分钟数据（API 限制）
    # 但周六凌晨没有数据，所以这里只是尝试
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"  下载时间范围: {start_date.date()} ~ {end_date.date()}")
    
    # 尝试获取 bar 数据
    df = bbg.get_bid_ask_bars(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        resample="1min"
    )
    
    bbg.disconnect()
    
    if df is not None and not df.empty:
        # 保存数据
        output_file = DATA_DIR / f"USDJPY_Curncy_bidask_1min_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file)
        print(f"  数据已保存: {output_file.name}")
        return df
    
    return None


def main():
    """主函数"""
    print("=" * 70)
    print("周末报价方案对比分析 - USDCNH + USDJPY")
    print("=" * 70)
    
    print(f"\n交易参数:")
    print(f"  USDCNH 每周交易量: ${USDCNH_TRADE_SIZE:,.0f} ({USDCNH_TRADE_SIZE/1e6:.0f}M USD)")
    print(f"  USDJPY 每周交易量: ¥{USDJPY_TRADE_SIZE:,.0f} ({USDJPY_TRADE_SIZE/1e9:.0f}B JPY)")
    print(f"  JPYCNH 汇率: {JPYCNH_RATE}")
    
    print(f"\n报价方案:")
    print(f"  原方案: 北京时间 周六 02:00-06:00 取 max(ASK)")
    print(f"  新方案: 北京时间 周六 00:00-06:00 取 max(ASK)")
    
    # ============================================================
    # 1. 分析 USDCNH
    # ============================================================
    print(f"\n" + "-" * 70)
    print("1. USDCNH 分析")
    print("-" * 70)
    
    # 使用包含完整周六数据的文件
    usdcnh_data = load_data("USDCNH_Curncy", "USDCNH_Curncy_bidask_1s_20260116_144224.xlsx")
    usdcnh_results = None
    
    if usdcnh_data is not None:
        usdcnh_results = analyze_weekend_pricing(usdcnh_data, "USDCNH")
        
        if usdcnh_results is not None:
            # 计算 PnL (单位: 人民币)
            # quote_diff 是汇率差异，乘以 USD 交易量直接得到 CNY
            usdcnh_results['pnl_cny'] = usdcnh_results['quote_diff'] * USDCNH_TRADE_SIZE
            usdcnh_results['quote_diff_pips'] = usdcnh_results['quote_diff'] * 10000
            
            print(f"\n  USDCNH 分析结果:")
            print(f"    周末数量: {len(usdcnh_results)}")
            print(f"    新方案更优: {(usdcnh_results['quote_diff'] > 0).sum()} 次")
            print(f"    平均差异: {usdcnh_results['quote_diff_pips'].mean():.2f} pips")
            print(f"    最大差异: {usdcnh_results['quote_diff_pips'].max():.2f} pips")
            print(f"    累计PnL增量: ¥{usdcnh_results['pnl_cny'].sum():,.0f}")
    
    # ============================================================
    # 2. 分析 USDJPY
    # ============================================================
    print(f"\n" + "-" * 70)
    print("2. USDJPY 分析")
    print("-" * 70)
    
    # 先尝试加载本地数据
    usdjpy_data = load_data("USDJPY_Curncy")
    
    # 如果没有本地数据，尝试从 Bloomberg 下载
    if usdjpy_data is None:
        print("  本地无 USDJPY 数据，尝试从 Bloomberg 下载...")
        usdjpy_data = download_usdjpy_data()
    
    usdjpy_results = None
    
    if usdjpy_data is not None:
        usdjpy_results = analyze_weekend_pricing(usdjpy_data, "USDJPY")
        
        if usdjpy_results is not None:
            # 计算 PnL
            # USDJPY 报价: 1 USD = X JPY
            # 如果报价提高，对于卖 JPY 买 USD 的交易，收益增加
            # PnL (JPY) = quote_diff * (USDJPY_TRADE_SIZE / 原报价)
            # 但更简单的方式：报价差异 * 交易量 / 100 (因为 USDJPY 报价约 150)
            # 实际上对于做市商: PnL = quote_diff * notional_in_base_ccy
            # 这里 40亿日元 做市，报价提高 0.01 (1 pip)
            # PnL (JPY) = 40亿 * 0.01 / 150 ≈ 26.67万 JPY
            
            # 简化计算: quote_diff * (USDJPY_TRADE_SIZE / avg_quote)
            avg_quote = usdjpy_results['original_quote'].mean()
            usdjpy_results['pnl_jpy'] = usdjpy_results['quote_diff'] * (USDJPY_TRADE_SIZE / avg_quote)
            usdjpy_results['pnl_cny'] = usdjpy_results['pnl_jpy'] * JPYCNH_RATE
            usdjpy_results['quote_diff_pips'] = usdjpy_results['quote_diff'] * 100  # USDJPY 1 pip = 0.01
            
            print(f"\n  USDJPY 分析结果:")
            print(f"    周末数量: {len(usdjpy_results)}")
            print(f"    新方案更优: {(usdjpy_results['quote_diff'] > 0).sum()} 次")
            print(f"    平均差异: {usdjpy_results['quote_diff_pips'].mean():.2f} pips")
            print(f"    最大差异: {usdjpy_results['quote_diff_pips'].max():.2f} pips")
            print(f"    累计PnL增量 (JPY): ¥{usdjpy_results['pnl_jpy'].sum():,.0f}")
            print(f"    累计PnL增量 (CNY): ¥{usdjpy_results['pnl_cny'].sum():,.0f}")
    else:
        print("  无法获取 USDJPY 数据")
    
    # ============================================================
    # 3. 汇总结果
    # ============================================================
    print(f"\n" + "=" * 70)
    print("汇总结果 (PnL 单位: 人民币)")
    print("=" * 70)
    
    total_pnl_cny = 0
    total_weekends = 0
    
    if usdcnh_results is not None:
        usdcnh_pnl = usdcnh_results['pnl_cny'].sum()
        total_pnl_cny += usdcnh_pnl
        total_weekends = max(total_weekends, len(usdcnh_results))
        print(f"\n  USDCNH:")
        print(f"    周末数: {len(usdcnh_results)}")
        print(f"    累计PnL增量: ¥{usdcnh_pnl:,.2f}")
        print(f"    平均每周: ¥{usdcnh_pnl/len(usdcnh_results):,.2f}")
    
    if usdjpy_results is not None:
        usdjpy_pnl = usdjpy_results['pnl_cny'].sum()
        total_pnl_cny += usdjpy_pnl
        total_weekends = max(total_weekends, len(usdjpy_results))
        print(f"\n  USDJPY:")
        print(f"    周末数: {len(usdjpy_results)}")
        print(f"    累计PnL增量: ¥{usdjpy_pnl:,.2f}")
        print(f"    平均每周: ¥{usdjpy_pnl/len(usdjpy_results):,.2f}")
    
    print(f"\n  " + "-" * 50)
    print(f"  总计:")
    print(f"    累计PnL增量: ¥{total_pnl_cny:,.2f}")
    
    if total_weekends > 0:
        avg_weekly = total_pnl_cny / total_weekends
        annual_estimate = avg_weekly * 52
        print(f"    平均每周增量: ¥{avg_weekly:,.2f}")
        print(f"    年化PnL估算: ¥{annual_estimate:,.2f}")
    
    # ============================================================
    # 4. 导出结果
    # ============================================================
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"weekend_pricing_combined_{timestamp}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # USDCNH 详细结果
        if usdcnh_results is not None:
            usdcnh_results.to_excel(writer, sheet_name='USDCNH详细', index=False)
        
        # USDJPY 详细结果
        if usdjpy_results is not None:
            usdjpy_results.to_excel(writer, sheet_name='USDJPY详细', index=False)
        
        # 汇总
        summary_data = []
        
        if usdcnh_results is not None:
            summary_data.append({
                '货币对': 'USDCNH',
                '交易量': f'{USDCNH_TRADE_SIZE/1e6:.0f}M USD',
                '周末数': len(usdcnh_results),
                '新方案更优次数': (usdcnh_results['quote_diff'] > 0).sum(),
                '平均差异(pips)': f"{usdcnh_results['quote_diff_pips'].mean():.2f}",
                '最大差异(pips)': f"{usdcnh_results['quote_diff_pips'].max():.2f}",
                '累计PnL增量(CNY)': f"¥{usdcnh_results['pnl_cny'].sum():,.0f}",
                '平均每周PnL(CNY)': f"¥{usdcnh_results['pnl_cny'].mean():,.0f}"
            })
        
        if usdjpy_results is not None:
            summary_data.append({
                '货币对': 'USDJPY',
                '交易量': f'{USDJPY_TRADE_SIZE/1e9:.0f}B JPY',
                '周末数': len(usdjpy_results),
                '新方案更优次数': (usdjpy_results['quote_diff'] > 0).sum(),
                '平均差异(pips)': f"{usdjpy_results['quote_diff_pips'].mean():.2f}",
                '最大差异(pips)': f"{usdjpy_results['quote_diff_pips'].max():.2f}",
                '累计PnL增量(CNY)': f"¥{usdjpy_results['pnl_cny'].sum():,.0f}",
                '平均每周PnL(CNY)': f"¥{usdjpy_results['pnl_cny'].mean():,.0f}"
            })
        
        if summary_data:
            summary_data.append({
                '货币对': '合计',
                '交易量': '-',
                '周末数': total_weekends,
                '新方案更优次数': '-',
                '平均差异(pips)': '-',
                '最大差异(pips)': '-',
                '累计PnL增量(CNY)': f"¥{total_pnl_cny:,.0f}",
                '平均每周PnL(CNY)': f"¥{total_pnl_cny/total_weekends:,.0f}" if total_weekends > 0 else '-'
            })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='汇总', index=False)
    
    print(f"\n结果已导出: {output_file}")
    
    print("\n" + "=" * 70)
    print("分析完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
