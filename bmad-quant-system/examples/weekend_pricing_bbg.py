#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
周末报价方案对比分析 - Bloomberg API 版本

自动从Bloomberg下载USDCNH的bid/ask数据，分析两种报价方案的差异：
- 原方案: 周六 02:00-06:00 取 max(ASK)
- 新方案: 周六 00:00-06:00 取 max(ASK)

使用方法:
    python examples/weekend_pricing_bbg.py

依赖:
    - Bloomberg Terminal 运行中
    - blpapi 已安装
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


class WeekendPricingBBG:
    """
    周末报价分析器 - Bloomberg API版
    
    自动下载数据并分析报价差异
    """
    
    def __init__(self, 
                 symbol: str = "USDCNH Curncy",
                 trade_size: float = 50_000_000,
                 resample: str = "1s"):
        """
        Args:
            symbol: Bloomberg代码
            trade_size: 每周末交易量（美元）
            resample: 数据重采样频率
        """
        self.symbol = symbol
        self.trade_size = trade_size
        self.resample = resample
        self.bbg = None
        self.data = None
        self.results = None
    
    def connect_bbg(self) -> bool:
        """连接Bloomberg"""
        try:
            from quant_system.tools.bbg_wrapper import BloombergWrapper
            self.bbg = BloombergWrapper()
            return self.bbg.connect()
        except ImportError as e:
            print(f"导入失败: {e}")
            print("请确保在 bmad-quant-system 目录下运行")
            return False
        except Exception as e:
            print(f"Bloomberg连接失败: {e}")
            return False
    
    def disconnect_bbg(self):
        """断开Bloomberg"""
        if self.bbg:
            self.bbg.disconnect()
    
    def download_weekend_data(self, 
                               weeks_back: int = 52,
                               end_date: datetime = None) -> pd.DataFrame:
        """
        下载周末数据
        
        Args:
            weeks_back: 向前多少周
            end_date: 结束日期
            
        Returns:
            包含所有周六凌晨数据的DataFrame
        """
        if self.bbg is None or not self.bbg.is_connected:
            if not self.connect_bbg():
                return None
        
        if end_date is None:
            end_date = datetime.now()
        
        # 找到所有周六
        saturdays = self._find_saturdays(end_date, weeks_back)
        
        print(f"\n准备下载 {len(saturdays)} 个周六的数据...")
        print(f"时间范围: {saturdays[-1]} ~ {saturdays[0]}")
        print(f"数据频率: {self.resample}")
        
        all_data = []
        
        for i, sat_date in enumerate(saturdays):
            # 每个周六下载 00:00 - 06:00 的数据
            start_dt = datetime.combine(sat_date, datetime.min.time())  # 00:00
            end_dt = start_dt + timedelta(hours=6)  # 06:00
            
            print(f"\n[{i+1}/{len(saturdays)}] 下载 {sat_date} 00:00-06:00...")
            
            try:
                df = self.bbg.get_bid_ask_bars(
                    symbol=self.symbol,
                    start_date=start_dt,
                    end_date=end_dt,
                    hours_back=6,
                    resample=self.resample
                )
                
                if df is not None and not df.empty:
                    df['weekend_date'] = sat_date
                    all_data.append(df)
                    print(f"    获取 {len(df)} 条数据")
                else:
                    print(f"    无数据")
                    
            except Exception as e:
                print(f"    下载失败: {e}")
        
        if not all_data:
            print("\n未获取到任何数据！")
            return None
        
        # 合并所有数据
        self.data = pd.concat(all_data)
        self.data.sort_index(inplace=True)
        
        print(f"\n数据下载完成: 共 {len(self.data)} 条记录")
        
        return self.data
    
    def _find_saturdays(self, end_date: datetime, weeks_back: int) -> List:
        """找到过去N周的所有周六日期"""
        saturdays = []
        current = end_date
        
        # 找到最近的周六
        while current.weekday() != 5:  # 5 = Saturday
            current -= timedelta(days=1)
        
        # 收集所有周六
        for _ in range(weeks_back):
            saturdays.append(current.date())
            current -= timedelta(days=7)
        
        return saturdays
    
    def analyze(self) -> pd.DataFrame:
        """
        分析两种报价方案的差异
        """
        if self.data is None or self.data.empty:
            print("无数据，请先下载数据")
            return None
        
        # 添加时间属性
        self.data['hour'] = self.data.index.hour
        
        # 按周末分组分析
        weekend_dates = self.data['weekend_date'].unique()
        
        results = []
        
        for weekend in weekend_dates:
            weekend_data = self.data[self.data['weekend_date'] == weekend]
            
            # 原方案：2:00-6:00
            original_window = weekend_data[(weekend_data['hour'] >= 2) & (weekend_data['hour'] < 6)]
            
            # 新方案：0:00-6:00
            new_window = weekend_data  # 全部数据就是 0:00-6:00
            
            if original_window.empty and new_window.empty:
                continue
            
            # 取ASK最大值
            original_quote = original_window['ask'].max() if not original_window.empty else np.nan
            new_quote = new_window['ask'].max() if not new_window.empty else np.nan
            
            # 记录最大值时间
            original_max_time = original_window['ask'].idxmax() if not original_window.empty and pd.notna(original_quote) else None
            new_max_time = new_window['ask'].idxmax() if not new_window.empty and pd.notna(new_quote) else None
            
            # 计算差异
            if pd.notna(original_quote) and pd.notna(new_quote):
                quote_diff = new_quote - original_quote
                pnl_diff = quote_diff * self.trade_size
            else:
                quote_diff = np.nan
                pnl_diff = np.nan
            
            # 检查最大值是否出现在0:00-2:00
            found_in_early_morning = False
            if new_max_time is not None:
                max_hour = new_max_time.hour
                found_in_early_morning = max_hour < 2
            
            results.append({
                'date': weekend,
                'original_quote': original_quote,
                'original_max_time': original_max_time,
                'new_quote': new_quote,
                'new_max_time': new_max_time,
                'quote_diff': quote_diff,
                'quote_diff_pips': quote_diff * 10000 if pd.notna(quote_diff) else np.nan,
                'pnl_diff': pnl_diff,
                'found_in_00_02': found_in_early_morning
            })
        
        self.results = pd.DataFrame(results)
        return self.results
    
    def print_summary(self):
        """打印分析摘要"""
        if self.results is None or self.results.empty:
            print("无分析结果")
            return
        
        valid_results = self.results.dropna(subset=['quote_diff'])
        
        print("\n" + "="*80)
        print("周末报价方案对比分析 - Bloomberg实时数据")
        print("="*80)
        
        print(f"\n数据来源: {self.symbol}")
        print(f"交易量: ${self.trade_size:,.0f} / 周末")
        print(f"数据频率: {self.resample}")
        
        print(f"\n方案对比:")
        print(f"  原方案: 周六 02:00-06:00 取 max(ASK)")
        print(f"  新方案: 周六 00:00-06:00 取 max(ASK)")
        
        print(f"\n统计结果 (共 {len(valid_results)} 个周末):")
        print("-"*80)
        
        if len(valid_results) == 0:
            print("  无有效数据")
            return
        
        total_pnl_diff = valid_results['pnl_diff'].sum()
        avg_pnl_diff = valid_results['pnl_diff'].mean()
        avg_quote_diff_pips = valid_results['quote_diff_pips'].mean()
        max_quote_diff_pips = valid_results['quote_diff_pips'].max()
        
        better_count = (valid_results['quote_diff'] > 0.00001).sum()  # 容忍微小误差
        same_count = (valid_results['quote_diff'].abs() < 0.00001).sum()
        early_morning_count = valid_results['found_in_00_02'].sum()
        
        print(f"  新方案更优次数: {better_count} / {len(valid_results)} ({better_count/len(valid_results)*100:.1f}%)")
        print(f"  两方案相同次数: {same_count} / {len(valid_results)} ({same_count/len(valid_results)*100:.1f}%)")
        print(f"  最大值在00:00-02:00的次数: {early_morning_count} / {len(valid_results)} ({early_morning_count/len(valid_results)*100:.1f}%)")
        print(f"\n  平均报价差异: {avg_quote_diff_pips:.2f} pips")
        print(f"  最大报价差异: {max_quote_diff_pips:.2f} pips")
        print(f"  平均每周PnL增量: ${avg_pnl_diff:,.2f}")
        print(f"  累计PnL增量: ${total_pnl_diff:,.2f}")
        
        # 年化估算
        weeks_in_year = 52
        annualized_pnl = avg_pnl_diff * weeks_in_year
        print(f"\n  年化PnL增量估算: ${annualized_pnl:,.2f}")
        
        print("="*80)
    
    def print_details(self, show_all: bool = False, top_n: int = 10):
        """打印详细结果"""
        if self.results is None or self.results.empty:
            print("无分析结果")
            return
        
        # 只显示新方案更优的情况
        if not show_all:
            better_results = self.results[self.results['quote_diff'] > 0.00001]
            if better_results.empty:
                print("\n没有新方案更优的周末")
                return
            display_df = better_results.head(top_n)
            print(f"\n新方案更优的周末 (共 {len(better_results)} 个):")
        else:
            display_df = self.results.head(top_n)
            print(f"\n所有周末结果 (前 {top_n} 个):")
        
        print("-"*120)
        print(f"{'日期':<12} {'原方案报价':>12} {'原方案时间':>12} {'新方案报价':>12} {'新方案时间':>12} {'差异(pips)':>12} {'PnL增量':>15}")
        print("-"*120)
        
        for _, row in display_df.iterrows():
            date_str = str(row['date'])
            orig_quote = f"{row['original_quote']:.5f}" if pd.notna(row['original_quote']) else "N/A"
            new_quote = f"{row['new_quote']:.5f}" if pd.notna(row['new_quote']) else "N/A"
            
            orig_time = str(row['original_max_time'])[11:19] if row['original_max_time'] else "N/A"
            new_time = str(row['new_max_time'])[11:19] if row['new_max_time'] else "N/A"
            
            diff_pips = f"{row['quote_diff_pips']:.2f}" if pd.notna(row['quote_diff_pips']) else "N/A"
            pnl_diff = f"${row['pnl_diff']:,.0f}" if pd.notna(row['pnl_diff']) else "N/A"
            
            print(f"{date_str:<12} {orig_quote:>12} {orig_time:>12} {new_quote:>12} {new_time:>12} {diff_pips:>12} {pnl_diff:>15}")
        
        print("-"*120)
    
    def export_results(self, filepath: str = None):
        """导出结果到Excel"""
        if self.results is None or self.results.empty:
            print("无结果可导出")
            return
        
        if filepath is None:
            output_dir = ROOT / 'output'
            filepath = output_dir / f'weekend_pricing_bbg_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            self.results.to_excel(writer, sheet_name='详细结果', index=False)
            
            # 摘要
            valid = self.results.dropna(subset=['quote_diff'])
            if len(valid) > 0:
                summary = pd.DataFrame([{
                    '分析周末数': len(valid),
                    '新方案更优次数': (valid['quote_diff'] > 0).sum(),
                    '平均报价差异(pips)': valid['quote_diff_pips'].mean(),
                    '最大报价差异(pips)': valid['quote_diff_pips'].max(),
                    '累计PnL增量': valid['pnl_diff'].sum(),
                    '平均每周PnL增量': valid['pnl_diff'].mean(),
                    '年化PnL估算': valid['pnl_diff'].mean() * 52,
                    '交易量': self.trade_size,
                    '数据来源': self.symbol
                }])
                summary.T.to_excel(writer, sheet_name='摘要')
            
            # 原始数据（如果不太大）
            if self.data is not None and len(self.data) < 100000:
                self.data.to_excel(writer, sheet_name='原始数据')
        
        print(f"结果已导出: {filepath}")
    
    def run(self, weeks_back: int = 52) -> pd.DataFrame:
        """
        一键运行：连接 -> 下载 -> 分析 -> 输出
        
        Args:
            weeks_back: 分析过去多少周
        """
        print("\n" + "#"*60)
        print("#  周末报价方案对比分析")
        print("#  数据来源: Bloomberg API")
        print("#"*60)
        
        # 连接Bloomberg
        print("\n[1] 连接Bloomberg...")
        if not self.connect_bbg():
            print("Bloomberg连接失败，请确保Terminal已启动")
            return None
        
        try:
            # 下载数据
            print("\n[2] 下载周末数据...")
            self.download_weekend_data(weeks_back=weeks_back)
            
            if self.data is None or self.data.empty:
                print("未获取到数据")
                return None
            
            # 分析
            print("\n[3] 分析报价差异...")
            self.analyze()
            
            # 输出结果
            print("\n[4] 分析结果:")
            self.print_summary()
            self.print_details(show_all=False)
            
            # 导出
            print("\n[5] 导出结果...")
            self.export_results()
            
            return self.results
            
        finally:
            # 断开连接
            self.disconnect_bbg()


def main():
    """主函数"""
    analyzer = WeekendPricingBBG(
        symbol="USDCNH Curncy",
        trade_size=50_000_000,  # 5000万美元
        resample="1s"          # 秒级数据
    )
    
    # 分析过去52周（约1年）
    analyzer.run(weeks_back=52)


if __name__ == '__main__':
    main()
