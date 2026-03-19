#!/usr/bin/env python
"""运行回测脚本

使用示例:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --config configs/friday_local.yaml
"""
import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from bmad import BacktestEngine, FridayNightStrategy, DataLoader


def main():
    parser = argparse.ArgumentParser(description='运行回测')
    parser.add_argument('--data', default='usdcnh_intraday.csv', help='数据文件')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金')
    parser.add_argument('--strategy', default='FridayNightStrategy', help='策略名称')
    args = parser.parse_args()
    
    print("=" * 60)
    print("BMAD 回测系统")
    print("=" * 60)
    
    # 加载数据
    data_path = ROOT / args.data
    if not data_path.exists():
        data_path = ROOT / 'data' / 'raw' / args.data
    
    print(f"\n[1] 加载数据: {data_path}")
    data = DataLoader.load_csv(str(data_path))
    print(f"    数据量: {len(data)} 行")
    print(f"    时间范围: {data.index[0]} ~ {data.index[-1]}")
    
    # 创建策略
    print(f"\n[2] 创建策略: {args.strategy}")
    strategy = FridayNightStrategy(
        entry_day=4,
        entry_hour=21,
        exit_day=5,
        exit_hour=2,
        direction='long',
        position_size=100000
    )
    
    # 创建回测引擎
    print(f"\n[3] 初始化回测引擎")
    print(f"    初始资金: {args.capital:,.0f}")
    engine = BacktestEngine(
        initial_capital=args.capital,
        commission_rate=0.00005,
        slippage=0.0001
    )
    
    engine.add_data('USDCNH', data)
    engine.add_strategy(strategy)
    
    # 运行回测
    print(f"\n[4] 运行回测...")
    results = engine.run()
    
    # 打印结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    for key, value in results['summary'].items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("回测完成!")
    

if __name__ == '__main__':
    main()
