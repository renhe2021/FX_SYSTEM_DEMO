#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
周末报价方案对比分析

业务背景：
- 作为做市商，需要给客户报周末的USDCNH卖出价(ASK)
- 原方案：周六凌晨 2:00-6:00 时间窗口内取 max(ASK)
- 新方案：周六凌晨 0:00-6:00 时间窗口内取 max(ASK)
- 每周末交易量：5000万美元

分析目标：
- 对比两种方案的报价差异
- 计算新方案带来的额外收益

数据要求：
- 需要包含周六凌晨 0:00-6:00 的bid/ask数据
- 建议下载周五全天 + 周六凌晨的数据
"""

import sys
import os
from pathlib import Path
from datetime import datetime, time

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np


class WeekendPricingAnalyzer:
    """周末报价分析器"""
    
    def __init__(self, trade_size: float = 50_000_000):
        """
        Args:
            trade_size: 每周末交易量（美元），默认5000万
        """
        self.trade_size = trade_size
        self.data = None
        self.results = None
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """
        加载数据
        
        Args:
            filepath: 数据文件路径（CSV或Excel）
        """
        if filepath.endswith('.csv'):
            self.data = pd.read_csv(filepath, parse_dates=['timestamp'])
        else:
            self.data = pd.read_excel(filepath, parse_dates=['timestamp'])
        
        self.data.set_index('timestamp', inplace=True)
        self.data.sort_index(inplace=True)
        
        print(f"数据加载完成: {len(self.data)} 条记录")
        print(f"时间范围: {self.data.index[0]} ~ {self.data.index[-1]}")
        print(f"列: {list(self.data.columns)}")
        
        # 添加时间属性
        self.data['weekday'] = self.data.index.dayofweek  # 0=周一, 5=周六, 6=周日
        self.data['hour'] = self.data.index.hour
        self.data['date'] = self.data.index.date
        
        return self.data
    
    def analyze(self) -> pd.DataFrame:
        """
        运行分析，对比两种报价方案
        
        Returns:
            包含每周末报价对比的DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据: load_data()")
        
        # 找出所有周六的日期
        saturday_data = self.data[self.data['weekday'] == 5]
        saturdays = saturday_data['date'].unique()
        
        print(f"\n找到 {len(saturdays)} 个周六")
        
        results = []
        
        for sat_date in saturdays:
            # 筛选该周六的数据
            sat_data = self.data[self.data['date'] == sat_date]
            
            # 原方案：2:00-6:00
            original_window = sat_data[(sat_data['hour'] >= 2) & (sat_data['hour'] < 6)]
            
            # 新方案：0:00-6:00
            new_window = sat_data[(sat_data['hour'] >= 0) & (sat_data['hour'] < 6)]
            
            if original_window.empty and new_window.empty:
                print(f"  {sat_date}: 无数据")
                continue
            
            # 计算报价（取ASK最大值）
            original_quote = original_window['ask'].max() if not original_window.empty else np.nan
            new_quote = new_window['ask'].max() if not new_window.empty else np.nan
            
            # 记录最大值出现的时间
            if not original_window.empty:
                original_max_time = original_window['ask'].idxmax()
            else:
                original_max_time = None
                
            if not new_window.empty:
                new_max_time = new_window['ask'].idxmax()
            else:
                new_max_time = None
            
            # 计算差异
            if pd.notna(original_quote) and pd.notna(new_quote):
                quote_diff = new_quote - original_quote
                pnl_diff = quote_diff * self.trade_size
            else:
                quote_diff = np.nan
                pnl_diff = np.nan
            
            results.append({
                'date': sat_date,
                'weekday': '周六',
                'original_quote': original_quote,
                'original_max_time': original_max_time,
                'new_quote': new_quote,
                'new_max_time': new_max_time,
                'quote_diff': quote_diff,
                'quote_diff_pips': quote_diff * 10000 if pd.notna(quote_diff) else np.nan,
                'pnl_diff': pnl_diff
            })
        
        self.results = pd.DataFrame(results)
        
        return self.results
    
    def print_summary(self):
        """打印分析摘要"""
        if self.results is None or self.results.empty:
            print("无分析结果")
            return
        
        print("\n" + "="*80)
        print("周末报价方案对比分析")
        print("="*80)
        
        print(f"\n交易参数:")
        print(f"  每周末交易量: ${self.trade_size:,.0f}")
        
        print(f"\n方案说明:")
        print(f"  原方案: 周六 02:00-06:00 取 max(ASK)")
        print(f"  新方案: 周六 00:00-06:00 取 max(ASK)")
        
        # 统计
        valid_results = self.results.dropna(subset=['quote_diff'])
        
        print(f"\n统计结果 (共 {len(valid_results)} 个周末):")
        print("-"*80)
        
        total_pnl_diff = valid_results['pnl_diff'].sum()
        avg_pnl_diff = valid_results['pnl_diff'].mean()
        avg_quote_diff_pips = valid_results['quote_diff_pips'].mean()
        max_quote_diff_pips = valid_results['quote_diff_pips'].max()
        
        # 新方案更优的次数
        better_count = (valid_results['quote_diff'] > 0).sum()
        same_count = (valid_results['quote_diff'] == 0).sum()
        
        print(f"  新方案更优次数: {better_count} / {len(valid_results)} ({better_count/len(valid_results)*100:.1f}%)")
        print(f"  两方案相同次数: {same_count} / {len(valid_results)} ({same_count/len(valid_results)*100:.1f}%)")
        print(f"  平均报价差异: {avg_quote_diff_pips:.2f} pips")
        print(f"  最大报价差异: {max_quote_diff_pips:.2f} pips")
        print(f"  平均每周PnL增量: ${avg_pnl_diff:,.2f}")
        print(f"  累计PnL增量: ${total_pnl_diff:,.2f}")
        
        # 年化估算
        weeks_in_year = 52
        if len(valid_results) > 0:
            annualized_pnl = avg_pnl_diff * weeks_in_year
            print(f"\n  年化PnL增量估算: ${annualized_pnl:,.2f}")
        
        print("="*80)
    
    def print_details(self, top_n: int = 10):
        """打印详细结果"""
        if self.results is None or self.results.empty:
            print("无分析结果")
            return
        
        print(f"\n详细结果 (前 {top_n} 个周末):")
        print("-"*100)
        print(f"{'日期':<12} {'原方案报价':>12} {'原方案时间':>20} {'新方案报价':>12} {'新方案时间':>20} {'差异(pips)':>12} {'PnL差异':>15}")
        print("-"*100)
        
        for _, row in self.results.head(top_n).iterrows():
            date_str = str(row['date'])
            orig_quote = f"{row['original_quote']:.5f}" if pd.notna(row['original_quote']) else "N/A"
            new_quote = f"{row['new_quote']:.5f}" if pd.notna(row['new_quote']) else "N/A"
            
            orig_time = str(row['original_max_time'])[11:19] if row['original_max_time'] else "N/A"
            new_time = str(row['new_max_time'])[11:19] if row['new_max_time'] else "N/A"
            
            diff_pips = f"{row['quote_diff_pips']:.2f}" if pd.notna(row['quote_diff_pips']) else "N/A"
            pnl_diff = f"${row['pnl_diff']:,.0f}" if pd.notna(row['pnl_diff']) else "N/A"
            
            print(f"{date_str:<12} {orig_quote:>12} {orig_time:>20} {new_quote:>12} {new_time:>20} {diff_pips:>12} {pnl_diff:>15}")
        
        print("-"*100)
    
    def export_to_excel(self, filepath: str):
        """导出结果到Excel"""
        if self.results is None or self.results.empty:
            print("无分析结果")
            return
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 详细结果
            self.results.to_excel(writer, sheet_name='详细结果', index=False)
            
            # 摘要统计
            valid_results = self.results.dropna(subset=['quote_diff'])
            summary = pd.DataFrame([{
                '总周末数': len(valid_results),
                '新方案更优次数': (valid_results['quote_diff'] > 0).sum(),
                '平均报价差异(pips)': valid_results['quote_diff_pips'].mean(),
                '最大报价差异(pips)': valid_results['quote_diff_pips'].max(),
                '累计PnL增量': valid_results['pnl_diff'].sum(),
                '平均每周PnL增量': valid_results['pnl_diff'].mean(),
                '交易量': self.trade_size
            }])
            summary.T.to_excel(writer, sheet_name='摘要')
        
        print(f"结果已导出: {filepath}")


def main():
    """主函数"""
    print("\n" + "#"*60)
    print("#  周末报价方案对比分析")
    print("#"*60)
    
    # 查找数据文件
    output_dir = ROOT / 'output'
    
    # 优先找包含周六凌晨数据的文件
    # 这里假设文件名包含时间范围信息
    data_files = list(output_dir.glob('USDCNH*.csv')) + list(output_dir.glob('USDCNH*.xlsx'))
    data_files = [f for f in data_files if not f.name.startswith('~$')]
    
    if not data_files:
        print("\n错误: 未找到数据文件")
        print("请从Bloomberg下载包含周六凌晨 0:00-6:00 的USDCNH bid/ask数据")
        print(f"数据目录: {output_dir}")
        return
    
    # 使用最新的文件
    data_file = sorted(data_files)[-1]
    print(f"\n使用数据文件: {data_file.name}")
    
    # 创建分析器
    analyzer = WeekendPricingAnalyzer(trade_size=50_000_000)
    
    # 加载数据
    analyzer.load_data(str(data_file))
    
    # 检查是否有周六凌晨的数据
    saturday_early = analyzer.data[
        (analyzer.data['weekday'] == 5) & 
        (analyzer.data['hour'] < 6)
    ]
    
    if saturday_early.empty:
        print("\n警告: 数据中没有周六凌晨 0:00-6:00 的数据！")
        print("请下载包含该时间段的数据后再运行分析。")
        print("\n当前数据的时间分布:")
        print(analyzer.data.groupby(['weekday', 'hour']).size().head(20))
        return
    
    # 运行分析
    analyzer.analyze()
    
    # 打印结果
    analyzer.print_summary()
    analyzer.print_details(top_n=10)
    
    # 导出结果
    export_path = output_dir / f'weekend_pricing_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    analyzer.export_to_excel(str(export_path))


if __name__ == '__main__':
    main()
