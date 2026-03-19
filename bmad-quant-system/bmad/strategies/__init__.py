"""策略库"""
from .base import BaseStrategy, StrategyParameter, Signal
from .registry import StrategyRegistry
from .friday_night import FridayNightStrategy
from .signal_strategy import (
    SignalStrategy, 
    SignalBacktestResult,
    ma_cross_signal,
    momentum_signal,
    mean_reversion_signal,
    bollinger_signal,
    rsi_signal
)

# 自动注册内置策略
StrategyRegistry.register(FridayNightStrategy)

__all__ = [
    'BaseStrategy', 'StrategyParameter', 'Signal',
    'StrategyRegistry', 'FridayNightStrategy',
    # 信号策略模块
    'SignalStrategy', 'SignalBacktestResult',
    'ma_cross_signal', 'momentum_signal', 'mean_reversion_signal',
    'bollinger_signal', 'rsi_signal'
]
