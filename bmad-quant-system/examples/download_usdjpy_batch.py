#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载 USDJPY 历史数据用于周末报价分析
尝试分周下载更多历史数据
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd


def get_saturdays(start_date: datetime, end_date: datetime) -> list:
    """获取时间范围内所有周六"""
    saturdays = []
    current = start_date
    while current <= end_date:
        if current.weekday() == 5:  # Saturday
            saturdays.append(current.date())
        current += timedelta(days=1)
    return saturdays


def download_usdjpy_batch():
    """批量下载 USDJPY 周末数据"""
    from quant_system.tools.bbg_wrapper import BloombergWrapper
    
    print("=" * 60)
    print("批量下载 USDJPY 周末 Bid/Ask 数据")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("Bloomberg 连接失败")
        return None
    
    symbol = "USDJPY Curncy"
    
    # 尝试获取过去 140 天内的周六数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=140)
    
    saturdays = get_saturdays(start_date, end_date)
    print(f"\n发现 {len(saturdays)} 个周六待下载")
    
    all_data = []
    
    for i, sat in enumerate(saturdays):
        print(f"\n[{i+1}/{len(saturdays)}] 下载 {sat} 数据...")
        
        # 周六 00:00 - 06:00
        sat_start = datetime.combine(sat, datetime.strptime("00:00", "%H:%M").time())
        sat_end = datetime.combine(sat, datetime.strptime("06:00", "%H:%M").time())
        
        try:
            df = bbg.get_bid_ask_bars(
                symbol=symbol,
                start_date=sat_start,
                end_date=sat_end,
                resample="1min"
            )
            
            if df is not None and not df.empty:
                df['saturday'] = str(sat)
                all_data.append(df)
                print(f"  成功: {len(df)} 条数据")
            else:
                print(f"  无数据")
                
        except Exception as e:
            print(f"  错误: {e}")
        
        # 暂停避免请求过快
        time.sleep(1)
    
    bbg.disconnect()
    
    if all_data:
        combined = pd.concat(all_data)
        
        # 保存数据
        output_dir = ROOT / "output"
        output_file = output_dir / f"USDJPY_Curncy_weekend_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        combined.to_excel(output_file)
        print(f"\n合并数据已保存: {output_file.name}")
        print(f"总条数: {len(combined)}")
        
        return combined
    else:
        print("\n无有效数据")
        return None


if __name__ == "__main__":
    download_usdjpy_batch()
