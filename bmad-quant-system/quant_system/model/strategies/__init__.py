"""策略模块 - 所有策略的注册和管理"""
from .base_strategy import BaseStrategy, StrategyRegistry
from .friday_night import FridayNightStrategy
from .ma_cross import MACrossStrategy
from .momentum import MomentumStrategy

# 注册所有策略
StrategyRegistry.register(FridayNightStrategy)
StrategyRegistry.register(MACrossStrategy)
StrategyRegistry.register(MomentumStrategy)

__all__ = [
    'BaseStrategy',
    'StrategyRegistry',
    'FridayNightStrategy',
    'MACrossStrategy',
    'MomentumStrategy'
]
