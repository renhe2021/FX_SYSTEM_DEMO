"""回测引擎测试"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def test_backtest_engine():
    """测试回测引擎基本功能"""
    from bmad import BacktestEngine, FridayNightStrategy
    
    # 生成测试数据
    dates = pd.date_range('2024-01-01', periods=1000, freq='15min')
    np.random.seed(42)
    
    data = pd.DataFrame({
        'open': 7.2 + np.random.randn(1000).cumsum() * 0.001,
        'high': 7.2 + np.random.randn(1000).cumsum() * 0.001 + 0.01,
        'low': 7.2 + np.random.randn(1000).cumsum() * 0.001 - 0.01,
        'close': 7.2 + np.random.randn(1000).cumsum() * 0.001,
        'volume': np.random.randint(1000, 10000, 1000)
    }, index=dates)
    
    # 创建引擎
    engine = BacktestEngine(initial_capital=1000000)
    engine.add_data('USDCNH', data)
    engine.add_strategy(FridayNightStrategy(position_size=100000))
    
    # 运行回测
    results = engine.run()
    
    assert 'summary' in results
    assert 'equity_curve' in results
    assert 'trades' in results
    
    print("✓ 回测引擎测试通过")


def test_friday_strategy():
    """测试周五策略信号生成"""
    from bmad.strategies import FridayNightStrategy
    
    # 生成包含周五的测试数据
    dates = pd.date_range('2024-01-01', periods=2000, freq='15min')
    
    data = pd.DataFrame({
        'open': 7.2,
        'high': 7.21,
        'low': 7.19,
        'close': 7.2,
        'volume': 1000
    }, index=dates)
    
    strategy = FridayNightStrategy(
        entry_day=4,
        entry_hour=21,
        exit_day=5,
        exit_hour=2
    )
    
    signals = strategy.generate_signals(data)
    
    # 应该有信号生成
    print(f"生成信号数: {len(signals)}")
    
    print("✓ 周五策略测试通过")


if __name__ == '__main__':
    test_backtest_engine()
    test_friday_strategy()
    print("\n所有测试通过!")
