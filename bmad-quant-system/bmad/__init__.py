"""
BMAD 量化交易系统
================

一个全面的量化交易回测与分析工具箱

模块结构:
- core: 核心回测引擎
- data: 数据源与加载
- strategies: 策略库
- analysis: 绩效分析
- utils: 通用工具

快速开始:
---------
# 方式1：完整回测引擎
from bmad import BacktestEngine, FridayNightStrategy
engine = BacktestEngine(initial_capital=1000000)
engine.add_data('USDCNH', data)
engine.add_strategy(FridayNightStrategy())
results = engine.run()

# 方式2：信号快速回测（适合参数反算）
from bmad import SignalStrategy, ma_cross_signal, DataLoader
data = DataLoader.load('output/USDCNH.csv')
strategy = SignalStrategy.from_function(ma_cross_signal, ma_fast=10, ma_slow=30)
result = strategy.backtest(data)
result.print_summary()

# 参数优化
best_params, best_result = strategy.optimize(data, {
    'ma_fast': [5, 10, 15, 20],
    'ma_slow': [20, 30, 50, 100]
})
"""

__version__ = "2.1.0"
__author__ = "BMAD Quant Team"

# Core
from .core.engine import BacktestEngine
from .core.portfolio import Portfolio, Position, Trade

# Data
from .data.sources.base import BaseDataSource
from .data.sources.csv_source import CSVDataSource
from .data.sources.bloomberg import BloombergDataSource
from .data.loader import DataLoader

# Strategies
from .strategies.base import BaseStrategy, StrategyParameter, Signal
from .strategies.friday_night import FridayNightStrategy
from .strategies.registry import StrategyRegistry
from .strategies.signal_strategy import (
    SignalStrategy,
    SignalBacktestResult,
    ma_cross_signal,
    momentum_signal,
    mean_reversion_signal,
    bollinger_signal,
    rsi_signal
)

# Analysis
from .analysis.performance import PerformanceAnalyzer
from .analysis.metrics import calculate_sharpe, calculate_max_drawdown

__all__ = [
    # Core
    'BacktestEngine', 'Portfolio', 'Position', 'Trade',
    # Data
    'BaseDataSource', 'CSVDataSource', 'BloombergDataSource', 'DataLoader',
    # Strategies
    'BaseStrategy', 'StrategyParameter', 'Signal',
    'FridayNightStrategy', 'StrategyRegistry',
    # Signal Strategy (新增)
    'SignalStrategy', 'SignalBacktestResult',
    'ma_cross_signal', 'momentum_signal', 'mean_reversion_signal',
    'bollinger_signal', 'rsi_signal',
    # Analysis
    'PerformanceAnalyzer', 'calculate_sharpe', 'calculate_max_drawdown',
]
