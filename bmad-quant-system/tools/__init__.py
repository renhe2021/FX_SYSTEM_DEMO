"""独立工具箱

这里放置各种独立的小工具，可以单独使用，不依赖完整的回测系统

工具列表:
- data_explorer: 数据探索与可视化
- fx_calculator: 外汇计算器
- spread_analyzer: 价差分析
- quick_plot: 快速绘图
"""

from .data_explorer import DataExplorer
from .fx_calculator import FXCalculator
from .spread_analyzer import SpreadAnalyzer
from .quick_plot import quick_plot, plot_ohlc, plot_returns

__all__ = [
    'DataExplorer', 'FXCalculator', 'SpreadAnalyzer',
    'quick_plot', 'plot_ohlc', 'plot_returns'
]
