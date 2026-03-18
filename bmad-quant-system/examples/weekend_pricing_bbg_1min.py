#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
周末报价方案对比分析 - 使用 Bloomberg API 下载数据
===============================================================

策略: 使用 IntradayBarRequest 分段下载每个周末的数据
- Bloomberg API 对 intraday 数据有时间限制，通常只支持最近 140 天
- 使用 1 分钟 Bar 数据 (因为秒级 bar 可能不被支持)

数据: USDCNH Curncy 的 ASK Bar 数据
时间: 尽可能多的周末数据

报价方案对比:
- 原方案: 周六 02:00-06:00 取 max(ASK)
- 新方案: 周六 00:00-06:00 取 max(ASK)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

# 设置控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


def get_friday_saturdays(start_date: datetime, end_date: datetime) -> list:
    """
    获取时间范围内所有周五到周六的日期对
    返回: [(周五日期, 周六日期), ...]
    """
    fridays = []
    current = start_date
    
    while current <= end_date:
        if current.weekday() == 4:  # 周五
            friday = current.date()
            saturday = (current + timedelta(days=1)).date()
            fridays.append((friday, saturday))
        current += timedelta(days=1)
    
    return fridays


def download_weekend_data_bars(bbg, symbol: str, friday, saturday) -> pd.DataFrame:
    """
    下载单个周末的 Bar 数据
    时间范围: 周五 22:00 到 周六 06:00 (北京时间)
    
    使用 1 分钟 Bar 请求 BID 和 ASK 数据
    """
    # 下载时间范围: 周五 22:00 到 周六 06:00
    start_dt = datetime.combine(friday, datetime.strptime("22:00", "%H:%M").time())
    end_dt = datetime.combine(saturday, datetime.strptime("06:00", "%H:%M").time())
    
    print(f"  Downloading: {start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}")
    
    # 使用 get_bid_ask_bars 获取 1 分钟间隔的数据
    df = bbg.get_bid_ask_bars(
        symbol=symbol,
        start_date=start_dt,
        end_date=end_dt,
        resample="1min"  # 使用 1 分钟
    )
    
    return df


def analyze_weekend_pricing(data: pd.DataFrame, saturday_date) -> dict:
    """
    分析单个周末的报价
    
    原方案: 周六 02:00-06:00 max(ASK)
    新方案: 周六 00:00-06:00 max(ASK)
    """
    if data is None or data.empty:
        return None
    
    # 确保 ask 列存在
    if 'ask' not in data.columns:
        print(f"  Warning: no 'ask' column in data")
        return None
    
    # 如果有 ask_high 列，使用它（更准确）
    if 'ask_high' in data.columns:
        ask_col = 'ask_high'
    else:
        ask_col = 'ask'
    
    # 筛选周六的数据
    saturday_data = data[data.index.date == saturday_date]
    
    if saturday_data.empty:
        print(f"  Warning: no data for Saturday {saturday_date}")
        return None
    
    # 原方案: 02:00-05:59
    original_window = saturday_data.between_time("02:00", "05:59")
    
    # 新方案: 00:00-05:59
    new_window = saturday_data.between_time("00:00", "05:59")
    
    if original_window.empty or new_window.empty:
        print(f"  Warning: insufficient data for {saturday_date}")
        return None
    
    # 取最大值
    original_max = original_window[ask_col].max()
    new_max = new_window[ask_col].max()
    
    # 找到最大值发生的时间
    original_max_time = original_window[original_window[ask_col] == original_max].index[0]
    new_max_time = new_window[new_window[ask_col] == new_max].index[0]
    
    return {
        'date': saturday_date,
        'original_quote': original_max,
        'original_max_time': original_max_time.strftime('%H:%M:%S'),
        'new_quote': new_max,
        'new_max_time': new_max_time.strftime('%H:%M:%S'),
        'quote_diff': new_max - original_max,
        'original_data_points': len(original_window),
        'new_data_points': len(new_window)
    }


def run_analysis_with_bbg():
    """
    使用 Bloomberg API 下载数据并分析
    """
    from quant_system.tools.bbg_wrapper import BloombergWrapper
    
    print("=" * 60)
    print("周末报价方案对比分析 - Bloomberg 1分钟 Bar 数据")
    print("=" * 60)
    
    # 初始化 Bloomberg
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("Bloomberg 连接失败！请确保 Bloomberg Terminal 正在运行")
        return None
    
    symbol = "USDCNH Curncy"
    trade_size = 50_000_000  # 5000万美元
    
    # Bloomberg Intraday 数据通常限制在 140 天内
    end_date = datetime.now()
    start_date = end_date - timedelta(days=140)
    
    print(f"\n分析参数:")
    print(f"  - 品种: {symbol}")
    print(f"  - 交易量: {trade_size:,.0f} USD")
    print(f"  - 时间范围: {start_date.date()} ~ {end_date.date()} (API限制140天)")
    print(f"  - 数据间隔: 1分钟 Bar")
    
    # 获取所有周五-周六日期对
    weekends = get_friday_saturdays(start_date, end_date)
    print(f"  - 周末数量: {len(weekends)}")
    
    # 收集所有周末的分析结果
    results = []
    all_data = []
    
    print(f"\n开始下载数据...")
    for i, (friday, saturday) in enumerate(weekends):
        print(f"\n[{i+1}/{len(weekends)}] 处理周末: {friday} (周五) ~ {saturday} (周六)")
        
        try:
            # 下载数据
            data = download_weekend_data_bars(bbg, symbol, friday, saturday)
            
            if data is not None and not data.empty:
                # 添加日期标记
                data['weekend'] = str(saturday)
                all_data.append(data.copy())
                
                # 分析
                result = analyze_weekend_pricing(data, saturday)
                if result:
                    results.append(result)
                    print(f"  Original: {result['original_quote']:.4f} @ {result['original_max_time']}")
                    print(f"  New:      {result['new_quote']:.4f} @ {result['new_max_time']}")
                    diff_pips = result['quote_diff'] * 10000
                    if diff_pips > 0:
                        print(f"  Diff:     +{diff_pips:.2f} pips (NEW IS BETTER!)")
                    else:
                        print(f"  Diff:     {diff_pips:.2f} pips")
            else:
                print(f"  No data available")
                
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # 暂停避免请求过快
        time.sleep(0.5)
    
    # 断开连接
    bbg.disconnect()
    
    if not results:
        print("\n没有有效的分析结果！")
        return None
    
    # 转换为 DataFrame
    results_df = pd.DataFrame(results)
    
    # 计算统计
    results_df['quote_diff_pips'] = results_df['quote_diff'] * 10000
    results_df['pnl_diff'] = results_df['quote_diff'] * trade_size
    
    print("\n" + "=" * 60)
    print("分析结果汇总")
    print("=" * 60)
    
    total_weekends = len(results_df)
    better_count = (results_df['quote_diff'] > 0).sum()
    same_count = (results_df['quote_diff'] == 0).sum()
    
    print(f"\n周末数量: {total_weekends}")
    print(f"新方案更优: {better_count} 次 ({better_count/total_weekends*100:.1f}%)")
    print(f"两方案相同: {same_count} 次 ({same_count/total_weekends*100:.1f}%)")
    
    print(f"\n报价差异统计 (pips):")
    print(f"  平均差异: {results_df['quote_diff_pips'].mean():.2f}")
    print(f"  最大差异: {results_df['quote_diff_pips'].max():.2f}")
    print(f"  标准差:   {results_df['quote_diff_pips'].std():.2f}")
    
    total_pnl = results_df['pnl_diff'].sum()
    avg_pnl = results_df['pnl_diff'].mean()
    
    print(f"\nPnL增量 (交易量: {trade_size/1e6:.0f}M USD):")
    print(f"  累计PnL增量: ${total_pnl:,.0f}")
    print(f"  平均每周增量: ${avg_pnl:,.0f}")
    print(f"  年化估算:     ${avg_pnl * 52:,.0f}")
    
    # 显示新方案更优的详细记录
    better_records = results_df[results_df['quote_diff'] > 0]
    if not better_records.empty:
        print(f"\n新方案更优的记录详情:")
        print("-" * 80)
        for _, row in better_records.iterrows():
            print(f"  {row['date']}: 原={row['original_quote']:.4f}@{row['original_max_time']}, "
                  f"新={row['new_quote']:.4f}@{row['new_max_time']}, "
                  f"差={row['quote_diff_pips']:.1f}pips, PnL=${row['pnl_diff']:,.0f}")
    
    # 导出结果
    output_dir = ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"weekend_pricing_bbg_1min_{timestamp}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='详细结果', index=False)
        
        summary = pd.DataFrame({
            '指标': [
                '分析周末数',
                '新方案更优次数',
                '新方案更优比例',
                '平均报价差异(pips)',
                '最大报价差异(pips)',
                '累计PnL增量(USD)',
                '平均每周PnL增量(USD)',
                '年化PnL估算(USD)'
            ],
            '数值': [
                total_weekends,
                better_count,
                f"{better_count/total_weekends*100:.1f}%",
                f"{results_df['quote_diff_pips'].mean():.2f}",
                f"{results_df['quote_diff_pips'].max():.2f}",
                f"${total_pnl:,.0f}",
                f"${avg_pnl:,.0f}",
                f"${avg_pnl * 52:,.0f}"
            ]
        })
        summary.to_excel(writer, sheet_name='统计摘要', index=False)
    
    print(f"\n结果已导出: {output_file}")
    
    # 保存原始数据
    if all_data:
        all_df = pd.concat(all_data, ignore_index=False)
        data_file = output_dir / f"weekend_raw_data_bbg_1min_{timestamp}.csv"
        all_df.to_csv(data_file)
        print(f"原始数据已导出: {data_file}")
    
    return results_df


def main():
    """主函数"""
    try:
        results = run_analysis_with_bbg()
        
        if results is not None:
            print("\n" + "=" * 60)
            print("分析完成!")
            print("=" * 60)
        
    except ImportError as e:
        print(f"\n模块导入错误: {e}")
        print("请确保已安装 blpapi: pip install blpapi")
    except Exception as e:
        print(f"\n运行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
