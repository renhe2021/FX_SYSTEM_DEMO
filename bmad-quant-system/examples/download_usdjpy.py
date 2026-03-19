#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载 USDJPY 数据用于周末报价分析
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd


def download_usdjpy():
    """下载 USDJPY 数据"""
    from quant_system.tools.bbg_wrapper import BloombergWrapper
    
    print("=" * 60)
    print("下载 USDJPY Bid/Ask 数据")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("Bloomberg 连接失败")
        return None
    
    symbol = "USDJPY Curncy"
    
    # 尝试下载最近一段时间的数据
    end_date = datetime.now()
    
    # 尝试下载整个交易周的数据（周一到周五）
    # 使用 1 分钟 bar
    start_date = end_date - timedelta(days=7)
    
    print(f"\n下载参数:")
    print(f"  品种: {symbol}")
    print(f"  时间: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"  间隔: 1分钟")
    
    # 获取 bid/ask bar 数据
    df = bbg.get_bid_ask_bars(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        resample="1min"
    )
    
    bbg.disconnect()
    
    if df is not None and not df.empty:
        print(f"\n数据下载成功: {len(df)} 条")
        print(f"时间范围: {df.index.min()} ~ {df.index.max()}")
        
        # 查看数据分布
        df['weekday'] = df.index.dayofweek
        print(f"\n按星期分布:")
        for d in sorted(df['weekday'].unique()):
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            print(f"  {day_names[d]}: {len(df[df['weekday']==d])} 条")
        
        # 保存数据
        output_dir = ROOT / "output"
        output_file = output_dir / f"USDJPY_Curncy_bidask_1min_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # 删除辅助列
        df_save = df.drop(columns=['weekday'], errors='ignore')
        df_save.to_excel(output_file)
        print(f"\n数据已保存: {output_file.name}")
        
        return df
    else:
        print("\n数据下载失败或为空")
        return None


if __name__ == "__main__":
    download_usdjpy()
