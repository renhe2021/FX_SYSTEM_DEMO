#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号回测示例
演示如何使用 SignalStrategy 进行快速回测和参数优化

使用方法:
    python examples/signal_backtest_demo.py
"""

import sys
import os
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from bmad import (
    DataLoader,
    SignalStrategy,
    ma_cross_signal,
    momentum_signal,
    mean_reversion_signal,
    bollinger_signal,
    rsi_signal
)


def find_latest_data():
    """找到最新的数据文件"""
    output_dir = ROOT / 'output'
    
    # 优先找CSV文件
    csv_files = list(output_dir.glob('*.csv'))
    if csv_files:
        return sorted(csv_files)[-1]
    
    # 其次找Excel文件
    xlsx_files = list(output_dir.glob('*.xlsx'))
    xlsx_files = [f for f in xlsx_files if not f.name.startswith('~$')]
    if xlsx_files:
        return sorted(xlsx_files)[-1]
    
    return None


def demo_basic_backtest():
    """示例1：基础信号回测"""
    print("\n" + "="*60)
    print("示例1：基础信号回测 - 均线交叉策略")
    print("="*60)
    
    # 加载数据
    data_file = find_latest_data()
    if not data_file:
        print("未找到数据文件，请先从Bloomberg下载数据")
        return None
    
    print(f"加载数据: {data_file.name}")
    data = DataLoader.load(str(data_file))
    print(f"数据量: {len(data)} 行")
    print(f"时间范围: {data.index[0]} ~ {data.index[-1]}")
    
    # 创建策略
    strategy = SignalStrategy.from_function(
        ma_cross_signal,
        trade_size=1_000_000,  # 100万美元
        spread_cost=True,      # 考虑点差
        slippage_pips=0.1,     # 0.1 pip滑点
        ma_fast=10,            # 快线周期
        ma_slow=30             # 慢线周期
    )
    
    # 运行回测
    result = strategy.backtest(data)
    
    # 显示结果
    result.print_summary()
    
    # 显示前5笔交易
    if result.trades:
        print("\n前5笔交易:")
        for i, trade in enumerate(result.trades[:5]):
            direction = "买入" if trade['direction'] == 1 else "卖出"
            print(f"  {i+1}. {trade['entry_time']} {direction} @ {trade['entry_price']:.5f} -> "
                  f"{trade['exit_time']} @ {trade['exit_price']:.5f}, "
                  f"PnL: {trade['pnl']:,.0f} ({trade['pnl_pips']:.1f} pips)")
    
    return result


def demo_parameter_optimization():
    """示例2：参数优化"""
    print("\n" + "="*60)
    print("示例2：参数优化 - 寻找最优均线参数")
    print("="*60)
    
    data_file = find_latest_data()
    if not data_file:
        print("未找到数据文件")
        return None
    
    data = DataLoader.load(str(data_file))
    
    # 创建策略
    strategy = SignalStrategy.from_function(
        ma_cross_signal,
        trade_size=1_000_000,
        spread_cost=True
    )
    
    # 定义参数网格
    param_grid = {
        'ma_fast': [5, 10, 15, 20, 30],
        'ma_slow': [20, 30, 50, 80, 100]
    }
    
    # 运行优化
    best_params, best_result = strategy.optimize(
        data, 
        param_grid, 
        metric='total_pnl'
    )
    
    # 显示最优结果
    best_result.print_summary()
    
    # 显示所有参数组合排名
    print("\n参数组合排名（Top 10）:")
    top_results = strategy.optimization_results.sort_values('total_pnl', ascending=False).head(10)
    print(top_results.to_string())
    
    return best_params, best_result


def demo_custom_signal():
    """示例3：自定义信号函数"""
    print("\n" + "="*60)
    print("示例3：自定义信号函数")
    print("="*60)
    
    # 定义自定义信号
    def breakout_signal(data: pd.DataFrame, 
                        lookback: int = 20,
                        threshold_pips: float = 2.0) -> pd.Series:
        """
        突破信号：价格突破N期高/低点时产生信号
        """
        signal = pd.Series(0, index=data.index)
        
        price_col = 'mid' if 'mid' in data.columns else 'close'
        price = data[price_col]
        
        rolling_high = price.rolling(window=lookback).max()
        rolling_low = price.rolling(window=lookback).min()
        threshold = threshold_pips * 0.0001
        
        # 突破高点买入
        signal[price > rolling_high.shift(1) + threshold] = 1
        # 突破低点卖出
        signal[price < rolling_low.shift(1) - threshold] = -1
        
        return signal
    
    data_file = find_latest_data()
    if not data_file:
        print("未找到数据文件")
        return None
    
    data = DataLoader.load(str(data_file))
    
    # 使用自定义信号
    strategy = SignalStrategy.from_function(
        breakout_signal,
        trade_size=1_000_000,
        spread_cost=True,
        lookback=30,
        threshold_pips=1.5
    )
    
    result = strategy.backtest(data)
    result.print_summary()
    
    return result


def demo_compare_strategies():
    """示例4：比较多个策略"""
    print("\n" + "="*60)
    print("示例4：策略对比")
    print("="*60)
    
    data_file = find_latest_data()
    if not data_file:
        print("未找到数据文件")
        return None
    
    data = DataLoader.load(str(data_file))
    
    strategies = {
        'MA(10,30)': (ma_cross_signal, {'ma_fast': 10, 'ma_slow': 30}),
        'MA(5,20)': (ma_cross_signal, {'ma_fast': 5, 'ma_slow': 20}),
        'Momentum(20)': (momentum_signal, {'lookback': 20, 'threshold': 0.0001}),
        'RSI(14)': (rsi_signal, {'period': 14, 'oversold': 30, 'overbought': 70}),
        'Bollinger(20,2)': (bollinger_signal, {'period': 20, 'num_std': 2.0}),
    }
    
    results = {}
    
    for name, (signal_func, params) in strategies.items():
        strategy = SignalStrategy.from_function(
            signal_func,
            trade_size=1_000_000,
            spread_cost=True,
            **params
        )
        result = strategy.backtest(data)
        results[name] = result
    
    # 打印比较表
    print("\n策略对比:")
    print("-" * 80)
    print(f"{'策略':<15} {'交易次数':>10} {'总PnL':>15} {'胜率':>10} {'夏普':>10}")
    print("-" * 80)
    
    for name, result in results.items():
        print(f"{name:<15} {result.num_trades:>10} {result.total_pnl:>15,.0f} "
              f"{result.win_rate*100:>9.1f}% {result.sharpe_ratio:>10.2f}")
    
    print("-" * 80)
    
    return results


def main():
    """主函数"""
    print("\n" + "#"*60)
    print("#  BMAD 信号回测示例")
    print("#"*60)
    
    # 运行示例
    demo_basic_backtest()
    
    # 取消注释运行其他示例
    # demo_parameter_optimization()
    # demo_custom_signal()
    # demo_compare_strategies()


if __name__ == '__main__':
    main()
