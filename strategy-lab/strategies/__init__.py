"""策略模块"""
from .base import BaseStrategy
from .friday_night import FridayNightStrategy
from .ma_cross import MACrossStrategy

__all__ = ['BaseStrategy', 'FridayNightStrategy', 'MACrossStrategy']
